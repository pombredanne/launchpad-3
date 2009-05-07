# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Acceptance tests for the codehosting server."""

__metaclass__ = type

import atexit
import os
import unittest
from xml.dom.minidom import parseString
import xmlrpclib

import bzrlib.branch
from bzrlib.tests import TestCaseWithTransport
from bzrlib.urlutils import local_path_from_url
from bzrlib.workingtree import WorkingTree

from canonical.codehosting.bzrutils import DenyingServer
from canonical.codehosting.tests.helpers import (
    adapt_suite, LoomTestMixin)
from canonical.codehosting.tests.servers import (
    CodeHostingTac, set_up_test_user, SSHCodeHostingServer)
from canonical.codehosting import get_bzr_path, get_bzr_plugins_path
from canonical.codehosting.vfs import branch_id_to_path
from canonical.config import config
from canonical.launchpad import database
from canonical.launchpad.ftests import login, logout, ANONYMOUS
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestSetup
from canonical.testing import ZopelessAppServerLayer
from canonical.testing.profiled import profiled

from lp.code.interfaces.branch import BranchType
from lp.code.interfaces.branchnamespace import get_branch_namespace


class SSHServerLayer(ZopelessAppServerLayer):

    _tac_handler = None

    @classmethod
    def getTacHandler(cls):
        if cls._tac_handler is None:
            cls._tac_handler = CodeHostingTac(
                config.codehosting.hosted_branches_root,
                config.codehosting.mirrored_branches_root)
        return cls._tac_handler

    @classmethod
    @profiled
    def setUp(cls):
        tac_handler = SSHServerLayer.getTacHandler()
        tac_handler.setUp()
        SSHServerLayer._reset()
        atexit.register(tac_handler.tearDown)

    @classmethod
    @profiled
    def tearDown(cls):
        SSHServerLayer._reset()
        SSHServerLayer.getTacHandler().tearDown()

    @classmethod
    @profiled
    def _reset(cls):
        """Reset the storage."""
        SSHServerLayer.getTacHandler().clear()

    @classmethod
    @profiled
    def testSetUp(cls):
        SSHServerLayer._reset()
        set_up_test_user('testuser', 'testteam')

    @classmethod
    @profiled
    def testTearDown(cls):
        SSHServerLayer._reset()


