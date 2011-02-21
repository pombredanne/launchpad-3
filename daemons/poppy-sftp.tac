# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This is a Twisted application config file.  To run, use:
#     twistd -noy sftp.tac
# or similar.  Refer to the twistd(1) man page for details.

import os
import logging
import tempfile

from twisted.application import service, strports
from twisted.conch.interfaces import ISession
from twisted.conch.ssh import filetransfer
from twisted.cred import checkers, credentials
from twisted.cred.portal import IRealm, Portal
from twisted.internet import defer
from twisted.protocols import ftp
from twisted.protocols.policies import TimeoutFactory
from twisted.python import components, filepath
from twisted.web.xmlrpc import Proxy

from zope.interface import implements

from canonical.config import config
from canonical.launchpad.daemons import readyservice

from lp.poppy.filesystem import UploadFileSystem
from lp.poppy.hooks import Hooks
from lp.poppy.twistedsftp import SFTPServer
from lp.services.sshserver.auth import (
    LaunchpadAvatar, PublicKeyFromLaunchpadChecker)
from lp.services.sshserver.service import SSHService
from lp.services.sshserver.session import DoNothingSession

# XXX: Rename this file to something that doesn't mention poppy. Talk to
# bigjools.


def make_portal():
    """Create and return a `Portal` for the SSH service.

    This portal accepts SSH credentials and returns our customized SSH
    avatars (see `LaunchpadAvatar`).
    """
    authentication_proxy = Proxy(
        config.poppy.authentication_endpoint)
    portal = Portal(Realm(authentication_proxy))
    portal.registerChecker(
        PublicKeyFromLaunchpadChecker(authentication_proxy))
    return portal


class PoppyAnonymousShell(ftp.FTPShell):
    """The 'command' interface for sessions.

    Roughly equivalent to the SFTPServer in the sftp side of things.
    """
    def __init__(self, fsroot):
        self._fs_root = fsroot
        self.uploadfilesystem = UploadFileSystem(tempfile.mkdtemp())
        self._current_upload = self.uploadfilesystem.rootpath
        os.chmod(self._current_upload, 0770)
        self._log = logging.getLogger("poppy-sftp")
        # XXX fix hooks
        self.hook = Hooks(
            self._fs_root, self._log, "ubuntu", perms='g+rws',
            prefix='-twftp')
        self.hook.new_client_hook(self._current_upload, 0, 0)
        self.hook.auth_verify_hook(self._current_upload, None, None)
        super(PoppyAnonymousShell, self).__init__(
            filepath.FilePath(self._current_upload))

    def openForWriting(self, file_segments):
        """Write the uploaded file to disk, safely.

        :param file_segments: A list containing string items, one for each
            path component of the file being uploaded.  The file referenced
            is relative to the temporary root for this session.

        If the file path contains directories, we create them.
        """
        filename = os.sep.join(file_segments)
        self._create_missing_directories(filename)
        return super(PoppyAnonymousShell, self).openForWriting(file_segments)

    def removeFile(self, path):
        # Same as SFTPServer
        pass

    def rename(self, old_path, new_path):
        # Same as SFTPServer
        abs_old = self._translate_path(old_path)
        abs_new = self._translate_path(new_path)
        os.rename(abs_old, abs_new)

    def makeDirectory(self, path):
        path = os.sep.join(path)
        return defer.maybeDeferred(self.uploadfilesystem.mkdir, path)

    def removeDirectory(self, path):
        path = os.sep.join(path)
        return defer.maybeDeferred(self.uploadfilesystem.rmdir(path))

    def logout(self):
        """Called when the client disconnects.

        We need to post-process the upload.
        """
        self.hook.client_done_hook(self._current_upload, 0, 0)

    def _create_missing_directories(self, filename):
        # Same as SFTPServer
        new_dir, new_file = os.path.split(
            self.uploadfilesystem._sanitize(filename))
        if new_dir != '':
            if not os.path.exists(
                os.path.join(self._current_upload, new_dir)):
                self.uploadfilesystem.mkdir(new_dir)

    def _translate_path(self, filename):
        return self.uploadfilesystem._full(
            self.uploadfilesystem._sanitize(filename))

    def list(self, path_segments, attrs):
        return defer.fail(ftp.CmdNotImplementedError("LIST"))


