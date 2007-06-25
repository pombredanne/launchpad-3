# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Tests for the virtual filesystem presented by Launchpad codehosting."""

__metaclass__ = type

import unittest
import stat

from bzrlib import errors
from bzrlib.tests import TestCaseWithTransport

from canonical.codehosting.tests.servers import (
    make_launchpad_server, make_sftp_server)

from canonical.codehosting.tests.helpers import (
    CodeHostingTestProviderAdapter, ServerTestCase, TwistedBzrlibLayer,
    adapt_suite, deferToThread)


class TestFilesystem(ServerTestCase, TestCaseWithTransport):

    layer = TwistedBzrlibLayer

    def _cleanUp(self, result):
        # XXX: JonathanLange 2007-06-13, Override Twisted's post-test cleanup.
        # The tests fail badly if this is removed, for unknown reasons.
        # See Launchpad bug 120156.
        from twisted.internet import defer
        return defer.succeed(None)

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
        self.assertRaises(
            (errors.PermissionDenied, errors.NoSuchFile),
            transport.rmdir, 'foo')

        # The 'foo' directory is still listed.
        self.assertTrue(transport.has('bar'))
        self.assertTrue(transport.has('foo'))

    @deferToThread
    def test_make_invalid_user_directory(self):
        # The top-level directory must always be of the form '~user'. However,
        # sometimes a transport will ask to look at files that aren't of that
        # form. In that case, we raise NoSuchFile.
        transport = self.getTransport()
        self.assertRaises(
            (errors.PermissionDenied, errors.NoSuchFile),
            transport.mkdir, 'apple')

    @deferToThread
    def test_make_valid_user_directory(self):
        # Making a top-level directory is not supported by the Launchpad
        # transport.
        transport = self.getTransport()
        self.assertRaises(
            (errors.PermissionDenied, errors.NoSuchFile),
            transport.mkdir, '~apple')

    @deferToThread
    def test_make_existing_user_directory(self):
        # Making a user directory raises an error. We don't really care what
        # the error is, but it should be one of FileExists,
        # TransportNotPossible or NoSuchFile
        transport = self.getTransport()
        self.assertRaises(
            (errors.PermissionDenied, errors.NoSuchFile),
            transport.mkdir, '~testuser')

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
        self.assertRaises(
            (errors.PermissionDenied, errors.NoSuchFile),
            transport.mkdir, '~testteam/+junk/new-branch')

    @deferToThread
    def test_make_product_directory_for_nonexistent_product(self):
        # Making a branch directory for a non-existent product is not allowed.
        # Products must first be registered in Launchpad.
        transport = self.getTransport()
        self.assertRaises(
            (errors.PermissionDenied, errors.NoSuchFile),
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
    def test_directory_inside_branch(self):
        # We allow users to create new branches by pushing them beneath an
        # existing product directory.
        transport = self.getTransport()
        transport.mkdir('~testuser/firefox/banana')
        transport.mkdir('~testuser/firefox/banana/.bzr')
        self.assertTrue(transport.has('~testuser/firefox/banana'))
        self.assertTrue(transport.has('~testuser/firefox/banana/.bzr'))

    @deferToThread
    def test_non_bzr_directory_inside_branch(self):
        # Users can only create '.bzr' directories inside a branch. Other
        # directories are strictly forbidden.
        # XXX: JonathanLange 2007-06-06, What about files?
        transport = self.getTransport()
        transport.mkdir('~testuser/+junk/banana')
        self.assertRaises(
            (errors.PermissionDenied, errors.NoSuchFile),
            transport.mkdir, '~testuser/+junk/banana/republic')

    @deferToThread
    def test_make_directory_without_prefix(self):
        # Because the user and product directories don't exist on the
        # filesystem, we can create a branch directory for a product even if
        # there are no existing branches for that product.
        transport = self.getTransport()
        transport.mkdir('~testuser/thunderbird/banana')
        self.assertTrue(transport.has('~testuser/thunderbird/banana'))

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
            (errors.FileExists, IOError),
            transport.rename, 'branch/.bzr/dir1', 'branch/.bzr/dir2')

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


class TestErrorMessages(ServerTestCase, TestCaseWithTransport):

    layer = TwistedBzrlibLayer

    def _cleanUp(self, result):
        print "Overriding Twisted's cleanup because it causes errors."
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
            "a product name registered in Launchpad",
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
    servers = [make_sftp_server(), make_launchpad_server()]
    adapter = CodeHostingTestProviderAdapter(servers)
    loader = unittest.TestLoader()
    filesystem_suite = loader.loadTestsFromTestCase(TestFilesystem)
    error_suite = loader.loadTestsFromTestCase(TestErrorMessages)
    return unittest.TestSuite(
        [adapt_suite(adapter, filesystem_suite), error_suite])