class SSHTestCase(TestCaseWithTransport, LoomTestMixin):
    """TestCase class that runs an SSH server as well as the app server."""

    layer = SSHServerLayer
    scheme = None

    def setUp(self):
        super(SSHTestCase, self).setUp()
        tac_handler = SSHServerLayer.getTacHandler()
        self.server = SSHCodeHostingServer(self.scheme, tac_handler)
        self.server.setUp()
        self.addCleanup(self.server.tearDown)

        # Prevent creation of in-process sftp:// and bzr+ssh:// transports --
        # such connections tend to leak threads and occasionally create
        # uncollectable garbage.
        ssh_denier = DenyingServer(['bzr+ssh://', 'sftp://'])
        ssh_denier.setUp()
        self.addCleanup(ssh_denier.tearDown)

        # Create a local branch with one revision
        tree = self.make_branch_and_tree('.')
        self.local_branch = tree.branch
        self.local_branch_path = local_path_from_url(self.local_branch.base)
        self.build_tree(['foo'])
        tree.add('foo')
        tree.commit('Added foo', rev_id='rev1')

    def __str__(self):
        return self.id()

    def getTransport(self, relpath=None):
        return self.server.getTransport(relpath)

    def assertBranchesMatch(self, local_url, remote_url):
        """Assert that two branches have the same last revision."""
        local_revision = self.getLastRevision(local_url)
        remote_revision = self.getLastRevision(remote_url)
        self.assertEqual(local_revision, remote_revision)

    def runInChdir(self, directory, func, *args, **kwargs):
        old_dir = os.getcwdu()
        os.chdir(directory)
        try:
            return func(*args, **kwargs)
        finally:
            os.chdir(old_dir)

    def _run_bzr(self, args, retcode=0):
        """Call run_bzr_subprocess with some common options.

        We always want to force the subprocess to do its ssh communication
        with paramiko (because OpenSSH doesn't respect the $HOME environment
        variable) and we want to load the plugins that are in rocketfuel
        (mainly so we can test the loom support).
        """
        return self.run_bzr_subprocess(
            args, env_changes={'BZR_SSH': 'paramiko',
                               'BZR_PLUGIN_PATH': get_bzr_plugins_path()},
            allow_plugins=True, retcode=retcode)

    def _run_bzr_error(self, args):
        """Run bzr expecting an error, returning the error message.
        """
        output, error = self._run_bzr(args, retcode=3)
        for line in error.splitlines():
            if line.startswith("bzr: ERROR"):
                return line
        raise AssertionError(
            "Didn't find error line in output:\n\n%s\n" % error)

    def branch(self, remote_url, local_directory):
        """Branch from the given URL to a local directory."""
        self._run_bzr(['branch', remote_url, local_directory])

    def get_bzr_path(self):
        """See `bzrlib.tests.TestCase.get_bzr_path`.

        We override this to return the 'bzr' executable from sourcecode.
        """
        return get_bzr_path()

    def push(self, local_directory, remote_url, use_existing_dir=False):
        """Push the local branch to the given URL."""
        args = ['push', '-d', local_directory, remote_url]
        if use_existing_dir:
            args.append('--use-existing-dir')
        self._run_bzr(args)

    def assertCantPush(self, local_directory, remote_url, error_messages=()):
        """Check that we cannot push from 'local_directory' to 'remote_url'.

        In addition, if a list of messages is supplied as the error_messages
        argument, check that the bzr client printed one of these messages
        which shouldn't include the 'bzr: ERROR:' part of the message.

        :return: The last line of the stderr from the subprocess, which will
            be the 'bzr: ERROR: <repr of Exception>' line.
        """
        error_line = self._run_bzr_error(
            ['push', '-d', local_directory, remote_url])
        # This will be the will be the 'bzr: ERROR: <repr of Exception>' line.
        if not error_messages:
            return error_line
        for msg in error_messages:
            if error_line.startswith('bzr: ERROR: ' + msg):
                return error_line
        self.fail(
            "Error message %r didn't match any of those supplied."
            % error_line)

    def getLastRevision(self, remote_url):
        """Get the last revision ID at the given URL."""
        # XXX MichaelHudson, 2008-12-11: This is foul.  If revision-info took
        # a -d argument, it would be much easier (and also work in the case of
        # the null revision at the other end).  Bzr 1.11's revision-info has a
        # -d option, so when we have that in rocketfuel we can rewrite this.
        output, error = self._run_bzr(
            ['cat-revision', '-r', 'branch:' + remote_url])
        dom = parseString(output)
        return dom.documentElement.attributes['revision_id'].value

    def getTransportURL(self, relpath=None, username=None):
        """Return the base URL for the tests."""
        if relpath is None:
            relpath = ''
        return self.server.get_url(username) + relpath

    def getDatabaseBranch(self, personName, productName, branchName):
        """Look up and return the specified branch from the database."""
        owner = database.Person.byName(personName)
        if productName is None:
            product = None
        else:
            product = database.Product.selectOneBy(name=productName)
        namespace = get_branch_namespace(owner, product)
        return namespace.getByName(branchName)

    def createBazaarBranch(self, user, product, branch, creator=None,
                           branch_root=None):
        """Create a new branch in the database and push our test branch there.

        Used to create branches that the test user is not able to create, and
        might not even be able to view.
        """
        authserver = xmlrpclib.ServerProxy(
            config.codehosting.authentication_endpoint)
        branchfs = xmlrpclib.ServerProxy(config.codehosting.branchfs_endpoint)
        if creator is None:
            creator_id = authserver.getUserAndSSHKeys(user)['id']
        else:
            creator_id = authserver.getUserAndSSHKeys(creator)['id']
        if branch_root is None:
            branch_root = self.server._mirror_root
        branch_id = branchfs.createBranch(
            creator_id, '/~%s/%s/%s' % (user, product, branch))
        branch_url = 'file://' + os.path.abspath(
            os.path.join(branch_root, branch_id_to_path(branch_id)))
        self.runInChdir(
            self.local_branch_path,
            self.run_bzr, ['push', '--create-prefix', branch_url],
            retcode=None)
        return branch_url


