# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from canonical.authserver.client.twistedclient import TwistedAuthServer

from twisted.conch import avatar, unix
from twisted.conch.ssh import session, filetransfer
from twisted.conch.ssh import factory, userauth, connection
from twisted.conch.checkers import SSHPublicKeyDatabase
from twisted.cred.checkers import ICredentialsChecker
from twisted.cred.portal import IRealm
from twisted.python import components
from twisted.python.filepath import FilePath, InsecurePath

from zope.interface import implements
import binascii
import os
import os.path
import errno


class SubsystemOnlySession(session.SSHSession, object):
    """A session adapter that disables every request except request_subsystem"""
    def __getattribute__(self, name):
        # Get out the big hammer :)
        # (I'm too lazy to override all the different request_ methods
        # individually, or write an ISession adapter to give the same effect.)
        if name.startswith('request_') and name != 'request_subsystem':
            raise AttributeError, name
        return object.__getattribute__(self, name)

    def closeReceived(self):
        # Without this, the client hangs when its finished transferring.
        self.loseConnection()


class SFTPOnlyAvatar(avatar.ConchUser):
    def __init__(self, avatarId, homeDirsRoot):
        # Double-check that we don't get unicode -- directory names on the file
        # system are a sequence of bytes as far as we're concerned.  We don't
        # want any tricky login names turning into a security problem.
        # (I'm reasonably sure cred guarantees this will be str, but in the
        # meantime let's make sure).
        assert type(avatarId) is str

        # XXX: These two asserts should be raise exceptions that cause proper
        #      auth failures, not asserts.  (an assert should never be triggered
        #      by bad user input).
        #  - Andrew Bennetts, 2005-01-21
        assert '/' not in avatarId
        assert avatarId not in ('.', '..')

        self.avatarId = avatarId
        self.homeDirsRoot = homeDirsRoot

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
        return os.path.join(self.homeDirsRoot, self.avatarId)


class SFTPServerForPushMirrorUser:
    """This is much like unix.SFTPServerForUnixConchUser, but:
        - doesn't allow any traversal above the home directory
        - uid/gid can't be set
        - symlinks cannot be made
    """
    # TODO: This doesn't return friendly error messages to the client when
    #       restricted operations are attempted (they generally are sent as
    #       "Failure").

    implements(filetransfer.ISFTPServer)

    def __init__(self, avatar):
        self.avatar = avatar
        self.homedir = FilePath(self.avatar.getHomeDir())
        # Make the home dir if it doesn't already exist
        try:
            self.homedir.makedirs()
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise

    def _childPath(self, path):
        if path.startswith('/'):
            path = '.' + path
        return self.homedir.preauthChild(path)

    def gotVersion(self, otherVersion, extData):
        # we don't support anything extra beyond standard SFTP
        return {}

    def extendedRequest(self, extendedName, extendedData):
        # We don't implement any extensions to SFTP.
        raise NotImplementedError
    
    def openFile(self, filename, flags, attrs):
        return unix.UnixSFTPFile(self, self._childPath(filename).path, flags,
                attrs)

    def removeFile(self, filename):
        self._childPath(filename).remove()

    def renameFile(self, oldpath, newpath):
        old = self._childPath(oldpath)
        new = self._childPath(newpath)
        os.rename(old.path, new.path)

    def makeDirectory(self, path, attrs):
        path = self._childPath(path).path
        os.mkdir(path)
        # XXX: self._setattrs(path)

    def removeDirectory(self, path):
        os.rmdir(self._childPath(path).path)

    def openDirectory(self, path):
        return unix.UnixSFTPDirectory(self, self._childPath(path).path)

    def _getAttrs(self, s):
        """Convert the result of os.stat/os.lstat to an SFTP attributes dict
        
        Ideally this would be named something more like _statToAttrs, but this
        is required by UnixSFTPDirectory.
        """
        # FIXME: We probably want to give fake uid/gid details.
        # From twisted.conch.unix.SFTPServerForUnixConchUser._getAttrs
        return {
            "size" : s.st_size,
            "uid" : s.st_uid,
            "gid" : s.st_gid,
            "permissions" : s.st_mode,
            "atime" : s.st_atime,
            "mtime" : s.st_mtime
        }

    def getAttrs(self, path, followLinks):
        path = self._childPath(path).path
        if followLinks:
            statFunc = os.stat
        else:
            statFunc = os.lstat
        return self._getAttrs(statFunc(path))
    
    def setAttrs(self, path, attrs):
        path = self._childPath(path).path
        # We ignore the uid and gid attributes!
        # XXX: should we raise an error if they try to set them?
        if 'permissions' in attrs:
            os.chmod(path, attrs["permissions"])
        if 'atime' in attrs and 'mtime' in attrs:
            os.utime(path, (attrs["atime"], attrs["mtime"]))

    def readLink(self, path):
        path = self._childPath(path).path
        return os.readlink(path)

    def makeLink(self, linkPath, targetPath):
        # We disallow symlinks entirely.
        raise OSError, 'Permission denied'

    def realPath(self, path):
        path = self._childPath(path)
        # Make sure it really exists
        path.restat()

        # If it exists, it must be a real path, because we've disallowed
        # creating symlinks!  So, we can just return the path as-is (after
        # prefixing it with "." rather than self.homedir).
        return '.' + path.path[len(self.homedir.path):]


components.registerAdapter(SFTPServerForPushMirrorUser, SFTPOnlyAvatar,
                           filetransfer.ISFTPServer)


class Realm:
    implements(IRealm)

    def __init__(self, homeDirsRoot):
        self.homeDirsRoot = homeDirsRoot

    def requestAvatar(self, avatarId, mind, *interfaces):
        avatar = SFTPOnlyAvatar(avatarId, self.homeDirsRoot)
        return interfaces[0], avatar, lambda: None


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
        
