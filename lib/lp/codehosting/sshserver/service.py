# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Twisted `service.Service` class for the codehosting SSH server.

An `SSHService` object can be used to launch the SSH server.
"""

__metaclass__ = type
__all__ = [
    'ACCESS_LOG_NAME',
    'get_key_path',
    'LOG_NAME',
    'make_portal',
    'PRIVATE_KEY_FILE',
    'PUBLIC_KEY_FILE',
    'SSHService',
    ]


import logging
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
from lp.codehosting.sshserver import accesslog, events
from lp.codehosting.sshserver.auth import get_portal, SSHUserAuthServer
from lp.services.twistedsupport import gatherResults
from lp.services.twistedsupport.loggingsupport import set_up_oops_reporting


# The names of the key files of the server itself. The directory itself is
# given in config.codehosting.host_key_pair_path.
PRIVATE_KEY_FILE = 'ssh_host_key_rsa'
PUBLIC_KEY_FILE = 'ssh_host_key_rsa.pub'

OOPS_CONFIG_SECTION = 'codehosting'
LOG_NAME = 'codehosting'
ACCESS_LOG_NAME = 'codehosting.access'


class KeepAliveSettingSSHServerTransport(SSHServerTransport):

    def connectionMade(self):
        SSHServerTransport.connectionMade(self)
        self.transport.setTcpKeepAlive(True)


def get_key_path(key_filename):
    key_directory = config.codehosting.host_key_pair_path
    return os.path.join(config.root, key_directory, key_filename)


def make_portal():
    """Create and return a `Portal` for the SSH service.

    This portal accepts SSH credentials and returns our customized SSH
    avatars (see `lp.codehosting.sshserver.auth.LaunchpadAvatar`).
    """
    authentication_proxy = Proxy(
        config.codehosting.authentication_endpoint)
    branchfs_proxy = Proxy(config.codehosting.branchfs_endpoint)
    return get_portal(authentication_proxy, branchfs_proxy)


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
        notify(events.UserConnected(transport, address))
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
                notify(events.AuthenticationFailed(transport))
            notify(events.UserDisconnected(transport))

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

    def __init__(self, portal, private_key_path, public_key_path,
                 port='tcp:22', idle_timeout=3600, banner=None):
        """Construct an SSH service.

        :param portal: The `Portal` that turns authentication requests into
            views on the system.
        :param private_key_path: The path to the SSH server's private key.
        :param public_key_path: The path to the SSH server's public key.
        :param port: The port to run the server on, expressed in Twisted's
            "strports" mini-language. Defaults to 'tcp:22'.
        :param idle_timeout: The number of seconds to wait before killing a
            connection that isn't doing anything. Defaults to 3600.
        :param banner: An announcement printed to users when they connect.
            By default, announce nothing.
        """
        ssh_factory = TimeoutFactory(
            Factory(
                portal,
                private_key=Key.fromFile(private_key_path),
                public_key=Key.fromFile(public_key_path),
                banner=banner),
            timeoutPeriod=idle_timeout)
        self.service = strports.service(port, ssh_factory)

    def startService(self):
        """Start the SSH service."""
        set_up_oops_reporting(OOPS_CONFIG_SECTION)
        manager = accesslog.LoggingManager(
            logging.getLogger(LOG_NAME),
            logging.getLogger(ACCESS_LOG_NAME),
            config.codehosting.access_log)
        manager.setUp()
        notify(events.ServerStarting())
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
            notify(events.ServerStopped())
            return ignored
        return deferred.addBoth(log_stopped)