class SmokeTest(SSHTestCase):
    """Smoke test for repository support."""

    def setUp(self):
        self.scheme = 'bzr+ssh'
        super(SmokeTest, self).setUp()
        self.first_tree = 'first'
        self.second_tree = 'second'

    def make_branch_specifying_repo_format(self, relpath, repo_format):
        bd = self.make_bzrdir(relpath, format=self.bzrdir_format)
        repo_format.initialize(bd)
        return bd.create_branch()

    def make_branch_and_tree(self, relpath):
        b = self.make_branch_specifying_repo_format(
            relpath, self.repository_format)
        return b.bzrdir.create_workingtree()

    def test_smoke(self):
        # Make a new branch
        tree = self.make_branch_and_tree(self.first_tree)

        # Push up a new branch.
        remote_url = self.getTransportURL('~testuser/+junk/new-branch')
        self.push(self.first_tree, remote_url)
        # XXX MichaelHudson, 2008-12-11: The way that getLastRevision is
        # currently implemented doesn't work with empty branches.  When it can
        # be rewritten to use revision-info, the next line can be re-enabled.
        # See comment in getLastRevision for more.
        #self.assertBranchesMatch(self.first_tree, remote_url)

        # Commit to it.
        tree.commit('new revision', allow_pointless=True)

        # Push it up again.
        self.push(self.first_tree, remote_url)
        self.assertBranchesMatch(self.first_tree, remote_url)

        # Pull it back down.
        self.branch(remote_url, self.second_tree)
        self.assertBranchesMatch(self.first_tree, self.second_tree)


