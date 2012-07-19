# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The processing of UEFI boot loader images.

UEFI Secure Boot requires boot loader images to be signed, and we want to
have signed images in the archive so that they can be used for upgrades.
This cannot be done on the build daemons because they are insufficiently
secure to hold signing keys, so we sign them as a custom upload instead.
"""

__metaclass__ = type

__all__ = [
    "process_uefi",
    "UefiUpload",
    ]

import os
import subprocess

from lp.archivepublisher.customupload import (
    CustomUpload,
    CustomUploadError,
    )
from lp.services.osutils import remove_if_exists


class UefiConfigurationError(CustomUploadError):
    """No signing key location is configured."""
    def __init__(self, message):
        CustomUploadError.__init__(
            self, "UEFI signing configuration error: %s" % message)


class UefiNothingToSign(CustomUploadError):
    """The tarball contained no *.efi files."""
    def __init__(self, tarfile_path):
        CustomUploadError.__init__(
            self, "UEFI upload '%s' contained no *.efi files" % tarfile_path)


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

    def setTargetDirectory(self, pubconf, tarfile_path, distroseries):
        if pubconf.uefiroot is None:
            raise UefiConfigurationError(
                "no UEFI root configured for this archive")
        self.key = os.path.join(pubconf.uefiroot, "uefi.key")
        self.cert = os.path.join(pubconf.uefiroot, "uefi.crt")
        if not os.access(self.key, os.R_OK):
            raise UefiConfigurationError(
                "UEFI private key %s not readable" % self.key)
        if not os.access(self.cert, os.R_OK):
            raise UefiConfigurationError(
                "UEFI certificate %s not readable" % self.cert)

        loader_type, self.version, self.arch = self.parsePath(tarfile_path)
        self.targetdir = os.path.join(
            pubconf.archiveroot, "dists", distroseries, "main", "uefi",
            "%s-%s" % (loader_type, self.arch))

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

    def getSigningCommand(self, image):
        """Return the command used to sign an image."""
        return ["sbsign", "--key", self.key, "--cert", self.cert, image]

    def sign(self, image):
        """Sign an image."""
        subprocess.check_call(self.getSigningCommand(image))

    def extract(self):
        """Copy the custom upload to a temporary directory, and sign it.

        No actual extraction is required.
        """
        super(UefiUpload, self).extract()
        efi_filenames = list(self.findEfiFilenames())
        if not efi_filenames:
            raise UefiNothingToSign(self.tarfile_path)
        for efi_filename in efi_filenames:
            remove_if_exists("%s.signed" % efi_filename)
            self.sign(efi_filename)

    def shouldInstall(self, filename):
        return filename.startswith("%s/" % self.version)


def process_uefi(pubconf, tarfile_path, distroseries):
    """Process a raw-uefi tarfile.

    Unpacking it into the given archive for the given distroseries.
    Raises CustomUploadError (or some subclass thereof) if anything goes
    wrong.
    """
    upload = UefiUpload()
    upload.process(pubconf, tarfile_path, distroseries)
