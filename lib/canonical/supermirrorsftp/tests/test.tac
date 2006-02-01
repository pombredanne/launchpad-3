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
from canonical.authserver.client.twistedclient import TwistedAuthServer

from canonical.supermirrorsftp import sftponly

keydir = sibpath(__file__, 'keys')
hostPublicKey = keys.getPublicKeyString(
    data=open(os.path.join(keydir, 'ssh_host_key_rsa.pub'), 'rb').read()
)
hostPrivateKey = keys.getPrivateKeyObject(
    data=open(os.path.join(keydir, 'ssh_host_key_rsa'), 'rb').read()
)

# Configure the authentication
homedirs = '/tmp/sftp-test/homedirs'
authserver = TwistedAuthServer('http://localhost:8999/v2/')

portal = portal.Portal(sftponly.Realm(homedirs, authserver))
portal.registerChecker(sftponly.PublicKeyFromLaunchpadChecker(authserver))
sftpfactory = sftponly.Factory(hostPublicKey, hostPrivateKey)
sftpfactory.portal = portal

# Configure it to listen on a port
application = service.Application('sftponly')
internet.TCPServer(22222, sftpfactory, interface='127.0.0.1').setServiceParent(application)

# Service that announces when the daemon is ready
tachandler.ReadyService().setServiceParent(application)


