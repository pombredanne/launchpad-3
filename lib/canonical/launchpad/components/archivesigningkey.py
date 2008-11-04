# Copyright 2008 Canonical Ltd.  All rights reserved.

"""ArchiveSigningKey implementation."""

__metaclass__ = type

__all__ = [
    'ArchiveSigningKey',
    ]


import os

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

    def exportSecretKey(self, key):
        """Export the given secret key into a private location.

        Place a ASCII armored export of the given secret key into the
        disk location specified in the configurarion. E.g:

        /<ppa.signing_keys_root>/<FINGERPRINT>.gpg

        :param key: a secret `PymeKey` object to be exported.

        :raises: `AssertionError` if the given key is public.
        """
        assert key.secret, "Only secret keys should be exported."

        export_path = os.path.join(
            config.personalpackagearchive.signing_keys_root,
            "%s.gpg" % key.fingerprint)
        exportKey(key, export_path)

    def exportPublicKey(self, key):
        """Export the given public key into the corresponding repository.

        Place a ASCII armored export of the given public key into the
        repository location. E.g: /<ppa_root>/key.gpg

        :param key: a public `PymeKey` object to be exported.

        :raises: `AssertionError` if the given key is secret.
        """
        assert not key.secret, "Only public keys should be exported."

        # XXX cprov 20081104: Publish configuration has no interface.
        from zope.security.proxy import removeSecurityProxy
        naked_pub_config = removeSecurityProxy(self.archive.getPubConfig())
        export_path = os.path.join(
            naked_pub_config.archiveroot, 'key.pub')
        exportKey(key, export_path)

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
        self.archive.signing_key = gpg_key

    def signRepository(self):
        """See `IArchiveSigningKey`."""
        pass

