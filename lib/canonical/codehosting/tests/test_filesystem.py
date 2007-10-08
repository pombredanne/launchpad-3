# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Tests for the virtual filesystem presented by Launchpad codehosting."""

__metaclass__ = type

import unittest
import stat

from bzrlib import errors
from bzrlib.tests import TestCaseWithTransport

from canonical.codehosting import branch_id_to_path
from canonical.codehosting.tests.servers import (
    make_launchpad_server, make_sftp_server)
from canonical.codehosting.tests.helpers import (
    CodeHostingTestProviderAdapter, ServerTestCase, adapt_suite, deferToThread)

from canonical.testing import TwistedLayer


def wait_for_disconnect(method):
    """Run 'method' and wait for it to fully disconnect from the server.

    Expects 'method' to be a method on an object that has a 'server' attribute
    with a 'runAndWaitForDisconnect' method. In practice, this means a subclass
    of `ServerTestCase`.
    """
    def decorated_function(self, *args, **kwargs):
        return self.server.runAndWaitForDisconnect(
            method, self, *args, **kwargs)
    decorated_function.__doc__ = method.__doc__
    decorated_function.__name__ = method.__name__
    return decorated_function


class TestBranchIDToPath(unittest.TestCase):
    """Tests for branch_id_to_path."""

    def test_branchIDToPath(self):
        # branch_id_to_path converts an integer branch ID into a path of four
        # segments, with each segment being a hexadecimal number.
        self.assertEqual('00/00/00/00', branch_id_to_path(0))
        self.assertEqual('00/00/00/01', branch_id_to_path(1))
        arbitrary_large_id = 6731
        assert "%x" % arbitrary_large_id == '1a4b', (
            "The arbitrary large id is not what we expect (1a4b): %s"
            % (arbitrary_large_id))
        self.assertEqual('00/00/1a/4b', branch_id_to_path(6731))


