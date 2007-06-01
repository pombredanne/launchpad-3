# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Acceptance tests for Supermirror SFTP server's bzr support."""

__metaclass__ = type

import gc
import os
import shutil
import signal
import tempfile
import threading
import unittest

import bzrlib.branch
from bzrlib.errors import NoSuchFile, NotBranchError, PermissionDenied
from bzrlib.tests.repository_implementations.test_repository import (
    TestCaseWithRepository)
from bzrlib.transport import get_transport, sftp, ssh, Server
from bzrlib.urlutils import local_path_from_url
from bzrlib.workingtree import WorkingTree

from twisted.conch.ssh import keys
from twisted.python.util import sibpath
from twisted.trial.unittest import TestCase as TrialTestCase

from canonical.codehosting.sftponly import (
    BazaarFileTransferServer, SFTPOnlyAvatar)
from canonical.codehosting.tests.helpers import (
    deferToThread, TwistedBzrlibLayer)
from canonical.config import config
from canonical.database.sqlbase import cursor, commit, sqlvalues
from canonical.launchpad import database
from canonical.launchpad.daemons.authserver import AuthserverService
from canonical.launchpad.daemons.sftp import SFTPService
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestSetup


class Authserver(Server):

    def __init__(self):
        self.authserver = AuthserverService()

    def setUp(self):
        self.authserver.startService()

    def tearDown(self):
        self.authserver.stopService()

    def get_url(self):
        return config.codehosting.authserver


class AuthserverWithKeys(Authserver):

    def __init__(self, testUser, testTeam):
        Authserver.__init__(self)
        self.testUser = testUser
        self.testTeam = testTeam

    def setUp(self):
        self.setUpTestUser()
        Authserver.setUp(self)

    def setUpTestUser(self):
        """Prepare 'testUser' and 'testTeam' Persons, giving 'testUser' a known
        SSH key.
        """
        # insert SSH keys for testuser -- and insert testuser!
        cur = cursor()
        cur.execute(
            "UPDATE Person SET name = '%s' WHERE name = 'spiv';"
            % self.testUser)
        cur.execute(
            "UPDATE Person SET name = '%s' WHERE name = 'name18';"
            % self.testTeam)
        cur.execute("""
            INSERT INTO SSHKey (person, keytype, keytext, comment)
            VALUES (7, 2,
            'AAAAB3NzaC1kc3MAAABBAL5VoWG5sy3CnLYeOw47L8m9A15hA/PzdX2u0B7c2Z1ktFPcEaEuKbLqKVSkXpYm7YwKj9y88A9Qm61CdvI0c50AAAAVAKGY0YON9dEFH3DzeVYHVEBGFGfVAAAAQCoe0RhBcefm4YiyQVwMAxwTlgySTk7FSk6GZ95EZ5Q8/OTdViTaalvGXaRIsBdaQamHEBB+Vek/VpnF1UGGm8YAAABAaCXDl0r1k93JhnMdF0ap4UJQ2/NnqCyoE8Xd5KdUWWwqwGdMzqB1NOeKN6ladIAXRggLc2E00UsnUXh3GE3Rgw==',
            'testuser');
            """)
        commit()

    def getPrivateKey(self):
        """Return the private key object used by 'testuser' for auth."""
        return keys.getPrivateKeyObject(
            data=open(sibpath(__file__, 'id_dsa'), 'rb').read())

    def getPublicKey(self):
        """Return the public key string used by 'testuser' for auth."""
        return keys.getPublicKeyString(
            data=open(sibpath(__file__, 'id_dsa.pub'), 'rb').read())


class CodeHostingServer(Server):

    def __init__(self, authserver, branches_root):
        self.authserver = authserver
        self._branches_root = branches_root

    def setUp(self):
        if os.path.isdir(self._branches_root):
            shutil.rmtree(self._branches_root)
        os.makedirs(self._branches_root, 0700)
        shutil.copytree(
            sibpath(__file__, 'keys'),
            os.path.join(self._branches_root, 'keys'))
        self.authserver.setUp()

    def tearDown(self):
        self.authserver.tearDown()
        shutil.rmtree(self._branches_root)

    def getTransport(self, relpath):
        """Return a new transport for 'relpath', adding necessary cleanup."""
        raise NotImplementedError()


