# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the transport-backed SFTP server implementation."""

import os
import unittest
import shutil

from bzrlib.tests import TestCaseInTempDir
from bzrlib import errors as bzr_errors
from bzrlib import urlutils

from twisted.conch.ssh import filetransfer
from twisted.conch.interfaces import ISFTPServer
from twisted.internet import defer
from twisted.python import failure
from twisted.python.util import mergeFunctionMetadata
from twisted.trial.unittest import TestCase as TrialTestCase

from canonical.config import config
from canonical.codehosting.sftp import (
    FatLocalTransport, TransportSFTPServer, FileIsADirectory)
from canonical.codehosting.sshserver import LaunchpadAvatar
from canonical.codehosting.tests.helpers import FakeLaunchpad
from canonical.codehosting.transport import BlockingProxy


class AsyncTransport:
    """Make a transport that returns Deferreds.

    While this could wrap any object and make its methods return Deferreds, we
    expect this to be wrapping FatLocalTransport (and so making a Twisted
    Transport, as defined in canonical.codehosting.sftp's docstring).
    """

    def __init__(self, transport):
        self._transport = transport

    def __getattr__(self, name):
        maybe_method = getattr(self._transport, name)
        if not callable(maybe_method):
            return maybe_method
        def defer_it(*args, **kwargs):
            return defer.maybeDeferred(maybe_method, *args, **kwargs)
        return mergeFunctionMetadata(maybe_method, defer_it)


class TestFatLocalTransport(TestCaseInTempDir):

    def setUp(self):
        TestCaseInTempDir.setUp(self)
        self.transport = FatLocalTransport(urlutils.local_path_to_url('.'))

    def test_writeChunk(self):
        # writeChunk writes a chunk of data to a file at a given offset.
        filename = 'foo'
        self.transport.put_bytes(filename, 'content')
        self.transport.writeChunk(filename, 1, 'razy')
        self.assertEqual('crazynt', self.transport.get_bytes(filename))


class TestSFTPAdapter(TrialTestCase):

    def makeLaunchpadAvatar(self):
        fake_launchpad = FakeLaunchpad()
        user_dict = fake_launchpad.getUser(1)
        user_dict['initialBranches'] = []
        authserver = BlockingProxy(fake_launchpad)
        return LaunchpadAvatar(user_dict['name'], None, user_dict, authserver)

    def test_canAdaptToSFTPServer(self):
        server = ISFTPServer(self.makeLaunchpadAvatar())
        self.assertIsInstance(server, TransportSFTPServer)
        deferred = server.makeDirectory(
            '~testuser/firefox/baz/.bzr', {'permissions': 0777})
        self.addCleanup(shutil.rmtree, config.codehosting.branches_root)
        return deferred


class GetAttrsMixin:
    """Mixin used to check getAttrs."""

    def checkAttrs(self, attrs, stat_value):
        """Check that an attrs dictionary matches a stat result."""
        self.assertEqual(stat_value.st_size, attrs['size'])
        self.assertEqual(os.getuid(), attrs['uid'])
        self.assertEqual(os.getgid(), attrs['gid'])
        self.assertEqual(stat_value.st_mode, attrs['permissions'])
        self.assertEqual(int(stat_value.st_mtime), attrs['mtime'])
        self.assertEqual(int(stat_value.st_atime), attrs['atime'])


