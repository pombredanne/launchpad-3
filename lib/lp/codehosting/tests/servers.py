# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Server used in codehosting acceptance tests."""

__metaclass__ = type

__all__ = [
    'CodeHostingTac',
    'SSHCodeHostingServer',
    ]


import os
import shutil
import tempfile

from zope.component import getUtility

from bzrlib.transport import get_transport, Server

from twisted.python.util import sibpath

from canonical.config import config
from canonical.database.sqlbase import commit
from canonical.launchpad.daemons.tachandler import TacTestSetup
from canonical.launchpad.interfaces import (
    IPersonSet, ISSHKeySet, SSHKeyType, TeamSubscriptionPolicy)


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
        self._hosted_root = hosted_area
        # The mirrored area.
        self._mirror_root = mirrored_area
        # Where the pidfile, logfile etc will go.
        self._server_root = tempfile.mkdtemp()

    def clear(self):
        """Clear the branch areas."""
        if os.path.isdir(self._hosted_root):
            shutil.rmtree(self._hosted_root)
        os.makedirs(self._hosted_root, 0700)
        if os.path.isdir(self._mirror_root):
            shutil.rmtree(self._mirror_root)
        os.makedirs(self._mirror_root, 0700)

    def setUpRoot(self):
        self.clear()

    def tearDownRoot(self):
        shutil.rmtree(self._hosted_root)
        shutil.rmtree(self._server_root)

    @property
    def root(self):
        return self._server_root

    @property
    def tacfile(self):
        return os.path.abspath(
            os.path.join(config.root, 'daemons', 'sftp.tac'))

    @property
    def logfile(self):
        return os.path.join(self.root, 'codehosting.log')

    @property
    def pidfile(self):
        return os.path.join(self.root, 'codehosting.pid')


class SSHCodeHostingServer(Server):

    def __init__(self, schema, tac_server):
        Server.__init__(self)
        self._schema = schema
        # XXX: JonathanLange 2008-10-08: This is used by createBazaarBranch in
        # test_acceptance.
        self._mirror_root = tac_server._mirror_root
        self._tac_server = tac_server

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

    def getTransport(self, path=None):
        if path is None:
            path = ''
        transport = get_transport(self.get_url()).clone(path)
        return transport

    def setUp(self):
        self._real_home, self._fake_home = self.setUpFakeHome()

    def tearDown(self):
        os.environ['HOME'] = self._real_home
        shutil.rmtree(self._fake_home)

    def get_url(self, user=None):
        if user is None:
            user = 'testuser'
        return '%s://%s@localhost:22222/' % (self._schema, user)
