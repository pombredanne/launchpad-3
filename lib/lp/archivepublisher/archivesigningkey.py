# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""ArchiveSigningKey implementation."""

__metaclass__ = type

__all__ = [
    'ArchiveSigningKey',
    'SignableArchive',
    'SigningMode',
    ]


import os

import gpgme
from lazr.enum import (
    EnumeratedType,
    Item,
    )
from twisted.internet.threads import deferToThread
from zope.component import getUtility
from zope.interface import implementer
from zope.security.proxy import (
    ProxyFactory,
    removeSecurityProxy,
    )

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.interfaces.archivesigningkey import (
    CannotSignArchive,
    IArchiveSigningKey,
    ISignableArchive,
    )
from lp.archivepublisher.run_parts import (
    find_run_parts_dir,
    run_parts,
    )
from lp.registry.interfaces.gpg import IGPGKeySet
from lp.services.config import config
from lp.services.gpg.interfaces import IGPGHandler
from lp.services.osutils import remove_if_exists
from lp.services.propertycache import get_property_cache


class SigningMode(EnumeratedType):
    """Archive file signing mode."""

    DETACHED = Item("Detached signature")
    CLEAR = Item("Cleartext signature")


@implementer(ISignableArchive)
class SignableArchive:
    """`IArchive` adapter for operations that involve signing files."""

    gpgme_modes = {
        SigningMode.DETACHED: gpgme.SIG_MODE_DETACH,
        SigningMode.CLEAR: gpgme.SIG_MODE_CLEAR,
        }

    def __init__(self, archive):
        self.archive = archive
        self.pubconf = getPubConfig(self.archive)

    @property
    def can_sign(self):
        """See `ISignableArchive`."""
        return (
            self.archive.signing_key is not None or
            find_run_parts_dir(
                self.archive.distribution.name, "sign.d") is not None)

    def _makeSignatures(self, signatures, log=None):
        """Make a sequence of signatures.

        This abstraction is useful in the case where we're using an
        in-process `GPGHandler`, since it avoids having to import the secret
        key more than once.

        :param signatures: A sequence of (input path, output path,
            `SigningMode`, suite) tuples.  Note that some backends may make
            a policy decision not to produce all the requested output paths.
        :param log: An optional logger.
        :return: A list of output paths that were produced.
        """
        if not self.can_sign:
            raise CannotSignArchive(
                "No signing key available for %s" % self.archive.displayname)

        if self.archive.signing_key is not None:
            secret_key_path = self.getPathForSecretKey(
                self.archive.signing_key)
            with open(secret_key_path) as secret_key_file:
                secret_key_export = secret_key_file.read()
            gpghandler = getUtility(IGPGHandler)
            secret_key = gpghandler.importSecretKey(secret_key_export)

        output_paths = []
        for input_path, output_path, mode, suite in signatures:
            if self.archive.signing_key is not None:
                with open(input_path) as input_file:
                    input_content = input_file.read()
                signature = gpghandler.signContent(
                    input_content, secret_key, mode=self.gpgme_modes[mode])
                with open(output_path, "w") as output_file:
                    output_file.write(signature)
                output_paths.append(output_path)
            elif find_run_parts_dir(
                    self.archive.distribution.name, "sign.d") is not None:
                remove_if_exists(output_path)
                env = {
                    "ARCHIVEROOT": self.pubconf.archiveroot,
                    "INPUT_PATH": input_path,
                    "OUTPUT_PATH": output_path,
                    "MODE": mode.name.lower(),
                    "DISTRIBUTION": self.archive.distribution.name,
                    "SUITE": suite,
                    }
                run_parts(
                    self.archive.distribution.name, "sign.d",
                    log=log, env=env)
                if os.path.exists(output_path):
                    output_paths.append(output_path)
            else:
                raise AssertionError(
                    "No signing key available for %s" %
                    self.archive.displayname)
        return output_paths

    def signRepository(self, suite, pubconf=None, suffix='', log=None):
        """See `ISignableArchive`."""
        if pubconf is None:
            pubconf = self.pubconf
        suite_path = os.path.join(pubconf.distsroot, suite)
        release_file_path = os.path.join(suite_path, 'Release' + suffix)
        if not os.path.exists(release_file_path):
            raise AssertionError(
                "Release file doesn't exist in the repository: %s" %
                release_file_path)

        output_names = []
        for output_path in self._makeSignatures([
                (release_file_path,
                 os.path.join(suite_path, 'Release.gpg' + suffix),
                 SigningMode.DETACHED, suite),
                (release_file_path,
                 os.path.join(suite_path, 'InRelease' + suffix),
                 SigningMode.CLEAR, suite),
                ], log=log):
            output_name = os.path.basename(output_path)
            if suffix:
                output_name = output_name[:-len(suffix)]
            assert (
                os.path.join(suite_path, output_name + suffix) == output_path)
            output_names.append(output_name)
        return output_names

    def signFile(self, suite, path, log=None):
        """See `ISignableArchive`."""
        # Allow the passed path to be relative to the archive root.
        path = os.path.realpath(os.path.join(self.pubconf.archiveroot, path))

        # Ensure the resulting path is within the archive root after
        # normalisation.
        # NOTE: uses os.sep to prevent /var/tmp/../tmpFOO attacks.
        archive_root = self.pubconf.archiveroot + os.sep
        if not path.startswith(archive_root):
            raise AssertionError(
                "Attempting to sign file (%s) outside archive_root for %s" % (
                    path, self.archive.displayname))

        self._makeSignatures(
            [(path, "%s.gpg" % path, SigningMode.DETACHED, suite)], log=log)


