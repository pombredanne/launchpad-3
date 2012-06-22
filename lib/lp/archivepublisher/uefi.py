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
    "UefiUpload",
    "process_uefi",
    ]

import os
import subprocess

from lp.archivepublisher.customupload import (
    CustomUpload,
    CustomUploadError,
    )
from lp.services.config import config
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

    The filename should be something like:

        <TYPE>_<VERSION>_<ARCH>.tar.gz

    where:

      * TYPE: loader type (e.g. 'efilinux');
      * VERSION: encoded version;
      * ARCH: targeted architecture tag (e.g. 'amd64').

    The contents are extracted in the archive in the following path:

        <ARCHIVE>/dists/<SUITE>/main/uefi/<TYPE>-<ARCH>/<VERSION>

    A 'current' symbolic link points to the most recent version.  The
    tarfile must contain at least one file matching the wildcard *.efi, and
    any such files are signed using the key configured in
    config.archivepublisher.uefi_key_location.
    """
    custom_type = "UEFI"

    def setTargetDirectory(self, archive_root, tarfile_path, distroseries):
        self.uefi_key_location = config.archivepublisher.uefi_key_location
        self.uefi_cert_location = config.archivepublisher.uefi_cert_location
        if self.uefi_key_location is None:
            raise UefiConfigurationError("no key configured")
        if not os.access(self.uefi_key_location, os.R_OK):
            raise UefiConfigurationError(
                "configured key %s not readable" % self.uefi_key_location)
        if self.uefi_cert_location is None:
            raise UefiConfigurationError("no certificate configured")
        if not os.access(self.uefi_cert_location, os.R_OK):
            raise UefiConfigurationError(
                "configured certificate %s not readable" %
                self.uefi_cert_location)

        tarfile_base = os.path.basename(tarfile_path)
        self.loader_type, self.version, self.arch = tarfile_base.split("_")
        self.arch = self.arch.split(".")[0]

        self.targetdir = os.path.join(
            archive_root, "dists", distroseries, "main", "uefi",
            "%s-%s" % (self.loader_type, self.arch))

    def getSeriesKey(self, tarfile_path):
        try:
            loader_type, _, arch = os.path.basename(tarfile_path).split("_")
            arch = arch.split(".")[0]
            return (loader_type, arch)
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
        return [
            "sbsign", "--key", self.uefi_key_location,
            "--cert", self.uefi_cert_location, image,
            ]

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


def process_uefi(archive_root, tarfile_path, distroseries):
    """Process a raw-uefi tarfile.

    Unpacking it into the given archive for the given distroseries.
    Raises CustomUploadError (or some subclass thereof) if anything goes
    wrong.
    """
    upload = UefiUpload()
    upload.process(archive_root, tarfile_path, distroseries)
