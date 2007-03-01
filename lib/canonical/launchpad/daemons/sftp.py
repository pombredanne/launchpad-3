# Copyright 2007 Canonical Ltd.  All rights reserved.

"""NOMERGE - make this docstring betterer.
"""

__metaclass__ = type
__all__ = ['SFTPService']


import os
import shutil

from twisted.cred import portal
from twisted.conch.ssh import keys
from twisted.application import service, strports

from canonical.config import config
from canonical.launchpad.daemons import tachandler
from canonical.authserver.client.twistedclient import TwistedAuthServer

from canonical.supermirrorsftp import sftponly


class SFTPService(service.Service):
    """A Twisted service for the supermirror SFTP server.
    """

    def __init__(self):
        self.service = self.makeService()

    def makeRealm(self):
        homedirs = config.supermirrorsftp.branches_root
        authserver = TwistedAuthServer(config.supermirrorsftp.authserver)
        return sftponly.Realm(homedirs, authserver)

    def makeFactory(self, hostPublicKey, hostPrivateKey):
        # Configure the authentication
        homedirs = config.supermirrorsftp.branches_root
        authserver = TwistedAuthServer(config.supermirrorsftp.authserver)
        p = portal.Portal(self.makeRealm())
        p.registerChecker(sftponly.PublicKeyFromLaunchpadChecker(authserver))
        sftpfactory = sftponly.Factory(hostPublicKey, hostPrivateKey)
        sftpfactory.portal = p
        return sftpfactory

    def makeService(self):
        hostPublicKey, hostPrivateKey = self.makeKeys()
        sftpfactory = self.makeFactory(hostPublicKey, hostPrivateKey)
        return strports.service(config.supermirrorsftp.port, sftpfactory)

    def makeKeys(self):
        # mkdir keys; cd keys; ssh-keygen -t rsa -f ssh_host_key_rsa
        keydir = config.supermirrorsftp.host_key_pair_path
        hostPublicKey = keys.getPublicKeyString(
            data=open(os.path.join(keydir,
                                   'ssh_host_key_rsa.pub'), 'rb').read())
        hostPrivateKey = keys.getPrivateKeyObject(
            data=open(os.path.join(keydir,
                                   'ssh_host_key_rsa'), 'rb').read())
        return hostPublicKey, hostPrivateKey

    def startService(self):
        service.Service.startService(self)
        self.service.startService()

    def stopService(self):
        service.Service.stopService(self)
        self.service.stopService()
