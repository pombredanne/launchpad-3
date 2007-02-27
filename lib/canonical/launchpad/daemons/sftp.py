# Copyright 2007 Canonical Ltd.  All rights reserved.

"""NOMERGE - make this docstring betterer.
"""

__metaclass__ = type
__all__ = ['SFTPSetup']


import os
import shutil

from twisted.cred import portal
from twisted.conch.ssh import keys
from twisted.application import service, strports

from canonical.config import config
from canonical.launchpad.daemons import tachandler
from canonical.authserver.client.twistedclient import TwistedAuthServer

from canonical.supermirrorsftp import sftponly


class SFTPSetup:
    def makeRoot(self, keydir):
        root = os.path.dirname(config.supermirrorsftp.host_key_pair_path)
        assert root == os.path.dirname(config.supermirrorsftp.branches_root), \
               "Parent of host_key_pair_path should be parent of branches_root."
        if os.path.isdir(root):
            shutil.rmtree(root)
        os.makedirs(root, 0700)
        shutil.copytree(keydir, config.supermirrorsftp.host_key_pair_path)

    def makeFactory(self, hostPublicKey, hostPrivateKey):
        # Configure the authentication
        homedirs = config.supermirrorsftp.branches_root
        authserver = TwistedAuthServer(config.supermirrorsftp.authserver)
        p = portal.Portal(sftponly.Realm(homedirs, authserver))
        p.registerChecker(sftponly.PublicKeyFromLaunchpadChecker(authserver))
        sftpfactory = sftponly.Factory(hostPublicKey, hostPrivateKey)
        sftpfactory.portal = p
        return sftpfactory

    def makeService(self, keydir):
        self.makeRoot(keydir)
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
