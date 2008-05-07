# Copyright 2008 Canonical Ltd.  All rights reserved.


import os
import unittest

from bzrlib.tests import TestCaseInTempDir
from bzrlib import errors as bzr_errors
from bzrlib import urlutils

from canonical.codehosting.sftp import FatLocalTransport, TransportSFTPServer
from twisted.conch.ssh import filetransfer
from twisted.python import failure


class TestSFTPServer(TestCaseInTempDir):

    def setUp(self):
        TestCaseInTempDir.setUp(self)
        transport = FatLocalTransport(urlutils.local_path_to_url('.'))
        self.sftp_server = TransportSFTPServer(transport)

    def test_writeChunk(self):
        handle = self.sftp_server.openFile('foo', 0, {})
        handle.writeChunk(0, 'bar')
        handle.close()
        self.failUnlessExists('foo')
        self.assertFileEqual('bar', 'foo')

    def test_readChunk(self):
        self.build_tree_contents([('foo', 'bar')])
        handle = self.sftp_server.openFile('foo', 0, {})
        self.assertEqual('ar', handle.readChunk(1, 2))

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

    def test_renameFile(self):
        self.build_tree_contents([('foo', 'bar')])
        self.sftp_server.renameFile('foo', 'baz')
        self.failIfExists('foo')
        self.failUnlessExists('baz')

    def test_makeDirectory(self):
        self.sftp_server.makeDirectory('foo', {'permissions': 0777})
        self.assertTrue(os.path.isdir('foo'), 'foo is not a directory')

    def test_removeDirectory(self):
        os.mkdir('foo')
        self.sftp_server.removeDirectory('foo')
        self.failIfExists('foo')

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
        self.assertEqual(
            os.path.abspath('foo'), self.sftp_server.realPath('bar'))

    def test_makeLink(self):
        self.assertRaises(NotImplementedError, self.sftp_server.makeLink,
                          'foo', 'bar')

    def test_readLink(self):
        self.assertRaises(NotImplementedError, self.sftp_server.readLink,
                          'foo')

    def test_openDirectory(self):
        self.build_tree(['foo/', 'foo/bar/', 'foo/baz'])
        directory = self.sftp_server.openDirectory('foo')
        self.assertEqual(set(['baz', 'bar']), set(directory))
        directory.close()

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

    def test_translateRandomError(self):
        exception = KeyboardInterrupt()
        result = self.assertRaises(KeyboardInterrupt,
            self.sftp_server.translateError,
            failure.Failure(exception))
        self.assertIs(result, exception)

    def do_translation_test(self, exception, sftp_code):
        result = self.assertRaises(filetransfer.SFTPError,
            self.sftp_server.translateError,
            failure.Failure(exception))
        self.assertEqual(sftp_code, result.code)
        self.assertEqual(str(exception), result.message)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
