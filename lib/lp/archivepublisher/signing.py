# Copyright 2012-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The processing of Signing tarballs.

UEFI Secure Boot requires boot loader images to be signed, and we want to
have signed images in the archive so that they can be used for upgrades.
This cannot be done on the build daemons because they are insufficiently
secure to hold signing keys, so we sign them as a custom upload instead.
"""

from __future__ import print_function

__metaclass__ = type

__all__ = [
    "SigningUpload",
    "UefiUpload",
    ]

import os
import shutil
import subprocess
import tarfile
import tempfile
import textwrap

from lp.archivepublisher.customupload import CustomUpload
from lp.services.osutils import remove_if_exists
from lp.soyuz.interfaces.queue import CustomUploadError


class SigningUploadPackError(CustomUploadError):
    def __init__(self, tarfile_path, exc):
        message = "Problem building tarball '%s': %s" % (
            tarfile_path, exc)
        CustomUploadError.__init__(self, message)


class SigningUpload(CustomUpload):
    """Signing custom upload.

    The filename must be of the form:

        <PACKAGE>_<VERSION>_<ARCH>.tar.gz

    where:

      * PACKAGE: source package of the contents;
      * VERSION: encoded version;
      * ARCH: targeted architecture tag (e.g. 'amd64').

    The contents are extracted in the archive in the following path:

        <ARCHIVE>/dists/<SUITE>/main/signed/<PACKAGE>-<ARCH>/<VERSION>

    A 'current' symbolic link points to the most recent version.  The
    tarfile must contain at least one file matching the wildcard *.efi, and
    any such files are signed using the archive's UEFI signing key.

    Signing keys may be installed in the "signingroot" directory specified in
    publisher configuration.  In this directory, the private key is
    "uefi.key" and the certificate is "uefi.crt".
    """
    custom_type = "signing"

    dists_directory = "signed"

    @staticmethod
    def parsePath(tarfile_path):
        tarfile_base = os.path.basename(tarfile_path)
        bits = tarfile_base.split("_")
        if len(bits) != 3:
            raise ValueError("%s is not TYPE_VERSION_ARCH" % tarfile_base)
        return bits[0], bits[1], bits[2].split(".")[0]

    def setComponents(self, tarfile_path):
        self.package, self.version, self.arch = self.parsePath(
            tarfile_path)

    def setTargetDirectory(self, pubconf, tarfile_path, suite):
        if pubconf.signingroot is None:
            if self.logger is not None:
                self.logger.warning(
                    "No signing root configured for this archive")
            self.uefi_key = None
            self.uefi_cert = None
            self.kmod_pem = None
            self.kmod_x509 = None
            self.autokey = False
        else:
            self.uefi_key = os.path.join(pubconf.signingroot, "uefi.key")
            self.uefi_cert = os.path.join(pubconf.signingroot, "uefi.crt")
            self.kmod_pem = os.path.join(pubconf.signingroot, "kmod.pem")
            self.kmod_x509 = os.path.join(pubconf.signingroot, "kmod.x509")
            self.autokey = pubconf.signingautokey

        self.setComponents(tarfile_path)

        dists_signed = os.path.join(pubconf.archiveroot, "dists",
            suite, "main", self.dists_directory)
        self.targetdir = os.path.join(
            dists_signed, "%s-%s" % (self.package, self.arch))
        self.archiveroot = pubconf.archiveroot

    def setSigningOptions(self):
        """Find and extract raw-signing.options from the tarball."""
        self.signing_options = {}

        options_file = os.path.join(self.tmpdir, self.version,
            "raw-signing.options")
        if not os.path.exists(options_file):
            return

        with open(options_file) as options_fd:
            for option in options_fd:
                self.signing_options[option.strip()] = True

    @classmethod
    def getSeriesKey(cls, tarfile_path):
        try:
            package, _, arch = cls.parsePath(tarfile_path)
            return package, arch
        except ValueError:
            return None

    def getArchiveOwnerAndName(self):
        # XXX apw 2016-05-18: pull out the PPA owner and name to seed key CN
        archive_name = os.path.dirname(self.archiveroot)
        owner_name = os.path.basename(os.path.dirname(archive_name))
        archive_name = os.path.basename(archive_name)

        return owner_name + ' ' + archive_name

    def callLog(self, description, cmdl):
        status = subprocess.call(cmdl)
        if status != 0:
            # Just log this rather than failing, since custom upload errors
            # tend to make the publisher rather upset.
            if self.logger is not None:
                self.logger.warning("%s Failed (cmd='%s')" %
                    (description, " ".join(cmdl)))
        return status

    def findSigningHandlers(self):
        """Find all the signable files in an extracted tarball."""
        for dirpath, dirnames, filenames in os.walk(self.tmpdir):
            for filename in filenames:
                if filename.endswith(".efi"):
                    yield (os.path.join(dirpath, filename), self.signUefi)
                elif filename.endswith(".ko"):
                    yield (os.path.join(dirpath, filename), self.signKmod)

    def getKeys(self, which, generate, *keynames):
        """Validate and return the uefi key and cert for encryption."""

        if self.autokey:
            for keyfile in keynames:
                if keyfile and not os.path.exists(keyfile):
                    generate()
                    break

        valid = True
        for keyfile in keynames:
            if keyfile and not os.access(keyfile, os.R_OK):
                if self.logger is not None:
                    self.logger.warning(
                        "%s key %s not readable" % (which, keyfile))
                valid = False

        if not valid:
            return [None for k in keynames]
        return keynames

    def generateUefiKeys(self):
        """Generate new UEFI Keys for this archive."""
        directory = os.path.dirname(self.uefi_key)
        if not os.path.exists(directory):
            os.makedirs(directory)

        common_name = '/CN=PPA ' + self.getArchiveOwnerAndName() + '/'

        old_mask = os.umask(0o077)
        try:
            new_key_cmd = [
                'openssl', 'req', '-new', '-x509', '-newkey', 'rsa:2048',
                '-subj', common_name, '-keyout', self.uefi_key,
                '-out', self.uefi_cert, '-days', '3650', '-nodes', '-sha256',
                ]
            self.callLog("UEFI keygen", new_key_cmd)
        finally:
            os.umask(old_mask)

        if os.path.exists(self.uefi_cert):
            os.chmod(self.uefi_cert, 0o644)

    def signUefi(self, image):
        """Attempt to sign an image."""
        remove_if_exists("%s.signed" % image)
        (key, cert) = self.getKeys('UEFI', self.generateUefiKeys,
            self.uefi_key, self.uefi_cert)
        if not key or not cert:
            return
        cmdl = ["sbsign", "--key", key, "--cert", cert, image]
        return self.callLog("UEFI signing", cmdl)

    def generateKmodKeys(self):
        """Generate new Kernel Signing Keys for this archive."""
        directory = os.path.dirname(self.kmod_pem)
        if not os.path.exists(directory):
            os.makedirs(directory)

        old_mask = os.umask(0o077)
        try:
            with tempfile.NamedTemporaryFile(suffix='.keygen') as tf:
                common_name = self.getArchiveOwnerAndName()

                genkey_text = textwrap.dedent("""\
                    [ req ]
                    default_bits = 4096
                    distinguished_name = req_distinguished_name
                    prompt = no
                    string_mask = utf8only
                    x509_extensions = myexts

                    [ req_distinguished_name ]
                    CN = /CN=PPA """ + common_name + """ kmod/

                    [ myexts ]
                    basicConstraints=critical,CA:FALSE
                    keyUsage=digitalSignature
                    subjectKeyIdentifier=hash
                    authorityKeyIdentifier=keyid
                    """)

                print(genkey_text, file=tf)

                # Close out the underlying file so we know it is complete.
                tf.file.close()

                new_key_cmd = [
                    'openssl', 'req', '-new', '-nodes', '-utf8', '-sha512',
                    '-days', '3650', '-batch', '-x509', '-config', tf.name,
                    '-outform', 'PEM', '-out', self.kmod_pem,
                    '-keyout', self.kmod_pem
                    ]
                if self.callLog("Kmod keygen key", new_key_cmd) == 0:
                    new_x509_cmd = [
                        'openssl', 'x509', '-in', self.kmod_pem,
                        '-outform', 'DER', '-out', self.kmod_x509
                        ]
                    if self.callLog("Kmod keygen cert", new_x509_cmd) != 0:
                        os.unlink(self.kmod_pem)
        finally:
            os.umask(old_mask)

        if os.path.exists(self.kmod_x509):
            os.chmod(self.kmod_x509, 0o644)

    def signKmod(self, image):
        """Attempt to sign a kernel module."""
        remove_if_exists("%s.sig" % image)
        (pem, cert) = self.getKeys('Kernel Module', self.generateKmodKeys,
            self.kmod_pem, self.kmod_x509)
        if not pem or not cert:
            return
        cmdl = ["kmodsign", "-D", "sha512", pem, cert, image, image + ".sig"]
        return self.callLog("Kmod signing", cmdl)

    def convertToTarball(self):
        """Convert unpacked output to signing tarball."""
        tarfilename = os.path.join(self.tmpdir, "signed.tar.gz")
        versiondir = os.path.join(self.tmpdir, self.version)

        try:
            with tarfile.open(tarfilename, "w:gz") as tarball:
                tarball.add(versiondir, arcname=self.version)
        except tarfile.TarError as exc:
            raise SigningUploadPackError(tarfilename, exc)

        # Clean out the original tree and move the signing tarball in.
        try:
            shutil.rmtree(versiondir)
            os.mkdir(versiondir)
            os.rename(tarfilename, os.path.join(versiondir, "signed.tar.gz"))
        except OSError as exc:
            raise SigningUploadPackError(tarfilename, exc)

    def extract(self):
        """Copy the custom upload to a temporary directory, and sign it.

        No actual extraction is required.
        """
        super(SigningUpload, self).extract()
        self.setSigningOptions()
        filehandlers = list(self.findSigningHandlers())
        for (filename, handler) in filehandlers:
            if (handler(filename) == 0 and
                'signed-only' in self.signing_options):
                os.unlink(filename)

        # If tarball output is requested, tar up the results.
        if 'tarball' in self.signing_options:
            self.convertToTarball()

    def shouldInstall(self, filename):
        return filename.startswith("%s/" % self.version)


class UefiUpload(SigningUpload):
    """Legacy UEFI Signing custom upload.

    Provides backwards compatibility UEFI signing uploads. Existing
    packages use the raw-uefi custom upload and expect the results
    to be published to dists/*/uefi.  These are a functional subset of
    raw-signing custom uploads differing only in where they are published
    in the archive.

    We expect to be able to remove this upload type once all existing
    packages are converted to the new form and location.
    """
    custom_type = "uefi"

    dists_directory = "uefi"
