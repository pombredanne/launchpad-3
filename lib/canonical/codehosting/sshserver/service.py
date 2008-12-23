# Copyright 2007-2008 Canonical Ltd.  All rights reserved.

"""Provides an SFTP server which Launchpad users can use to host their Bazaar
branches. For more information, see lib/canonical/codehosting/README.
"""

__metaclass__ = type
__all__ = [
    'SSHService',
    ]


import os

from twisted.application import service, strports
from twisted.conch.ssh.factory import SSHFactory
from twisted.conch.ssh.keys import Key
from twisted.web.xmlrpc import Proxy

from canonical.codehosting.sshserver.accesslog import set_up_logging
from canonical.codehosting.sshserver.auth import get_portal, SSHUserAuthServer
from canonical.config import config


class Factory(SSHFactory):
    """SSH factory that uses our authentication service."""

    def __init__(self, hostPublicKey, hostPrivateKey, portal):
        self.publicKeys = {
            'ssh-rsa': hostPublicKey
        }
        self.privateKeys = {
            'ssh-rsa': hostPrivateKey
        }
        self.services['ssh-userauth'] = SSHUserAuthServer
        self.portal = portal

    def startFactory(self):
        SSHFactory.startFactory(self)
        os.umask(0022)


class SSHService(service.Service):
    """A Twisted service for the supermirror SFTP server."""

    def __init__(self):
        self.service = self.makeService()

    def makeFactory(self, hostPublicKey, hostPrivateKey):
        """Create and return an SFTP server that uses the given public and
        private keys.
        """
        authentication_proxy = Proxy(
            config.codehosting.authentication_endpoint)
        branchfs_proxy = Proxy(config.codehosting.branchfs_endpoint)
        portal = get_portal(authentication_proxy, branchfs_proxy)
        return Factory(hostPublicKey, hostPrivateKey, portal)

    def makeService(self):
        """Return a service that provides an SFTP server. This is called in
        the constructor.
        """
        hostPublicKey, hostPrivateKey = self.makeKeys()
        sftpfactory = self.makeFactory(hostPublicKey, hostPrivateKey)
        return strports.service(config.codehosting.port, sftpfactory)

    def makeKeys(self):
        """Load the public and private host keys from the configured key pair
        path. Returns both keys in a 2-tuple.

        :return: (hostPublicKey, hostPrivateKey)
        """
        keydir = config.codehosting.host_key_pair_path
        hostPublicKey = Key.fromString(
            open(os.path.join(keydir, 'ssh_host_key_rsa.pub'), 'rb').read())
        hostPrivateKey = Key.fromString(
            open(os.path.join(keydir, 'ssh_host_key_rsa'), 'rb').read())
        return hostPublicKey, hostPrivateKey

    def startService(self):
        """Start the SFTP service."""
        set_up_logging(configure_oops_reporting=False)
        service.Service.startService(self)
        self.service.startService()

    def stopService(self):
        """Stop the SFTP service."""
        service.Service.stopService(self)
        return self.service.stopService()
