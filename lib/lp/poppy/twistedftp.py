# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Twisted FTP implementation of the Poppy upload server."""

__metaclass__ = type
__all__ = [
    'FTPRealm',
    'PoppyAnonymousShell',
    ]

import logging
import os
import tempfile

from twisted.application import service, strports
from twisted.cred import checkers, credentials
from twisted.cred.portal import IRealm, Portal
from twisted.internet import defer
from twisted.protocols import ftp
from twisted.python import filepath

from zope.interface import implements
from zope.component import getUtility

from canonical.launchpad.interfaces.gpghandler import (
    GPGVerificationError,
    IGPGHandler,
    )

from canonical.config import config
from lp.poppy import get_poppy_root
from lp.poppy.filesystem import UploadFileSystem
from lp.poppy.hooks import Hooks
from lp.registry.interfaces.gpg import IGPGKeySet
from lp.services.database import read_transaction


class PoppyAccessCheck:
    """An `ICredentialsChecker` for Poppy FTP sessions."""
    implements(checkers.ICredentialsChecker)
    credentialInterfaces = (
        credentials.IUsernamePassword, credentials.IAnonymous)

    def requestAvatarId(self, credentials):
        # Poppy allows any credentials.  People can use "anonymous" if
        # they want but anything goes.  Thus, we don't actually *check* the
        # credentials, and we return the standard avatarId for 'anonymous'.
        return checkers.ANONYMOUS


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
        self.hook = Hooks(
            self._fs_root, self._log, "ubuntu", perms='g+rws',
            prefix='-ftp')
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
        path = self._path(file_segments)
        try:
            fObj = path.open("w")
        except (IOError, OSError), e:
            return ftp.errnoToFailure(e.errno, path)
        except:
            # Push any other error up to Twisted to deal with.
            return defer.fail()
        return defer.succeed(PoppyFileWriter(fObj))

    def makeDirectory(self, path):
        """Make a directory using the secure `UploadFileSystem`."""
        path = os.sep.join(path)
        return defer.maybeDeferred(self.uploadfilesystem.mkdir, path)

    def access(self, segments):
        """Permissive CWD that auto-creates target directories."""
        if segments:
            path = self._path(segments)
            path.makedirs()
        return super(PoppyAnonymousShell, self).access(segments)

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

    def list(self, path_segments, attrs):
        return defer.fail(ftp.CmdNotImplementedError("LIST"))


class FTPRealm:
    """FTP Realm that lets anyone in."""
    implements(IRealm)

    def __init__(self, root):
        self.root = root

    def requestAvatar(self, avatarId, mind, *interfaces):
        """Return a Poppy avatar - that is, an "authorisation".

        Poppy FTP avatars are totally fake, we don't care about credentials.
        See `PoppyAccessCheck` above.
        """
        for iface in interfaces:
            if iface is ftp.IFTPShell:
                avatar = PoppyAnonymousShell(self.root)
                return ftp.IFTPShell, avatar, getattr(
                    avatar, 'logout', lambda: None)
        raise NotImplementedError(
            "Only IFTPShell interface is supported by this realm")


class PoppyFileWriter(ftp._FileWriter):
    """An `IWriteFile` that checks for signed changes files."""

    def close(self):
        """Called after the file has been completely downloaded."""
        if self.fObj.name.endswith(".changes"):
            error = self.validateGPG(self.fObj.name)
            if error is not None:
                # PermissionDeniedError is one of the few ftp exceptions
                # that lets us pass an error string back to the client.
                return defer.fail(ftp.PermissionDeniedError(error))
        return defer.succeed(None)

    @read_transaction
    def validateGPG(self, signed_file):
        """Check the GPG signature in the file referenced by signed_file.

        Return an error string if there's a problem, or None.
        """
        try:
            sig = getUtility(IGPGHandler).getVerifiedSignatureResilient(
                file(signed_file, "rb").read())
        except GPGVerificationError, error:
            return ("Changes file must be signed with a valid GPG "
                    "signature: %s" % error)

        key = getUtility(IGPGKeySet).getByFingerprint(sig.fingerprint)
        if key is None:
            return (
                "Signing key %s not registered in launchpad."
                % sig.fingerprint)

        if key.active == False:
            return "Changes file is signed with a deactivated key"

        return None


class FTPServiceFactory(service.Service):
    """A factory that makes an `FTPService`"""

    def __init__(self, port):
        realm = FTPRealm(get_poppy_root())
        portal = Portal(realm)
        portal.registerChecker(PoppyAccessCheck())
        factory = ftp.FTPFactory(portal)

        factory.tld = get_poppy_root()
        factory.protocol = ftp.FTP
        factory.welcomeMessage = "Launchpad upload server"
        factory.timeOut = config.poppy.idle_timeout

        self.ftpfactory = factory
        self.portno = port

    @staticmethod
    def makeFTPService(port=2121):
        strport = "tcp:%s" % port
        factory = FTPServiceFactory(port)
        return strports.service(strport, factory.ftpfactory)
