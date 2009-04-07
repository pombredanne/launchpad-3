# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0231

"""Custom authentication for the SSH server.

Launchpad's SSH server authenticates users against a XML-RPC service (see
`canonical.launchpad.interfaces.authserver.IAuthServer` and
`PublicKeyFromLaunchpadChecker`) and provides richer error messages in the
case of failed authentication (see `SSHUserAuthServer`).
"""

__metaclass__ = type
__all__ = [
    'get_portal',
    'SSHUserAuthServer',
    ]

import binascii

from twisted.conch import avatar
from twisted.conch.error import ConchError
from twisted.conch.interfaces import IConchUser, ISession
from twisted.conch.ssh import filetransfer, keys, userauth
from twisted.conch.ssh.common import getNS, NS
from twisted.conch.checkers import SSHPublicKeyDatabase

from twisted.cred.error import UnauthorizedLogin
from twisted.cred.checkers import ICredentialsChecker
from twisted.cred import credentials
from twisted.cred.portal import IRealm, Portal

from twisted.python import components, failure

from zope.event import notify
from zope.interface import implements

from canonical.codehosting import sftp
from canonical.codehosting.sshserver import accesslog
from canonical.codehosting.sshserver.session import (
    launch_smart_server, PatchedSSHSession)
from canonical.codehosting.vfs.branchfsclient import trap_fault
from canonical.config import config
from canonical.launchpad.xmlrpc import faults


class LaunchpadAvatar(avatar.ConchUser):
    """An account on the SSH server, corresponding to a Launchpad person.

    :ivar branchfs_proxy: A Twisted XML-RPC client for the authserver. The
        server must implement `IBranchFileSystem`.
    :ivar channelLookup: See `avatar.ConchUser`.
    :ivar subsystemLookup: See `avatar.ConchUser`.
    :ivar user_id: The Launchpad database ID of the Person for this account.
    :ivar username: The Launchpad username for this account.
    """

    def __init__(self, userDict, branchfs_proxy):
        avatar.ConchUser.__init__(self)
        self.branchfs_proxy = branchfs_proxy
        self.user_id = userDict['id']
        self.username = userDict['name']

        # Set the only channel as a standard SSH session (with a couple of bug
        # fixes).
        self.channelLookup = {'session': PatchedSSHSession}
        # ...and set the only subsystem to be SFTP.
        self.subsystemLookup = {'sftp': sftp.FileTransferServer}

    def logout(self):
        notify(accesslog.UserLoggedOut(self))


components.registerAdapter(launch_smart_server, LaunchpadAvatar, ISession)

components.registerAdapter(
    sftp.avatar_to_sftp_server, LaunchpadAvatar, filetransfer.ISFTPServer)


class UserDisplayedUnauthorizedLogin(UnauthorizedLogin):
    """UnauthorizedLogin which should be reported to the user."""


class Realm:
    implements(IRealm)

    def __init__(self, authentication_proxy, branchfs_proxy):
        self.authentication_proxy = authentication_proxy
        self.branchfs_proxy = branchfs_proxy

    def requestAvatar(self, avatarId, mind, *interfaces):
        # Fetch the user's details from the authserver -- YYY using the mind
        # as a some kind of key as a cache.
        deferred = self.authentication_proxy.callRemote('getUser', avatarId)

        # Once all those details are retrieved, we can construct the avatar.
        def gotUserDict(userDict):
            avatar = LaunchpadAvatar(userDict, self.branchfs_proxy)
            return interfaces[0], avatar, avatar.logout
        return deferred.addCallback(gotUserDict)


