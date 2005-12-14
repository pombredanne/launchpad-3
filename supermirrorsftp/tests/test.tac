# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
#
# This is a Twisted application config file.  To run, use:
#     twistd -noy sftp.tac
# or similar.  Refer to the twistd(1) man page for details.

import os

from twisted.cred import portal
from twisted.conch.ssh import keys
from twisted.application import service, internet
from twisted.python.util import sibpath
from twisted.internet import defer

from canonical.launchpad.daemons import tachandler

from supermirrorsftp import sftponly

keydir = sibpath(__file__, 'keys')
hostPublicKey = keys.getPublicKeyString(
    data=open(os.path.join(keydir, 'ssh_host_key_rsa.pub'), 'rb').read()
)
hostPrivateKey = keys.getPrivateKeyObject(
    data=open(os.path.join(keydir, 'ssh_host_key_rsa'), 'rb').read()
)

# Configure the authentication
homedirs = '/tmp/sftp-test/homedirs'
class FakeAuthserver:
    def getSSHKeys(self, username):
        assert username == 'testuser'
        keytext = open(sibpath(__file__, 'id_dsa.pub'),'r').read().split()[1]
        return defer.succeed([(2, keytext)])
    def getUser(self, username):
        assert username == 'testuser'
        return defer.succeed({
            'id': 1, 
            'name': 'testuser', 
            'teams': [{'id': 1, 'name': 'testuser', 'initialBranches': []},
                      {'id': 2, 'name': 'testteam', 'initialBranches': []}],
        })
    def getBranchesForUser(self, personID):
        return defer.succeed([])
authserver = FakeAuthserver()

portal = portal.Portal(sftponly.Realm(homedirs, authserver))
portal.registerChecker(sftponly.PublicKeyFromLaunchpadChecker(authserver))
sftpfactory = sftponly.Factory(hostPublicKey, hostPrivateKey)
sftpfactory.portal = portal

# Configure it to listen on a port
application = service.Application('sftponly')
internet.TCPServer(22222, sftpfactory, interface='127.0.0.1').setServiceParent(application)

# Service that announces when the daemon is ready
tachandler.ReadyService().setServiceParent(application)


