# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""ArchiveSigningKey interface."""

__metaclass__ = type

__all__ = [
    'IArchiveSigningKey',
    ]

from zope.interface import Attribute, Interface
from zope.schema import Object

from canonical.launchpad import _
from canonical.launchpad.interfaces.archive import IArchive


class IArchiveSigningKey(Interface):
    """`ArchiveSigningKey` interface."""

    archive = Object(
        title=_('Corresponding IArchive'), required=True, schema=IArchive)

    public_key_path = Attribute(
        "Absolute disk path of an export of the corresponding public "
        "signing key.")

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
        :raises: `AssertionError` if the given key is public.
        """

    def exportPublicKey(key):
        """Export the given public key into the corresponding repository.

        Place a ASCII armored export of the given public key into the
        repository location, specified by `public_key_path`. E.g:

        /<ppa_repository_root>/key.gpg

        :param key: a public `PymeKey` object to be exported.
        :raises: `AssertionError` if the given key is secret.
        """

    def generateSigningKey():
        """Generate a new GPG secret/public key pair."""

    def signRepository():
        """Sign the corresponding repository."""


