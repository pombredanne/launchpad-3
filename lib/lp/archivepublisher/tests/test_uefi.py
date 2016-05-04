# Copyright 2012-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test UEFI custom uploads."""

__metaclass__ = type

import os

from fixtures import MonkeyPatch

from lp.archivepublisher.customupload import (
    CustomUploadAlreadyExists,
    CustomUploadBadUmask,
    )
from lp.archivepublisher.uefi import SigningUpload
from lp.services.osutils import write_file
from lp.services.tarfile_helpers import LaunchpadWriteTarFile
from lp.testing import TestCase
from lp.testing.fakemethod import FakeMethod


class FakeMethodGenUefiKeys(FakeMethod):
    """Fake execution of generation of Uefi keys pairs."""
    def __init__(self, upload=None, *args, **kwargs):
        super(FakeMethodGenUefiKeys, self).__init__(*args, **kwargs)
        self.upload = upload

    def __call__(self, *args, **kwargs):
        super(FakeMethodGenUefiKeys, self).__call__(*args, **kwargs)

        write_file(self.upload.key, "")
        write_file(self.upload.cert, "")


class FakeConfig:
    """A fake publisher configuration for the main archive."""
    def __init__(self, distroroot, signingroot):
        self.distroroot = distroroot
        self.signingroot = signingroot
        self.archiveroot = os.path.join(self.distroroot, 'ubuntu')
        self.signingautokey = False


class FakeConfigPPA:
    """A fake publisher configuration for a PPA."""
    def __init__(self, distroroot, signingroot, owner, ppa):
        self.distroroot = distroroot
        self.signingroot = signingroot
        self.archiveroot = os.path.join(self.distroroot, owner, ppa, 'ubuntu')
        self.signingautokey = True