class TestFilesystem(ServerTestCase, TestCaseWithTransport):

    layer = TwistedLayer

    def _cleanUp(self, result):
        # XXX: JonathanLange 2007-06-13 bug=120156
        # Override Twisted's post-test cleanup.
        # The tests fail badly if this is removed, for unknown reasons.
        from twisted.internet import defer
        return defer.succeed(None)

    def assertPermissionDenied(self, function, *args, **kwargs):
        """Assert that calling 'function' raises a permission denied error.

        The actual exception depends on whether the function operates on an
        SFTP transport or a smart server transport. The SFTP transport will
        raise `errors.PermissionDenied` and the smart server transport will
        raise `errors.NoSuchFile`.
        """
        # XXX: JonathanLange 2007-08-01, The smart server should raise
        # PermissionDenied, just like the SFTP server. However, a bug in Bazaar
        # (bug 118736) prevents PermissionDenied errors from being transmitted
        # over the wire, so the server raises NoSuchFile instead.
        self.assertRaises(
            (errors.PermissionDenied, errors.NoSuchFile),
            function, *args, **kwargs)

    @deferToThread
    def test_remove_branch_directory(self):
        # Make some directories under ~testuser/+junk (i.e. create some empty
        # branches)
        transport = self.getTransport('~testuser/+junk')
        transport.mkdir('foo')
        transport.mkdir('bar')
        self.failUnless(stat.S_ISDIR(transport.stat('foo').st_mode))
        self.failUnless(stat.S_ISDIR(transport.stat('bar').st_mode))

        # Try to remove a branch directory, which is not allowed.
        self.assertPermissionDenied(transport.rmdir, 'foo')

        # The 'foo' directory is still listed.
        self.assertTrue(transport.has('bar'))
        self.assertTrue(transport.has('foo'))

    @deferToThread
    def test_make_invalid_user_directory(self):
        # The top-level directory must always be of the form '~user'. However,
        # sometimes a transport will ask to look at files that aren't of that
        # form. In that case, the transport is denied permission.
        transport = self.getTransport()
        self.assertPermissionDenied(transport.mkdir, 'apple')

    @deferToThread
    def test_make_valid_user_directory(self):
        # Making a top-level directory is not supported by the Launchpad
        # transport.
        transport = self.getTransport()
        self.assertPermissionDenied(transport.mkdir, '~apple')

    @deferToThread
    def test_make_existing_user_directory(self):
        # Making a user directory raises an error. We don't really care what
        # the error is, but it should be one of FileExists,
        # TransportNotPossible or NoSuchFile
        transport = self.getTransport()
        self.assertPermissionDenied(transport.mkdir, '~testuser')

    @deferToThread
    def test_mkdir_not_team_member_error(self):
        # You can't make a branch under the directory of a team that you don't
        # belong to.
        transport = self.getTransport()
        self.assertRaises(
            errors.NoSuchFile,
            transport.mkdir, '~not-my-team/firefox/new-branch')

    @deferToThread
    def test_make_team_branch_directory(self):
        # You can make a branch directory under a team directory that you are a
        # member of (so long as it's a real product), though.
        transport = self.getTransport()
        transport.mkdir('~testteam/firefox/shiny-new-thing')
        self.assertTrue(
            transport.has('~testteam/firefox/shiny-new-thing'))

    @deferToThread
    def test_make_team_junk_branch_directory(self):
        # Teams do not have +junk products
        transport = self.getTransport()
        self.assertPermissionDenied(
            transport.mkdir, '~testteam/+junk/new-branch')

    @deferToThread
    def test_make_product_directory_for_nonexistent_product(self):
        # Making a branch directory for a non-existent product is not allowed.
        # Products must first be registered in Launchpad.
        transport = self.getTransport()
        self.assertPermissionDenied(
            transport.mkdir, '~testuser/no-such-product/new-branch')

    @deferToThread
    def test_make_branch_directory(self):
        # We allow users to create new branches by pushing them beneath an
        # existing product directory.
        transport = self.getTransport()
        transport.mkdir('~testuser/firefox/banana')
        self.assertTrue(transport.has('~testuser/firefox/banana'))

    @deferToThread
    def test_make_junk_branch(self):
        # Users can make branches beneath their '+junk' folder.
        transport = self.getTransport()
        transport.mkdir('~testuser/+junk/banana')
        # See comment in test_make_branch_directory.
        self.assertTrue(transport.has('~testuser/+junk/banana'))

    @deferToThread
    @wait_for_disconnect
    def test_directory_inside_branch(self):
        # We allow users to create new branches by pushing them beneath an
        # existing product directory.
        transport = self.getTransport()
        transport.mkdir('~testuser/firefox/banana')
        transport.mkdir('~testuser/firefox/banana/.bzr')
        self.assertTrue(transport.has('~testuser/firefox/banana'))
        self.assertTrue(transport.has('~testuser/firefox/banana/.bzr'))

    @deferToThread
    @wait_for_disconnect
    def test_bzr_backup_directory_inside_branch(self):
        # Bazaar sometimes needs to create .bzr.backup directories directly
        # underneath the branch directory. Thus, we allow the creation of
        # .bzr.backup directories.
        transport = self.getTransport()
        transport.mkdir('~testuser/firefox/banana')
        transport.mkdir('~testuser/firefox/banana/.bzr.backup')
        self.assertTrue(transport.has('~testuser/firefox/banana'))
        self.assertTrue(
            transport.has('~testuser/firefox/banana/.bzr.backup'))

    @deferToThread
    def test_non_bzr_directory_inside_branch(self):
        # Users can only create Bazaar control directories (e.g. '.bzr') inside
        # a branch. Other directories are strictly forbidden.
        transport = self.getTransport()
        transport.mkdir('~testuser/+junk/banana')
        self.assertPermissionDenied(
            transport.mkdir, '~testuser/+junk/banana/republic')

    @deferToThread
    @wait_for_disconnect
    def test_non_bzr_file_inside_branch(self):
        # Users can only create Bazaar control directories (e.g. '.bzr') inside
        # a branch. Files are not allowed.
        transport = self.getTransport()
        transport.mkdir('~testuser/+junk/banana')
        self.assertPermissionDenied(
            transport.put_bytes, '~testuser/+junk/banana/README', 'Hello!')

    @deferToThread
    @wait_for_disconnect
    def test_rename_to_non_bzr_directory_fails(self):
        # Users cannot create an allowed directory (e.g. '.bzr' or
        # '.bzr.backup') and then rename it to something that's not allowed
        # (e.g. 'republic').
        transport = self.getTransport()
        transport.mkdir('~testuser/firefox/banana')
        transport.mkdir('~testuser/firefox/banana/.bzr')
        self.assertPermissionDenied(
            transport.rename, '~testuser/firefox/banana/.bzr',
            '~testuser/firefox/banana/republic')

    @deferToThread
    def test_make_directory_without_prefix(self):
        # Because the user and product directories don't exist on the
        # filesystem, we can create a branch directory for a product even if
        # there are no existing branches for that product.
        transport = self.getTransport()
        transport.mkdir('~testuser/thunderbird/banana')
        self.assertTrue(transport.has('~testuser/thunderbird/banana'))

    @deferToThread
    @wait_for_disconnect
    def test_rename_directory_to_existing_directory_fails(self):
        # 'rename dir1 dir2' should fail if 'dir2' exists. Unfortunately, it
        # will only fail if they both contain files/directories.
        transport = self.getTransport('~testuser/+junk')
        transport.mkdir('branch')
        transport.mkdir('branch/.bzr')
        transport.mkdir('branch/.bzr/dir1')
        transport.mkdir('branch/.bzr/dir1/foo')
        transport.mkdir('branch/.bzr/dir2')
        transport.mkdir('branch/.bzr/dir2/bar')
        self.assertRaises(
            (errors.FileExists, IOError),
            transport.rename, 'branch/.bzr/dir1', 'branch/.bzr/dir2')

    @deferToThread
    @wait_for_disconnect
    def test_rename_directory_succeeds(self):
        # 'rename dir1 dir2' succeeds if 'dir2' doesn't exist.
        transport = self.getTransport('~testuser/+junk')
        transport.mkdir('branch')
        transport.mkdir('branch/.bzr')
        transport.mkdir('branch/.bzr/dir1')
        transport.mkdir('branch/.bzr/dir1/foo')
        transport.rename('branch/.bzr/dir1', 'branch/.bzr/dir2')
        self.assertEqual(['dir2'], transport.list_dir('branch/.bzr'))


