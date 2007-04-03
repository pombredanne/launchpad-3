# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Acceptance tests for Supermirror SFTP server's bzr support.
"""

__metaclass__ = type

import unittest
import tempfile
import os
import signal
import shutil
import gc
import threading

import bzrlib.branch
from bzrlib.tests import TestCaseInTempDir, TestCaseWithMemoryTransport
from bzrlib.tests.repository_implementations.test_repository import (
    TestCaseWithRepository)
# XXX -- Unused, but needed to work-around bug in bzr 0.11
# Jonathan Lange, 2007-03-22
##from bzrlib.tests import blackbox
from bzrlib.errors import NoSuchFile, NotBranchError, PermissionDenied
from bzrlib.transport import get_transport
from bzrlib.transport import sftp, ssh
from bzrlib.urlutils import local_path_from_url
from bzrlib.workingtree import WorkingTree

from twisted.internet import defer, threads
from twisted.python.util import sibpath
from twisted.trial.unittest import TestCase as TrialTestCase

import canonical
from canonical.config import config
from canonical.database.sqlbase import cursor, commit
from canonical.launchpad import database
from canonical.launchpad.daemons.authserver import AuthserverService
from canonical.launchpad.daemons.sftp import SFTPService
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestSetup
from canonical.supermirrorsftp.sftponly import (
    BazaarFileTransferServer, SFTPOnlyAvatar)
from canonical.database.sqlbase import sqlvalues
from canonical.testing import TwistedLayer


def deferToThread(f):
    """Run the given callable in a separate thread and return a Deferred which
    fires when the function completes.
    """
    def decorated(*args, **kwargs):
        d = defer.Deferred()
        def runInThread():
            return threads._putResultInDeferred(d, f, args, kwargs)

        t = threading.Thread(target=runInThread)
        t.start()
        return d
    return decorated


class TestSFTPService(SFTPService):
    """SFTP service that uses the the TestSFTPOnlyAvatar and installs the test
    keys in a place that the SFTP server can find them.

    This class, TestSFTPOnlyAvatar and TestBazaarFileTransferServer work
    together to provide a threading event which is set when the first
    connecting client closes its connection to the SFTP server.
    """

    root = '/tmp/sftp-test'
    _event = None

    def setConnectionLostEvent(self, event):
        self._event = event

    def setUpRoot(self):
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)
        os.makedirs(self.root, 0700)
        shutil.copytree(sibpath(__file__, 'keys'),
                        os.path.join(self.root, 'keys'))

    def makeRealm(self):
        realm = SFTPService.makeRealm(self)
        realm.avatarFactory = self.makeAvatar
        return realm

    def makeAvatar(self, avatarId, homeDirsRoot, userDict, launchpad):
        self.avatar = TestSFTPOnlyAvatar(avatarId, homeDirsRoot,
                                         userDict, launchpad)
        self.avatar._event = self._event
        return self.avatar

    def makeService(self):
        self.setUpRoot()
        return SFTPService.makeService(self)


class TestSFTPOnlyAvatar(SFTPOnlyAvatar):
    """SFTP avatar that uses the TestBazaarFileTransferServer."""
    def __init__(self, avatarId, homeDirsRoot, userDict, launchpad):
        SFTPOnlyAvatar.__init__(self, avatarId, homeDirsRoot, userDict,
                                launchpad)
        self.subsystemLookup = {'sftp': self.makeFileTransferServer}

    def makeFileTransferServer(self, data=None, avatar=None):
        return TestBazaarFileTransferServer(self._event, data, avatar)


class TestBazaarFileTransferServer(BazaarFileTransferServer):
    """BazaarFileTransferServer that sets a threading event when it loses its
    first connection.
    """
    def __init__(self, event, data=None, avatar=None):
        BazaarFileTransferServer.__init__(self, data=data, avatar=avatar)
        self.connectionLostEvent = event

    def connectionLost(self, reason):
        d = self.sendMirrorRequests()
        if self.connectionLostEvent is not None:
            d.addBoth(lambda ignored: self.connectionLostEvent.set())
        return d


class SFTPTestCase(TrialTestCase, TestCaseWithRepository):

    def setUp(self):
        # Install the default SIGCHLD handler so that read() calls don't get
        # EINTR errors when child processes exit.
        self._oldSigChld = signal.getsignal(signal.SIGCHLD)
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        super(SFTPTestCase, self).setUp()

        # insert SSH keys for testuser -- and insert testuser!
        cur = cursor()
        cur.execute(
            "UPDATE Person SET name = 'testuser' WHERE name = 'spiv';")
        cur.execute(
            "UPDATE Person SET name = 'testteam' WHERE name = 'name18';")
        cur.execute("""
            INSERT INTO SSHKey (person, keytype, keytext, comment)
            VALUES (7, 2,
            'AAAAB3NzaC1kc3MAAABBAL5VoWG5sy3CnLYeOw47L8m9A15hA/PzdX2u0B7c2Z1ktFPcEaEuKbLqKVSkXpYm7YwKj9y88A9Qm61CdvI0c50AAAAVAKGY0YON9dEFH3DzeVYHVEBGFGfVAAAAQCoe0RhBcefm4YiyQVwMAxwTlgySTk7FSk6GZ95EZ5Q8/OTdViTaalvGXaRIsBdaQamHEBB+Vek/VpnF1UGGm8YAAABAaCXDl0r1k93JhnMdF0ap4UJQ2/NnqCyoE8Xd5KdUWWwqwGdMzqB1NOeKN6ladIAXRggLc2E00UsnUXh3GE3Rgw==',
            'testuser');
            """)
        commit()

        # Point $HOME at a test ssh config and key.
        self.userHome = os.path.abspath(tempfile.mkdtemp())
        os.makedirs(os.path.join(self.userHome, '.ssh'))
        shutil.copyfile(
            sibpath(__file__, 'id_dsa'),
            os.path.join(self.userHome, '.ssh', 'id_dsa'))
        shutil.copyfile(
            sibpath(__file__, 'id_dsa.pub'),
            os.path.join(self.userHome, '.ssh', 'id_dsa.pub'))
        os.chmod(os.path.join(self.userHome, '.ssh', 'id_dsa'), 0600)
        self.realHome = os.environ['HOME']
        os.environ['HOME'] = self.userHome

        # XXX spiv 2005-01-13:
        # Force bzrlib to use paramiko (because OpenSSH doesn't respect $HOME)
        _old_vendor_manager = ssh._ssh_vendor_manager._cached_ssh_vendor
        def restore_vendor_manager():
            ssh._ssh_vendor_manager._cached_ssh_vendor = _old_vendor_manager
        self.addCleanup(restore_vendor_manager)
        ssh._ssh_vendor_manager._cached_ssh_vendor = ssh.ParamikoVendor()

        # Start authserver.
        self.authserver = AuthserverService()
        self.authserver.startService()

        # Start the SFTP server
        self.server = TestSFTPService()
        self.server.startService()
        self.server_base = 'sftp://testuser@localhost:22222/'

    def tearDown(self):
        # Undo setUp.
        self.server.stopService()

        # XXX: spiv 2006-02-09: manually break cycles in uncollectable garbage
        # caused by the server shutting down while paramiko clients still have
        # connections to it.  This bug has been fixed in upstream paramiko, so
        # soon this will be unnecessary.
        gc.collect()
        obj = None
        for obj in gc.garbage:
            if getattr(obj, 'auth_handler', None) is not None:
                obj.auth_handler = None
        del obj
        del gc.garbage[:]
        gc.collect()

        os.environ['HOME'] = self.realHome
        self.authserver.stopService()
        # XXX spiv 2006-04-27: We need to do bzrlib's tear down first, because
        # LaunchpadZopelessTestSetup's tear down will remove bzrlib's logging
        # handlers, causing it to blow up.  See bug #41697.
        super(SFTPTestCase, self).tearDown()

        shutil.rmtree(self.userHome)

        # XXX spiv 2006-04-28: as the comment bzrlib.tests.run_suite says, this
        # is "a little bogus".  Because we aren't using the bzr test runner, we
        # have to manually clean up the test????.tmp dirs.
        shutil.rmtree(TestCaseWithMemoryTransport.TEST_ROOT)
        TestCaseWithMemoryTransport.TEST_ROOT = None
        signal.signal(signal.SIGCHLD, self._oldSigChld)

    def closeAllConnections(self):
        """Closes all open bzrlib SFTP connections.

        bzrlib doesn't provide a facility for closing sftp connections. The
        closest it gets is clearing the connection cache and forcing the
        connection objects to be garbage collected. This means that this method
        won't actually close a connection if a reference to it is still around.
        """
        for client in sftp._connected_hosts.values():
            client.close()
            client.sock.transport.close()
        sftp.clear_connection_cache()
        gc.collect()


class AcceptanceTests(SFTPTestCase):
    """
    These are the agreed acceptance tests for the Supermirror SFTP system's
    initial implementation of bzr support, converted from the English at
    https://launchpad.canonical.com/SupermirrorTaskList
    """
    layer = TwistedLayer

    def setUp(self):
        super(AcceptanceTests, self).setUp()

        # Create a local branch with one revision
        tree = self.make_branch_and_tree('.')
        self.local_branch = tree.branch
        self.build_tree(['foo'])
        tree.add('foo')
        tree.commit('Added foo', rev_id='rev1')

    @deferToThread
    def _test_1_bzr_sftp(self):
        """
        The bzr client should be able to read and write to the Supermirror SFTP
        server just like another other SFTP server.  This means that actions
        like:
            * `bzr push sftp://testinstance/somepath`
            * `bzr log sftp://testinstance/somepath`
        (and/or their bzrlib equivalents) and so on should work, so long as the
        user has permission to read or write to those URLs.
        """
        remote_url = self.server_base + '~testuser/+junk/test-branch'
        remote_revision = self._push(remote_url)
        self.assertEqual(self.local_branch.last_revision(),
                         remote_revision)

    def test_1_bzr_sftp(self):
        return self._test_1_bzr_sftp()

    def _push(self, remote_url):
        # Do not run this in the main thread! It does a blocking read from the
        # SFTP server, which is running in the Twisted reactor in this process.
        old_dir = os.getcwdu()
        os.chdir(local_path_from_url(self.local_branch.base))
        try:
            push_done = threading.Event()
            self.server.setConnectionLostEvent(push_done)
            self.run_bzr_captured(['push', remote_url], retcode=None)
            result = bzrlib.branch.Branch.open(remote_url).last_revision()
            self.closeAllConnections()
            push_done.wait()
        finally:
            os.chdir(old_dir)
        return result

    @deferToThread
    def _test_bzr_push_again(self):
        """Pushing to an existing branch must work.

        test_1_bzr_sftp tests that the initial push works. Here we test that
        pushing further revisions to an existing branch works as well.
        """
        # Initial push.
        remote_url = self.server_base + '~testuser/+junk/test-branch'
        remote_revision = self._push(remote_url)
        self.assertEqual(remote_revision, 'rev1')
        # Add a single revision to the local branch.
        tree = WorkingTree.open(self.local_branch.base)
        tree.commit('Empty commit', rev_id='rev2')
        # Push the new revision.
        remote_revision = self._push(remote_url)
        self.assertEqual(remote_revision, 'rev2')

    def test_bzr_push_again(self):
        return self._test_bzr_push_again()

    @deferToThread
    def _test_2_namespace_restrictions(self):
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
        self._test_missing_parent_directory(
            '~testuser/product-that-does-not-exist/hello')

        # Teams do not have +junk products
        self._test_missing_parent_directory('~testteam/+junk/hello')

        # Cannot push to team directories that the user isn't a member of --
        # they cannot see them at all.
        self._test_missing_parent_directory('~not-my-team/real-product/hello')

        # XXX spiv 2006-01-11: what about lp-incompatible branch dir names (e.g.
        # capital Letters) -- Are they disallowed or accepted?  If accepted,
        # what will that branch's Branch.name be in the database?  Probably just
        # disallow, and try to have a tolerable error.

    def test_2_namespace_restrictions(self):
        return self._test_2_namespace_restrictions()

    def _test_missing_parent_directory(self, relpath):
        transport = get_transport(self.server_base + relpath).clone('..')
        self.assertRaises((NoSuchFile, PermissionDenied),
                          transport.mkdir, 'hello')

    @deferToThread
    def _test_3_db_rename_branch(self):
        """
        Branches should be able to be renamed in the Launchpad webapp, and
        those renames should be immediately reflected in subsequent SFTP
        connections.

        Also, the renames may happen in the database for other reasons, e.g. if
        the DBA running a one-off script.
        """

        # Push the local branch to the server
        remote_url = self.server_base + '~testuser/+junk/test-branch'
        self._push(remote_url)

        # Rename branch in the database
        LaunchpadZopelessTestSetup().txn.begin()
        testuser = database.Person.byName('testuser')
        branch = database.Branch.selectOneBy(
            ownerID=testuser.id, name='test-branch')
        self.branch_id = branch.id
        branch.name = 'renamed-branch'
        LaunchpadZopelessTestSetup().txn.commit()

        # Force bzrlib to make a new SFTP connection.
        self.closeAllConnections()

        remote_revision = self._push(remote_url)
        self.assertEqual(remote_revision, self.local_branch.last_revision())

        # Assign to a different product in the database. This is
        # effectively a Rename as far as bzr is concerned: the URL changes.
        LaunchpadZopelessTestSetup().txn.begin()
        branch = database.Branch.get(self.branch_id)
        branch.product = database.Product.byName('firefox')
        LaunchpadZopelessTestSetup().txn.commit()

        self.closeAllConnections()

        self.assertRaises(
            NotBranchError,
            bzrlib.branch.Branch.open,
            self.server_base + '~testuser/+junk/renamed-branch')

        remote_branch = bzrlib.branch.Branch.open(
            self.server_base + '~testuser/firefox/renamed-branch')
        self.assertEqual(remote_branch.last_revision(),
                         self.local_branch.last_revision())

        # Rename person in the database. Again, the URL changes (and so
        # does the username we have to connect as!).
        LaunchpadZopelessTestSetup().txn.begin()
        branch = database.Branch.get(self.branch_id)
        branch.owner.name = 'renamed-user'
        LaunchpadZopelessTestSetup().txn.commit()

        server_base = self.server_base.replace('testuser', 'renamed-user')
        remote_branch = bzrlib.branch.Branch.open(
            server_base + '~renamed-user/firefox/renamed-branch')
        self.assertEqual(remote_branch.last_revision(),
                         self.local_branch.last_revision())

    def test_3_db_rename_branch(self):
        return self._test_3_db_rename_branch()


    # Test 4: URL for mirroring
    #    There should be an API that can generate a URL for a branch for
    #    copy-to-mirror script to use. For example, for a branch with a database
    #    ID of 0xabcdef12, the URL may be something like
    #    `/srv/supermirrorsftp/branches/ab/cd/ef/12`.
    # This is covered by
    # canonical.launchpad.ftests.test_branchpulllist.test_branch_pull_render


    @deferToThread
    def _test_5_mod_rewrite_data(self):
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
        self._push(self.server_base + '~testuser/+junk/test-branch')

        # Retrieve the branch from the database.  selectOne will fail if the
        # branch does not exist (or if somehow multiple branches match!).
        branch = database.Branch.selectOne(
            "owner = %s AND product IS NULL AND name = %s"
            % sqlvalues(database.Person.byName('testuser').id, 'test-branch'))

        self.assertEqual(None, branch.url)
        # If we get this far, the branch has been correctly inserted into the
        # database.

    def test_5_mod_rewrite_data(self):
        return self._test_5_mod_rewrite_data()

    @deferToThread
    def _test_push_team_branch(self):
        remote_url = self.server_base + '~testteam/firefox/a-new-branch'
        remote_revision = self._push(remote_url)
        # Check that the pushed branch looks right
        self.assertEqual(remote_revision, self.local_branch.last_revision())

    def test_push_team_branch(self):
        return self._test_push_team_branch()


def test_suite():
    # Construct a test suite that runs AcceptanceTests with several different
    # repository formats.
    from bzrlib.repository import (
        format_registry, RepositoryTestProviderAdapter)
    from bzrlib.repofmt.weaverepo import RepositoryFormat6
    from bzrlib.tests import (
        adapt_modules, default_transport, TestSuite, iter_suite_tests)
    supported_formats = [RepositoryFormat6()]
    supported_formats.extend([
        format_registry.get(k) for k in format_registry.keys()])
    adapter = RepositoryTestProviderAdapter(
        default_transport,
        # None here will cause a readonly decorator to be created
        # by the TestCaseWithTransport.get_readonly_transport method.
        None,
        [(format, format._matchingbzrdir) for format in
         supported_formats])

    suite = unittest.TestSuite()
    for test in iter_suite_tests(unittest.makeSuite(AcceptanceTests)):
        suite.addTests(adapter.adapt(test))
    return suite


# Be paranoid since we trash directories as part of this.
assert config.default_section == 'testrunner', \
        'Imported dangerous test harness outside of the test runner'
