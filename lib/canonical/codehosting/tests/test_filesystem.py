# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Tests for the virtual filesystem presented by Launchpad codehosting."""

__metaclass__ = type

import unittest
import stat

from bzrlib import errors
from bzrlib.tests import TestCaseWithTransport

from canonical.codehosting import branch_id_to_path
from canonical.codehosting.tests.helpers import (
    CodeHostingTestProviderAdapter, ServerTestCase, adapt_suite)
from canonical.codehosting.tests.servers import (
    make_launchpad_server, make_sftp_server)
from canonical.config import config
from canonical.testing import TwistedLaunchpadZopelessLayer
from canonical.twistedsupport import defer_to_thread

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

    layer = TwistedLaunchpadZopelessLayer

    @defer_to_thread
    def test_remove_branch_directory(self):
        # Make some directories under ~testuser/+junk (i.e. create some empty
        # branches)
        transport = self.getTransport('~testuser/+junk')
        transport.mkdir('foo')
        transport.mkdir('bar')
        self.failUnless(stat.S_ISDIR(transport.stat('foo').st_mode))
        self.failUnless(stat.S_ISDIR(transport.stat('bar').st_mode))

        # Try to remove a branch directory, which is not allowed.
        self.assertTransportRaises(
            errors.PermissionDenied, transport.rmdir, 'foo')

        # The 'foo' directory is still listed.
        self.assertTrue(transport.has('bar'))
        self.assertTrue(transport.has('foo'))

    @defer_to_thread
    def test_make_invalid_user_directory(self):
        # The top-level directory must always be of the form '~user'. However,
        # sometimes a transport will ask to look at files that aren't of that
        # form. In that case, the transport is denied permission.
        transport = self.getTransport()
        self.assertTransportRaises(
            errors.PermissionDenied, transport.mkdir, 'apple')

    @defer_to_thread
    def test_make_valid_user_directory(self):
        # Making a top-level directory is not supported by the Launchpad
        # transport.
        transport = self.getTransport()
        self.assertTransportRaises(
            errors.PermissionDenied, transport.mkdir, '~apple')

    @defer_to_thread
    def test_make_existing_user_directory(self):
        # Making a user directory raises an error. We don't really care what
        # the error is, but it should be one of FileExists,
        # TransportNotPossible or NoSuchFile
        transport = self.getTransport()
        self.assertTransportRaises(
            errors.PermissionDenied, transport.mkdir, '~testuser')

    @defer_to_thread
    def test_mkdir_not_team_member_error(self):
        # You can't make a branch under the directory of a team that you don't
        # belong to.
        transport = self.getTransport()
        # The SFTP server will get NoSuchFile because /~not-my-team
        # does not exist, while the smart server gets PermissionDenied
        # because we can't create the given branch.
        self.assertTransportRaises(
            (errors.NoSuchFile, errors.PermissionDenied),
            transport.mkdir, '~not-my-team/firefox/new-branch')

    @defer_to_thread
    def test_make_team_branch_directory(self):
        # You can make a branch directory under a team directory that you are
        # a member of (so long as it's a real product).
        transport = self.getTransport()
        transport.mkdir('~testteam/firefox/shiny-new-thing')
        self.assertTrue(
            transport.has('~testteam/firefox/shiny-new-thing'))

    @defer_to_thread
    def test_make_team_junk_branch_directory(self):
        # Teams do not have +junk products
        transport = self.getTransport()
        # The SFTP server will get NoSuchFile because /~testteam/+junk
        # does not exist, while the smart server gets PermissionDenied
        # because we can't create the given branch.
        self.assertTransportRaises(
            (errors.NoSuchFile, errors.PermissionDenied),
            transport.mkdir, '~testteam/+junk/new-branch')

    @defer_to_thread
    def test_make_product_directory_for_nonexistent_product(self):
        # Making a branch directory for a non-existent product is not allowed.
        # Products must first be registered in Launchpad.
        transport = self.getTransport()
        self.assertTransportRaises(
            errors.PermissionDenied,
            transport.mkdir, '~testuser/no-such-product/new-branch')

    @defer_to_thread
    def test_make_branch_directory(self):
        # We allow users to create new branches by pushing them beneath an
        # existing product directory.
        transport = self.getTransport()
        transport.mkdir('~testuser/firefox/banana')
        self.assertTrue(transport.has('~testuser/firefox/banana'))

    @defer_to_thread
    def test_make_junk_branch(self):
        # Users can make branches beneath their '+junk' folder.
        transport = self.getTransport()
        transport.mkdir('~testuser/+junk/banana')
        # See comment in test_make_branch_directory.
        self.assertTrue(transport.has('~testuser/+junk/banana'))

    @defer_to_thread
    def test_get_stacking_policy(self):
        # A stacking policy control file is served underneath product
        # directories for products that have a default stacked-on branch.
        transport = self.getTransport()
        control_file = transport.get_bytes(
            '~testuser/evolution/.bzr/control.conf')
        self.assertEqual(
            'default_stack_on=%s~vcs-imports/evolution/main'
            % config.codehosting.supermirror_root,
            control_file.strip())

    @defer_to_thread
    @wait_for_disconnect
    def test_directory_inside_branch(self):
        # We allow users to create new branches by pushing them beneath an
        # existing product directory.
        transport = self.getTransport()
        transport.mkdir('~testuser/firefox/banana')
        transport.mkdir('~testuser/firefox/banana/.bzr')
        self.assertTrue(transport.has('~testuser/firefox/banana'))
        self.assertTrue(transport.has('~testuser/firefox/banana/.bzr'))

    @defer_to_thread
    @wait_for_disconnect
    def test_bzr_backup_directory_inside_branch(self):
        # Bazaar sometimes needs to create .bzr.backup directories directly
        # underneath the branch directory. Thus, we allow the creation of
        # .bzr.backup directories. The .bzr.backup directory is a deprecated
        # name. Now Bazaar uses 'backup.bzr'.
        transport = self.getTransport()
        transport.mkdir('~testuser/firefox/banana')
        transport.mkdir('~testuser/firefox/banana/.bzr.backup')
        self.assertTrue(transport.has('~testuser/firefox/banana'))
        self.assertTrue(
            transport.has('~testuser/firefox/banana/.bzr.backup'))

    @defer_to_thread
    @wait_for_disconnect
    def test_backup_bzr_directory_inside_branch(self):
        # Bazaar sometimes needs to create backup.bzr directories directly
        # underneath the branch directory. This is alternative name for the
        # backup.bzr directory.
        transport = self.getTransport()
        transport.mkdir('~testuser/firefox/banana')
        transport.mkdir('~testuser/firefox/banana/backup.bzr')
        self.assertTrue(transport.has('~testuser/firefox/banana'))
        self.assertTrue(
            transport.has('~testuser/firefox/banana/backup.bzr'))

    @defer_to_thread
    def test_non_bzr_directory_inside_branch(self):
        # Users can only create Bazaar control directories (e.g. '.bzr')
        # inside a branch. Other directories are strictly forbidden.
        transport = self.getTransport()
        transport.mkdir('~testuser/+junk/banana')
        self.assertTransportRaises(
            errors.PermissionDenied,
            transport.mkdir, '~testuser/+junk/banana/republic')

    @defer_to_thread
    @wait_for_disconnect
    def test_non_bzr_file_inside_branch(self):
        # Users can only create Bazaar control directories (e.g. '.bzr')
        # inside a branch. Files are not allowed.
        transport = self.getTransport()
        transport.mkdir('~testuser/+junk/banana')
        self.assertTransportRaises(
            errors.PermissionDenied,
            transport.put_bytes, '~testuser/+junk/banana/README', 'Hello!')

    @defer_to_thread
    @wait_for_disconnect
    def test_rename_to_non_bzr_directory_fails(self):
        # Users cannot create an allowed directory (e.g. '.bzr' or
        # '.bzr.backup') and then rename it to something that's not allowed
        # (e.g. 'republic').
        transport = self.getTransport()
        transport.mkdir('~testuser/firefox/banana')
        transport.mkdir('~testuser/firefox/banana/.bzr')
        self.assertTransportRaises(
            errors.PermissionDenied,
            transport.rename, '~testuser/firefox/banana/.bzr',
            '~testuser/firefox/banana/republic')

    @defer_to_thread
    def test_make_directory_without_prefix(self):
        # Because the user and product directories don't exist on the
        # filesystem, we can create a branch directory for a product even if
        # there are no existing branches for that product.
        transport = self.getTransport()
        transport.mkdir('~testuser/thunderbird/banana')
        self.assertTrue(transport.has('~testuser/thunderbird/banana'))

    @defer_to_thread
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

    @defer_to_thread
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

    @defer_to_thread
    @wait_for_disconnect
    def test_make_directory_twice(self):
        # The transport raises a `FileExists` error if we try to make a
        # directory that already exists.
        transport = self.getTransport('~testuser/+junk')
        transport.mkdir('branch')
        transport.mkdir('branch/.bzr')
        transport.mkdir('branch/.bzr/dir1')
        self.assertRaises(
            errors.FileExists, transport.mkdir, 'branch/.bzr/dir1')


def test_suite():
    # Parametrize the tests so they run against the SFTP server and a Bazaar
    # smart server. This ensures that both services provide the same
    # behaviour.
    servers = [make_sftp_server, make_launchpad_server]
    adapter = CodeHostingTestProviderAdapter(servers)
    loader = unittest.TestLoader()
    filesystem_suite = loader.loadTestsFromTestCase(TestFilesystem)
    return adapt_suite(adapter, filesystem_suite)
