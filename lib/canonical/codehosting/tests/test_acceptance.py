# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Acceptance tests for Supermirror SFTP server's bzr support."""

__metaclass__ = type

import os
import unittest

import bzrlib.branch
from bzrlib.errors import NoSuchFile, NotBranchError, PermissionDenied
from bzrlib.tests.repository_implementations.test_repository import (
    TestCaseWithRepository)
from bzrlib.urlutils import local_path_from_url
from bzrlib.workingtree import WorkingTree

from canonical.codehosting.tests.helpers import (
    adapt_suite, deferToThread, ServerTestCase, TwistedBzrlibLayer)
from canonical.codehosting.tests.servers import (
    AuthserverWithKeys, SSHCodeHostingServer)
from canonical.database.sqlbase import sqlvalues
from canonical.launchpad import database
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestSetup


class AcceptanceTests(ServerTestCase, TestCaseWithRepository):
    """Acceptance tests for the Launchpad codehosting service's Bazaar support.

    Originally converted from the English at
    https://launchpad.canonical.com/SupermirrorTaskList
    """

    layer = TwistedBzrlibLayer

    server = None

    def getDefaultServer(self):
        authserver = AuthserverWithKeys('testuser', 'testteam')
        branches_root = '/tmp/sftp-test'
        return SSHCodeHostingServer('sftp', authserver, branches_root)

    def installServer(self, server):
        super(AcceptanceTests, self).installServer(server)
        self.default_user = server.authserver.testUser
        self.default_team = server.authserver.testTeam

    def setUp(self):
        super(AcceptanceTests, self).setUp()

        # Create a local branch with one revision
        tree = self.make_branch_and_tree('.')
        self.local_branch = tree.branch
        self.build_tree(['foo'])
        tree.add('foo')
        tree.commit('Added foo', rev_id='rev1')

    def runAndWaitForDisconnect(self, func, *args, **kwargs):
        old_dir = os.getcwdu()
        os.chdir(local_path_from_url(self.local_branch.base))
        try:
            result = self.server.runAndWaitForDisconnect(func, *args, **kwargs)
        finally:
            os.chdir(old_dir)
        return result

    def push(self, remote_url):
        """Push the local branch to the given URL.

        This method is used to test then end-to-end behaviour of pushing Bazaar
        branches to the SFTP server.

        Do NOT run this method in the main thread! It does a blocking read from
        the SFTP server, which is running in the Twisted reactor in the main
        thread.
        """
        self.runAndWaitForDisconnect(
            self.run_bzr_captured, ['push', remote_url], retcode=None)

    def getLastRevision(self, remote_url):
        """Get the last revision at the given URL.

        Do NOT run this method in the main thread! It does a blocking read from
        the SFTP server, which is running in the Twisted reactor in the main
        thread.
        """
        return self.runAndWaitForDisconnect(
            lambda: bzrlib.branch.Branch.open(remote_url).last_revision())

    def getTransportURL(self, relpath=None, username=None):
        """Return the base URL for the tests."""
        if relpath is None:
            relpath = ''
        return self.server.get_url(username) + relpath

    @deferToThread
    def test_bzr_sftp(self):
        """
        The bzr client should be able to read and write to the Supermirror SFTP
        server just like another other SFTP server.  This means that actions
        like:
            * `bzr push sftp://testinstance/somepath`
            * `bzr log sftp://testinstance/somepath`
        (and/or their bzrlib equivalents) and so on should work, so long as the
        user has permission to read or write to those URLs.
        """
        remote_url = self.getTransportURL('~testuser/+junk/test-branch')
        self.push(remote_url)
        remote_revision = self.getLastRevision(remote_url)
        self.assertEqual(self.local_branch.last_revision(),
                         remote_revision)

    @deferToThread
    def test_bzr_push_again(self):
        """Pushing to an existing branch must work.

        test_1_bzr_sftp tests that the initial push works. Here we test that
        pushing further revisions to an existing branch works as well.
        """
        # Initial push.
        remote_url = self.getTransportURL('~testuser/+junk/test-branch')
        self.push(remote_url)
        remote_revision = self.getLastRevision(remote_url)
        self.assertEqual(remote_revision, 'rev1')
        # Add a single revision to the local branch.
        tree = WorkingTree.open(self.local_branch.base)
        tree.commit('Empty commit', rev_id='rev2')
        # Push the new revision.
        self.push(remote_url)
        remote_revision = self.getLastRevision(remote_url)
        self.assertEqual(remote_revision, 'rev2')

    @deferToThread
    def test_namespace_restrictions(self):
        """
        The namespace restrictions described in
        SupermirrorFilesystemHierarchy should be enforced. So operations
        such as:
            * `bzr push sftp://testinstance/~user/missing-product/new-branch`
            * `bzr push sftp://testinstance/~not-my-team/real-product/some-branch`
            * `bzr push sftp://testinstance/~team/+junk/anything`
        should fail.
        """
        # Cannot push branches to products that don't exist
        self._testMissingParentDirectory(
            '~testuser/product-that-does-not-exist/hello')

        # Teams do not have +junk products
        self._testMissingParentDirectory('~testteam/+junk/hello')

        # Cannot push to team directories that the user isn't a member of --
        # they cannot see them at all.
        self._testMissingParentDirectory('~not-my-team/real-product/hello')

        # XXX spiv 2006-01-11: what about lp-incompatible branch dir names (e.g.
        # capital Letters) -- Are they disallowed or accepted?  If accepted,
        # what will that branch's Branch.name be in the database?  Probably just
        # disallow, and try to have a tolerable error.

    def _testMissingParentDirectory(self, relpath):
        transport = self.server.getTransport(relpath).clone('..')
        try:
            self.assertRaises(
                (NoSuchFile, PermissionDenied),
                self.runAndWaitForDisconnect, transport.mkdir, 'hello')
        except self.failureException, e:
            raise AssertionError("%s: %s" % (e, relpath))

    @deferToThread
    def test_db_rename_branch(self):
        """
        Branches should be able to be renamed in the Launchpad webapp, and
        those renames should be immediately reflected in subsequent SFTP
        connections.

        Also, the renames may happen in the database for other reasons, e.g. if
        the DBA running a one-off script.
        """

        # Push the local branch to the server
        remote_url = self.getTransportURL('~testuser/+junk/test-branch')
        self.push(remote_url)

        # Rename branch in the database
        LaunchpadZopelessTestSetup().txn.begin()
        testuser = database.Person.byName('testuser')
        branch = database.Branch.selectOneBy(
            ownerID=testuser.id, name='test-branch')
        self.branch_id = branch.id
        branch.name = 'renamed-branch'
        LaunchpadZopelessTestSetup().txn.commit()

        self.push(remote_url)
        remote_revision = self.getLastRevision(remote_url)
        self.assertEqual(remote_revision, self.local_branch.last_revision())

        # Assign to a different product in the database. This is
        # effectively a Rename as far as bzr is concerned: the URL changes.
        LaunchpadZopelessTestSetup().txn.begin()
        branch = database.Branch.get(self.branch_id)
        branch.product = database.Product.byName('firefox')
        LaunchpadZopelessTestSetup().txn.commit()

        self.assertRaises(
            NotBranchError,
            self.runAndWaitForDisconnect,
            bzrlib.branch.Branch.open,
            self.getTransportURL('~testuser/+junk/renamed-branch'))

        remote_revision = self.getLastRevision(
            self.getTransportURL('~testuser/firefox/renamed-branch'))
        self.assertEqual(remote_revision,
                         self.local_branch.last_revision())

        # Rename person in the database. Again, the URL changes (and so
        # does the username we have to connect as!).
        LaunchpadZopelessTestSetup().txn.begin()
        branch = database.Branch.get(self.branch_id)
        branch.owner.name = 'renamed-user'
        LaunchpadZopelessTestSetup().txn.commit()

        url = self.getTransportURL(
            '~renamed-user/firefox/renamed-branch', 'renamed-user')
        remote_revision = self.getLastRevision(url)
        self.assertEqual(remote_revision, self.local_branch.last_revision())

    @deferToThread
    def test_mod_rewrite_data(self):
        """
        A mapping file for use with Apache's mod_rewrite should be generated
        correctly.
        """
        # We already test that the mapping file is correctly generated from the
        # database in
        # lib/canonical/launchpad/scripts/ftests/test_supermirror_rewritemap.py,
        # so here we just need to show that creating a branch puts the right
        # values in the database.

        # Push branch to sftp server
        self.push(self.getTransportURL('~testuser/+junk/test-branch'))

        # Retrieve the branch from the database.  selectOne will fail if the
        # branch does not exist (or if somehow multiple branches match!).
        branch = database.Branch.selectOne(
            "owner = %s AND product IS NULL AND name = %s"
            % sqlvalues(database.Person.byName('testuser').id, 'test-branch'))

        self.assertEqual(None, branch.url)
        # If we get this far, the branch has been correctly inserted into the
        # database.

    @deferToThread
    def test_push_team_branch(self):
        remote_url = self.getTransportURL('~testteam/firefox/a-new-branch')
        self.push(remote_url)
        remote_revision = self.getLastRevision(remote_url)
        # Check that the pushed branch looks right
        self.assertEqual(remote_revision, self.local_branch.last_revision())


