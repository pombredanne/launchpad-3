# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""Tests for Supermirror SFTP server's bzr support."""

__metaclass__ = type

import unittest
import stat

from bzrlib import errors
from bzrlib.transport import get_transport
from bzrlib.tests import TestCaseWithTransport, TestCaseWithMemoryTransport

from canonical.codehosting.transport import branch_id_to_path
from canonical.codehosting.transport import LaunchpadServer

from canonical.codehosting.tests.test_acceptance import (
    adapt_suite, AuthserverWithKeys, CodeHostingTestProviderAdapter,
    SSHCodeHostingServer, SSHTestCase)
from canonical.codehosting.tests.test_transport import FakeLaunchpad
from canonical.codehosting.tests.helpers import (
    TwistedBzrlibLayer, deferToThread)
from canonical.testing import BzrlibLayer


class SFTPTests(SSHTestCase, TestCaseWithTransport):

    layer = TwistedBzrlibLayer

    def _cleanUp(self, result):
        print "Overriding Twisted's cleanup because it causes errors."
        from twisted.internet import defer
        return defer.succeed(None)

    def installServer(self, server):
        self.server = server

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
        e = self.assertRaises(
            (errors.PermissionDenied, errors.NoSuchFile),
            transport.rmdir, 'foo')
## XXX: JonathanLange 2007-06-05, SFTP only -- HPSS hides the error message.
##         self.failUnless(
##             "removing branch directory 'foo' is not allowed." in str(e), str(e))

        # The 'foo' directory is still listed.
        self.assertTrue(transport.has('bar'))
        self.assertTrue(transport.has('foo'))

    @deferToThread
    def test_mkdir_toplevel_error(self):
        # You cannot create a top-level directory.
        transport = self.getTransport()
        e = self.assertRaises(
            (errors.PermissionDenied, errors.NoSuchFile),
            transport.mkdir, 'foo')
## XXX: JonathanLange 2007-06-05, SFTP only -- HPSS hides the error message.
##         self.failUnless(
##             "Branches must be inside a person or team directory." in str(e),
##             str(e))

    @deferToThread
    def test_mkdir_invalid_product_error(self):
        # Make some directories under ~testuser/+junk (i.e. create some empty
        # branches)
        transport = self.getTransport('~testuser')

        # You cannot create a product directory unless the product name is
        # registered in Launchpad.
        e = self.assertRaises(
            (errors.PermissionDenied, errors.NoSuchFile),
            transport.mkdir, 'no-such-product')
## XXX: JonathanLange 2007-06-05, SFTP only -- HPSS hides the error message.
##         self.failUnless(
##             "Directories directly under a user directory must be named after a "
##             "product name registered in Launchpad" in str(e),
##             str(e))

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
##         transport.mkdir('~testteam/firefox')

##         # Confirm the mkdir worked by using list_dir.
##         self.failUnless('firefox' in transport.list_dir('~testteam'))

        # You can of course mkdir a branch, too
        transport.mkdir('~testteam/firefox/shiny-new-thing')
        self.assertTrue(
            transport.has('~testteam/firefox/shiny-new-thing'))

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

# XXX: JonathanLange 2007-06-05, SFTP only test. Depends on backing transport.
##     @deferToThread
##     def test_rename_directory_to_empty_directory_succeeds(self):
##         # 'rename dir1 dir2' succeeds if 'dir2' is empty. Not sure we want this
##         # behaviour, but it's worth documenting.
##         transport = self.getTransport('~testuser/+junk')
##         transport.mkdir('branch')
##         transport.mkdir('branch/.bzr')
##         transport.mkdir('branch/.bzr/dir1')
##         transport.mkdir('branch/.bzr/dir2')
##         transport.rename('branch/.bzr/dir1', 'branch/.bzr/dir2')
##         self.assertEqual(['dir2'], transport.list_dir('branch/.bzr'))

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


