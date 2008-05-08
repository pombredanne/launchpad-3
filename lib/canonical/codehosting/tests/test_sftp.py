# Copyright 2008 Canonical Ltd.  All rights reserved.


import os
import unittest
import shutil

from bzrlib.tests import TestCase, TestCaseInTempDir
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
    """Why are you even looking at this?

    This wraps around a Bazaar transport and makes all of its methods return
    Deferreds using maybeDeferred.

    In addition to normal Bazaar transport methods, this also supports
    writeChunk and local_realPath.
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
        deferred = server.makeDirectory('~testuser/firefox/baz/.bzr', 0777)
        self.addCleanup(shutil.rmtree, config.codehosting.branches_root)
        return deferred


class TestSFTPServer(TrialTestCase, TestCaseInTempDir):

    def setUp(self):
        TrialTestCase.setUp(self)
        TestCaseInTempDir.setUp(self)
        transport = AsyncTransport(
            FatLocalTransport(urlutils.local_path_to_url('.')))
        self.sftp_server = TransportSFTPServer(transport)

    def test_writeChunk(self):
        handle = self.sftp_server.openFile('foo', 0, {})
        handle.writeChunk(0, 'bar')
        handle.close()
        self.failUnlessExists('foo')
        self.assertFileEqual('bar', 'foo')

    def test_writeChunkError(self):
        os.mkdir('foo')
        handle = self.sftp_server.openFile('foo', 0, {})
        deferred = handle.writeChunk(0, 'bar')
        return self.assertFailure(deferred, filetransfer.SFTPError)

    def test_readChunk(self):
        self.build_tree_contents([('foo', 'bar')])
        handle = self.sftp_server.openFile('foo', 0, {})
        deferred = handle.readChunk(1, 2)
        return deferred.addCallback(self.assertEqual, 'ar')

    def test_readChunkError(self):
        handle = self.sftp_server.openFile('foo', 0, {})
        deferred = handle.readChunk(1, 2)
        return self.assertFailure(deferred, filetransfer.SFTPError)

    def test_setAttrs(self):
        self.build_tree_contents([('foo', 'bar')])
        self.sftp_server.openFile('foo', 0, {}).setAttrs({})

    def test_getAttrs(self):
        self.build_tree_contents([('foo', 'bar')])
        self.assertEqual({}, self.sftp_server.openFile('foo', 0,
                         {}).getAttrs())

    def test_ServersetAttrs(self):
        self.build_tree_contents([('foo', 'bar')])
        self.sftp_server.setAttrs('foo', {})

    def test_ServergetAttrs(self):
        self.build_tree_contents([('foo', 'bar')])
        self.assertEqual({}, self.sftp_server.getAttrs('foo', False))

    def test_removeFile(self):
        self.build_tree_contents([('foo', 'bar')])
        self.sftp_server.removeFile('foo')
        self.failIfExists('foo')

    def test_removeFileError(self):
        deferred = self.sftp_server.removeFile('foo')
        return self.assertFailure(deferred, filetransfer.SFTPError)

    def test_renameFile(self):
        self.build_tree_contents([('foo', 'bar')])
        self.sftp_server.renameFile('foo', 'baz')
        self.failIfExists('foo')
        self.failUnlessExists('baz')

    def test_renameFileError(self):
        deferred = self.sftp_server.renameFile('foo', 'baz')
        return self.assertFailure(deferred, filetransfer.SFTPError)

    def test_makeDirectory(self):
        self.sftp_server.makeDirectory('foo', {'permissions': 0777})
        self.assertTrue(os.path.isdir('foo'), 'foo is not a directory')

    def test_makeDirectoryError(self):
        deferred = self.sftp_server.makeDirectory(
            'foo/bar', {'permissions': 0777})
        return self.assertFailure(deferred, filetransfer.SFTPError)

    def test_removeDirectory(self):
        os.mkdir('foo')
        self.sftp_server.removeDirectory('foo')
        self.failIfExists('foo')

    def test_removeDirectoryError(self):
        deferred = self.sftp_server.removeDirectory('foo')
        return self.assertFailure(deferred, filetransfer.SFTPError)

    def test_gotVersion(self):
        extended = self.sftp_server.gotVersion('version', {})
        self.assertEqual({}, extended)

    def test_extendedRequest(self):
        # We don't support any extensions.
        self.assertRaises(
            NotImplementedError, self.sftp_server.extendedRequest,
            'foo', 'bar')

    def test_realPath(self):
        os.symlink('foo', 'bar')
        deferred = self.sftp_server.realPath('bar')
        return deferred.addCallback(self.assertEqual, os.path.abspath('foo'))

    def test_makeLink(self):
        self.assertRaises(NotImplementedError, self.sftp_server.makeLink,
                          'foo', 'bar')

    def test_readLink(self):
        self.assertRaises(NotImplementedError, self.sftp_server.readLink,
                          'foo')

    def test_openDirectory(self):
        self.build_tree(['foo/', 'foo/bar/', 'foo/baz'])
        deferred = self.sftp_server.openDirectory('foo')
        def check_open_directory(directory):
            self.assertEqual(
                [('bar', 'bar', {}), ('baz', 'baz', {})],
                list(sorted((directory))))
            directory.close()
        return deferred.addCallback(check_open_directory)

    def test_openDirectoryError(self):
        deferred = self.sftp_server.openDirectory('foo')
        return self.assertFailure(deferred, filetransfer.SFTPError)

    def test_translatePermissionDenied(self):
        exception = bzr_errors.PermissionDenied('foo')
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
        exception = KeyboardInterrupt()
        result = self.assertRaises(KeyboardInterrupt,
            self.sftp_server.translateError,
            failure.Failure(exception), 'methodName')
        self.assertIs(result, exception)

    def do_translation_test(self, exception, sftp_code, method_name=None):
        result = self.assertRaises(filetransfer.SFTPError,
            self.sftp_server.translateError,
            failure.Failure(exception), method_name)
        self.assertEqual(sftp_code, result.code)
        self.assertEqual(str(exception), result.message)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
