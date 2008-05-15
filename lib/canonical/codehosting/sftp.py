# Copyright 2008 Canonical Ltd.  All rights reserved.

"""An SFTP server that backs on to a special kind of Bazaar Transport.

The Bazaar Transport is special in two ways:

 1. It implements two methods `writeChunk` and `local_realPath` (see the
    `FatLocalTransport` class for a description of these)
 2. Every transport method returns Deferreds and does not block.

We call such a transport a "Twisted Transport".
"""

__all__ = ['AvatarToSFTPAdapter', 'TransportSFTPServer']
__metaclass__ = type


import errno
import os

from bzrlib import errors as bzr_errors
from bzrlib import osutils, urlutils
from bzrlib.transport.local import LocalTransport
from twisted.conch.ssh import filetransfer
from twisted.conch.interfaces import ISFTPFile, ISFTPServer
from twisted.internet import defer
from zope.interface import implements

from canonical.codehosting.transport import (
    AsyncLaunchpadTransport, LaunchpadServer)
from canonical.config import config


class FileIsADirectory(bzr_errors.PathError):
    """Raised when writeChunk is called on a directory.

    This exists mainly to be translated into the appropriate SFTP error.
    """

    _fmt = 'File is a directory: %(path)r%(extra)s'


class FatLocalTransport(LocalTransport):
    """A Bazaar transport that also implements writeChunk and local_realPath.

    We need these so that we can implement SFTP over a Bazaar transport.
    """

    def writeChunk(self, name, offset, data):
        """Write a chunk of data to file `name` at `offset`."""
        abspath = self._abspath(name)
        osutils.check_legal_path(abspath)
        try:
            chunk_file = os.open(abspath, os.O_CREAT | os.O_WRONLY)
        except OSError, e:
            if e.errno != errno.EISDIR:
                raise
            raise FileIsADirectory(name)
        os.lseek(chunk_file, offset, 0)
        os.write(chunk_file, data)
        os.close(chunk_file)

    def local_realPath(self, path):
        """Return the absolute path to `path`."""
        abspath = self._abspath(path)
        return os.path.realpath(abspath)


def with_sftp_error(func):
    """Decorator used to translate Bazaar errors into SFTP errors.

    This assumes that the function being decorated returns a Deferred.

    See `TransportSFTPServer.translateError` for the details of the
    translation.
    """
    def decorator(*args, **kwargs):
        deferred = func(*args, **kwargs)
        return deferred.addErrback(TransportSFTPServer.translateError,
                                   func.__name__)
    return decorator


class TransportSFTPFile:
    """An implementation of `ISFTPFile` that backs onto a Bazaar transport.

    The transport must be a Twisted Transport.
    """

    implements(ISFTPFile)

    def __init__(self, transport, name, flags):
        self.name = name
        self._flags = flags
        self.transport = transport
        self._should_create = TransportSFTPFile._shouldCreate(flags)
        self._written = False

    def _append(self):
        """Is this file opened append?"""
        return bool(self._flags & filetransfer.FXF_APPEND)

    def _writable(self):
        """Is this file opened writable?"""
        # The Twisted VFS adapter creates a file when any of these flags are
        # set. It's possible that we only need to check for FXF_CREAT.
        write_mask = (
            filetransfer.FXF_WRITE | filetransfer.FXF_APPEND |
            filetransfer.FXF_CREAT)
        return bool(self._flags & write_mask)

    @staticmethod
    def _shouldCreate(flags):
        create_mask = (
            filetransfer.FXF_WRITE | filetransfer.FXF_APPEND |
            filetransfer.FXF_CREAT)
        return bool(flags & create_mask)

    @with_sftp_error
    def writeChunk(self, offset, data):
        """See `ISFTPFile`."""
        if not self._writable():
            raise filetransfer.SFTPError(
                filetransfer.FX_PERMISSION_DENIED,
                "%r was opened read-only." % self.name)
        self._written = True
        if self._append():
            return self.transport.append_bytes(self.name, data)
        else:
            return self.transport.writeChunk(self.name, offset, data)

    @with_sftp_error
    def readChunk(self, offset, length):
        """See `ISFTPFile`."""
        deferred = self.transport.readv(self.name, [(offset, length)])
        def get_first_chunk(read_things):
            return read_things.next()[1]
        deferred.addCallback(get_first_chunk)
        return deferred.addErrback(self._check_for_eof)

    def _check_for_eof(self, failure):
        failure.trap(bzr_errors.ShortReadvError)
        # XXX: JonathanLange 2008-05-13: We might be discarding data here. But
        # even if we weren't, current versions of Bazaar wouldn't actually use
        # it. If Bazaar changes to include the returned data in a
        # ShortReadvError, we should consider changing this method.
        return ''

    def setAttrs(self, attrs):
        """See `ISFTPFile`.

        The Transport interface does not allow setting any attributes.
        """
        # XXX 2008-05-09 JonathanLange: This should at least raise an error,
        # not do nothing silently.
        pass

    @with_sftp_error
    def getAttrs(self):
        """See `ISFTPFile`."""
        deferred = self.transport.stat(self.name)
        def translate_stat(stat_val):
            return {
                'size': stat_val.st_size,
                'uid': stat_val.st_uid,
                'gid': stat_val.st_gid,
                'permissions': stat_val.st_mode,
                'atime': stat_val.st_atime,
                'mtime': stat_val.st_mtime,
            }
        return deferred.addCallback(translate_stat)

    def close(self):
        """See `ISFTPFile`."""
        if self._written or not self._should_create:
            return defer.succeed(None)

        deferred = self.transport.has(self.name)
        def maybe_create_file(already_exists):
            if not already_exists:
                return self.transport.put_bytes(self.name, '')
        return deferred.addCallback(maybe_create_file)