class PoppyAccessCheck:
    implements(checkers.ICredentialsChecker)
    credentialInterfaces = credentials.IUsernamePassword,

    def requestAvatarId(self, credentials):
        # Poppy allows any credentials.  People can use "anonymous" if
        # they want but anything goes.  Returning "poppy" here is
        # a totally arbitrary avatar.
        return "poppy"


class Realm:
    implements(IRealm)

    def __init__(self, authentication_proxy):
        self.authentication_proxy = authentication_proxy

    def requestAvatar(self, avatar_id, mind, *interfaces):
        # Fetch the user's details from the authserver
        deferred = mind.lookupUserDetails(
            self.authentication_proxy, avatar_id)

        # Once all those details are retrieved, we can construct the avatar.
        def got_user_dict(user_dict):
            avatar = LaunchpadAvatar(user_dict)
            return interfaces[0], avatar, avatar.logout

        return deferred.addCallback(got_user_dict)


class FTPRealm:
    """FTP Realm that lets anyone in."""
    implements(IRealm)

    def __init__(self, root):
        self.root = root

    def requestAvatar(self, avatarId, mind, *interfaces):
        for iface in interfaces:
            if iface is ftp.IFTPShell:
                avatar = PoppyAnonymousShell(self.root)
                return ftp.IFTPShell, avatar, getattr(
                    avatar, 'logout', lambda: None)
        raise NotImplementedError(
            "Only IFTPShell interface is supported by this realm")


def get_poppy_root():
    """Return the poppy root to use for this server.

    If the POPPY_ROOT environment variable is set, use that. If not, use
    config.poppy.fsroot.
    """
    poppy_root = os.environ.get('POPPY_ROOT', None)
    if poppy_root:
        return poppy_root
    return config.poppy.fsroot


def poppy_sftp_adapter(avatar):
    return SFTPServer(avatar, get_poppy_root())


components.registerAdapter(
    poppy_sftp_adapter, LaunchpadAvatar, filetransfer.ISFTPServer)

components.registerAdapter(DoNothingSession, LaunchpadAvatar, ISession)


class FTPServiceFactory(service.Service):
    def __init__(self, port):
        factory = ftp.FTPFactory()
        realm = FTPRealm(get_poppy_root())
        portal = Portal(realm)
        portal.registerChecker(
            PoppyAccessCheck())#, IAnonymous)

        factory.tld = get_poppy_root()
        factory.portal = portal
        factory.protocol = ftp.FTP
        # Setting this works around the fact that the twistd FTP server
        # invokes a special restricted shell when someone logs in as
        # "anonymous" which is the default for 'dput'.
        factory.userAnonymous = "userthatwillneverhappen"
        self.ftpfactory = factory
        self.portno = port
        # XXX self.timeOut = ?
        # XXX self.welcomeMessage = ?

    @staticmethod
    def makeFTPService(port=2121):
        strport = "tcp:%s" % port
        factory = FTPServiceFactory(port)
        return strports.service(strport, factory.ftpfactory)
        #return reactor.listenTCP(0, self.factory, interface="127.0.0.1")

ftpservice = FTPServiceFactory.makeFTPService()

# Construct an Application that has the Poppy SSH server.
application = service.Application('poppy-sftp')

ftpservice.setServiceParent(application)

def timeout_decorator(factory):
    """Add idle timeouts to a factory."""
    return TimeoutFactory(factory, timeoutPeriod=config.poppy.idle_timeout)

svc = SSHService(
    portal=make_portal(),
    private_key_path=config.poppy.host_key_private,
    public_key_path=config.poppy.host_key_public,
    oops_configuration='poppy',
    main_log='poppy',
    access_log='poppy.access',
    access_log_path=config.poppy.access_log,
    strport=config.poppy.port,
    factory_decorator=timeout_decorator,
    banner=config.poppy.banner)
svc.setServiceParent(application)

# Service that announces when the daemon is ready
readyservice.ReadyService().setServiceParent(application)
