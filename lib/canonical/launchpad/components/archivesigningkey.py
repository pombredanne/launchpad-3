# Copyright 2008 Canonical Ltd.  All rights reserved.

"""ArchiveSigningKey implementation."""

__metaclass__ = type

__all__ = [
    'ArchiveSigningKey',
    ]


import os

import gpgme

from zope.component import getUtility
from zope.interface import implements

from canonical.config import config
from canonical.launchpad.interfaces.archivesigningkey import (
    IArchiveSigningKey)
from canonical.launchpad.interfaces.gpghandler import IGPGHandler
from canonical.launchpad.interfaces.gpg import IGPGKeySet, GPGKeyAlgorithm
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities


def exportKey(key, export_path):
    """Export the given key in the given export_path.

    Create full path if it doesn't exist.
    """
    if not os.path.exists(os.path.dirname(export_path)):
        os.makedirs(os.path.dirname(export_path))

    export_file = open(export_path, 'w')
    export_file.write(key.export())
    export_file.close()


class ArchiveSigningKey:
    """`IArchive` adapter for manipulating its GPG key."""

    implements(IArchiveSigningKey)

    def __init__(self, archive):
        self.archive = archive

    @property
    def _archive_root_path(self):
        # XXX cprov 20081104: IArchive pub configuration doesn't implement
        # any interface.
        from zope.security.proxy import removeSecurityProxy
        naked_pub_config = removeSecurityProxy(self.archive.getPubConfig())
        return naked_pub_config.archiveroot

    def _setSigningKey(self, gpg_key):
        # XXX cprov 20081104: setting 'signing_archive' requires lp.Admin
        # on IArchive and we better not relax it system-wide.
        from zope.security.proxy import removeSecurityProxy
        naked_archive = removeSecurityProxy(self.archive)
        naked_archive.signing_key = gpg_key

    def getPathForSecretKey(self, key):
        """See `IArchiveSigningKey`."""
        return os.path.join(
            config.personalpackagearchive.signing_keys_root,
            "%s.gpg" % key.fingerprint)

    @property
    def public_key_path(self):
        """See `IArchiveSigningKey`."""
        return os.path.join(self._archive_root_path, 'key.pub')

    def exportSecretKey(self, key):
        """See `IArchiveSigningKey`."""
        assert key.secret, "Only secret keys should be exported."
        exportKey(key, self.getPathForSecretKey(key))

    def exportPublicKey(self, key):
        """See `IArchiveSigningKey`."""
        assert not key.secret, "Only public keys should be exported."
        exportKey(key, self.public_key_path)

    def generateSigningKey(self):
        """See `IArchiveSigningKey`."""
        assert self.archive.signing_key is None, (
            "Cannot override signing_keys.")

        gpghandler = getUtility(IGPGHandler)
        key_owner = getUtility(ILaunchpadCelebrities).ppa_key_guard

        key_displayname = "%s signing key" % self.archive.title
        secret_key = gpghandler.generateKey(key_displayname)
        self.exportSecretKey(secret_key)

        pub_key = gpghandler.retrieveKey(secret_key.fingerprint)
        self.exportPublicKey(pub_key)

        # Store a IGPGKey with the public key information.
        algorithm = GPGKeyAlgorithm.items[pub_key.algorithm]
        gpg_key = getUtility(IGPGKeySet).new(
            key_owner, pub_key.keyid, pub_key.fingerprint, pub_key.keysize,
            algorithm, active=True, can_encrypt=pub_key.can_encrypt)

        # Assign the public key reference to the context IArchive.
        self._setSigningKey(gpg_key)

    def signRepository(self):
        """See `IArchiveSigningKey`."""
        assert self.archive.signing_key is not None, (
            "No signing key available for %s" % self.archive.title)

        release_file_path = os.path.join(self._archive_root_path, 'Release')
        assert os.path.exists(release_file_path), (
            "Release file doesn't exist in the repository")

        secret_key_export = open(
            self.getPathForSecretKey(self.archive.signing_key)).read()

        gpghandler = getUtility(IGPGHandler)
        secret_key = gpghandler.importSecretKey(secret_key_export)

        release_file_content = open(release_file_path).read()
        signature = gpghandler.signContent(
            release_file_content, secret_key.fingerprint,
            mode=gpgme.SIG_MODE_DETACH)

        release_signature_file = open(
            os.path.join(self._archive_root_path, 'Release.gpg'), 'w')
        release_signature_file.write(signature)
        release_signature_file.close()
