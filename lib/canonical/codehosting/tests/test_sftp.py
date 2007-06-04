# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""Tests for Supermirror SFTP server's bzr support."""

__metaclass__ = type

import unittest
import stat

from bzrlib import errors
from bzrlib.transport import get_transport
from bzrlib.tests import TestCaseWithMemoryTransport

from canonical.codehosting.transport import branch_id_to_path
from canonical.codehosting.transport import LaunchpadServer

from canonical.codehosting.tests.test_acceptance import SSHTestCase
from canonical.codehosting.tests.test_transport import FakeLaunchpad
from canonical.codehosting.tests.helpers import (
    TwistedBzrlibLayer, deferToThread)
from canonical.testing import BzrlibLayer


class SFTPTests(SSHTestCase):

    layer = TwistedBzrlibLayer

    def _cleanUp(self, result):
        print "Overriding Twisted's cleanup because it causes errors."
        from twisted.internet import defer
        return defer.succeed(None)

    @deferToThread
    def test_rmdir_branch(self):
        # Make some directories under ~testuser/+junk (i.e. create some empty
        # branches)
        transport = self.getTransport('~testuser/+junk')
        transport.mkdir('foo')
        transport.mkdir('bar')
        self.failUnless(stat.S_ISDIR(transport.stat('foo').st_mode))
        self.failUnless(stat.S_ISDIR(transport.stat('bar').st_mode))

        # Try to remove a branch directory, which is not allowed.
        e = self.assertRaises(errors.PermissionDenied, transport.rmdir, 'foo')
        self.failUnless(
            "removing branch directory 'foo' is not allowed." in str(e), str(e))

        # The 'foo' directory is still listed.
        self.failUnlessEqual(['bar', 'foo'], sorted(transport.list_dir('.')))

    @deferToThread
    def test_mkdir_toplevel_error(self):
        # You cannot create a top-level directory.
        transport = self.getTransport()
        e = self.assertRaises(errors.PermissionDenied, transport.mkdir, 'foo')
        self.failUnless(
            "Branches must be inside a person or team directory." in str(e),
            str(e))

    @deferToThread
    def test_mkdir_invalid_product_error(self):
        # Make some directories under ~testuser/+junk (i.e. create some empty
        # branches)
        transport = self.getTransport('~testuser')

        # You cannot create a product directory unless the product name is
        # registered in Launchpad.
        e = self.assertRaises(errors.PermissionDenied,
                transport.mkdir, 'no-such-product')
        self.failUnless(
            "Directories directly under a user directory must be named after a "
            "product name registered in Launchpad" in str(e),
            str(e))

    @deferToThread
    def test_mkdir_not_team_member_error(self):
        # You can't mkdir in a team directory unless you're a member of that
        # team (in fact, you can't even see the directory).
        transport = self.getTransport()
        e = self.assertRaises(errors.NoSuchFile,
                transport.mkdir, '~not-my-team/mozilla-firefox')
        self.failUnless("~not-my-team" in str(e))

    @deferToThread
    def test_mkdir_team_member(self):
        # You can mkdir in a team directory that you're a member of (so long as
        # it's a real product), though.
        transport = self.getTransport()
        transport.mkdir('~testteam/firefox')

        # Confirm the mkdir worked by using list_dir.
        self.failUnless('firefox' in transport.list_dir('~testteam'))

        # You can of course mkdir a branch, too
        transport.mkdir('~testteam/firefox/shiny-new-thing')
        self.failUnless(
            'shiny-new-thing' in transport.list_dir('~testteam/firefox'))
        transport.mkdir('~testteam/firefox/shiny-new-thing/.bzr')

    @deferToThread
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
            IOError, transport.rename, 'branch/.bzr/dir1', 'branch/.bzr/dir2')

    @deferToThread
    def test_rename_directory_to_empty_directory_succeeds(self):
        # 'rename dir1 dir2' succeeds if 'dir2' is empty. Not sure we want this
        # behaviour, but it's worth documenting.
        transport = self.getTransport('~testuser/+junk')
        transport.mkdir('branch')
        transport.mkdir('branch/.bzr')
        transport.mkdir('branch/.bzr/dir1')
        transport.mkdir('branch/.bzr/dir2')
        transport.rename('branch/.bzr/dir1', 'branch/.bzr/dir2')
        self.assertEqual(['dir2'], transport.list_dir('branch/.bzr'))

    @deferToThread
    def test_rename_directory_succeeds(self):
        # 'rename dir1 dir2' succeeds if 'dir2' doesn't exist.
        transport = self.getTransport('~testuser/+junk')
        transport.mkdir('branch')
        transport.mkdir('branch/.bzr')
        transport.mkdir('branch/.bzr/dir1')
        transport.mkdir('branch/.bzr/dir1/foo')
        transport.rename('branch/.bzr/dir1', 'branch/.bzr/dir2')
        self.assertEqual(['dir2'], transport.list_dir('branch/.bzr'))


