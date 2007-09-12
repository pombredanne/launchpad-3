# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

import binascii
import os

from twisted.conch import avatar
from twisted.conch.error import ConchError
from twisted.conch.interfaces import ISession
from twisted.conch.ssh import session, filetransfer
from twisted.conch.ssh import factory, userauth, connection
from twisted.conch.ssh.common import getNS, NS
from twisted.conch.checkers import SSHPublicKeyDatabase

from twisted.cred.error import UnauthorizedLogin
from twisted.cred.checkers import ICredentialsChecker
from twisted.cred.portal import IRealm

from twisted.internet import defer

from twisted.python import components, failure

from twisted.vfs.pathutils import FileSystem
from twisted.vfs.adapters import sftp

from canonical.codehosting.bazaarfs import SFTPServerRoot
from canonical.codehosting.smartserver import launch_smart_server
from canonical.config import config

from zope.interface import implements


class SubsystemOnlySession(session.SSHSession, object):
    """Session adapter that corrects a bug in Conch."""

    def closeReceived(self):
        # Without this, the client hangs when its finished transferring.
        self.loseConnection()


class LaunchpadAvatar(avatar.ConchUser):

    def __init__(self, avatarId, homeDirsRoot, userDict, launchpad):
        # Double-check that we don't get unicode -- directory names on the file
        # system are a sequence of bytes as far as we're concerned.  We don't
        # want any tricky login names turning into a security problem.
        # (I'm reasonably sure twisted.cred guarantees this will be str, but in
        # the meantime let's make sure).
        assert type(avatarId) is str

        self.avatarId = avatarId
        self.homeDirsRoot = homeDirsRoot
        self._launchpad = launchpad

        # Fetch user details from the authserver
        self.lpid = userDict['id']
        self.lpname = userDict['name']
        self.teams = userDict['teams']

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

    def fetchProductID(self, productName):
        """Fetch the product ID for productName.

        Returns a Deferred of the result, which may be None if no product by
        that name exists.

        This method guarantees repeatable reads: on a particular instance of
        LaunchpadAvatar, fetchProductID will always return the same value for a
        given productName.
        """
        productID = self._productIDs.get(productName)
        if productID is not None:
            # XXX: Andrew Bennetts 2005-12-13: Should the None result
            # (i.e. not found) be remembered too, to ensure repeatable reads?
            return defer.succeed(productID)
        deferred = self._launchpad.fetchProductID(productName)
        deferred.addCallback(self._cbRememberProductID, productName)
        return deferred

    def createBranch(self, loginID, userName, productName, branchName):
        """Register a new branch in Launchpad.

        Returns a Deferred with the new branch ID.
        """
        return self._launchpad.createBranch(
            loginID, userName, productName, branchName)

    def _cbRememberProductID(self, productID, productName):
        if productID is None:
            return None
        # XXX: Andrew Bennetts 2007-01-26:
        # Why convert the number to a string here?
        productID = str(productID)
        self._productIDs[productName] = productID
        self._productNames[productID] = productName
        return productID

    def _runAsUser(self, f, *args, **kwargs):
        # Version of UnixConchUser._runAsUser with the setuid bits stripped out
        # -- we don't need them.
        try:
            f = iter(f)
        except TypeError:
            f = [(f, args, kwargs)]
        for i in f:
            func = i[0]
            args = len(i)>1 and i[1] or ()
            kw = len(i)>2 and i[2] or {}
            r = func(*args, **kw)
        return r

    def makeFileSystem(self):
        return FileSystem(SFTPServerRoot(self))


# XXX Andrew Bennetts 2007-01-26: This is nasty.  We want a filesystem per
# SFTP session, not per avatar, so we let the standard adapter grab a per
# avatar object, and immediately override with the one we want it to use.
class AdaptFileSystemUserToISFTP(sftp.AdaptFileSystemUserToISFTP):
    def __init__(self, avatar):
        sftp.AdaptFileSystemUserToISFTP.__init__(self, avatar)
        self.filesystem = avatar.makeFileSystem()


components.registerAdapter(AdaptFileSystemUserToISFTP, LaunchpadAvatar,
                           filetransfer.ISFTPServer)

components.registerAdapter(launch_smart_server, LaunchpadAvatar, ISession)


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
                                        self.authserver)
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

    # XXX Jonathan Lange 2007-03-19: Copied from
    # twisted/conch/ssh/userauth.py, with modifications noted.
    # In Twisted r19857 and earlier, this method does not return a Deferred,
    # but should. See http://twistedmatrix.com/trac/ticket/2528 for progress.
    def ssh_USERAUTH_REQUEST(self, packet):
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
        # The following line does not appear in the original Twisted source.
        d.addErrback(self._ebLogToBanner)
        d.addErrback(self._ebBadAuth)
        # Not in original Twisted method
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
        self._dirtyBranches = set()
        self.client.filesystem.root.setListenerFactory(self.makeListener)
        self._launchpad = self.client.avatar._launchpad

    def makeListener(self, branchID):
        def flag_as_dirty():
            self.branchDirtied(branchID)
        return flag_as_dirty

    def branchDirtied(self, branchID):
        self._dirtyBranches.add(branchID)

    def sendMirrorRequests(self):
        """Request that all changed branches be mirrored. Return a deferred
        which fires when each request has received a response from the server.
        """
        deferreds = [self._launchpad.requestMirror(branch)
                     for branch in self._dirtyBranches]
        return defer.gatherResults(deferreds)

    def connectionLost(self, reason):
        self.sendMirrorRequests()