class SSHUserAuthServer(userauth.SSHUserAuthServer):

    def __init__(self, transport=None):
        self.transport = transport
        self._configured_banner_sent = False

    def sendBanner(self, text, language='en'):
        bytes = '\r\n'.join(text.encode('UTF8').splitlines() + [''])
        self.transport.sendPacket(userauth.MSG_USERAUTH_BANNER,
                                  NS(bytes) + NS(language))

    def _sendConfiguredBanner(self, passed_through):
        if (not self._configured_banner_sent
            and config.codehosting.banner is not None):
            self._configured_banner_sent = True
            self.sendBanner(config.codehosting.banner)
        return passed_through

    def ssh_USERAUTH_REQUEST(self, packet):
        # This is copied and pasted from twisted/conch/ssh/userauth.py in
        # Twisted 8.0.1. We do this so we can add _ebLogToBanner between
        # two existing errbacks.
        user, nextService, method, rest = getNS(packet, 3)
        if user != self.user or nextService != self.nextService:
            self.authenticatedWith = [] # clear auth state
        self.user = user
        self.nextService = nextService
        self.method = method
        d = self.tryAuth(method, user, rest)
        if not d:
            self._ebBadAuth(failure.Failure(ConchError('auth returned none')))
            return
        d.addCallback(self._sendConfiguredBanner)
        d.addCallbacks(self._cbFinishedAuth)
        d.addErrback(self._ebMaybeBadAuth)
        # This line does not appear in the original.
        d.addErrback(self._ebLogToBanner)
        d.addErrback(self._ebBadAuth)
        return d

    def _cbFinishedAuth(self, result):
        ret = userauth.SSHUserAuthServer._cbFinishedAuth(self, result)
        # Tell the avatar about the transport, so we can tie it to the
        # connection in the logs.
        avatar = self.transport.avatar
        avatar.transport = self.transport
        notify(accesslog.UserLoggedIn(avatar))
        return ret

    def _ebLogToBanner(self, reason):
        reason.trap(UserDisplayedUnauthorizedLogin)
        self.sendBanner(reason.getErrorMessage())
        return reason

    def auth_publickey(self, packet):
        # Copy-paste-hack from conch!
        hasSig = ord(packet[0])
        algName, blob, rest = getNS(packet[1:], 2)
        pubKey = keys.Key.fromString(blob).keyObject
        signature = hasSig and getNS(rest)[0] or None
        if hasSig:
            b = NS(self.transport.sessionID) + chr(userauth.MSG_USERAUTH_REQUEST) + \
                NS(self.user) + NS(self.nextService) + NS('publickey') + \
                chr(hasSig) +  NS(keys.objectType(pubKey)) + NS(blob)
            # YYY Create our own kind of credential here.
            c = credentials.SSHPrivateKey(self.user, algName, blob, b, signature)
            # Pass something useful in as the mind.
            return self.portal.login(c, None, IConchUser)
        else:
            # YYY Create our own kind of credential here.
            c = credentials.SSHPrivateKey(self.user, algName, blob, None, None)
            # Pass something useful in as the mind.
            return self.portal.login(c, None, IConchUser).addErrback(
                                                        self._ebCheckKey,
                                                        packet[1:])


class PublicKeyFromLaunchpadChecker(SSHPublicKeyDatabase):
    """Cred checker for getting public keys from launchpad.

    It knows how to get the public keys from the authserver.
    """
    implements(ICredentialsChecker)

    def __init__(self, authserver):
        self.authserver = authserver

    def checkKey(self, credentials):
        # YYY Use some part of credentials as the key into a cache for these
        # results.
        d = self.authserver.callRemote(
            'getUserAndSSHKeys', credentials.username)
        d.addCallback(self._checkForAuthorizedKey, credentials)
        d.addErrback(self._reportNoSuchUser, credentials)
        return d

    def _reportNoSuchUser(self, failure, credentials):
        trap_fault(failure, faults.NoSuchPersonWithName)
        raise UserDisplayedUnauthorizedLogin(
            "No such Launchpad account: %s" % credentials.username)

    def _checkForAuthorizedKey(self, userDict, credentials):
        if credentials.algName == 'ssh-dss':
            wantKeyType = 'DSA'
        elif credentials.algName == 'ssh-rsa':
            wantKeyType = 'RSA'
        else:
            # unknown key type
            return False

        if len(userDict['keys']) == 0:
            raise UserDisplayedUnauthorizedLogin(
                "Launchpad user %r doesn't have a registered SSH key"
                % credentials.username)

        for keytype, keytext in userDict['keys']:
            if keytype != wantKeyType:
                continue
            try:
                if keytext.decode('base64') == credentials.blob:
                    return True
            except binascii.Error:
                continue

        raise UnauthorizedLogin(
            "Your SSH key does not match any key registered for Launchpad "
            "user %s" % credentials.username)


def get_portal(authentication_proxy, branchfs_proxy):
    """Get a portal for connecting to Launchpad codehosting."""
    portal = Portal(Realm(authentication_proxy, branchfs_proxy))
    portal.registerChecker(
        PublicKeyFromLaunchpadChecker(authentication_proxy))
    return portal