class TestSFTPFile(TrialTestCase, TestCaseInTempDir, GetAttrsMixin):
    """Tests for `TransportSFTPServer` and `TransportSFTPFile`."""

    def setUp(self):
        TrialTestCase.setUp(self)
        TestCaseInTempDir.setUp(self)
        transport = AsyncTransport(
            FatLocalTransport(urlutils.local_path_to_url('.')))
        self._sftp_server = TransportSFTPServer(transport)

    def assertSFTPError(self, sftp_code, function, *args, **kwargs):
        """Assert that calling functions fails with `sftp_code`."""
        deferred = defer.maybeDeferred(function, *args, **kwargs)
        deferred = self.assertFailure(deferred, filetransfer.SFTPError)
        def check_sftp_code(exception):
            self.assertEqual(sftp_code, exception.code)
            return exception
        return deferred.addCallback(check_sftp_code)

    def openFile(self, path, flags, attrs):
        return self._sftp_server.openFile(path, flags, attrs)

    def test_createEmptyFile(self):
        # Opening a file with create flags and then closing it will create a
        # new, empty file.
        handle = self.openFile('foo', filetransfer.FXF_CREAT, {})
        deferred = handle.close()
        return deferred.addCallback(
            lambda ignored: self.assertFileEqual('', 'foo'))

    def test_createFileWithData(self):
        # writeChunk writes data to the file.
        handle = self.openFile(
            'foo', filetransfer.FXF_CREAT | filetransfer.FXF_WRITE, {})
        deferred = handle.writeChunk(0, 'bar')
        deferred.addCallback(lambda ignored: handle.close())
        return deferred.addCallback(
            lambda ignored: self.assertFileEqual('bar', 'foo'))

    def test_writeChunkToFile(self):
        self.build_tree_contents([('foo', 'bar')])
        handle = self.openFile(
            'foo', filetransfer.FXF_CREAT | filetransfer.FXF_WRITE, {})
        deferred = handle.writeChunk(1, 'qux')
        deferred.addCallback(lambda ignored: handle.close())
        return deferred.addCallback(
            lambda ignored: self.assertFileEqual('bqux', 'foo'))

    def test_writeToReadOpenedFile(self):
        # writeChunk raises an error if we try to write to a file that has
        # been opened only for reading.
        self.build_tree_contents([('foo', 'bar')])
        handle = self.openFile('foo', filetransfer.FXF_READ, {})
        return self.assertSFTPError(
            filetransfer.FX_PERMISSION_DENIED,
            handle.writeChunk, 0, 'new content')

    def test_writeToAppendingFileIgnoresOffset(self):
        # If a file is opened with the 'append' flag, writeChunk ignores its
        # offset parameter.
        self.build_tree_contents([('foo', 'bar')])
        handle = self.openFile('foo', filetransfer.FXF_APPEND, {})
        deferred = handle.writeChunk(0, 'baz')
        return deferred.addCallback(
            lambda ignored: self.assertFileEqual('barbaz', 'foo'))

    def test_openAndCloseExistingFileLeavesUnchanged(self):
        # If we open a file with the 'create' flag and without the 'truncate'
        # flag, the file remains unchanged.
        self.build_tree_contents([('foo', 'bar')])
        handle = self.openFile('foo', filetransfer.FXF_CREAT, {})
        deferred = handle.close()
        return deferred.addCallback(
            lambda ignored: self.assertFileEqual('bar', 'foo'))

    def test_writeChunkError(self):
        # Errors in writeChunk are translated to SFTPErrors.
        os.mkdir('foo')
        handle = self.openFile('foo', filetransfer.FXF_WRITE, {})
        deferred = handle.writeChunk(0, 'bar')
        return self.assertFailure(deferred, filetransfer.SFTPError)

    def test_readChunk(self):
        # readChunk reads a chunk of data from the file.
        self.build_tree_contents([('foo', 'bar')])
        handle = self.openFile('foo', 0, {})
        deferred = handle.readChunk(1, 2)
        return deferred.addCallback(self.assertEqual, 'ar')

    def test_readChunkEOF(self):
        # readChunk returns the empty string if it reads past the end-of-file.
        # See comment in _check_for_eof for more details.
        self.build_tree_contents([('foo', 'bar')])
        handle = self.openFile('foo', 0, {})
        deferred = handle.readChunk(2, 10)
        return deferred.addCallback(self.assertEqual, '')

    def test_readChunkError(self):
        # Errors in readChunk are translated to SFTPErrors.
        handle = self.openFile('foo', 0, {})
        deferred = handle.readChunk(1, 2)
        return self.assertFailure(deferred, filetransfer.SFTPError)

    def test_setAttrs(self):
        # setAttrs on TransportSFTPFile does nothing.
        self.build_tree_contents([('foo', 'bar')])
        self.openFile('foo', 0, {}).setAttrs({})

    def test_getAttrs(self):
        # getAttrs on TransportSFTPFile returns a dictionary consistent
        # with the results of os.stat.
        self.build_tree_contents([('foo', 'bar')])
        stat_value = os.stat('foo')
        deferred = self.openFile('foo', 0, {}).getAttrs()
        return deferred.addCallback(self.checkAttrs, stat_value)

    def test_getAttrsError(self):
        # Errors in getAttrs on TransportSFTPFile are translated into
        # SFTPErrors.
        deferred = self.openFile('foo', 0, {}).getAttrs()
        return self.assertFailure(deferred, filetransfer.SFTPError)


