# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Twisted `service.Service` class for the codehosting SSH server.

An `SSHService` object can be used to launch the SSH server.
"""

__metaclass__ = type
__all__ = [
    'SSHService',
    ]


import os

from twisted.application import service, strports
from twisted.conch.ssh.factory import SSHFactory
from twisted.conch.ssh.keys import Key
from twisted.conch.ssh.transport import SSHServerTransport
from twisted.internet import defer
from twisted.protocols.policies import TimeoutFactory
from twisted.web.xmlrpc import Proxy

from zope.event import notify

from canonical.config import config
from lp.codehosting.sshserver import accesslog
from lp.codehosting.sshserver.auth import get_portal, SSHUserAuthServer
from lp.services.twistedsupport import gatherResults


# The names of the key files of the server itself. The directory itself is
# given in config.codehosting.host_key_pair_path.
PRIVATE_KEY_FILE = 'ssh_host_key_rsa'
PUBLIC_KEY_FILE = 'ssh_host_key_rsa.pub'


class KeepAliveSettingSSHServerTransport(SSHServerTransport):

    def connectionMade(self):
        SSHServerTransport.connectionMade(self)
        self.transport.setTcpKeepAlive(True)


def get_key_path(key_filename):
    key_directory = config.codehosting.host_key_pair_path
    return os.path.join(config.root, key_directory, key_filename)


class Factory(SSHFactory):
    """SSH factory that uses the codehosting custom authentication.

    This class tells the SSH service to use our custom authentication service
    and configures the host keys for the SSH server. It also logs connection
    to and disconnection from the SSH server.
    """

    protocol = KeepAliveSettingSSHServerTransport

    def __init__(self, portal, private_key, public_key, banner=None):
        """Construct an SSH factory.

        :param portal: The portal used to turn credentials into users.
        :param private_key: The private key of the server, must be RSA.
        :param public_key: The public key of the server, must be RSA.
        :param banner: The text to display when users successfully log in.
        """
        # Although 'portal' isn't part of the defined interface for
        # `SSHFactory`, defining it here is how the `SSHUserAuthServer` gets
        # at it. (Look for the beautiful line "self.portal =
        # self.transport.factory.portal").
        self.portal = portal
        self.services['ssh-userauth'] = self._makeAuthServer
        self._private_key = private_key
        self._public_key = public_key
        self._banner = banner

    def _makeAuthServer(self, *args, **kwargs):
        kwargs['banner'] = self._banner
        return SSHUserAuthServer(*args, **kwargs)

    def buildProtocol(self, address):
        """Build an SSH protocol instance, logging the event.

        The protocol object we return is slightly modified so that we can hook
        into the 'connectionLost' event and log the disconnection.
        """
        transport = SSHFactory.buildProtocol(self, address)
        transport._realConnectionLost = transport.connectionLost
        transport.connectionLost = (
            lambda reason: self.connectionLost(transport, reason))
        notify(accesslog.UserConnected(transport, address))
        return transport

    def connectionLost(self, transport, reason):
        """Call 'connectionLost' on 'transport', logging the event."""
        try:
            return transport._realConnectionLost(reason)
        finally:
            # Conch's userauth module sets 'avatar' on the transport if the
            # authentication succeeded. Thus, if it's not there,
            # authentication failed. We can't generate this event from the
            # authentication layer since:
            #
            # a) almost every SSH login has at least one failure to
            # authenticate due to multiple keys on the client-side.
            #
            # b) the server doesn't normally generate a "go away" event.
            # Rather, the client simply stops trying.
            if getattr(transport, 'avatar', None) is None:
                notify(accesslog.AuthenticationFailed(transport))
            notify(accesslog.UserDisconnected(transport))

    def getPublicKeys(self):
        """Return the server's configured public key.

        See `SSHFactory.getPublicKeys`.
        """
        return {'ssh-rsa': self._public_key}

    def getPrivateKeys(self):
        """Return the server's configured private key.

        See `SSHFactory.getPrivateKeys`.
        """
        return {'ssh-rsa': self._private_key}


class SSHService(service.Service):
    """A Twisted service for the codehosting SSH server."""

    def __init__(self):
        self.service = self.makeService()

    def makePortal(self):
        """Create and return a `Portal` for the SSH service.

        This portal accepts SSH credentials and returns our customized SSH
        avatars (see `lp.codehosting.sshserver.auth.LaunchpadAvatar`).
        """
        authentication_proxy = Proxy(
            config.codehosting.authentication_endpoint)
        branchfs_proxy = Proxy(config.codehosting.branchfs_endpoint)
        return get_portal(authentication_proxy, branchfs_proxy)

    def makeService(self):
        """Return a service that provides an SFTP server. This is called in
        the constructor.
        """
        ssh_factory = TimeoutFactory(
            Factory(
                self.makePortal(),
                public_key=Key.fromFile(get_key_path(PUBLIC_KEY_FILE)),
                private_key=Key.fromFile(get_key_path(PRIVATE_KEY_FILE)),
                banner=config.codehosting.banner),
            timeoutPeriod=config.codehosting.idle_timeout)
        return strports.service(config.codehosting.port, ssh_factory)

    def startService(self):
        """Start the SSH service."""
        accesslog.LoggingManager().setUp(
            configure_oops_reporting=True, mangle_stdout=True)
        notify(accesslog.ServerStarting())
        # By default, only the owner of files should be able to write to them.
        # Perhaps in the future this line will be deleted and the umask
        # managed by the startup script.
        os.umask(0022)
        service.Service.startService(self)
        self.service.startService()

    def stopService(self):
        """Stop the SSH service."""
        deferred = gatherResults([
            defer.maybeDeferred(service.Service.stopService, self),
            defer.maybeDeferred(self.service.stopService)])
        def log_stopped(ignored):
            notify(accesslog.ServerStopped())
            return ignored
        return deferred.addBoth(log_stopped)