@implementer(IArchiveSigningKey)
class ArchiveSigningKey(SignableArchive):
    """`IArchive` adapter for manipulating its GPG key."""

    def getPathForSecretKey(self, key):
        """See `IArchiveSigningKey`."""
        return os.path.join(
            config.personalpackagearchive.signing_keys_root,
            "%s.gpg" % key.fingerprint)

    def exportSecretKey(self, key):
        """See `IArchiveSigningKey`."""
        assert key.secret, "Only secret keys should be exported."
        export_path = self.getPathForSecretKey(key)

        if not os.path.exists(os.path.dirname(export_path)):
            os.makedirs(os.path.dirname(export_path))

        with open(export_path, 'w') as export_file:
            export_file.write(key.export())

    def generateSigningKey(self):
        """See `IArchiveSigningKey`."""
        assert self.archive.signing_key is None, (
            "Cannot override signing_keys.")

        # Always generate signing keys for the default PPA, even if it
        # was not expecifically requested. The default PPA signing key
        # is then propagated to the context named-ppa.
        default_ppa = self.archive.owner.archive
        if self.archive != default_ppa:
            if default_ppa.signing_key is None:
                IArchiveSigningKey(default_ppa).generateSigningKey()
            key = default_ppa.signing_key
            self.archive.signing_key_owner = key.owner
            self.archive.signing_key_fingerprint = key.fingerprint
            del get_property_cache(self.archive).signing_key
            return

        key_displayname = (
            "Launchpad PPA for %s" % self.archive.owner.displayname)
        secret_key = getUtility(IGPGHandler).generateKey(key_displayname)
        self._setupSigningKey(secret_key)

    def setSigningKey(self, key_path, async_keyserver=False):
        """See `IArchiveSigningKey`."""
        assert self.archive.signing_key is None, (
            "Cannot override signing_keys.")
        assert os.path.exists(key_path), (
            "%s does not exist" % key_path)

        with open(key_path) as key_file:
            secret_key_export = key_file.read()
        secret_key = getUtility(IGPGHandler).importSecretKey(secret_key_export)
        return self._setupSigningKey(
            secret_key, async_keyserver=async_keyserver)

    def _uploadPublicSigningKey(self, secret_key):
        """Upload the public half of a signing key to the keyserver."""
        # The handler's security proxying doesn't protect anything useful
        # here, and when we're running in a thread we don't have an
        # interaction.
        gpghandler = removeSecurityProxy(getUtility(IGPGHandler))
        pub_key = gpghandler.retrieveKey(secret_key.fingerprint)
        gpghandler.uploadPublicKey(pub_key.fingerprint)
        return pub_key

    def _storeSigningKey(self, pub_key):
        """Store signing key reference in the database."""
        key_owner = getUtility(ILaunchpadCelebrities).ppa_key_guard
        key, _ = getUtility(IGPGKeySet).activate(
            key_owner, pub_key, pub_key.can_encrypt)
        self.archive.signing_key_owner = key.owner
        self.archive.signing_key_fingerprint = key.fingerprint
        del get_property_cache(self.archive).signing_key

    def _setupSigningKey(self, secret_key, async_keyserver=False):
        """Mandatory setup for signing keys.

        * Export the secret key into the protected disk location.
        * Upload public key to the keyserver.
        * Store the public GPGKey reference in the database and update
          the context archive.signing_key.
        """
        self.exportSecretKey(secret_key)
        if async_keyserver:
            # If we have an asynchronous keyserver running in the current
            # thread using Twisted, then we need some contortions to ensure
            # that the GPG handler doesn't deadlock.  This is most easily
            # done by deferring the GPG handler work to another thread.
            # Since that thread won't have a Zope interaction, we need to
            # unwrap the security proxy for it.
            d = deferToThread(
                self._uploadPublicSigningKey, removeSecurityProxy(secret_key))
            d.addCallback(ProxyFactory)
            d.addCallback(self._storeSigningKey)
            return d
        else:
            pub_key = self._uploadPublicSigningKey(secret_key)
            self._storeSigningKey(pub_key)
