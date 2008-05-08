# Copyright 2008 Canonical Ltd.  All rights reserved.

__all__ = ['AvatarToSFTPAdapter', 'TransportSFTPServer']
__metaclass__ = type


import os.path

from bzrlib import errors as bzr_errors
from bzrlib import osutils, urlutils
from bzrlib.transport.local import LocalTransport
from twisted.conch.ssh import filetransfer
from twisted.conch.interfaces import ISFTPServer
from zope.interface import implements

from canonical.codehosting.transport import (
    AsyncLaunchpadTransport, LaunchpadServer)
from canonical.config import config


class FatLocalTransport(LocalTransport):

    def writeChunk(self, name, offset, data):
        abspath = self._abspath(name)
        osutils.check_legal_path(abspath)
        chunk_file = open(abspath, 'w')
        chunk_file.seek(offset)
        chunk_file.write(data)

    def local_realPath(self, path):
        abspath = self._abspath(path)
        return os.path.realpath(abspath)


class SFTPServerFile:

    def __init__(self, transport, name):
        self.name = name
        self.transport = transport

    def writeChunk(self, offset, data):
        return self.transport.writeChunk(self.name, offset, data)

    def readChunk(self, offset, length):
        deferred = self.transport.readv(self.name, [(offset, length)])
        def get_first_chunk(read_things):
            return read_things.next()[1]
        return deferred.addCallback(get_first_chunk)

    def setAttrs(self, attrs):
        pass

    def getAttrs(self):
        return {}

    def close(self):
        pass


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

    implements(ISFTPServer)

    def __init__(self, transport):
        self.transport = transport

    def extendedRequest(self, extendedName, extendedData):
        raise NotImplementedError

    def makeLink(self, src, dest):
        raise NotImplementedError()

    def openDirectory(self, path):
        class DirectoryListing:

            def __init__(self, files):
                self.position = iter(files)

            def __iter__(self):
                return self

            def next(self):
                return self.position.next()

            def close(self):
                # I can't believe we had to implement a whole class just to
                # have this do-nothing method.
                pass

        deferred = self.transport.list_dir(path)
        return deferred.addCallback(DirectoryListing)

    def openFile(self, path, flags, attrs):
        return SFTPServerFile(self.transport, path)

    def readLink(self, path):
        raise NotImplementedError()

    def realPath(self, relpath):
        return self.transport.local_realPath(relpath)

    def setAttrs(self, path, attrs):
        return self.openFile(path, 0, {}).setAttrs(attrs)

    def getAttrs(self, path, followLinks):
        return self.openFile(path, 0, {}).getAttrs()

    def gotVersion(self, otherVersion, extensionData):
        return {}

    def makeDirectory(self, path, attrs):
        return self.transport.mkdir(path)

    def removeDirectory(self, path):
        return self.transport.rmdir(path)

    def removeFile(self, path):
        return self.transport.delete(path)

    def renameFile(self, oldpath, newpath):
        return self.transport.rename(oldpath, newpath)

    def translateError(self, failure):
        types_to_codes = {
            bzr_errors.PermissionDenied: filetransfer.FX_PERMISSION_DENIED,
            bzr_errors.NoSuchFile: filetransfer.FX_NO_SUCH_FILE,
            bzr_errors.FileExists: filetransfer.FX_FILE_ALREADY_EXISTS,
            }
        try:
            sftp_code = types_to_codes[failure.type]
        except KeyError:
            failure.raiseException()
        raise filetransfer.SFTPError(sftp_code, failure.getErrorMessage())