def make_repository_tests(base_suite):
    # Construct a test suite that runs AcceptanceTests with several different
    # repository formats.
    #
    # We do this so that we can be sure that users can host various different
    # formats without any trouble.
    from bzrlib.repository import RepositoryTestProviderAdapter
    from bzrlib.repository import format_registry
    from bzrlib.repofmt.weaverepo import RepositoryFormat6
    from bzrlib.tests import default_transport

    # Test all the formats except for the default. The default format is tested
    # by the server tests.
    supported_formats = [RepositoryFormat6()]
    supported_formats.extend([
        format_registry.get(k) for k in format_registry.keys()
        if k != format_registry.default_key])
    adapter = RepositoryTestProviderAdapter(
        default_transport,
        # None here will cause a readonly decorator to be created
        # by the TestCaseWithTransport.get_readonly_transport method.
        None,
        [(format, format._matchingbzrdir) for format in supported_formats])

    return adapt_suite(adapter, base_suite)


def make_server_tests(base_suite):
    from bzrlib.repository import RepositoryFormat
    from canonical.codehosting.tests.helpers import (
        CodeHostingRepositoryTestProviderAdapter)
    repository_format = RepositoryFormat.get_default_format()

    authserver = AuthserverWithKeys('testuser', 'testteam')
    branches_root = '/tmp/sftp-test'
    servers = [
        SSHCodeHostingServer('sftp', authserver, branches_root),
        SSHCodeHostingServer('bzr+ssh', authserver, branches_root)]
    adapter = CodeHostingRepositoryTestProviderAdapter(
        repository_format, servers)
    return adapt_suite(adapter, base_suite)


def test_suite():
    base_suite = unittest.makeSuite(AcceptanceTests)
    suite = unittest.TestSuite()
    suite.addTest(make_repository_tests(base_suite))
    suite.addTest(make_server_tests(base_suite))
    return suite