class TestErrorMessages(ServerTestCase, TestCaseWithTransport):

    layer = TwistedLayer

    def _cleanUp(self, result):
        # XXX: JonathanLange 2007-06-13 bug=120156: Override Twisted's
        # post-test cleanup. The tests fail badly if this is removed, for
        # unknown reasons.
        from twisted.internet import defer
        return defer.succeed(None)

    def installServer(self, server):
        self.server = server

    def getDefaultServer(self):
        return make_sftp_server()

    @deferToThread
    def test_make_toplevel_directory_error(self):
        transport = self.getTransport()
        e = self.assertRaises(
            errors.PermissionDenied, transport.mkdir, 'directory')
        self.assertIn(
            "Branches must be inside a person or team directory.", str(e))

    @deferToThread
    def test_remove_branch_error(self):
        transport = self.getTransport()
        transport.mkdir('~testuser/+junk/foo')
        e = self.assertRaises(
            errors.PermissionDenied, transport.rmdir, '~testuser/+junk/foo')
        self.assertIn(
            "removing branch directory 'foo' is not allowed.", str(e))

    @deferToThread
    def test_make_product_directory_for_nonexistent_product_error(self):
        transport = self.getTransport()
        e = self.assertRaises(
            errors.PermissionDenied,
            transport.mkdir, '~testuser/no-such-product/new-branch')
        self.assertIn(
            "Directories directly under a user directory must be named after "
            "a project name registered in Launchpad",
            str(e))

    @deferToThread
    def test_mkdir_not_team_member_error(self):
        # You can't make a branch under the directory of a team that you don't
        # belong to.
        transport = self.getTransport()
        e = self.assertRaises(
            errors.NoSuchFile,
            transport.mkdir, '~not-my-team/firefox/new-branch')
        self.assertIn("~not-my-team", str(e))


def test_suite():
    # Parametrize the tests so they run against the SFTP server and a Bazaar
    # smart server. This ensures that both services provide the same behaviour.
    servers = [make_sftp_server, make_launchpad_server]
    adapter = CodeHostingTestProviderAdapter(servers)
    loader = unittest.TestLoader()
    filesystem_suite = loader.loadTestsFromTestCase(TestFilesystem)
    error_suite = loader.loadTestsFromTestCase(TestErrorMessages)
    return unittest.TestSuite(
        [adapt_suite(adapter, filesystem_suite), error_suite])
