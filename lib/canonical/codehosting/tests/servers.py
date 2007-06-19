# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Servers used in codehosting tests."""

__metaclass__ = type

__all__ = [
    'Authserver', 'AuthserverWithKeys', 'CodeHostingServer',
    'SSHCodeHostingServer', 'make_bzr_ssh_server', 'make_launchpad_server',
    'make_sftp_server']


import gc
import os
import shutil
import tempfile
import threading

from bzrlib.transport import get_transport, sftp, ssh, Server

from twisted.conch.interfaces import ISession
from twisted.conch.ssh import keys
from twisted.internet import defer, protocol
from twisted.protocols import basic
from twisted.python import components
from twisted.python.util import sibpath

from canonical.config import config
from canonical.database.sqlbase import commit, cursor
from canonical.launchpad.daemons.tachandler import TacTestSetup
from canonical.launchpad.daemons.sftp import SSHService
from canonical.launchpad.daemons.authserver import AuthserverService

from canonical.codehosting.smartserver import launch_smart_server
from canonical.codehosting.sshserver import (
    BazaarFileTransferServer, LaunchpadAvatar)
from canonical.codehosting.transport import LaunchpadServer

from canonical.codehosting.tests.helpers import FakeLaunchpad


def make_launchpad_server():
    user_id = 1
    return FakeLaunchpadServer(user_id)


def make_sftp_server():
    authserver = AuthserverWithKeys('testuser', 'testteam')
    branches_root = '/tmp/sftp-test'
    return SFTPCodeHostingServer(authserver, branches_root)


def make_bzr_ssh_server():
    authserver = AuthserverWithKeys('testuser', 'testteam')
    branches_root = '/tmp/sftp-test'
    return BazaarSSHCodeHostingServer(authserver, branches_root)


class ConnectionTrackingParamikoVendor(ssh.ParamikoVendor):
    """Wrapper for ParamikoVendor that tracks connections.

    Used by the test suite to make sure that all connections are closed in a
    timely fashion.
    """

    def __init__(self):
        ssh.ParamikoVendor.__init__(self)
        self._ssh_transports = []
        self._ssh_channels = []
        self._sftp_clients = []

    def _connect(self, username, password, host, port):
        transport = ssh.ParamikoVendor._connect(
            self, username, password, host, port)
        self._ssh_transports.append(transport)
        return transport

    def connect_sftp(self, username, password, host, port):
        client = ssh.ParamikoVendor.connect_sftp(
            self, username, password, host, port)
        self._sftp_clients.append(client)
        return client

    def _closeAllTransports(self):
        if self._sftp_clients:
            while self._sftp_clients:
                client = self._sftp_clients.pop()
                client.close()
            sftp.clear_connection_cache()
            gc.collect()
        while self._ssh_transports:
            connection = self._ssh_transports.pop()
            connection.close()


class Authserver(Server):

    def __init__(self):
        self.authserver = None

    def setUp(self):
        self.authserver = AuthserverService()
        self.authserver.startService()

    def tearDown(self):
        return self.authserver.stopService()

    def get_url(self):
        return config.codehosting.authserver


class AuthserverTac(TacTestSetup):
    """Handler for running the Authserver .tac file.

    Used to run the authserver out-of-process.
    """
    def setUpRoot(self):
        pass

    @property
    def root(self):
        return ''

    @property
    def tacfile(self):
        import canonical
        return os.path.abspath(os.path.join(
            os.path.dirname(canonical.__file__), os.pardir, os.pardir,
            'daemons/authserver.tac'
            ))

    @property
    def pidfile(self):
        return '/tmp/authserver.pid'

    @property
    def logfile(self):
        return '/tmp/authserver.log'


class AuthserverOutOfProcess(Server):
    """Server to run the authserver out-of-process."""

    def __init__(self):
        self.tachandler = AuthserverTac()

    def setUp(self):
        self.tachandler.setUp()

    def tearDown(self):
        self.tachandler.tearDown()
        return defer.succeed(None)

    def get_url(self):
        return config.codehosting.authserver


class AuthserverWithKeys(AuthserverOutOfProcess):
    """Server to run the authserver, setting up SSH key configuration."""

    def __init__(self, testUser, testTeam):
        AuthserverOutOfProcess.__init__(self)
        self.testUser = testUser
        self.testTeam = testTeam

    def setUp(self):
        self.setUpTestUser()
        AuthserverOutOfProcess.setUp(self)

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


class FakeLaunchpadServer(LaunchpadServer):

    def __init__(self, user_id):
        authserver = FakeLaunchpad()
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
        shutil.rmtree(self._branches_root)
        return self.authserver.tearDown()

    def getTransport(self, relpath):
        """Return a new transport for 'relpath', adding necessary cleanup."""
        raise NotImplementedError()