class AcceptanceTests(SSHTestCase):
    """Acceptance tests for the Launchpad codehosting service.

    Originally converted from the English at
    https://launchpad.canonical.com/SupermirrorTaskList
    """

    def assertNotBranch(self, url):
        """Assert that there's no branch at 'url'."""
        error_line = self._run_bzr_error(
            ['cat-revision', '-r', 'branch:' + url])
        self.assertTrue(
            error_line.startswith('bzr: ERROR: Not a branch:'),
            'Expected "Not a branch", found %r' % error_line)

    def makeDatabaseBranch(self, owner_name, product_name, branch_name,
                           branch_type=BranchType.HOSTED):
        """Create a new branch in the database."""
        owner = database.Person.selectOneBy(name=owner_name)
        if product_name == '+junk':
            product = None
        else:
            product = database.Product.selectOneBy(name=product_name)
        if branch_type == BranchType.MIRRORED:
            url = 'http://example.com'
        else:
            url = None

        namespace = get_branch_namespace(owner, product)
        return namespace.createBranch(
            branch_type=branch_type, name=branch_name, registrant=owner,
            url=url)

    def test_push_to_new_branch(self):
        """
        The bzr client should be able to read and write to the codehosting
        server just like another other server.  This means that actions
        like:
            * `bzr push bzr+ssh://testinstance/somepath`
            * `bzr log sftp://testinstance/somepath`
        (and/or their bzrlib equivalents) and so on should work, so long as
        the user has permission to read or write to those URLs.
        """
        remote_url = self.getTransportURL('~testuser/+junk/test-branch')
        self.push(self.local_branch_path, remote_url)
        self.assertBranchesMatch(self.local_branch_path, remote_url)

    def test_push_to_existing_branch(self):
        """Pushing to an existing branch must work."""
        # Initial push.
        remote_url = self.getTransportURL('~testuser/+junk/test-branch')
        self.push(self.local_branch_path, remote_url)
        remote_revision = self.getLastRevision(remote_url)
        self.assertEqual(remote_revision, 'rev1')
        # Add a single revision to the local branch.
        tree = WorkingTree.open(self.local_branch.base)
        tree.commit('Empty commit', rev_id='rev2')
        # Push the new revision.
        self.push(self.local_branch_path, remote_url)
        self.assertBranchesMatch(self.local_branch_path, remote_url)

    def test_rename_branch(self):
        """
        Branches should be able to be renamed in the Launchpad webapp, and
        those renames should be immediately reflected in subsequent SFTP
        connections.

        Also, the renames may happen in the database for other reasons, e.g.
        if the DBA running a one-off script.
        """

        # Push the local branch to the server
        remote_url = self.getTransportURL('~testuser/+junk/test-branch')
        self.push(self.local_branch_path, remote_url)

        # Rename branch in the database
        LaunchpadZopelessTestSetup().txn.begin()
        branch = self.getDatabaseBranch('testuser', None, 'test-branch')
        branch.name = 'renamed-branch'
        LaunchpadZopelessTestSetup().txn.commit()

        # Check that it's not at the old location.
        self.assertNotBranch(
            self.getTransportURL('~testuser/+junk/test-branch'))

        # Check that it *is* at the new location.
        self.assertBranchesMatch(
            self.local_branch_path,
            self.getTransportURL('~testuser/+junk/renamed-branch'))


    def test_rename_product(self):
        # Push the local branch to the server
        remote_url = self.getTransportURL('~testuser/+junk/test-branch')
        self.push(self.local_branch_path, remote_url)

        # Assign to a different product in the database. This is effectively a
        # rename as far as bzr is concerned: the URL changes.
        LaunchpadZopelessTestSetup().txn.begin()
        branch = self.getDatabaseBranch('testuser', None, 'test-branch')
        branch.product = database.Product.byName('firefox')
        LaunchpadZopelessTestSetup().txn.commit()

        self.assertNotBranch(
            self.getTransportURL('~testuser/+junk/test-branch'))

        self.assertBranchesMatch(
            self.local_branch_path,
            self.getTransportURL('~testuser/firefox/test-branch'))

    def test_rename_user(self):
        # Rename person in the database. Again, the URL changes (and so does
        # the username we have to connect as!).
        remote_url = self.getTransportURL('~testuser/+junk/test-branch')
        self.push(self.local_branch_path, remote_url)

        LaunchpadZopelessTestSetup().txn.begin()
        branch = self.getDatabaseBranch('testuser', None, 'test-branch')
        # Renaming a person requires a Zope interaction.
        login(ANONYMOUS)
        branch.owner.name = 'renamed-user'
        logout()
        LaunchpadZopelessTestSetup().txn.commit()

        # Check that it's not at the old location.
        self.assertNotBranch(
            self.getTransportURL(
                '~testuser/+junk/test-branch', 'renamed-user'))

        # Check that it *is* at the new location.
        self.assertBranchesMatch(
            self.local_branch_path,
            self.getTransportURL(
                '~renamed-user/+junk/test-branch', 'renamed-user'))

    def test_push_team_branch(self):
        remote_url = self.getTransportURL('~testteam/firefox/a-new-branch')
        self.push(self.local_branch_path, remote_url)
        self.assertBranchesMatch(self.local_branch_path, remote_url)

    def test_push_new_branch_creates_branch_in_database(self):
        remote_url = self.getTransportURL(
            '~testuser/+junk/totally-new-branch')
        self.push(self.local_branch_path, remote_url)

        # Retrieve the branch from the database.
        LaunchpadZopelessTestSetup().txn.begin()
        branch = self.getDatabaseBranch(
            'testuser', None, 'totally-new-branch')
        LaunchpadZopelessTestSetup().txn.abort()

        self.assertEqual(
            '~testuser/+junk/totally-new-branch', branch.unique_name)

    def test_push_triggers_mirror_request(self):
        # Pushing new data to a branch should trigger a mirror request.
        remote_url = self.getTransportURL(
            '~testuser/+junk/totally-new-branch')
        self.push(self.local_branch_path, remote_url)

        # Retrieve the branch from the database.
        LaunchpadZopelessTestSetup().txn.begin()
        branch = self.getDatabaseBranch(
            'testuser', None, 'totally-new-branch')
        # Confirm that the branch hasn't had a mirror requested yet. Not core
        # to the test, but helpful for checking internal state.
        self.assertNotEqual(None, branch.next_mirror_time)
        branch.next_mirror_time = None
        LaunchpadZopelessTestSetup().txn.commit()

        # Add a single revision to the local branch.
        tree = WorkingTree.open(self.local_branch.base)
        tree.commit('Empty commit', rev_id='rev2')

        # Push the new revision.
        self.push(self.local_branch_path, remote_url)

        # Retrieve the branch from the database.
        LaunchpadZopelessTestSetup().txn.begin()
        branch = self.getDatabaseBranch(
            'testuser', None, 'totally-new-branch')
        self.assertNotEqual(None, branch.next_mirror_time)
        LaunchpadZopelessTestSetup().txn.abort()

    def test_cant_access_private_branch(self):
        # Trying to get information about a private branch should fail as if
        # the branch doesn't exist.

        # 'salgado' is a member of landscape-developers.
        salgado = database.Person.selectOneBy(name='salgado')
        landscape_dev = database.Person.selectOneBy(
            name='landscape-developers')
        self.assertTrue(
            salgado.inTeam(landscape_dev),
            "salgado should be a member of landscape-developers, but isn't.")

        # Make a private branch.
        branch_url = self.createBazaarBranch(
            'landscape-developers', 'landscape', 'some-branch',
            creator='salgado')
        # Sanity checking that the branch is actually there. We don't care
        # about the result, only that the call succeeds.
        self.getLastRevision(branch_url)

        # Check that testuser can't access the branch.
        remote_url = self.getTransportURL(
            '~landscape-developers/landscape/some-branch')
        self.assertNotBranch(remote_url)

    def test_can_push_to_existing_hosted_branch(self):
        # If a hosted branch exists in the database, but not on the
        # filesystem, and is writable by the user, then the user is able to
        # push to it.
        LaunchpadZopelessTestSetup().txn.begin()
        branch = self.makeDatabaseBranch('testuser', 'firefox', 'some-branch')
        remote_url = self.getTransportURL(branch.unique_name)
        LaunchpadZopelessTestSetup().txn.commit()
        self.push(self.local_branch_path, remote_url, use_existing_dir=True)
        self.assertBranchesMatch(self.local_branch_path, remote_url)

    def test_cant_push_to_existing_mirrored_branch(self):
        # Users cannot push to mirrored branches.
        LaunchpadZopelessTestSetup().txn.begin()
        branch = self.makeDatabaseBranch(
            'testuser', 'firefox', 'some-branch', BranchType.MIRRORED)
        remote_url = self.getTransportURL(branch.unique_name)
        LaunchpadZopelessTestSetup().txn.commit()
        self.assertCantPush(
            self.local_branch_path, remote_url,
            ['Permission denied:', 'Transport operation not possible:'])

    def test_cant_push_to_existing_unowned_hosted_branch(self):
        # Users can only push to hosted branches that they own.
        LaunchpadZopelessTestSetup().txn.begin()
        branch = self.makeDatabaseBranch('sabdfl', 'firefox', 'some-branch')
        remote_url = self.getTransportURL(branch.unique_name)
        LaunchpadZopelessTestSetup().txn.commit()
        self.assertCantPush(
            self.local_branch_path, remote_url,
            ['Permission denied:', 'Transport operation not possible:'])

    def test_can_push_loom_branch(self):
        # We can push and pull a loom branch.
        tree = self.makeLoomBranchAndTree('loom')
        remote_url = self.getTransportURL('~testuser/+junk/loom')
        self.push('loom', remote_url)
        self.assertBranchesMatch('loom', remote_url)


