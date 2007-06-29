# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Acceptance tests for Supermirror SFTP server's bzr support."""

__metaclass__ = type

import os
import unittest
import xmlrpclib

import bzrlib.branch
from bzrlib.errors import NotBranchError
from bzrlib.tests.repository_implementations.test_repository import (
    TestCaseWithRepository)
from bzrlib.urlutils import local_path_from_url
from bzrlib.workingtree import WorkingTree

from canonical.codehosting.tests.helpers import (
    adapt_suite, deferToThread, ServerTestCase, TwistedBzrlibLayer)
from canonical.codehosting.tests.servers import (
    make_bzr_ssh_server, make_sftp_server)
from canonical.codehosting.transport import branch_id_to_path
from canonical.launchpad import database
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestSetup


class SSHTestCase(ServerTestCase, TestCaseWithRepository):

    layer = TwistedBzrlibLayer
    server = None

    def installServer(self, server):
        super(SSHTestCase, self).installServer(server)
        self.default_user = server.authserver.testUser
        self.default_team = server.authserver.testTeam

    def setUp(self):
        super(SSHTestCase, self).setUp()

        # Create a local branch with one revision
        tree = self.make_branch_and_tree('.')
        self.local_branch = tree.branch
        self.build_tree(['foo'])
        tree.add('foo')
        tree.commit('Added foo', rev_id='rev1')

    def runInChdir(self, func, *args, **kwargs):
        old_dir = os.getcwdu()
        os.chdir(local_path_from_url(self.local_branch.base))
        try:
            return func(*args, **kwargs)
        finally:
            os.chdir(old_dir)

    def push(self, remote_url):
        """Push the local branch to the given URL.

        This method is used to test then end-to-end behaviour of pushing Bazaar
        branches to the SFTP server.

        Do NOT run this method in the main thread! It does a blocking read from
        the SFTP server, which is running in the Twisted reactor in the main
        thread.
        """
        self.runInChdir(
            self.server.runAndWaitForDisconnect,
            self.run_bzr_captured, ['push', remote_url], retcode=None)

    def getLastRevision(self, remote_url):
        """Get the last revision at the given URL.

        Do NOT run this method in the main thread! It does a blocking read from
        the SFTP server, which is running in the Twisted reactor in the main
        thread.
        """
        return self.runInChdir(
            self.server.runAndWaitForDisconnect,
            lambda: bzrlib.branch.Branch.open(remote_url).last_revision())

    def getTransportURL(self, relpath=None, username=None):
        """Return the base URL for the tests."""
        if relpath is None:
            relpath = ''
        return self.server.get_url(username) + relpath

    def getHostedBranch(self, personName, productName, branchName):
        """Look up and return the specified branch from the database."""
        owner = database.Person.byName('testuser')
        if productName is None:
            product = None
        else:
            product = database.Product.selectOneBy(name=productName)
        return database.Branch.selectOneBy(
            owner=owner, product=product, name=branchName)


class AcceptanceTests(SSHTestCase):
    """Acceptance tests for the Launchpad codehosting service's Bazaar support.

    Originally converted from the English at
    https://launchpad.canonical.com/SupermirrorTaskList
    """

    def getDefaultServer(self):
        return make_sftp_server()

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
        self.assertEqual(self.local_branch.last_revision(), remote_revision)

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
        branch = self.getHostedBranch('testuser', None, 'test-branch')
        branch_id = branch.id
        branch.name = 'renamed-branch'
        LaunchpadZopelessTestSetup().txn.commit()

        self.push(remote_url)
        remote_revision = self.getLastRevision(remote_url)
        self.assertEqual(remote_revision, self.local_branch.last_revision())

        # Assign to a different product in the database. This is
        # effectively a Rename as far as bzr is concerned: the URL changes.
        LaunchpadZopelessTestSetup().txn.begin()
        branch = database.Branch.get(branch_id)
        branch.product = database.Product.byName('firefox')
        LaunchpadZopelessTestSetup().txn.commit()

        self.assertRaises(
            NotBranchError,
            self.runInChdir,
            self.server.runAndWaitForDisconnect,
            bzrlib.branch.Branch.open,
            self.getTransportURL('~testuser/+junk/renamed-branch'))

        remote_revision = self.getLastRevision(
            self.getTransportURL('~testuser/firefox/renamed-branch'))
        self.assertEqual(remote_revision,
                         self.local_branch.last_revision())

        # Rename person in the database. Again, the URL changes (and so
        # does the username we have to connect as!).
        LaunchpadZopelessTestSetup().txn.begin()
        branch = database.Branch.get(branch_id)
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

        # Retrieve the branch from the database.
        branch = self.getHostedBranch('testuser', None, 'test-branch')

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

    @deferToThread
    def test_push_new_branch_creates_branch_in_database(self):
        remote_url = self.getTransportURL('~testuser/+junk/totally-new-branch')
        self.push(remote_url)

        # Retrieve the branch from the database.
        LaunchpadZopelessTestSetup().txn.begin()
        branch = self.getHostedBranch('testuser', None, 'totally-new-branch')
        LaunchpadZopelessTestSetup().txn.abort()

        self.assertEqual(
            '~testuser/+junk/totally-new-branch', branch.unique_name)

    @deferToThread
    def test_push_triggers_mirror_request(self):
        # Pushing new data to a branch should trigger a mirror request.
        remote_url = self.getTransportURL('~testuser/+junk/totally-new-branch')
        self.push(remote_url)

        # Retrieve the branch from the database.
        LaunchpadZopelessTestSetup().txn.begin()
        branch = self.getHostedBranch('testuser', None, 'totally-new-branch')
        # Confirm that the branch hasn't had a mirror requested yet. Not core
        # to the test, but helpful for checking internal state.
        self.assertNotEqual(None, branch.mirror_request_time)
        branch.mirror_request_time = None
        LaunchpadZopelessTestSetup().txn.commit()

        # Add a single revision to the local branch.
        tree = WorkingTree.open(self.local_branch.base)
        tree.commit('Empty commit', rev_id='rev2')

        # Push the new revision.
        self.push(remote_url)

        # Retrieve the branch from the database.
        LaunchpadZopelessTestSetup().txn.begin()
        branch = self.getHostedBranch('testuser', None, 'totally-new-branch')
        self.assertNotEqual(None, branch.mirror_request_time)
        LaunchpadZopelessTestSetup().txn.abort()