class TestLaunchpadTransportMakeDirectory(SSHTestCase, TestCaseWithTransport):

    layer = TwistedBzrlibLayer

    def getDefaultServer(self):
        authserver = FakeLaunchpad()
        user_id = 1
        backing_transport = self.get_transport()
        server = LaunchpadServer(authserver, user_id, backing_transport)
        return server

    def installServer(self, server):
        self.server = server

    def getTransport(self):
        return get_transport(self.server.get_url())

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
    def test_make_product_directory_for_nonexistent_product(self):
        # Making a directory for a non-existent product is not allowed.
        # Products must first be registered in Launchpad.
        transport = self.getTransport()
        self.assertRaises(
            (errors.PermissionDenied, errors.NoSuchFile),
            transport.mkdir, '~testuser/pear')

## XXX: JonathanLange 2007-06-05, Behaves differently for SFTP and HPSS
##     @deferToThread
##     def test_make_product_directory_for_existent_product(self):
##         # The transport raises a FileExists error if it tries to make the
##         # directory of a product that is registered with Launchpad.

##         # XXX: JonathanLange 2007-05-27, do we care what the error is? It
##         # should be TransportNotPossible or FileExists. NoSuchFile might be
##         # acceptable though.
##         transport = self.getTransport()
##         self.assertRaises(
##             (errors.PermissionDenied, errors.NoSuchFile),
##             transport.mkdir, '~testuser/firefox')

    @deferToThread
    def test_make_branch_directory(self):
        # We allow users to create new branches by pushing them beneath an
        # existing product directory.
        transport = self.getTransport()
        transport.mkdir('~testuser/firefox/banana')
        # This implicitly tests that the branch has been created in the
        # database. The call to transport.has will blow up if it can't map the
        # path to a branch ID, there won't be a branch ID unless the branch is
        # in the database.
        self.assertTrue(transport.has('~testuser/firefox/banana'))
        transport.mkdir('~testteam/firefox/banana')
        self.assertTrue(transport.has('~testteam/firefox/banana'))

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
    def test_make_directory_without_prefix(self):
        # Because the user and product directories don't exist on the
        # filesystem, we can create a branch directory for a product even if
        # there are no existing branches for that product.
        transport = self.getTransport()
        transport.mkdir('~testuser/thunderbird/banana')
        self.assertTrue(transport.has('~testuser/thunderbird/banana'))

    @deferToThread
    def test_make_two_directories(self):
        # Bazaar doesn't have a makedirs() facility for transports, so we need
        # to make sure that we can make a directory on the backing transport if
        # its parents exist and if they don't exist.
        transport = self.getTransport()
        transport.mkdir('~testuser/thunderbird/banana')
        transport.mkdir('~testuser/thunderbird/orange')
        self.assertTrue(transport.has('~testuser/thunderbird/banana'))
        self.assertTrue(transport.has('~testuser/thunderbird/orange'))



class FakeLaunchpadServer(LaunchpadServer):
    def __init__(self, authserver, user_id):
        LaunchpadServer.__init__(self, authserver, user_id, None)
        self._schema = 'lp'

    def getTransport(self, path=None):
        if path is None:
            path = ''
        transport = get_transport(self.get_url()).clone(path)
        return transport

    def setUp(self):
        from bzrlib.transport.memory import MemoryTransport
        self.backing_transport = MemoryTransport()
        self.authserver = FakeLaunchpad()
        self._branches = dict(self._iter_branches())
        LaunchpadServer.setUp(self)


def make_launchpad_server():
    user_id = 1
    return FakeLaunchpadServer(FakeLaunchpad(), user_id)


def make_sftp_server():
    authserver = AuthserverWithKeys('testuser', 'testteam')
    branches_root = '/tmp/sftp-test'
    return SSHCodeHostingServer('sftp', authserver, branches_root)


def test_suite():
    servers = [make_sftp_server(), make_launchpad_server()]
    adapter = CodeHostingTestProviderAdapter(servers)
    base_suite = unittest.TestLoader().loadTestsFromName(__name__)
    return adapt_suite(adapter, base_suite)