class TestSFTPServer(TrialTestCase, TestCaseInTempDir, GetAttrsMixin):
    """Tests for `TransportSFTPServer` and `TransportSFTPFile`."""

    def setUp(self):
        TrialTestCase.setUp(self)
        TestCaseInTempDir.setUp(self)
        transport = AsyncTransport(
            FatLocalTransport(urlutils.local_path_to_url('.')))
        self.sftp_server = TransportSFTPServer(transport)

    def test_serverSetAttrs(self):
        # setAttrs on the TransportSFTPServer doesn't do anything either.
        self.build_tree_contents([('foo', 'bar')])
        self.sftp_server.setAttrs('foo', {})

    def test_serverGetAttrs(self):
        # getAttrs on the TransportSFTPServer also returns a dictionary
        # consistent with the results of os.stat.
        self.build_tree_contents([('foo', 'bar')])
        stat_value = os.stat('foo')
        deferred = self.sftp_server.getAttrs('foo', False)
        return deferred.addCallback(self.checkAttrs, stat_value)

    def test_serverGetAttrsError(self):
        # Errors in getAttrs on the TransportSFTPServer are translated into
        # SFTPErrors.
        deferred = self.sftp_server.getAttrs('nonexistent', False)
        return self.assertFailure(deferred, filetransfer.SFTPError)

    def test_removeFile(self):
        # removeFile removes the file.
        self.build_tree_contents([('foo', 'bar')])
        deferred = self.sftp_server.removeFile('foo')
        def assertFileRemoved(ignored):
            self.failIfExists('foo')
        return deferred.addCallback(assertFileRemoved)

    def test_removeFileError(self):
        # Errors in removeFile are translated into SFTPErrors.
        deferred = self.sftp_server.removeFile('foo')
        return self.assertFailure(deferred, filetransfer.SFTPError)

    def test_renameFile(self):
        # renameFile renames the file.
        self.build_tree_contents([('foo', 'bar')])
        deferred = self.sftp_server.renameFile('foo', 'baz')
        def assertFileRenamed(ignored):
            self.failIfExists('foo')
            self.failUnlessExists('baz')
        return deferred.addCallback(assertFileRenamed)

    def test_renameFileError(self):
        # Errors in renameFile are translated into SFTPErrors.
        deferred = self.sftp_server.renameFile('foo', 'baz')
        return self.assertFailure(deferred, filetransfer.SFTPError)

    def test_makeDirectory(self):
        # makeDirectory makes the directory.
        deferred = self.sftp_server.makeDirectory(
            'foo', {'permissions': 0777})
        def assertDirectoryExists(ignored):
            self.assertTrue(os.path.isdir('foo'), 'foo is not a directory')
            self.assertEqual(040777, os.stat('foo').st_mode)
        return deferred.addCallback(assertDirectoryExists)

    def test_makeDirectoryError(self):
        # Errors in makeDirectory are translated into SFTPErrors.
        deferred = self.sftp_server.makeDirectory(
            'foo/bar', {'permissions': 0777})
        return self.assertFailure(deferred, filetransfer.SFTPError)

    def test_removeDirectory(self):
        # removeDirectory removes the directory.
        os.mkdir('foo')
        deferred = self.sftp_server.removeDirectory('foo')
        def assertDirectoryRemoved(ignored):
            self.failIfExists('foo')
        return deferred.addCallback(assertDirectoryRemoved)

    def test_removeDirectoryError(self):
        # Errors in removeDirectory are translated into SFTPErrors.
        deferred = self.sftp_server.removeDirectory('foo')
        return self.assertFailure(deferred, filetransfer.SFTPError)

    def test_gotVersion(self):
        # gotVersion returns an empty dictionary.
        extended = self.sftp_server.gotVersion('version', {})
        self.assertEqual({}, extended)

    def test_extendedRequest(self):
        # We don't support any extensions.
        self.assertRaises(
            NotImplementedError, self.sftp_server.extendedRequest,
            'foo', 'bar')

    def test_realPath(self):
        # realPath returns the absolute path of the file.
        os.symlink('foo', 'bar')
        deferred = self.sftp_server.realPath('bar')
        return deferred.addCallback(self.assertEqual, os.path.abspath('foo'))

    def test_makeLink(self):
        # makeLink is not supported.
        self.assertRaises(NotImplementedError, self.sftp_server.makeLink,
                          'foo', 'bar')

    def test_readLink(self):
        # readLink is not supported.
        self.assertRaises(NotImplementedError, self.sftp_server.readLink,
                          'foo')

    def test_openDirectory(self):
        # openDirectory returns an iterator that iterates over the contents of
        # the directory.
        self.build_tree(['foo/', 'foo/bar/', 'foo/baz'])
        deferred = self.sftp_server.openDirectory('foo')
        def check_open_directory(directory):
            self.assertEqual(
                [('bar', 'bar', {}), ('baz', 'baz', {})],
                list(sorted((directory))))
            directory.close()
        return deferred.addCallback(check_open_directory)

    def test_openDirectoryError(self):
        # Errors in openDirectory are translated into SFTPErrors.
        deferred = self.sftp_server.openDirectory('foo')
        return self.assertFailure(deferred, filetransfer.SFTPError)

    def do_translation_test(self, exception, sftp_code, method_name=None):
        """Test that `exception` is translated into the correct SFTPError."""
        result = self.assertRaises(filetransfer.SFTPError,
            self.sftp_server.translateError,
            failure.Failure(exception), method_name)
        self.assertEqual(sftp_code, result.code)
        self.assertEqual(str(exception), result.message)

    def test_translatePermissionDenied(self):
        exception = bzr_errors.PermissionDenied('foo')
        self.do_translation_test(exception, filetransfer.FX_PERMISSION_DENIED)

    def test_translateTransportNotPossible(self):
        exception = bzr_errors.TransportNotPossible('foo')
        self.do_translation_test(exception, filetransfer.FX_PERMISSION_DENIED)

    def test_translateNoSuchFile(self):
        exception = bzr_errors.NoSuchFile('foo')
        self.do_translation_test(exception, filetransfer.FX_NO_SUCH_FILE)

    def test_translateFileExists(self):
        exception = bzr_errors.FileExists('foo')
        self.do_translation_test(
            exception, filetransfer.FX_FILE_ALREADY_EXISTS)

    def test_translateFileIsADirectory(self):
        exception = FileIsADirectory('foo')
        self.do_translation_test(
            exception, filetransfer.FX_FILE_IS_A_DIRECTORY)

    def test_translateDirectoryNotEmpty(self):
        exception = bzr_errors.DirectoryNotEmpty('foo')
        self.do_translation_test(
            exception, filetransfer.FX_FAILURE)

    def test_translateRandomError(self):
        # translateError re-raises unrecognized errors.
        exception = KeyboardInterrupt()
        result = self.assertRaises(KeyboardInterrupt,
            self.sftp_server.translateError,
            failure.Failure(exception), 'methodName')
        self.assertIs(result, exception)



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
