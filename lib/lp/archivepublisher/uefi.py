# Copyright 2012-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The processing of UEFI boot loader images.

UEFI Secure Boot requires boot loader images to be signed, and we want to
have signed images in the archive so that they can be used for upgrades.
This cannot be done on the build daemons because they are insufficiently
secure to hold signing keys, so we sign them as a custom upload instead.
"""

__metaclass__ = type

__all__ = [
    "process_signing",
    "UefiUpload",
    ]

import os
import subprocess

from lp.archivepublisher.customupload import CustomUpload
from lp.services.osutils import remove_if_exists


class UefiUpload(CustomUpload):
    """UEFI boot loader custom upload.

    The filename must be of the form:

        <TYPE>_<VERSION>_<ARCH>.tar.gz

    where:

      * TYPE: loader type (e.g. 'efilinux');
      * VERSION: encoded version;
      * ARCH: targeted architecture tag (e.g. 'amd64').

    The contents are extracted in the archive in the following path:

        <ARCHIVE>/dists/<SUITE>/main/uefi/<TYPE>-<ARCH>/<VERSION>

    A 'current' symbolic link points to the most recent version.  The
    tarfile must contain at least one file matching the wildcard *.efi, and
    any such files are signed using the archive's UEFI signing key.

    Signing keys may be installed in the "uefiroot" directory specified in
    publisher configuration.  In this directory, the private key is
    "uefi.key" and the certificate is "uefi.crt".
    """
    custom_type = "UEFI"

    @staticmethod
    def parsePath(tarfile_path):
        tarfile_base = os.path.basename(tarfile_path)
        bits = tarfile_base.split("_")
        if len(bits) != 3:
            raise ValueError("%s is not TYPE_VERSION_ARCH" % tarfile_base)
        return bits[0], bits[1], bits[2].split(".")[0]

    def setComponents(self, tarfile_path):
        self.loader_type, self.version, self.arch = self.parsePath(
            tarfile_path)

    def setTargetDirectory(self, pubconf, tarfile_path, distroseries):
        if pubconf.uefiroot is None:
            if self.logger is not None:
                self.logger.warning("No UEFI root configured for this archive")
            self.key = None
            self.cert = None
            self.autokey = False
        else:
            self.key = os.path.join(pubconf.uefiroot, "uefi.key")
            self.cert = os.path.join(pubconf.uefiroot, "uefi.crt")
            self.autokey = pubconf.uefiautokey

        self.setComponents(tarfile_path)
        self.targetdir = os.path.join(
            pubconf.archiveroot, "dists", distroseries, "main", "uefi",
            "%s-%s" % (self.loader_type, self.arch))
        self.archiveroot = pubconf.archiveroot

    @classmethod
    def getSeriesKey(cls, tarfile_path):
        try:
            loader_type, _, arch = cls.parsePath(tarfile_path)
            return loader_type, arch
        except ValueError:
            return None

    def findEfiFilenames(self):
        """Find all the *.efi files in an extracted tarball."""
        for dirpath, dirnames, filenames in os.walk(self.tmpdir):
            for filename in filenames:
                if filename.endswith(".efi"):
                    yield os.path.join(dirpath, filename)

    def generateUefiKeys(self):
        """Generate new UEFI Keys for this archive."""
        directory = os.path.dirname(self.key)
        if not os.path.exists(directory):
            os.makedirs(directory)

        # XXX: pull out the PPA owner and name to seed key CN
        archive_name = os.path.dirname(self.archiveroot)
        owner_name = os.path.basename(os.path.dirname(archive_name))
        archive_name = os.path.basename(archive_name)
        common_name = '/CN=PPA ' + owner_name + ' ' + archive_name + '/'

        old_mask = os.umask(0o077)
        try:
            new_key_cmd = [
                'openssl', 'req', '-new', '-x509', '-newkey', 'rsa:2048',
                '-subj', common_name, '-keyout', self.key, '-out', self.cert,
                '-days', '3650', '-nodes', '-sha256',
                ]
            if subprocess.call(new_key_cmd) != 0:
                # Just log this rather than failing, since custom upload errors
                # tend to make the publisher rather upset.
                if self.logger is not None:
                    self.logger.warning(
                        "Failed to generate UEFI signing keys for %s" %
                        common_name)
        finally:
            os.umask(old_mask)

        if os.path.exists(self.cert):
            os.chmod(self.cert, 0o644)

    def getUefiKeys(self):
        """Validate and return the uefi key and cert for encryption."""

        if self.key and self.cert:
            # If neither of the key files exists then attempt to
            # generate them.
            if (self.autokey and not os.path.exists(self.key)
                and not os.path.exists(self.cert)):
                self.generateUefiKeys()

            # If we have keys, but cannot read them they are dead to us.
            if not os.access(self.key, os.R_OK):
                if self.logger is not None:
                    self.logger.warning(
                        "UEFI private key %s not readable" % self.key)
                self.key = None
            if not os.access(self.cert, os.R_OK):
                if self.logger is not None:
                    self.logger.warning(
                        "UEFI certificate %s not readable" % self.cert)
                self.cert = None

        return (self.key, self.cert)

    def signUefi(self, image):
        """Attempt to sign an image."""
        (key, cert) = self.getUefiKeys()
        if not key or not cert:
            return
        cmdl = ["sbsign", "--key", key, "--cert", cert, image]
        if subprocess.call(cmdl) != 0:
            # Just log this rather than failing, since custom upload errors
            # tend to make the publisher rather upset.
            if self.logger is not None:
                self.logger.warning("UEFI Signing Failed '%s'" %
                    " ".join(cmdl))

    def extract(self):
        """Copy the custom upload to a temporary directory, and sign it.

        No actual extraction is required.
        """
        super(UefiUpload, self).extract()
        efi_filenames = list(self.findEfiFilenames())
        for efi_filename in efi_filenames:
            remove_if_exists("%s.signed" % efi_filename)
            self.signUefi(efi_filename)

    def shouldInstall(self, filename):
        return filename.startswith("%s/" % self.version)


def process_signing(pubconf, tarfile_path, distroseries, logger=None):
    """Process a raw-uefi/raw-signing tarfile.

    Unpacking it into the given archive for the given distroseries.
    Raises CustomUploadError (or some subclass thereof) if anything goes
    wrong.
    """
    upload = UefiUpload(logger=logger)
    upload.process(pubconf, tarfile_path, distroseries)
