# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from canonical.authserver.client.sshkeys import TwistedAuthServer

from twisted.conch import avatar, unix
from twisted.conch.ssh import session, filetransfer
from twisted.conch.ssh import factory, userauth, connection
from twisted.conch.checkers import SSHPublicKeyDatabase
from twisted.cred.checkers import ICredentialsChecker
from twisted.cred.portal import IRealm
from twisted.python import components

from zope.interface import implements
import binascii


class SubsystemOnlySession(session.SSHSession, object):
    """A session adapter that disables every request except request_subsystem"""
    def __getattribute__(self, name):
        # Get out the big hammer :)
        # (I'm too lazy to override all the different request_ methods
        # individually, or write an ISession adapter to give the same effect.)
        if name.startswith('request_') and name != 'request_subsystem':
            raise AttributeError, name
        return object.__getattribute__(self, name)


class SFTPOnlyAvatar(avatar.ConchUser):
    def __init__(self, avatarId):
        self.avatarId = avatarId

        # Set the only channel as a session that only allows requests for
        # subsystems...
        self.channelLookup = {'session': SubsystemOnlySession}
        # ...and set the only subsystem to be SFTP.
        self.subsystemLookup = {'sftp': filetransfer.FileTransferServer}

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

    def getHomeDir(self):
        # XXX: the base should be configurable!
        return '/tmp/' + self.avatarId


# XXX: We need to customise unix.SFTPServerForUnixConchUser, we want to restrict
#      it a little.
components.registerAdapter(unix.SFTPServerForUnixConchUser, SFTPOnlyAvatar, filetransfer.ISFTPServer)


class Realm:
    implements(IRealm)

    def requestAvatar(self, avatarId, mind, *interfaces):
        return interfaces[0], SFTPOnlyAvatar(avatarId), lambda: None


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


class PublicKeyFromLaunchpadChecker(SSHPublicKeyDatabase):
    implements(ICredentialsChecker)

    def __init__(self, authserverURL):
        self.authserver = TwistedAuthServer(authserverURL)

    def checkKey(self, credentials):
        authorizedKeys = self.authserver.getSSHKeys(credentials.username)
        authorizedKeys.addCallback(self._cb_hasAuthorisedKey, credentials)
        return authorizedKeys
                
    def _cb_hasAuthorisedKey(self, keys, credentials):
        for keytype, keytext in keys:
            try:
                if keytext.decode('base64') == credentials.blob:
                    return True
            except binascii.Error:
                continue

        return False
        