class SSHCodeHostingServer(CodeHostingServer):

    def setUpFakeHome(self):
        user_home = os.path.abspath(tempfile.mkdtemp())
        os.makedirs(os.path.join(user_home, '.ssh'))
        shutil.copyfile(
            sibpath(__file__, 'id_dsa'),
            os.path.join(user_home, '.ssh', 'id_dsa'))
        shutil.copyfile(
            sibpath(__file__, 'id_dsa.pub'),
            os.path.join(user_home, '.ssh', 'id_dsa.pub'))
        os.chmod(os.path.join(user_home, '.ssh', 'id_dsa'), 0600)
        real_home, os.environ['HOME'] = os.environ['HOME'], user_home
        return real_home, user_home

    def forceParamiko(self):
        _old_vendor_manager = ssh._ssh_vendor_manager._cached_ssh_vendor
        ssh._ssh_vendor_manager._cached_ssh_vendor = ssh.ParamikoVendor()
        return _old_vendor_manager

    def setUp(self):
        self._real_home, self._fake_home = self.setUpFakeHome()
        self._old_vendor_manager = self.forceParamiko()
        CodeHostingServer.setUp(self)
        self.server = TestSSHService()
        self.server.startService()

    def tearDown(self):
        self.server.stopService()
        os.environ['HOME'] = self._real_home
        CodeHostingServer.tearDown(self)
        shutil.rmtree(self._fake_home)
        ssh._ssh_vendor_manager._cached_ssh_vendor = self._old_vendor_manager

    def get_url(self, user=None):
        if user is None:
            user = self.authserver.testUser
        return '%s://%s@localhost:22222/' % (self._schema, user)

    def runAndWaitForDisconnect(self, func, *args, **kwargs):
        """Run the given function, close all SFTP connections, and wait for the
        server to acknowledge the end of the session.
        """
        ever_connected = threading.Event()
        done = threading.Event()
        self.server.setConnectionMadeEvent(ever_connected)
        self.server.setConnectionLostEvent(done)
        try:
            return func(*args, **kwargs)
        finally:
            self.closeAllConnections()
            # done.wait() can block forever if func() never actually
            # connects, so only wait if we are sure that the client
            # connected.
            if ever_connected.isSet():
                done.wait()


class SFTPCodeHostingServer(SSHCodeHostingServer):

    def setUp(self):
        SSHCodeHostingServer.setUp(self)
        self._schema = 'sftp'
        self._clients_to_close = []

    def tearDown(self):
        self._closeClients(self._clients_to_close)
        SSHCodeHostingServer.tearDown(self)

    def _closeClients(self, clients):
        while clients:
            client = clients.pop()
            client.close()
            client.sock.transport.close()

    def closeAllConnections(self):
        """Closes all open bzrlib SFTP connections.

        bzrlib doesn't provide a facility for closing sftp connections. The
        closest it gets is clearing the connection cache and forcing the
        connection objects to be garbage collected. This means that this method
        won't actually close a connection if a reference to it is still around.
        """
        self._closeClients(sftp._connected_hosts.values())
        sftp.clear_connection_cache()
        gc.collect()

    def getTransport(self, path=None):
        """Get a paramiko transport pointing to `path` on the base server."""
        if path is None:
            path = ''
        transport = get_transport(self.get_url()).clone(path)
        self._clients_to_close.append(transport._sftp)
        return transport


class SmartSSHCodeHostingServer(SSHCodeHostingServer):

    def setUp(self):
        SSHCodeHostingServer.setUp(self)
        self._schema = 'bzr+ssh'

    def getTransport(self, path=None):
        if path is None:
            path = ''
        transport = get_transport(self.get_url()).clone(path)
        return transport

    def closeAllConnections(self):
        pass


class TestSSHService(SFTPService):
    """SSH service that uses the the TestSFTPOnlyAvatar and installs the test
    keys in a place that the SSH server can find them.

    This class, TestSFTPOnlyAvatar and TestBazaarFileTransferServer work
    together to provide a threading event which is set when the first
    connecting XXX client closes its connection to the SSH server.
    """

    _connection_lost_event = None
    _connection_made_event = None
    avatar = None

    def getConnectionLostEvent(self):
        return self._connection_lost_event

    def getConnectionMadeEvent(self):
        return self._connection_made_event

    def setConnectionLostEvent(self, event):
        self._connection_lost_event = event

    def setConnectionMadeEvent(self, event):
        self._connection_made_event = event

    def makeRealm(self):
        realm = SFTPService.makeRealm(self)
        realm.avatarFactory = self.makeAvatar
        return realm

    def makeAvatar(self, avatarId, homeDirsRoot, userDict, launchpad):
        self.avatar = TestSFTPOnlyAvatar(self, avatarId, homeDirsRoot,
                                         userDict, launchpad)
        return self.avatar


class TestSFTPOnlyAvatar(SFTPOnlyAvatar):
    """SSH avatar that uses the TestBazaarFileTransferServer."""

    def __init__(self, service, avatarId, homeDirsRoot, userDict, launchpad):
        SFTPOnlyAvatar.__init__(self, avatarId, homeDirsRoot, userDict,
                                launchpad)
        self.service = service
        self.subsystemLookup = {'sftp': self.makeFileTransferServer}

    def getConnectionLostEvent(self):
        return self.service.getConnectionLostEvent()

    def getConnectionMadeEvent(self):
        return self.service.getConnectionMadeEvent()

    def makeFileTransferServer(self, data=None, avatar=None):
        return TestBazaarFileTransferServer(data, avatar)


