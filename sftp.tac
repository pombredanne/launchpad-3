# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
#
# This is a Twisted application config file.  To run, use:
#     twistd -noy sftp.tac
# or similar.  Refer to the twistd(1) man page for details.

from supermirrorsftp import sftponly
from twisted.cred import portal
from twisted.conch.ssh import keys
from twisted.application import service, internet
import os

authserverURL = 'http://localhost:8999/'
keydir = os.environ.get('SUPERMIRROR_KEYDIR', os.path.join(os.getcwd(),'keys'))
hostPublicKey = keys.getPublicKeyString(
    data=open(os.path.join(keydir, 'ssh_host_key_rsa.pub'), 'rb').read()
)
hostPrivateKey = keys.getPrivateKeyObject(
    data=open(os.path.join(keydir, 'ssh_host_key_rsa'), 'rb').read()
)

# Configure the authentication
homedirs = os.environ.get('SUPERMIRROR_HOMEDIRS', '/tmp')
portal = portal.Portal(sftponly.Realm(homedirs))
portal.registerChecker(sftponly.PublicKeyFromLaunchpadChecker(authserverURL))
sftpfactory = sftponly.Factory(hostPublicKey, hostPrivateKey)
sftpfactory.portal = portal

# Configure it to listen on a port
application = service.Application('sftponly')
internet.TCPServer(5022, sftpfactory).setServiceParent(application)