def _get_transport_for_dir(directory):
    url = urlutils.local_path_to_url(directory)
    return FatLocalTransport(url)


def avatar_to_sftp_server(avatar):
    user_id = avatar.lpid
    authserver = avatar._launchpad
    hosted_transport = _get_transport_for_dir(
        config.codehosting.branches_root)
    mirror_transport = _get_transport_for_dir(
        config.supermirror.branchesdest)
    server = LaunchpadServer(
        authserver, user_id, hosted_transport, mirror_transport)
    server.setUp()
    transport = AsyncLaunchpadTransport(server, server.get_url())
    return TransportSFTPServer(transport)


class TransportSFTPServer:
    """An implementation of `ISFTPServer` that backs onto a Bazaar transport.

    The transport must be a Twisted Transport.
    """

    implements(ISFTPServer)

    def __init__(self, transport):
        self.transport = transport

    def extendedRequest(self, extendedName, extendedData):
        """See `ISFTPServer`."""
        raise NotImplementedError

    def makeLink(self, src, dest):
        """See `ISFTPServer`."""
        raise NotImplementedError()

    @with_sftp_error
    def openDirectory(self, path):
        """See `ISFTPServer`."""
        class DirectoryListing:
            """Class to satisfy openDirectory return interface.

            openDirectory returns an iterator -- with a `close` method.  Hence
            this class.
            """

            def __init__(self, files):
                self.position = (
                    (filename, filename, {}) for filename in files)

            def __iter__(self):
                return self

            def next(self):
                return self.position.next()

            def close(self):
                # I can't believe we had to implement a whole class just to
                # have this do-nothing method (abentley).
                pass

        deferred = self.transport.list_dir(path)
        return deferred.addCallback(DirectoryListing)

    def openFile(self, path, flags, attrs):
        """See `ISFTPServer`."""
        return TransportSFTPFile(self.transport, path, flags)

    def readLink(self, path):
        """See `ISFTPServer`."""
        raise NotImplementedError()

    def realPath(self, relpath):
        """See `ISFTPServer`."""
        return self.transport.local_realPath(relpath)

    def setAttrs(self, path, attrs):
        """See `ISFTPServer`.

        This just delegates to TransportSFTPFile's implementation.
        """
        return self.openFile(path, 0, {}).setAttrs(attrs)

    def getAttrs(self, path, followLinks):
        """See `ISFTPServer`.

        This just delegates to TransportSFTPFile's implementation.
        """
        return self.openFile(path, 0, {}).getAttrs()

    def gotVersion(self, otherVersion, extensionData):
        """See `ISFTPServer`."""
        return {}

    @with_sftp_error
    def makeDirectory(self, path, attrs):
        """See `ISFTPServer`."""
        return self.transport.mkdir(path, attrs['permissions'])

    @with_sftp_error
    def removeDirectory(self, path):
        """See `ISFTPServer`."""
        return self.transport.rmdir(path)

    @with_sftp_error
    def removeFile(self, path):
        """See `ISFTPServer`."""
        return self.transport.delete(path)

    @with_sftp_error
    def renameFile(self, oldpath, newpath):
        """See `ISFTPServer`."""
        return self.transport.rename(oldpath, newpath)

    @staticmethod
    def translateError(failure, func_name):
        """Translate Bazaar errors to `filetransfer.SFTPError` instances."""
        types_to_codes = {
            bzr_errors.PermissionDenied: filetransfer.FX_PERMISSION_DENIED,
            bzr_errors.TransportNotPossible:
                filetransfer.FX_PERMISSION_DENIED,
            bzr_errors.NoSuchFile: filetransfer.FX_NO_SUCH_FILE,
            bzr_errors.FileExists: filetransfer.FX_FILE_ALREADY_EXISTS,
            bzr_errors.DirectoryNotEmpty: filetransfer.FX_FAILURE,
            FileIsADirectory: filetransfer.FX_FILE_IS_A_DIRECTORY,
            }
        # Bazaar expects makeDirectory to fail with exactly the string "mkdir
        # failed".
        names_to_messages = {
            'makeDirectory': 'mkdir failed',
            }
        try:
            sftp_code = types_to_codes[failure.type]
        except KeyError:
            failure.raiseException()
        message = names_to_messages.get(func_name, failure.getErrorMessage())
        raise filetransfer.SFTPError(sftp_code, message)