class TestBazaarFileTransferServer(BazaarFileTransferServer):
    """BazaarFileTransferServer that sets a threading event when it loses its
    first connection.
    """
    def __init__(self, data=None, avatar=None):
        BazaarFileTransferServer.__init__(self, data=data, avatar=avatar)
        self.avatar = avatar

    def getConnectionLostEvent(self):
        return self.avatar.getConnectionLostEvent()

    def getConnectionMadeEvent(self):
        return self.avatar.getConnectionMadeEvent()

    def connectionMade(self):
        event = self.getConnectionMadeEvent()
        if event is not None:
            event.set()

    def connectionLost(self, reason):
        d = self.sendMirrorRequests()
        event = self.getConnectionLostEvent()
        if event is not None:
            d.addBoth(lambda ignored: event.set())
        return d


class SSHTestCase(TrialTestCase, TestCaseWithRepository):

    server = None
    default_user = 'testuser'
    default_team = 'testteam'

    def installServer(self, server):
        self.server = server
        self.default_user = server.authserver.testUser
        self.default_team = server.authserver.testTeam

    def setUpSignalHandling(self):
        oldSigChld = signal.getsignal(signal.SIGCHLD)
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        self.addCleanup(lambda: signal.signal(signal.SIGCHLD, oldSigChld))

    def setUp(self):
        super(SSHTestCase, self).setUp()

        # Install the default SIGCHLD handler so that read() calls don't get
        # EINTR errors when child processes exit.
        self.setUpSignalHandling()

        if self.server is None:
            authserver = AuthserverWithKeys(
                self.default_user, self.default_team)
            branches_root = '/tmp/sftp-test'
            self.server = SFTPCodeHostingServer(authserver, branches_root)

        self.server.setUp()
        self.addCleanup(self.server.tearDown)

    def __str__(self):
        return self.id()

    def getTransportURL(self, relpath=None, username=None):
        """Return the base URL for the tests."""
        if relpath is None:
            relpath = ''
        return self.server.get_url(username) + relpath


class AcceptanceTests(SSHTestCase):
    """Acceptance tests for the Launchpad codehosting service's Bazaar support.

    Originally converted from the English at
    https://launchpad.canonical.com/SupermirrorTaskList
    """

    layer = TwistedBzrlibLayer

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

    def setUp(self):
        super(AcceptanceTests, self).setUp()

        # Create a local branch with one revision
        tree = self.make_branch_and_tree('.')
        self.local_branch = tree.branch
        self.build_tree(['foo'])
        tree.add('foo')
        tree.commit('Added foo', rev_id='rev1')

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
        self.assertRaises((NoSuchFile, PermissionDenied),
                          self.runAndWaitForDisconnect,
                          transport.mkdir, 'hello')

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



class CodeHostingTestProviderAdapter:

    def __init__(self, format, servers):
        self._repository_format = format
        self._servers = servers

    def adapt(self, test):
        from copy import deepcopy
        from bzrlib.tests import default_transport
        result = unittest.TestSuite()
        for server in self._servers:
            new_test = deepcopy(test)
            new_test.transport_server = default_transport
            new_test.transport_readonly_server = None
            new_test.bzrdir_format = self._repository_format._matchingbzrdir
            new_test.repository_format = self._repository_format
            new_test.installServer(server)
            def make_new_test_id():
                new_id = "%s(%s)" % (new_test.id(), server.__class__.__name__)
                return lambda: new_id
            new_test.id = make_new_test_id()
            result.addTest(new_test)
        return result


def adapt_suite(adapter, base_suite):
    from bzrlib.tests import iter_suite_tests
    suite = unittest.TestSuite()
    for test in iter_suite_tests(base_suite):
        suite.addTests(adapter.adapt(test))
    return suite


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
    repository_format = RepositoryFormat.get_default_format()

    authserver = AuthserverWithKeys('testuser', 'testteam')
    branches_root = '/tmp/sftp-test'
    servers = [
        SFTPCodeHostingServer(authserver, branches_root),
        SmartSSHCodeHostingServer(authserver, branches_root)]
    adapter = CodeHostingTestProviderAdapter(repository_format, servers)
    return adapt_suite(adapter, base_suite)


def test_suite():
    base_suite = unittest.makeSuite(AcceptanceTests)
    suite = unittest.TestSuite()
    suite.addTest(make_repository_tests(base_suite))
    suite.addTest(make_server_tests(base_suite))
    return suite
