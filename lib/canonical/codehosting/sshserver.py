# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0231

import binascii
import os
import logging

from twisted.conch import avatar
from twisted.conch.error import ConchError
from twisted.conch.interfaces import ISession
from twisted.conch.ssh import (
    channel, connection, factory, filetransfer, session, userauth)
from twisted.conch.ssh.common import getNS, NS
from twisted.conch.checkers import SSHPublicKeyDatabase

from twisted.cred.error import UnauthorizedLogin
from twisted.cred.checkers import ICredentialsChecker
from twisted.cred.portal import IRealm

from twisted.internet import defer
from twisted.internet.protocol import connectionDone

from twisted.python import components, failure

from canonical.codehosting import sftp
from canonical.codehosting.smartserver import launch_smart_server
from canonical.config import config

from zope.interface import implements


class SubsystemOnlySession(session.SSHSession, object):
    """Session adapter that corrects a bug in Conch."""

    def closeReceived(self):
        # Without this, the client hangs when its finished transferring.
        self.loseConnection()

    def loseConnection(self):
        # XXX: JonathanLange 2008-03-31: This deliberately replaces the
        # implementation of session.SSHSession.loseConnection. The default
        # implementation will try to call loseConnection on the client
        # transport even if it's None. I don't know *why* it is None, so this
        # doesn't necessarily address the root cause.
        transport = getattr(self.client, 'transport', None)
        if transport is not None:
            transport.loseConnection()
        # This is called by session.SSHSession.loseConnection. SSHChannel is
        # the base class of SSHSession.
        channel.SSHChannel.loseConnection(self)


class LaunchpadAvatar(avatar.ConchUser):

    def __init__(self, avatarId, homeDirsRoot, userDict, launchpad):
        # Double-check that we don't get unicode -- directory names on the
        # file system are a sequence of bytes as far as we're concerned. We
        # don't want any tricky login names turning into a security problem.
        # (I'm reasonably sure twisted.cred guarantees this will be str, but
        # in the meantime let's make sure).
        assert type(avatarId) is str

        self.avatarId = avatarId
        self.homeDirsRoot = homeDirsRoot
        self._launchpad = launchpad

        self.lpid = userDict['id']
        self.lpname = userDict['name']
        self.teams = userDict['teams']

        logging.getLogger('codehosting.ssh').info('%r logged in', self.lpname)
        self.logger = logging.getLogger('codehosting.sftp.%s' % self.lpname)

        # Extract the initial branches from the user dict.
        branches_by_team = dict(userDict['initialBranches'])
        self.branches = {}
        for team in self.teams:
            branches_by_product = branches_by_team.get(team['id'], [])
            self.branches[team['id']] = team_branches = []
            for (product_id, product_name), branches in branches_by_product:
                team_branches.append((product_id, product_name, branches))
        self._productIDs = {}
        self._productNames = {}

        # XXX: Andrew Bennetts 2007-01-26:
        # See AdaptFileSystemUserToISFTP below.
        self.filesystem = None

        # Set the only channel as a session that only allows requests for
        # subsystems...
        self.channelLookup = {'session': SubsystemOnlySession}
        # ...and set the only subsystem to be SFTP.
        self.subsystemLookup = {'sftp': BazaarFileTransferServer}


components.registerAdapter(launch_smart_server, LaunchpadAvatar, ISession)

components.registerAdapter(
    sftp.avatar_to_sftp_server, LaunchpadAvatar, filetransfer.ISFTPServer)


class UserDisplayedUnauthorizedLogin(UnauthorizedLogin):
    """UnauthorizedLogin which should be reported to the user."""


class Realm:
    implements(IRealm)

    avatarFactory = LaunchpadAvatar

    def __init__(self, homeDirsRoot, authserver):
        self.homeDirsRoot = homeDirsRoot
        self.authserver = authserver

    def requestAvatar(self, avatarId, mind, *interfaces):
        # Fetch the user's details from the authserver
        deferred = self.authserver.getUser(avatarId)

        # Then fetch more details: the branches owned by this user (and the
        # teams they are a member of).
        def getInitialBranches(userDict):
            # XXX: Andrew Bennetts 2005-12-13: This makes many XML-RPC
            #      requests where a better API could require only one
            #      (or include it in the team dict in the first place).
            deferred = self.authserver.getBranchesForUser(userDict['id'])
            def _gotBranches(branches):
                userDict['initialBranches'] = branches
                return userDict
            return deferred.addCallback(_gotBranches)
        deferred.addCallback(getInitialBranches)

        # Once all those details are retrieved, we can construct the avatar.
        def gotUserDict(userDict):
            avatar = self.avatarFactory(avatarId, self.homeDirsRoot, userDict,
                                        self.authserver.proxy)
            return interfaces[0], avatar, lambda: None
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

    def _ebLogToBanner(self, reason):
        reason.trap(UserDisplayedUnauthorizedLogin)
        self.sendBanner(reason.getErrorMessage())
        return reason


class Factory(factory.SSHFactory):
    services = {
        'ssh-userauth': SSHUserAuthServer,
        'ssh-connection': connection.SSHConnection
    }

    def __init__(self, hostPublicKey, hostPrivateKey):
        self.publicKeys = {
            'ssh-rsa': hostPublicKey
        }
        self.privateKeys = {
            'ssh-rsa': hostPrivateKey
        }

    def startFactory(self):
        factory.SSHFactory.startFactory(self)
        os.umask(0022)


class PublicKeyFromLaunchpadChecker(SSHPublicKeyDatabase):
    """Cred checker for getting public keys from launchpad.

    It knows how to get the public keys from the authserver.
    """
    implements(ICredentialsChecker)

    def __init__(self, authserver):
        self.authserver = authserver

    def checkKey(self, credentials):
        d = self.authserver.getUser(credentials.username)
        return d.addCallback(self._checkUserExistence, credentials)

    def _checkUserExistence(self, userDict, credentials):
        if len(userDict) == 0:
            raise UserDisplayedUnauthorizedLogin(
                "No such Launchpad account: %s" % credentials.username)

        authorizedKeys = self.authserver.getSSHKeys(credentials.username)

        # Add callback to try find the authorized key
        authorizedKeys.addCallback(self._checkForAuthorizedKey, credentials)
        return authorizedKeys

    def _checkForAuthorizedKey(self, keys, credentials):
        if credentials.algName == 'ssh-dss':
            wantKeyType = 'DSA'
        elif credentials.algName == 'ssh-rsa':
            wantKeyType = 'RSA'
        else:
            # unknown key type
            return False

        if len(keys) == 0:
            raise UserDisplayedUnauthorizedLogin(
                "Launchpad user %r doesn't have a registered SSH key"
                % credentials.username)

        for keytype, keytext in keys:
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


class BazaarFileTransferServer(filetransfer.FileTransferServer):

    def __init__(self, data=None, avatar=None):
        filetransfer.FileTransferServer.__init__(self, data, avatar)
        self.logger = avatar.logger

    def connectionLost(self, reason=connectionDone):
        self.logger.info('Connection lost: %s', reason)