class TestLaunchpadTransportMakeDirectory(TestCaseWithMemoryTransport):

    layer = BzrlibLayer

    def setUp(self):
        TestCaseWithMemoryTransport.setUp(self)
        self.authserver = FakeLaunchpad()
        self.user_id = 1
        self.backing_transport = self.get_transport()
        self.server = LaunchpadServer(
            self.authserver, self.user_id, self.backing_transport)
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        self.transport = get_transport(self.server.get_url())

    def test_make_invalid_user_directory(self):
        # The top-level directory must always be of the form '~user'. However,
        # sometimes a transport will ask to look at files that aren't of that
        # form. In that case, we raise NoSuchFile.
        self.assertRaises(
            errors.NoSuchFile, self.transport.mkdir, 'apple')

    def test_make_valid_user_directory(self):
        # Making a top-level directory is not supported by the Launchpad
        # transport.
        self.assertRaises(errors.NoSuchFile, self.transport.mkdir, '~apple')

    def test_make_existing_user_directory(self):
        # Making a user directory raises an error. We don't really care what
        # the error is, but it should be one of FileExists,
        # TransportNotPossible or NoSuchFile
        self.assertRaises(errors.NoSuchFile, self.transport.mkdir, '~foo')

    def test_make_product_directory_for_nonexistent_product(self):
        # Making a directory for a non-existent product is not allowed.
        # Products must first be registered in Launchpad.
        transport = get_transport(self.server.get_url())
        self.assertRaises(errors.NoSuchFile, self.transport.mkdir, '~foo/pear')

    def test_make_product_directory_for_existent_product(self):
        # The transport raises a FileExists error if it tries to make the
        # directory of a product that is registered with Launchpad.

        # XXX: JonathanLange 2007-05-27, do we care what the error is? It
        # should be TransportNotPossible or FileExists. NoSuchFile might be
        # acceptable though.
        self.assertRaises(errors.NoSuchFile, self.transport.mkdir, '~foo/bar')

    def test_make_branch_directory(self):
        # We allow users to create new branches by pushing them beneath an
        # existing product directory.
        self.transport.mkdir('~foo/bar/banana')
        # This implicitly tests that the branch has been created in the
        # database. The call to transport.has will blow up if it can't map the
        # path to a branch ID, there won't be a branch ID unless the branch is
        # in the database.
        self.assertTrue(self.transport.has('~foo/bar/banana'))
        self.transport.mkdir('~team1/bar/banana')
        self.assertTrue(self.transport.has('~team1/bar/banana'))

    def test_make_junk_branch(self):
        # Users can make branches beneath their '+junk' folder.
        self.transport.mkdir('~foo/+junk/banana')
        # See comment in test_make_branch_directory.
        self.assertTrue(self.transport.has('~foo/+junk/banana'))

    def test_directory_inside_branch(self):
        # We allow users to create new branches by pushing them beneath an
        # existing product directory.
        self.transport.mkdir('~foo/bar/banana')
        self.transport.mkdir('~foo/bar/banana/.bzr')
        # WHITEBOX ALERT. The transport doesn't have any API for providing the
        # branch ID (which is a good thing), and we need the id to find the
        # path on the underlying transport.
        branch_id = self.server._branches[('foo', 'bar', 'banana')]
        self.assertTrue(
            self.backing_transport.has(branch_id_to_path(branch_id)))

    def test_make_directory_without_prefix(self):
        # Because the user and product directories don't exist on the
        # filesystem, we can create a branch directory for a product even if
        # there are no existing branches for that product.
        self.transport.mkdir('~foo/product2/banana')
        self.assertTrue(self.transport.has('~foo/product2/banana'))

    def test_make_two_directories(self):
        # Bazaar doesn't have a makedirs() facility for transports, so we need
        # to make sure that we can make a directory on the backing transport if
        # its parents exist and if they don't exist.
        self.transport.mkdir('~foo/product2/banana')
        self.transport.mkdir('~foo/product2/orange')
        self.assertTrue(self.transport.has('~foo/product2/banana'))
        self.assertTrue(self.transport.has('~foo/product2/orange'))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
