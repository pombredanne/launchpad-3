# Copyright 2007-2008 Canonical Ltd.  All rights reserved.

"""Twisted `service.Service` class for the codehosting SSH server.

An `SSHService` object can be used to launch the SSH server.
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

from canonical.codehosting.sshserver.auth import (
    PublicKeyFromLaunchpadChecker, Realm, SSHUserAuthServer)
from canonical.config import config


class Factory(SSHFactory):
    """SSH factory that uses the codehosting custom authentication.

    This class tells the SSH service to use our custom authentication service
    and configures the host keys for the SSH server.
    """

    services = {
        'ssh-userauth': SSHUserAuthServer,
        'ssh-connection': SSHConnection
    }

    def __init__(self, portal):
        SSHFactory.__init__(self)
        # Although 'portal' isn't part of the defined interface for
        # `SSHFactory`, defining it here is how the `SSHUserAuthServer` gets
        # at it. (Look for the beautiful line "self.portal =
        # self.transport.factory.portal").
        self.portal = portal

    def _loadKey(self, key_filename):
        key_directory = config.codehosting.host_key_pair_path
        key_path = os.path.join(key_directory, key_filename)
        return Key.fromFile(key_path)

    def getPublicKeys(self):
        """Return the server's configured public key.

        See `SSHFactory.getPublicKeys`.
        """
        public_key = self._loadKey('ssh_host_key_rsa.pub')
        return {'ssh-rsa': public_key}

    def getPrivateKeys(self):
        """Return the server's configured private key.

        See `SSHFactory.getPrivateKeys`.
        """
        private_key = self._loadKey('ssh_host_key_rsa')
        return {'ssh-rsa': private_key}


class SSHService(service.Service):
    """A Twisted service for the codehosting SSH server."""

    def __init__(self):
        self.service = self.makeService()

    def makePortal(self):
        """Create and return a `Portal` for the SSH service.

        This portal accepts SSH credentials and returns our customized SSH
        avatars (see `canonical.codehosting.sshserver.auth.LaunchpadAvatar`).
        """
        authentication_proxy = Proxy(
            config.codehosting.authentication_endpoint)
        branchfs_proxy = Proxy(config.codehosting.branchfs_endpoint)
        portal = Portal(Realm(authentication_proxy, branchfs_proxy))
        portal.registerChecker(
            PublicKeyFromLaunchpadChecker(authentication_proxy))
        return portal

    def makeService(self):
        """Return a service that provides an SFTP server. This is called in
        the constructor.
        """
        ssh_factory = Factory(self.makePortal())
        return strports.service(config.codehosting.port, ssh_factory)

    def startService(self):
        """Start the SSH service."""
        set_up_logging()
        # By default, only the owner of files should be able to write to them.
        # Perhaps in the future this line will be deleted and the umask
        # managed by the startup script.
        os.umask(0022)
        service.Service.startService(self)
        self.service.startService()

    def stopService(self):
        """Stop the SSH service."""
        service.Service.stopService(self)
        return self.service.stopService()


def set_up_logging():
    """Set up and return the codehosting logger."""
    log = logging.getLogger('codehosting')
    log.setLevel(logging.CRITICAL)
    return log