class TestUefi(TestCase):

    def setUp(self):
        super(TestUefi, self).setUp()
        self.temp_dir = self.makeTemporaryDirectory()
        self.signing_dir = self.makeTemporaryDirectory()
        self.pubconf = FakeConfig(self.temp_dir, self.signing_dir)
        self.suite = "distroseries"
        # CustomUpload.installFiles requires a umask of 0o022.
        old_umask = os.umask(0o022)
        self.addCleanup(os.umask, old_umask)

    def setUpPPA(self):
        self.pubconf = FakeConfigPPA(self.temp_dir, self.signing_dir,
            'ubuntu-archive', 'testing')
        self.testcase_cn = '/CN=PPA ubuntu-archive testing/'

    def setUpKeyAndCert(self, create=True):
        self.key = os.path.join(self.signing_dir, "uefi.key")
        self.cert = os.path.join(self.signing_dir, "uefi.crt")
        if create:
            write_file(self.key, "")
            write_file(self.cert, "")

    def openArchive(self, loader_type, version, arch):
        self.path = os.path.join(
            self.temp_dir, "%s_%s_%s.tar.gz" % (loader_type, version, arch))
        self.buffer = open(self.path, "wb")
        self.archive = LaunchpadWriteTarFile(self.buffer)

    def process(self):
        self.archive.close()
        self.buffer.close()
        fake_call = FakeMethod()
        upload = SigningUpload()
        upload.signUefi = FakeMethod()
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload.process(self.pubconf, self.path, self.suite)
        # Under no circumstances is it safe to execute actual commands.
        self.assertEqual(0, fake_call.call_count)

        return upload

    def getSignedPath(self, loader_type, arch):
        return os.path.join(
            self.pubconf.archiveroot, "dists", self.suite, "main", "signed",
            "%s-%s" % (loader_type, arch))

    def getUefiPath(self, loader_type, arch):
        return os.path.join(
            self.pubconf.archiveroot, "dists", self.suite, "main", "uefi",
            "%s-%s" % (loader_type, arch))

    def test_unconfigured(self):
        # If there is no key/cert configuration, processing succeeds but
        # nothing is signed.  Signing is attempted.
        self.pubconf = FakeConfig(self.temp_dir, None)
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        upload = self.process()
        self.assertEqual(1, upload.signUefi.call_count)

    def test_missing_key_and_cert(self):
        # If the configured key/cert are missing, processing succeeds but
        # nothing is signed.  Signing is attempted.
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        upload = self.process()
        self.assertEqual(1, upload.signUefi.call_count)

    def test_no_efi_files(self):
        # Tarballs containing no *.efi files are extracted without complaint.
        # Nothing is signed.
        self.setUpKeyAndCert()
        self.openArchive("empty", "1.0", "amd64")
        self.archive.add_file("1.0/hello", "world")
        upload = self.process()
        self.assertTrue(os.path.exists(os.path.join(
            self.getSignedPath("empty", "amd64"), "1.0", "hello")))
        self.assertEqual(0, upload.signUefi.call_count)

    def test_already_exists(self):
        # If the target directory already exists, processing fails.
        self.setUpKeyAndCert()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        os.makedirs(os.path.join(self.getSignedPath("test", "amd64"), "1.0"))
        self.assertRaises(CustomUploadAlreadyExists, self.process)

    def test_bad_umask(self):
        # The umask must be 0o022 to avoid incorrect permissions.
        self.setUpKeyAndCert()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/dir/file.efi", "foo")
        os.umask(0o002)  # cleanup already handled by setUp
        self.assertRaises(CustomUploadBadUmask, self.process)

    def test_correct_uefi_signing_command_executed(self):
        # Check that calling signUefi() will generate the expected command
        # when appropriate keys are present.
        self.setUpKeyAndCert()
        fake_call = FakeMethod()
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload = SigningUpload()
        upload.generateUefiKeys = FakeMethod()
        upload.setTargetDirectory(
            self.pubconf, "test_1.0_amd64.tar.gz", "distroseries")
        upload.signUefi('t.efi')
        self.assertEqual(1, fake_call.call_count)
        # Assert command form.
        args = fake_call.calls[0][0][0]
        expected_cmd = [
            'sbsign', '--key', self.key, '--cert', self.cert, 't.efi',
        ]
        self.assertEqual(expected_cmd, args)
        self.assertEqual(0, upload.generateUefiKeys.call_count)

    def test_correct_uefi_signing_command_executed_no_keys(self):
        # Check that calling signUefi() will generate no commands when
        # no keys are present.
        self.setUpKeyAndCert(create=False)
        fake_call = FakeMethod()
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload = SigningUpload()
        upload.generateUefiKeys = FakeMethod()
        upload.setTargetDirectory(
            self.pubconf, "test_1.0_amd64.tar.gz", "distroseries")
        upload.signUefi('t.efi')
        self.assertEqual(0, fake_call.call_count)
        self.assertEqual(0, upload.generateUefiKeys.call_count)

    def test_correct_uefi_keygen_command_executed(self):
        # Check that calling generateUefiKeys() will generate the
        # expected command.
        self.setUpPPA()
        self.setUpKeyAndCert(create=False)
        fake_call = FakeMethod()
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload = SigningUpload()
        upload.setTargetDirectory(
            self.pubconf, "test_1.0_amd64.tar.gz", "distroseries")
        upload.generateUefiKeys()
        self.assertEqual(1, fake_call.call_count)
        # Assert the actual command matches.
        args = fake_call.calls[0][0][0]
        expected_cmd = [
            'openssl', 'req', '-new', '-x509', '-newkey', 'rsa:2048',
            '-subj', self.testcase_cn, '-keyout', self.key, '-out', self.cert,
            '-days', '3650', '-nodes', '-sha256',
            ]
        self.assertEqual(expected_cmd, args)

    def test_signs_image(self):
        # Each image in the tarball is signed.
        self.setUpKeyAndCert()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        upload = self.process()
        self.assertEqual(1, upload.signUefi.call_count)

    def test_installed(self):
        # Files in the tarball are installed correctly.
        self.setUpKeyAndCert()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.process()
        self.assertTrue(os.path.exists(os.path.join(
            self.getSignedPath("test", "amd64"), "1.0", "empty.efi")))
        self.assertTrue(os.path.exists(os.path.join(
            self.getUefiPath("test", "amd64"), "1.0", "empty.efi")))

    def test_create_uefi_keys_autokey_off(self):
        # Keys are not created.
        self.setUpKeyAndCert(create=False)
        self.assertFalse(os.path.exists(self.key))
        self.assertFalse(os.path.exists(self.cert))
        fake_call = FakeMethod()
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload = SigningUpload()
        upload.generateUefiKeys = FakeMethodGenUefiKeys(upload=upload)
        upload.setTargetDirectory(
            self.pubconf, "test_1.0_amd64.tar.gz", "distroseries")
        upload.signUefi('t.efi')
        self.assertEqual(0, upload.generateUefiKeys.call_count)
        self.assertFalse(os.path.exists(self.key))
        self.assertFalse(os.path.exists(self.cert))

    def test_create_uefi_keys_autokey_on(self):
        # Keys are created on demand.
        self.setUpPPA()
        self.setUpKeyAndCert(create=False)
        self.assertFalse(os.path.exists(self.key))
        self.assertFalse(os.path.exists(self.cert))
        fake_call = FakeMethod()
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload = SigningUpload()
        upload.generateUefiKeys = FakeMethodGenUefiKeys(upload=upload)
        upload.setTargetDirectory(
            self.pubconf, "test_1.0_amd64.tar.gz", "distroseries")
        upload.signUefi('t.efi')
        self.assertEqual(1, upload.generateUefiKeys.call_count)
        self.assertTrue(os.path.exists(self.key))
        self.assertTrue(os.path.exists(self.cert))
