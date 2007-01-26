# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from twisted.conch import avatar
from twisted.conch.ssh import session, filetransfer
from twisted.conch.ssh import factory, userauth, connection
from twisted.conch.checkers import SSHPublicKeyDatabase
from twisted.cred.checkers import ICredentialsChecker
from twisted.cred.portal import IRealm
from twisted.internet import defer
from twisted.python import components
from twisted.vfs.pathutils import FileSystem
from twisted.vfs.adapters import sftp
from canonical.supermirrorsftp.bazaarfs import SFTPServerRoot

from zope.interface import implements
import binascii
import os
import os.path


class SubsystemOnlySession(session.SSHSession, object):
    """A session adapter that disables every request except request_subsystem"""
    def __getattribute__(self, name):
        # Get out the big hammer :)
        # (This is easier than overriding all the different request_ methods
        # individually, or writing an ISession adapter to give the same effect.)
        if name.startswith('request_') and name not in ('request_subsystem',
                                                        'request_exec'):
            raise AttributeError(name)
        return object.__getattribute__(self, name)

    def closeReceived(self):
        # Without this, the client hangs when its finished transferring.
        self.loseConnection()


class SFTPOnlyAvatar(avatar.ConchUser):
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
        self.branches = {}
        for teamDict in self.teams:
            self.branches[teamDict['id']] = teamDict['initialBranches']

        self._productIDs = {}
        self._productNames = {}

        self.filesystem = FileSystem(SFTPServerRoot(self))

        # Set the only channel as a session that only allows requests for
        # subsystems...
        self.channelLookup = {'session': SubsystemOnlySession}
        # ...and set the only subsystem to be SFTP.
        self.subsystemLookup = {'sftp': filetransfer.FileTransferServer}

    def fetchProductID(self, productName):
        """Fetch the product ID for productName.

        Returns a Deferred of the result, which may be None if no product by
        that name exists.

        This method guarantees repeatable reads: on a particular instance of
        SFTPOnlyAvatar, fetchProductID will always return the same value for a
        given productName.
        """
        productID = self._productIDs.get(productName)
        if productID is not None:
            # XXX: should the None result (i.e. not found) be remembered too, to
            #      ensure repeatable reads?
            #  -- Andrew Bennetts, 2005-12-13
            return defer.succeed(productID)
        deferred = self._launchpad.fetchProductID(productName)
        deferred.addCallback(self._cbRememberProductID, productName)
        return deferred

    def createBranch(self, userID, productID, branchName):
        """Register a new branch in Launchpad.

        Returns a Deferred with the new branch ID.
        """
        return self._launchpad.createBranch(userID, productID, branchName)

    def _cbRememberProductID(self, productID, productName):
        if productID is None:
            return None
        # XXX: Why convert the number to a string here?
        #  -- Andrew Bennetts, 2007-01-26
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


components.registerAdapter(sftp.AdaptFileSystemUserToISFTP, SFTPOnlyAvatar,
                           filetransfer.ISFTPServer)


class Realm:
    implements(IRealm)

    def __init__(self, homeDirsRoot, authserver):
        self.homeDirsRoot = homeDirsRoot
        self.authserver = authserver

    def requestAvatar(self, avatarId, mind, *interfaces):
        # Fetch the user's details from the authserver
        deferred = self.authserver.getUser(avatarId)
        
        # Then fetch more details: the branches owned by this user (and the
        # teams they are a member of).
        def getInitialBranches(userDict):
            # XXX: this makes many XML-RPC requests where a better API could
            #      require only one (or include it in the team dict in the first
            #      place).
            #  -- Andrew Bennetts, 2005-12-13
            deferreds = []
            for teamDict in userDict['teams']:
                deferred = self.authserver.getBranchesForUser(teamDict['id'])
                def _gotBranches(branches, teamDict=teamDict):
                    teamDict['initialBranches'] = branches
                deferred.addCallback(_gotBranches)
                deferreds.append(deferred)
            def allDone(ignore):
                return userDict

            # This callback will complete when all the getBranchesForUser calls
            # have completed and added initialBranches to each team dict, and
            # will return the userDict.
            return defer.DeferredList(deferreds,
                    fireOnOneErrback=True).addCallback(allDone)
        deferred.addCallback(getInitialBranches)

        # Once all those details are retrieved, we can construct the avatar.
        def gotUserDict(userDict):
            avatar = SFTPOnlyAvatar(avatarId, self.homeDirsRoot, userDict,
                                    self.authserver)
            return interfaces[0], avatar, lambda: None
        return deferred.addCallback(gotUserDict)


class Factory(factory.SSHFactory):
    services = {
        'ssh-userauth': userauth.SSHUserAuthServer,
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
        authorizedKeys = self.authserver.getSSHKeys(credentials.username)

        # Add callback to try find the authorised key
        authorizedKeys.addCallback(self._cb_hasAuthorisedKey, credentials)
        return authorizedKeys
                
    def _cb_hasAuthorisedKey(self, keys, credentials):
        if credentials.algName == 'ssh-dss':
            wantKeyType = 'DSA'
        elif credentials.algName == 'ssh-rsa':
            wantKeyType = 'RSA'
        else:
            # unknown key type
            return False

        for keytype, keytext in keys:
            if keytype != wantKeyType:
                continue
            try:
                if keytext.decode('base64') == credentials.blob:
                    return True
            except binascii.Error:
                continue

        return False
        

if __name__ == "__main__":
    # Run doctests.
    import doctest
    doctest.testmod()

