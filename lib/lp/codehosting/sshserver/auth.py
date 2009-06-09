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

from twisted.internet import defer

from twisted.python import components, failure

from zope.event import notify
from zope.interface import implements

from lp.codehosting import sftp
from lp.codehosting.sshserver import accesslog
from lp.codehosting.sshserver.session import (
    launch_smart_server, PatchedSSHSession)
from lp.codehosting.vfs.branchfsclient import trap_fault
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
        # Fetch the user's details from the authserver
        deferred = mind.lookupUserDetails(self.authentication_proxy, avatarId)

        # Once all those details are retrieved, we can construct the avatar.
        def gotUserDict(userDict):
            avatar = LaunchpadAvatar(userDict, self.branchfs_proxy)
            return interfaces[0], avatar, avatar.logout
        return deferred.addCallback(gotUserDict)


class ISSHPrivateKeyWithMind(credentials.ISSHPrivateKey):
    """Marker interface for SSH credentials that reference a Mind."""


class SSHPrivateKeyWithMind(credentials.SSHPrivateKey):
    """SSH credentials that also reference a Mind."""

    implements(ISSHPrivateKeyWithMind)

    def __init__(self, username, algName, blob, sigData, signature, mind):
        credentials.SSHPrivateKey.__init__(
            self, username, algName, blob, sigData, signature)
        self.mind = mind


class UserDetailsMind:
    """A 'Mind' object that answers and caches requests for user details.

    A mind is a (poorly named) concept from twisted.cred that basically can be
    passed to portal.login to represent the client side view of
    authentication.  In our case we attach a mind to the SSHUserAuthServer
    object that corresponds to an attempt to authenticate against the server.
    """

    def __init__(self):
        self.cache = {}

    def lookupUserDetails(self, proxy, username):
        """Find details for the named user, including registered SSH keys.

        This method basically wraps `IAuthServer.getUserAndSSHKeys` -- see the
        documentation of that method for more details -- and caches the
        details found for any particular user.

        :param proxy: A twisted.web.xmlrpc.Proxy object for the authentication
            endpoint.
        :param username: The username to look up.
        """
        if username in self.cache:
            return defer.succeed(self.cache[username])
        else:
            d = proxy.callRemote('getUserAndSSHKeys', username)
            d.addBoth(self._add_to_cache, username)
            return d

    def _add_to_cache(self, result, username):
        """Add the results to our cache."""
        self.cache[username] = result
        return result


class SSHUserAuthServer(userauth.SSHUserAuthServer):
    """Subclass of Conch's SSHUserAuthServer to customize various behaviors.

    There are two main differences:

     * We override ssh_USERAUTH_REQUEST to display as a banner the reason why
       an authentication attempt failed.

     * We override auth_publickey to create credentials that reference a
       UserDetailsMind and pass the same mind to self.portal.login.

    Conch is not written in a way to make this easy; we've had to copy and
    paste and change the implementations of these methods.
    """

    def __init__(self, transport=None):
        self.transport = transport
        self._configured_banner_sent = False
        self._mind = UserDetailsMind()
        self.interfaceToMethod = userauth.SSHUserAuthServer.interfaceToMethod
        self.interfaceToMethod[ISSHPrivateKeyWithMind] = 'publickey'

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

    def getMind(self):
        """Return the mind that should be passed to self.portal.login().

        If multiple requests to authenticate within this overall login attempt
        should share state, this method can return the same mind each time.
        """
        return self._mind

    def makePublicKeyCredentials(self, username, algName, blob, sigData,
                                 signature):
        """Construct credentials for a request to login with a public key.

        Our implementation returns a SSHPrivateKeyWithMind.

        :param username: The username the request is for.
        :param algName: The algorithm name for the blob.
        :param blob: The public key blob as sent by the client.
        :param sigData: The data the signature was made from.
        :param signature: The signed data.  This is checked to verify that the
            user owns the private key.
        """
        mind = self.getMind()
        return SSHPrivateKeyWithMind(
                username, algName, blob, sigData, signature, mind)

    def auth_publickey(self, packet):
        # This is copied and pasted from twisted/conch/ssh/userauth.py in
        # Twisted 8.0.1. We do this so we can customize how the credentials
        # are built and pass a mind to self.portal.login.
        hasSig = ord(packet[0])
        algName, blob, rest = getNS(packet[1:], 2)
        pubKey = keys.Key.fromString(blob).keyObject
        signature = hasSig and getNS(rest)[0] or None
        if hasSig:
            b = NS(self.transport.sessionID) + \
                chr(userauth.MSG_USERAUTH_REQUEST) +  NS(self.user) + \
                NS(self.nextService) + NS('publickey') +  chr(hasSig) + \
                NS(keys.objectType(pubKey)) + NS(blob)
            # The next three lines are different from the original.
            c = self.makePublicKeyCredentials(
                self.user, algName, blob, b, signature)
            return self.portal.login(c, self.getMind(), IConchUser)
        else:
            # The next four lines are different from the original.
            c = self.makePublicKeyCredentials(
                self.user, algName, blob, None, None)
            return self.portal.login(
                c, self.getMind(), IConchUser).addErrback(
                    self._ebCheckKey, packet[1:])


class PublicKeyFromLaunchpadChecker(SSHPublicKeyDatabase):
    """Cred checker for getting public keys from launchpad.

    It knows how to get the public keys from the authserver.
    """
    credentialInterfaces = ISSHPrivateKeyWithMind,
    implements(ICredentialsChecker)

    def __init__(self, authserver):
        self.authserver = authserver

    def checkKey(self, credentials):
        """Check whether `credentials` is a valid request to authenticate.

        We check the key data in credentials against the keys the named user
        has registered in Launchpad.
        """
        d = credentials.mind.lookupUserDetails(
            self.authserver, credentials.username)
        d.addCallback(self._checkForAuthorizedKey, credentials)
        d.addErrback(self._reportNoSuchUser, credentials)
        return d

    def _reportNoSuchUser(self, failure, credentials):
        """Report the user named in the credentials not existing nicely."""
        trap_fault(failure, faults.NoSuchPersonWithName)
        raise UserDisplayedUnauthorizedLogin(
            "No such Launchpad account: %s" % credentials.username)

    def _checkForAuthorizedKey(self, userDict, credentials):
        """Check the key data in credentials against the keys found in LP."""
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