class SmartserverTests(SSHTestCase):
    """Acceptance tests for the codehosting smartserver."""

    def makeMirroredBranch(self, person_name, product_name, branch_name):
        ro_branch_url = self.createBazaarBranch(
            person_name, product_name, branch_name)

        # Mark as mirrored.
        LaunchpadZopelessTestSetup().txn.begin()
        branch = self.getDatabaseBranch(
            person_name, product_name, branch_name)
        branch.branch_type = BranchType.MIRRORED
        branch.url = "http://example.com/smartservertest/branch"
        LaunchpadZopelessTestSetup().txn.commit()
        return ro_branch_url

    def test_can_read_readonly_branch(self):
        # We can get information from a read-only branch.
        ro_branch_url = self.createBazaarBranch(
            'sabdfl', '+junk', 'ro-branch')
        revision = bzrlib.branch.Branch.open(ro_branch_url).last_revision()
        remote_revision = self.getLastRevision(
            self.getTransportURL('~sabdfl/+junk/ro-branch'))
        self.assertEqual(revision, remote_revision)

    def test_cant_write_to_readonly_branch(self):
        # We can't write to a read-only branch.
        ro_branch_url = self.createBazaarBranch(
            'sabdfl', '+junk', 'ro-branch')
        revision = bzrlib.branch.Branch.open(ro_branch_url).last_revision()

        # Create a new revision on the local branch.
        tree = WorkingTree.open(self.local_branch.base)
        tree.commit('Empty commit', rev_id='rev2')

        # Push the local branch to the remote url
        remote_url = self.getTransportURL('~sabdfl/+junk/ro-branch')
        self.assertCantPush(self.local_branch_path, remote_url)

    def test_can_read_mirrored_branch(self):
        # Users should be able to read mirrored branches that they own.
        # Added to catch bug 126245.
        ro_branch_url = self.makeMirroredBranch(
            'testuser', 'firefox', 'mirror')
        revision = bzrlib.branch.Branch.open(ro_branch_url).last_revision()
        remote_revision = self.getLastRevision(
            self.getTransportURL('~testuser/firefox/mirror'))
        self.assertEqual(revision, remote_revision)

    def test_can_read_unowned_mirrored_branch(self):
        # Users should be able to read mirrored branches even if they don't
        # own those branches.
        ro_branch_url = self.makeMirroredBranch('sabdfl', 'firefox', 'mirror')
        revision = bzrlib.branch.Branch.open(ro_branch_url).last_revision()
        remote_revision = self.getLastRevision(
            self.getTransportURL('~sabdfl/firefox/mirror'))
        self.assertEqual(revision, remote_revision)

    def test_authserver_error_propagation(self):
        # Errors raised by createBranch on the authserver should be displayed
        # sensibly by the client.  We test this by pushing to a product that
        # does not exist (the other error message possibilities are covered by
        # unit tests).
        remote_url = self.getTransportURL('~sabdfl/no-such-product/branch')
        message = "Project 'no-such-product' does not exist."
        last_line = self.assertCantPush(self.local_branch_path, remote_url)
        self.assertTrue(
            message in last_line, '%r not in %r' % (message, last_line))