class SmartserverTests(SSHTestCase):
    """Acceptance tests for the smartserver component of Launchpad codehosting
    service's Bazaar support.
    """

    def getDefaultServer(self):
        return make_bzr_ssh_server()

    @deferToThread
    def test_can_read_readonly_branch(self):
        # We can get information from a read-only branch.
        authserver = xmlrpclib.ServerProxy(self.server.authserver.get_url())
        sabdfl_id = authserver.getUser('sabdfl')['id']
        ro_branch_id = authserver.createBranch(sabdfl_id, '', 'ro-branch')
        ro_branch_url = 'file://' + os.path.abspath(
            os.path.join(self.server._mirror_root,
                         branch_id_to_path(ro_branch_id)))
        self.runInChdir(
            self.run_bzr_captured, ['push', '--create-prefix', ro_branch_url],
            retcode=None)

        revision = bzrlib.branch.Branch.open(ro_branch_url).last_revision()
        remote_revision = self.getLastRevision(
            self.getTransportURL('~sabdfl/+junk/ro-branch'))
        self.assertEqual(revision, remote_revision)

    @deferToThread
    def test_cant_write_to_readonly_branch(self):
        # We can't write to a read-only branch.

        # XXX: JonathanLange 2007-06-29, This test has been known to fail
        # intermittently. The cause of the failure is unknown, due partly to a
        # lack of information. To correct that, we dump the authserver log file
        # to stdout in the event of an error, so that it will appear in the PQM
        # output.
        try:
            authserver = xmlrpclib.ServerProxy(self.server.authserver.get_url())
            sabdfl_id = authserver.getUser('sabdfl')['id']
        except:
            authserver_log = open(
                self.server.authserver.tachandler.logfile, 'r')
            print '-' * 8
            print authserver_log.read()
            print '-' * 8
            authserver_log.close()
            raise
        ro_branch_id = authserver.createBranch(sabdfl_id, '', 'ro-branch')
        ro_branch_url = 'file://' + os.path.abspath(
            os.path.join(self.server._mirror_root,
                         branch_id_to_path(ro_branch_id)))
        self.runInChdir(
            self.run_bzr_captured, ['push', '--create-prefix', ro_branch_url],
            retcode=None)

        revision = bzrlib.branch.Branch.open(ro_branch_url).last_revision()

        # Create a new revision on the local branch.
        tree = WorkingTree.open(self.local_branch.base)
        tree.commit('Empty commit', rev_id='rev2')

        # Push the local branch to the remote url
        remote_url = self.getTransportURL('~sabdfl/+junk/ro-branch')
        self.push(remote_url)
        remote_revision = self.getLastRevision(remote_url)

        # UNCHANGED!
        self.assertEqual(revision, remote_revision)


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


def make_server_tests(base_suite, servers):
    from bzrlib.repository import RepositoryFormat
    from canonical.codehosting.tests.helpers import (
        CodeHostingRepositoryTestProviderAdapter)
    repository_format = RepositoryFormat.get_default_format()

    adapter = CodeHostingRepositoryTestProviderAdapter(
        repository_format, servers)
    return adapt_suite(adapter, base_suite)


def test_suite():
    base_suite = unittest.makeSuite(AcceptanceTests)
    suite = unittest.TestSuite()
    suite.addTest(make_repository_tests(base_suite))
    suite.addTest(make_server_tests(
        base_suite, [make_sftp_server, make_bzr_ssh_server]))
    suite.addTest(make_server_tests(
        unittest.makeSuite(SmartserverTests), [make_bzr_ssh_server]))
    return suite
