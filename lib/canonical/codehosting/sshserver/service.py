# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Provides an SFTP server which Launchpad users can use to host their Bazaar
branches. For more information, see lib/canonical/codehosting/README.
"""

__metaclass__ = type
__all__ = [
    'SSHService',
    ]


import logging
import os

from twisted.application import service, strports
from twisted.conch.ssh.connection import SSHConnection
from twisted.conch.ssh.factory import SSHFactory
from twisted.conch.ssh.keys import Key
from twisted.cred.portal import Portal
from twisted.web.xmlrpc import Proxy

from canonical.config import config

from canonical.codehosting.sshserver.auth import (
    PublicKeyFromLaunchpadChecker, Realm, SSHUserAuthServer)


class Factory(SSHFactory):
    services = {
        'ssh-userauth': SSHUserAuthServer,
        'ssh-connection': SSHConnection
    }

    def __init__(self, hostPublicKey, hostPrivateKey):
        self.publicKeys = {
            'ssh-rsa': hostPublicKey
        }
        self.privateKeys = {
            'ssh-rsa': hostPrivateKey
        }

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
        portal = Portal(Realm(authentication_proxy, branchfs_proxy))
        portal.registerChecker(
            PublicKeyFromLaunchpadChecker(authentication_proxy))
        sftpfactory = Factory(hostPublicKey, hostPrivateKey)
        sftpfactory.portal = portal
        return sftpfactory

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
        set_up_logging()
        service.Service.startService(self)
        self.service.startService()

    def stopService(self):
        """Stop the SFTP service."""
        service.Service.stopService(self)
        return self.service.stopService()


def set_up_logging():
    """Set up logging for the smart server.

    This sets up a debugging handler on the 'codehosting' logger, makes sure
    that things logged there won't go to stderr (necessary because of
    bzrlib.trace shenanigans) and then returns the 'codehosting' logger.

    In addition, if configure_oops_reporting is True, install a
    Twisted log observer that ensures unhandled exceptions get
    reported as OOPSes.
    """
    log = logging.getLogger('codehosting')
    log.setLevel(logging.CRITICAL)
    return log
