# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test UEFI custom uploads."""

import os
from textwrap import dedent

from lp.archivepublisher.customupload import (
    CustomUploadAlreadyExists,
    CustomUploadBadUmask,
    )
from lp.archivepublisher.uefi import (
    UefiConfigurationError,
    UefiNothingToSign,
    UefiUpload,
    )
from lp.services.config import config
from lp.services.osutils import write_file
from lp.services.tarfile_helpers import LaunchpadWriteTarFile
from lp.testing import TestCase
from lp.testing.fakemethod import FakeMethod


class TestUefi(TestCase):

    def setUp(self):
        super(TestUefi, self).setUp()
        self.temp_dir = self.makeTemporaryDirectory()
        self.suite = "distroseries"
        # CustomUpload.installFiles requires a umask of 022.
        old_umask = os.umask(022)
        self.addCleanup(os.umask, old_umask)

    def pushConfiguration(self, key_location, cert_location):
        uefi_config = dedent("""
            [archivepublisher]
            uefi_key_location: %s
            uefi_cert_location: %s
            """ % (key_location, cert_location))
        config.push("uefi_config", uefi_config)
        self.addCleanup(config.pop, "uefi_config")

    def setUpKeyAndCert(self):
        self.key_location = os.path.join(self.temp_dir, "test.key")
        self.cert_location = os.path.join(self.temp_dir, "test.cert")
        write_file(self.key_location, "")
        write_file(self.cert_location, "")
        self.pushConfiguration(self.key_location, self.cert_location)

    def openArchive(self, loader_type, version, arch):
        self.path = os.path.join(
            self.temp_dir, "%s_%s_%s.tar.gz" % (loader_type, version, arch))
        self.buffer = open(self.path, "wb")
        self.archive = LaunchpadWriteTarFile(self.buffer)

    def process(self):
        self.archive.close()
        self.buffer.close()
        upload = UefiUpload()
        upload.sign = FakeMethod()
        upload.process(self.temp_dir, self.path, self.suite)
        return upload

    def getUefiPath(self, loader_type, arch):
        return os.path.join(
            self.temp_dir, "dists", self.suite, "main", "uefi",
            "%s-%s" % (loader_type, arch))

    def test_unconfigured(self):
        # If there is no key/cert configuration, processing fails.
        self.pushConfiguration("none", "none")
        self.openArchive("test", "1.0", "amd64")
        self.assertRaises(UefiConfigurationError, self.process)

    def test_missing_key_and_cert(self):
        # If the configured key/cert are missing, processing fails.
        self.pushConfiguration(
            os.path.join(self.temp_dir, "key"),
            os.path.join(self.temp_dir, "cert"))
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.assertRaises(UefiConfigurationError, self.process)

    def test_no_efi_files(self):
        # Tarballs containing no *.efi files are rejected.
        self.setUpKeyAndCert()
        self.openArchive("empty", "1.0", "amd64")
        self.archive.add_file("hello", "world")
        self.assertRaises(UefiNothingToSign, self.process)

    def test_already_exists(self):
        # If the target directory already exists, processing fails.
        self.setUpKeyAndCert()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        os.makedirs(os.path.join(self.getUefiPath("test", "amd64"), "1.0"))
        self.assertRaises(CustomUploadAlreadyExists, self.process)

    def test_bad_umask(self):
        # The umask must be 022 to avoid incorrect permissions.
        self.setUpKeyAndCert()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/dir/file.efi", "foo")
        os.umask(002)  # cleanup already handled by setUp
        self.assertRaises(CustomUploadBadUmask, self.process)

    def test_correct_signing_command(self):
        # getSigningCommand returns the correct command.
        self.setUpKeyAndCert()
        upload = UefiUpload()
        upload.setTargetDirectory(
            self.temp_dir, "test_1.0_amd64.tar.gz", "distroseries")
        expected_command = [
            "sbsign", "--key", self.key_location, "--cert", self.cert_location,
            "t.efi"]
        self.assertEqual(expected_command, upload.getSigningCommand("t.efi"))

    def test_signs_image(self):
        # Each image in the tarball is signed.
        self.setUpKeyAndCert()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        upload = self.process()
        self.assertEqual(1, upload.sign.call_count)
        self.assertEqual(1, len(upload.sign.calls[0][0]))
        self.assertEqual(
            "empty.efi", os.path.basename(upload.sign.calls[0][0][0]))

    def test_installed(self):
        # Files in the tarball are installed correctly.
        self.setUpKeyAndCert()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.process()
        self.assertTrue(os.path.exists(os.path.join(
            self.getUefiPath("test", "amd64"), "1.0", "empty.efi")))