class SSHCodeHostingServer(CodeHostingServer):

    def __init__(self, schema, authserver, branches_root):
        self._schema = schema
        CodeHostingServer.__init__(self, authserver, branches_root)

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
        vendor = ConnectionTrackingParamikoVendor()
        ssh._ssh_vendor_manager._cached_ssh_vendor = vendor
        return _old_vendor_manager

    def getTransport(self, path=None):
        if path is None:
            path = ''
        transport = get_transport(self.get_url()).clone(path)
        return transport

    def closeAllConnections(self):
        ssh._ssh_vendor_manager._cached_ssh_vendor._closeAllTransports()

    def setUp(self):
        self._real_home, self._fake_home = self.setUpFakeHome()
        self._old_vendor_manager = self.forceParamiko()
        CodeHostingServer.setUp(self)
        self.server = _TestSSHService()
        self.server.startService()

    def tearDown(self):
        self.closeAllConnections()
        deferred1 = self.server.stopService()
        os.environ['HOME'] = self._real_home
        deferred2 = CodeHostingServer.tearDown(self)
        shutil.rmtree(self._fake_home)
        ssh._ssh_vendor_manager._cached_ssh_vendor = self._old_vendor_manager
        return defer.gatherResults([deferred1, deferred2])

    def get_url(self, user=None):
        if user is None:
            user = self.authserver.testUser
        return '%s://%s@localhost:22222/' % (self._schema, user)


class SFTPCodeHostingServer(SSHCodeHostingServer):

    def __init__(self, authserver, branches_root):
        SSHCodeHostingServer.__init__(self, 'sftp', authserver, branches_root)

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


LPSERVE_TERMINATED = 'lpserve terminated'
LPSERVE_SOCKET_VARIABLE = 'TEST_SERVICE'


class UnrecognizedLine(Exception):
    """Raised when the _DisconnectNotifyProtocol receives an unrecognized line.
    """


class _DisconnectNotifyProtocol(basic.LineOnlyReceiver):
    """Protocol that listens for notification of disconnect from a subprocess.
    """

    def __init__(self, disconnectEvent):
        self._disconnectEvent = disconnectEvent

    def lineReceived(self, line):
        if line.strip() == LPSERVE_TERMINATED:
            # set the event
            self._disconnectEvent.set()
        else:
            raise UnrecognizedLine(line)


class _DisconnectNotifyServerFactory(protocol.ServerFactory):
    """Factory to launch a server that listens for notification of disconnect.
    """

    def __init__(self):
        self._disconnectEvent = None

    def setConnectionLostEvent(self, event):
        self._disconnectEvent = event

    def buildProtocol(self, address):
        return _DisconnectNotifyProtocol(self._disconnectEvent)


class BazaarSSHCodeHostingServer(SSHCodeHostingServer):

    def __init__(self, authserver, branches_root):
        SSHCodeHostingServer.__init__(
            self, 'bzr+ssh', authserver, branches_root)
        self._factory = _DisconnectNotifyServerFactory()

    def setUp(self):
        SSHCodeHostingServer.setUp(self)
        from twisted.internet import reactor
        self._listening = reactor.listenTCP(0, self._factory)

    def tearDown(self):
        deferred1 = self._listening.stopListening()
        deferred2 = SSHCodeHostingServer.tearDown(self)
        return defer.gatherResults([deferred1, deferred2])

    # Send an event from the child process if the environment variable is set.

    def runAndWaitForDisconnect(self, func, *args, **kwargs):
        """Run the given function, close all connections, and wait for the
        server to acknowledge the end of the session.
        """
        done = threading.Event()
        self._factory.setConnectionLostEvent(done)
        def make_test_launchpad_server(avatar):
            server = launch_smart_server(avatar)
            address = self._listening.getHost()
            server.environment[LPSERVE_SOCKET_VARIABLE] = '%s:%s' % (address.host, address.port)
            return server
        components.ALLOW_DUPLICATES, ALLOW_DUPLICATES = True, components.ALLOW_DUPLICATES
        old_adapter = components.getAdapterFactory(
            LaunchpadAvatar, ISession, None)
        components.registerAdapter(
            make_test_launchpad_server, LaunchpadAvatar, ISession)
        try:
            return func(*args, **kwargs)
        finally:
            self.closeAllConnections()
            done.wait()
            self._factory.setConnectionLostEvent(None)
            if old_adapter is not None:
                components.registerAdapter(
                    old_adapter, LaunchpadAvatar, ISession)
            components.ALLOW_DUPLICATES = ALLOW_DUPLICATES


class _TestSSHService(SSHService):
    """SSH service that uses the the _TestLaunchpadAvatar and installs the test
    keys in a place that the SSH server can find them.

    This class, _TestLaunchpadAvatar and _TestBazaarFileTransferServer work
    together to provide a threading event which is set when the first
    connecting SSH client closes its connection to the SSH server.
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
        realm = SSHService.makeRealm(self)
        realm.avatarFactory = self.makeAvatar
        return realm

    def makeAvatar(self, avatarId, homeDirsRoot, userDict, launchpad):
        self.avatar = _TestLaunchpadAvatar(self, avatarId, homeDirsRoot,
                                           userDict, launchpad)
        return self.avatar


class _TestLaunchpadAvatar(LaunchpadAvatar):
    """SSH avatar that uses the _TestBazaarFileTransferServer."""

    def __init__(self, service, avatarId, homeDirsRoot, userDict, launchpad):
        LaunchpadAvatar.__init__(self, avatarId, homeDirsRoot, userDict,
                                 launchpad)
        self.service = service
        self.subsystemLookup = {'sftp': self.makeFileTransferServer}

    def getConnectionLostEvent(self):
        return self.service.getConnectionLostEvent()

    def getConnectionMadeEvent(self):
        return self.service.getConnectionMadeEvent()

    def makeFileTransferServer(self, data=None, avatar=None):
        return _TestBazaarFileTransferServer(data, avatar)


class _TestBazaarFileTransferServer(BazaarFileTransferServer):
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
