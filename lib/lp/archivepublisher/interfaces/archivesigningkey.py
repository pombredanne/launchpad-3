# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""ArchiveSigningKey interface."""

__metaclass__ = type

__all__ = [
    'CannotSignArchive',
    'IArchiveSigningKey',
    'ISignableArchive',
    ]

from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import Object

from lp import _
from lp.soyuz.interfaces.archive import IArchive


class CannotSignArchive(Exception):
    """An archive is not set up for signing."""


class ISignableArchive(Interface):
    """`SignableArchive` interface.

    `IArchive` adapter for operations that involve signing files.
    """

    archive = Object(
        title=_('Corresponding IArchive'), required=True, schema=IArchive)

    can_sign = Attribute("True if this archive is set up for signing.")

    def signRepository(suite, pubconf=None, suffix='', log=None):
        """Sign the corresponding repository.

        :param suite: suite name to be signed.
        :param pubconf: an optional publisher configuration instance
            indicating where files should be written (if not passed, uses
            the archive's defaults).
        :param suffix: an optional suffix for repository index files (e.g.
            ".new" to help with publishing files atomically).
        :param log: an optional logger.
        :raises CannotSignArchive: if the context archive is not set up for
            signing.
        :raises AssertionError: if there is no Release file in the given
            suite.
        """

    def signFile(suite, path, log=None):
        """Sign the corresponding file.

        :param suite: name of the suite containing the file to be signed.
        :param path: path within dists to sign with the archive key.
        :param log: an optional logger.
        :raises CannotSignArchive: if the context archive is not set up for
            signing.
        :raises AssertionError: if the given 'path' is outside of the
            archive root.
        """


class IArchiveSigningKey(ISignableArchive):
    """`ArchiveSigningKey` interface.

    `IArchive` adapter for operations using its 'signing_key'.

    Note that this adapter only works on zopeless mode for generating
    new signing keys.
    """

    def getPathForSecretKey(key):
        """Return the absolute path to access a secret key export.

        Disk location specified in the configurarion, for storing a
        secret key, e.g.:

        /<ppa.signing_keys_root>/<FINGERPRINT>.gpg

        :param key: a secret `PymeKey` object to be exported.
        :return: path to the key export.
        """

    def exportSecretKey(key):
        """Export the given secret key into a private location.

        Place a ASCII armored export of the given secret key in the
        location specified by `getPathForSecretKey`.

        :param key: a secret `PymeKey` object to be exported.
        :raises AssertionError: if the given key is public.
        """

    def generateSigningKey():
        """Generate a new GPG secret/public key pair.

        For named-ppas, the existing signing-key for the default PPA
        owner by the same user/team is reused. The *trust* belongs to
        the archive maintainer (owner) not the archive itself.

        Default ppas get brand new keys via the following procedure.

         * Export the secret key in the configuration disk location;
         * Upload the public key to the configuration keyserver;
         * Store a reference for the public key in GPGKey table, which
           is set as the context archive 'signing_key'.

        :raises AssertionError: if the context archive already has a
            `signing_key`.
        :raises GPGUploadFailure: if the just-generated key could not be
            upload to the keyserver.
        """

    def setSigningKey(key_path, async_keyserver=False):
        """Set a given secret key export as the context archive signing key.

        :param key_path: full path to the secret key.
        :param async_keyserver: true if the keyserver is running
            asynchronously in the current thread.
        :raises AssertionError: if the context archive already has a
            `signing_key`.
        :raises AssertionError: if the given 'key_path' does not exist.
        """
