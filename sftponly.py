from canonical.authserver.client.sshkeys import TwistedAuthServer

from twisted.conch import avatar
from twisted.conch.ssh import session, filetransfer
from twisted.conch.ssh import factory, userauth, connection
from twisted.conch.checkers import SSHPublicKeyDatabase
from twisted.cred.checkers import ICredentialsChecker

from zope.interface import implements


class SubsystemOnlySession(session.SSHSession, object):
    """A session adapter that disables every request except request_subsystem"""
    def __getattribute__(self, name):
        # Get out the big hammer :)
        # (I'm too lazy to override all the different request_ methods
        # individually, or write an ISession adapter to give the same effect.)
        if name.startswith('request') and name != 'request_subsystem':
            raise AttributeError, name
        return object.__getattribute__(self, name)


class SFTPOnlyAvatar(avatar.ConchUser):
    # Set the only channel as a session that only allows requests for
    # subsystems...
    channelLookup = {'session': SubsystemOnlySession}
    # ...and set the only subsystem to be SFTP.
    subsystemLookup = {'sftp': filetransfer.FileTransferServer}


class Realm:
    implements(portal.IRealm)

    def requestAvatar(self, avatarId, mind, *interfaces):
        return interfaces[0], SFTPOnlyAvatar(avatarId), lambda: None


class Factory(factory.SSHFactory):
    publicKeys = {
        'ssh-rsa': hostPublicKey
    }
    privateKeys = {
        'ssh-rsa': hostPrivateKey
    }
    services = {
        'ssh-userauth': userauth.SSHUserAuthServer,
        'ssh-connection': connection.SSHConnection
    }


class PublicKeyFromLaunchpadChecker(SSHPublicKeyDatabase):
    implements(ICredentialsChecker)

    def __init__(self, authserverURL):
        self.authserver = TwistedAuthServer(authserverURL)

    def checkKey(self, credentials):
        authorizedKeys = self.authserver.getSSHKeys(credentials.username)
        authorizedKeys.addCallback(self._cb_hasAuthorisedKey, credentials)
        return authorizedKeys
                
    def _cb_hasAuthorisedKey(self, keys, credentials):
        for keytype, keytext in credentials:
            try:
                if base64.decodestring(l2[1]) == credentials.blob:
                    return True
            except binascii.Error:
                continue

        return False
        
