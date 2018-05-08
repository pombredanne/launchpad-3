# Copyright 2012-2018 Canonical Ltd.  This software is licensed under the
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
import stat
import subprocess
import tarfile
import tempfile
import textwrap

import scandir

from lp.archivepublisher.config import getPubConfig
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

    def setTargetDirectory(self, archive, tarfile_path, suite):
        self.archive = archive
        pubconf = getPubConfig(archive)
        if pubconf.signingroot is None:
            if self.logger is not None:
                self.logger.warning(
                    "No signing root configured for this archive")
            self.uefi_key = None
            self.uefi_cert = None
            self.kmod_pem = None
            self.kmod_x509 = None
            self.opal_pem = None
            self.opal_x509 = None
            self.autokey = False
        else:
            self.uefi_key = os.path.join(pubconf.signingroot, "uefi.key")
            self.uefi_cert = os.path.join(pubconf.signingroot, "uefi.crt")
            self.kmod_pem = os.path.join(pubconf.signingroot, "kmod.pem")
            self.kmod_x509 = os.path.join(pubconf.signingroot, "kmod.x509")
            self.opal_pem = os.path.join(pubconf.signingroot, "opal.pem")
            self.opal_x509 = os.path.join(pubconf.signingroot, "opal.x509")
            self.autokey = pubconf.signingautokey

        self.setComponents(tarfile_path)

        dists_signed = os.path.join(pubconf.archiveroot, "dists",
            suite, "main", self.dists_directory)
        self.targetdir = os.path.join(
            dists_signed, "%s-%s" % (self.package, self.arch))
        self.archiveroot = pubconf.archiveroot
        self.temproot = pubconf.temproot

        self.public_keys = set()

    def publishPublicKey(self, key):
        """Record this key as having been used in this upload."""
        self.public_keys.add(key)

    def copyPublishedPublicKeys(self):
        """Copy out published keys into the custom upload."""
        keydir = os.path.join(self.tmpdir, self.version, "control")
        if not os.path.exists(keydir):
            os.makedirs(keydir)
        for key in self.public_keys:
            # Ensure we only emit files which are world readable.
            if stat.S_IMODE(os.stat(key).st_mode) & stat.S_IROTH:
                shutil.copy(key, os.path.join(keydir, os.path.basename(key)))
            else:
                if self.logger is not None:
                    self.logger.warning(
                        "%s: public key not world readable" % key)

    def setSigningOptions(self):
        """Find and extract raw-signing options from the tarball."""
        self.signing_options = {}

        # Look for an options file in the top level control directory.
        options_file = os.path.join(self.tmpdir, self.version,
            "control", "options")
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
        for dirpath, dirnames, filenames in scandir.walk(self.tmpdir):
            for filename in filenames:
                if filename.endswith(".efi"):
                    yield (os.path.join(dirpath, filename), self.signUefi)
                elif filename.endswith(".ko"):
                    yield (os.path.join(dirpath, filename), self.signKmod)
                elif filename.endswith(".opal"):
                    yield (os.path.join(dirpath, filename), self.signOpal)

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

    def generateKeyCommonName(self, owner, archive, suffix=''):
        # PPA <owner> <archive> <suffix>
        # truncate <owner> <archive> to ensure the overall form is shorter
        # than 64 characters but the suffix is maintained
        if suffix:
            suffix = " " + suffix
        common_name = "PPA %s %s" % (owner, archive)
        return common_name[0:64 - len(suffix)] + suffix

    def generateUefiKeys(self):
        """Generate new UEFI Keys for this archive."""
        directory = os.path.dirname(self.uefi_key)
        if not os.path.exists(directory):
            os.makedirs(directory)

        common_name = self.generateKeyCommonName(
            self.archive.owner.name, self.archive.name)
        subject = '/CN=' + common_name + '/'

        old_mask = os.umask(0o077)
        try:
            new_key_cmd = [
                'openssl', 'req', '-new', '-x509', '-newkey', 'rsa:2048',
                '-subj', subject, '-keyout', self.uefi_key,
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
        self.publishPublicKey(cert)
        cmdl = ["sbsign", "--key", key, "--cert", cert, image]
        return self.callLog("UEFI signing", cmdl)

    def generatePemX509Pair(self, key_type, pem_filename, x509_filename):
        """Generate new pem/x509 key pairs."""
        directory = os.path.dirname(pem_filename)
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Truncate name to 64 character maximum.
        common_name = self.generateKeyCommonName(
            self.archive.owner.name, self.archive.name, key_type)

        old_mask = os.umask(0o077)
        try:
            with tempfile.NamedTemporaryFile(suffix='.keygen') as tf:
                genkey_text = textwrap.dedent("""\
                    [ req ]
                    default_bits = 4096
                    distinguished_name = req_distinguished_name
                    prompt = no
                    string_mask = utf8only
                    x509_extensions = myexts

                    [ req_distinguished_name ]
                    CN = %s

                    [ myexts ]
                    basicConstraints=critical,CA:FALSE
                    keyUsage=digitalSignature
                    subjectKeyIdentifier=hash
                    authorityKeyIdentifier=keyid
                    """ % common_name)

                print(genkey_text, file=tf)

                # Close out the underlying file so we know it is complete.
                tf.file.close()

                new_key_cmd = [
                    'openssl', 'req', '-new', '-nodes', '-utf8', '-sha512',
                    '-days', '3650', '-batch', '-x509', '-config', tf.name,
                    '-outform', 'PEM', '-out', pem_filename,
                    '-keyout', pem_filename
                    ]
                if self.callLog(key_type + " keygen key", new_key_cmd) == 0:
                    new_x509_cmd = [
                        'openssl', 'x509', '-in', pem_filename,
                        '-outform', 'DER', '-out', x509_filename
                        ]
                    if self.callLog(key_type + " keygen cert",
                                    new_x509_cmd) != 0:
                        os.unlink(pem_filename)
        finally:
            os.umask(old_mask)

        if os.path.exists(x509_filename):
            os.chmod(x509_filename, 0o644)

    def generateKmodKeys(self):
        """Generate new Kernel Signing Keys for this archive."""
        self.generatePemX509Pair("Kmod", self.kmod_pem, self.kmod_x509)

    def signKmod(self, image):
        """Attempt to sign a kernel module."""
        remove_if_exists("%s.sig" % image)
        (pem, cert) = self.getKeys('Kernel Module', self.generateKmodKeys,
            self.kmod_pem, self.kmod_x509)
        if not pem or not cert:
            return
        self.publishPublicKey(cert)
        cmdl = ["kmodsign", "-D", "sha512", pem, cert, image, image + ".sig"]
        return self.callLog("Kmod signing", cmdl)

    def generateOpalKeys(self):
        """Generate new Opal Signing Keys for this archive."""
        self.generatePemX509Pair("Opal", self.opal_pem, self.opal_x509)

    def signOpal(self, image):
        """Attempt to sign a kernel image for Opal."""
        remove_if_exists("%s.sig" % image)
        (pem, cert) = self.getKeys('Opal Kernel', self.generateOpalKeys,
            self.opal_pem, self.opal_x509)
        if not pem or not cert:
            return
        self.publishPublicKey(cert)
        cmdl = ["kmodsign", "-D", "sha512", pem, cert, image, image + ".sig"]
        return self.callLog("Opal signing", cmdl)

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

        # Copy out the public keys where they were used.
        self.copyPublishedPublicKeys()

        # If tarball output is requested, tar up the results.
        if 'tarball' in self.signing_options:
            self.convertToTarball()

    def installFiles(self, archive, suite):
        """After installation hash and sign the installed result."""
        # Avoid circular import.
        from lp.archivepublisher.publishing import DirectoryHash

        super(SigningUpload, self).installFiles(archive, suite)

        versiondir = os.path.join(self.targetdir, self.version)
        with DirectoryHash(versiondir, self.temproot) as hasher:
            hasher.add_dir(versiondir)
        for checksum_path in hasher.checksum_paths:
            if self.shouldSign(checksum_path):
                self.sign(archive, suite, checksum_path)

    def shouldInstall(self, filename):
        return filename.startswith("%s/" % self.version)

    def shouldSign(self, filename):
        return filename.endswith("SUMS")


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