def make_server_tests(base_suite, servers):
    from canonical.codehosting.tests.helpers import (
        CodeHostingTestProviderAdapter)
    adapter = CodeHostingTestProviderAdapter(servers)
    return adapt_suite(adapter, base_suite)


def make_smoke_tests(base_suite):
    from bzrlib.tests.per_repository import (
        all_repository_format_scenarios,
        )
    excluded_scenarios = [
        # RepositoryFormat4 is not initializable (bzrlib raises TestSkipped
        # when you try).
        'RepositoryFormat4',
        # Fetching weave formats from the smart server is known to be broken.
        # See bug 173807 and bzrlib.tests.test_repository.
        'RepositoryFormat5',
        'RepositoryFormat6',
        'RepositoryFormat7',
        ]
    scenarios = all_repository_format_scenarios()
    scenarios = [
        scenario for scenario in scenarios
        if scenario[0] not in excluded_scenarios
        and not scenario[0].startswith('RemoteRepositoryFormat')]
    new_suite = unittest.TestSuite()
    try:
        from bzrlib.tests import multiply_tests
        multiply_tests(base_suite, scenarios, new_suite)
    except ImportError:
        # XXX: MichaelHudson, 2009-03-11: This except clause can be deleted
        # once sourcecode/bzr has bzr.dev r4102.
        from bzrlib.tests import adapt_tests, TestScenarioApplier
        adapter = TestScenarioApplier()
        adapter.scenarios = scenarios
        adapt_tests(base_suite, adapter, new_suite)
    return new_suite


def test_suite():
    base_suite = unittest.makeSuite(AcceptanceTests)
    suite = unittest.TestSuite()

    suite.addTest(make_server_tests(base_suite, ['sftp', 'bzr+ssh']))
    suite.addTest(make_server_tests(
            unittest.makeSuite(SmartserverTests), ['bzr+ssh']))
    suite.addTest(make_smoke_tests(unittest.makeSuite(SmokeTest)))
    return suite
