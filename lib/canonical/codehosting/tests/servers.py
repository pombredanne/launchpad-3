# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Servers used in codehosting tests."""

__metaclass__ = type

__all__ = [
    'SSHCodeHostingServer',
    'make_bzr_ssh_server',
    'make_launchpad_server',
    'make_sftp_server',
    ]


import gc
import os
import shutil
import tempfile

from zope.component import getUtility

from bzrlib.transport import get_transport, ssh, Server

from twisted.python.util import sibpath

from canonical.codehosting import get_rocketfuel_root
from canonical.config import config
from canonical.database.sqlbase import commit
from canonical.launchpad.daemons.tachandler import TacTestSetup
from canonical.launchpad.interfaces import (
    IPersonSet, ISSHKeySet, SSHKeyType, TeamSubscriptionPolicy)


def make_sftp_server():
    branches_root = config.codehosting.branches_root
    mirror_root = config.supermirror.branchesdest
    return SSHCodeHostingServer('sftp', branches_root, mirror_root)


def make_bzr_ssh_server():
    branches_root = config.codehosting.branches_root
    mirror_root = config.supermirror.branchesdest
    return SSHCodeHostingServer('bzr+ssh', branches_root, mirror_root)


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
            gc.collect()
        while self._ssh_transports:
            connection = self._ssh_transports.pop()
            connection.close()


def set_up_host_keys_for_testing():
    """Put ssh host keys into a directory where the server will find them."""
    key_pair_path = config.codehosting.host_key_pair_path
    if os.path.isdir(key_pair_path):
        shutil.rmtree(key_pair_path)
    parent = os.path.dirname(key_pair_path)
    if not os.path.isdir(parent):
        os.makedirs(parent)
    shutil.copytree(
        sibpath(__file__, 'keys'), os.path.join(key_pair_path))


def set_up_test_user(test_user, test_team):
    """Configure a user called 'test_user' with SSH keys.

    Also make sure that 'test_user' belongs to 'test_team'.
    """
    person_set = getUtility(IPersonSet)
    testUser = person_set.getByName('no-priv')
    testUser.name = test_user
    testTeam = person_set.newTeam(
        testUser, test_team, test_team,
        subscriptionpolicy=TeamSubscriptionPolicy.OPEN)
    testUser.join(testTeam)
    ssh_key_set = getUtility(ISSHKeySet)
    ssh_key_set.new(
        testUser, SSHKeyType.DSA,
        'AAAAB3NzaC1kc3MAAABBAL5VoWG5sy3CnLYeOw47L8m9A15hA/PzdX2u0B7c2Z1k'
        'tFPcEaEuKbLqKVSkXpYm7YwKj9y88A9Qm61CdvI0c50AAAAVAKGY0YON9dEFH3Dz'
        'eVYHVEBGFGfVAAAAQCoe0RhBcefm4YiyQVwMAxwTlgySTk7FSk6GZ95EZ5Q8/OTd'
        'ViTaalvGXaRIsBdaQamHEBB+Vek/VpnF1UGGm8YAAABAaCXDl0r1k93JhnMdF0ap'
        '4UJQ2/NnqCyoE8Xd5KdUWWwqwGdMzqB1NOeKN6ladIAXRggLc2E00UsnUXh3GE3R'
        'gw==', 'testuser')
    commit()


class CodeHostingTac(TacTestSetup):

    def __init__(self, hosted_area, mirrored_area):
        super(CodeHostingTac, self).__init__()
        # The hosted area.
        self._branches_root = hosted_area
        # The mirrored area.
        self._mirror_root = mirrored_area
        # Where the pidfile, logfile etc will go.
        self._server_root = tempfile.mkdtemp()

    def setUpRoot(self):
        if os.path.isdir(self._branches_root):
            shutil.rmtree(self._branches_root)
        os.makedirs(self._branches_root, 0700)
        if os.path.isdir(self._mirror_root):
            shutil.rmtree(self._mirror_root)
        os.makedirs(self._mirror_root, 0700)
        set_up_host_keys_for_testing()
        set_up_test_user('testuser', 'testteam')

    def tearDownRoot(self):
        shutil.rmtree(self._branches_root)
        shutil.rmtree(self._server_root)

    @property
    def root(self):
        return self._server_root

    @property
    def tacfile(self):
        return os.path.abspath(
            os.path.join(get_rocketfuel_root(), 'daemons/sftp.tac'))

    @property
    def logfile(self):
        return os.path.join(self.root, 'codehosting.log')

    @property
    def pidfile(self):
        return os.path.join(self.root, 'codehosting.pid')


class SSHCodeHostingServer(Server):

    def __init__(self, schema, branches_root, mirror_root):
        Server.__init__(self)
        self._schema = schema
        # XXX: JonathanLange 2008-10-08: This is used by createBazaarBranch in
        # test_acceptance.
        self._mirror_root = mirror_root
        self._tac_server = CodeHostingTac(branches_root, mirror_root)

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
        self._tac_server.setUp()
        self._real_home, self._fake_home = self.setUpFakeHome()
        self._old_vendor_manager = self.forceParamiko()

    def tearDown(self):
        self.closeAllConnections()
        os.environ['HOME'] = self._real_home
        self._tac_server.tearDown()
        shutil.rmtree(self._fake_home)
        ssh._ssh_vendor_manager._cached_ssh_vendor = self._old_vendor_manager

    def get_url(self, user=None):
        if user is None:
            user = 'testuser'
        return '%s://%s@localhost:22222/' % (self._schema, user)
