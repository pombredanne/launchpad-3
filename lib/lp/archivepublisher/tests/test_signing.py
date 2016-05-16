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
from lp.archivepublisher.signing import SigningUpload
from lp.services.osutils import write_file
from lp.services.tarfile_helpers import LaunchpadWriteTarFile
from lp.testing import TestCase
from lp.testing.fakemethod import FakeMethod


class FakeMethodCallers(FakeMethod):
    """Fake execution general commands."""
    def __init__(self, upload=None, *args, **kwargs):
        super(FakeMethodCallers, self).__init__(*args, **kwargs)
        self.upload = upload
        self.callers = {}

    def __call__(self, *args, **kwargs):
        super(FakeMethodCallers, self).__call__(*args, **kwargs)

        import inspect
        frame = inspect.currentframe()
        try:
            frame = frame.f_back
            caller = frame.f_code.co_name
        finally:
            del frame  # As per no-leak stack inspection in Python reference.

        self.callers[caller] = self.callers.get(caller, 0) + 1

        if hasattr(self, caller):
            return getattr(self, caller)(*args, **kwargs)

        return 0

    def caller_call_count(self, caller):
        return self.callers.get(caller, 0)


class FakeMethodGenerateKeys(FakeMethodCallers):
    """ Fake UEFI/Kmod key Generators."""
    def generateUefiKeys(self, *args, **kwargs):
            write_file(self.upload.uefi_key, "")
            write_file(self.upload.uefi_cert, "")
            return 0

    def generateKmodKeys(self, *args, **kwargs):
            write_file(self.upload.kmod_pem, "")
            write_file(self.upload.kmod_x509, "")
            return 0


class FakeMethodGenUefiKeys(FakeMethod):
    """Fake execution of generation of Uefi keys pairs."""
    def __init__(self, upload=None, *args, **kwargs):
        super(FakeMethodGenUefiKeys, self).__init__(*args, **kwargs)
        self.upload = upload

    def __call__(self, *args, **kwargs):
        super(FakeMethodGenUefiKeys, self).__call__(*args, **kwargs)

        write_file(self.upload.uefi_key, "")
        write_file(self.upload.uefi_cert, "")


class FakeMethodGenkmodKeys(FakeMethod):
    """Fake execution of generation of Uefi keys pairs."""
    def __init__(self, upload=None, *args, **kwargs):
        super(FakeMethodGenUefiKeys, self).__init__(*args, **kwargs)
        self.upload = upload

    def __call__(self, *args, **kwargs):
        super(FakeMethodGenUefiKeys, self).__call__(*args, **kwargs)

        write_file(self.upload.kmod_pem, "")
        write_file(self.upload.kmod_x509, "")


class FakeConfigPrimary:
    """A fake publisher configuration for the main archive."""
    def __init__(self, distroroot, signingroot):
        self.distroroot = distroroot
        self.signingroot = signingroot
        self.archiveroot = os.path.join(self.distroroot, 'ubuntu')
        self.signingautokey = False


class FakeConfigCopy:
    """A fake publisher configuration for a copy archive."""
    def __init__(self, distroroot):
        self.distroroot = distroroot
        self.signingroot = None
        self.archiveroot = os.path.join(self.distroroot, 'ubuntu')
        self.signingautokey = False


class FakeConfigPPA:
    """A fake publisher configuration for a PPA."""
    def __init__(self, distroroot, signingroot, owner, ppa):
        self.distroroot = distroroot
        self.signingroot = signingroot
        self.archiveroot = os.path.join(self.distroroot, owner, ppa, 'ubuntu')
        self.signingautokey = True


class TestSigning(TestCase):

    def setUp(self):
        super(TestSigning, self).setUp()
        self.temp_dir = self.makeTemporaryDirectory()
        self.signing_dir = self.makeTemporaryDirectory()
        self.pubconf = FakeConfigPrimary(self.temp_dir, self.signing_dir)
        self.suite = "distroseries"
        # CustomUpload.installFiles requires a umask of 0o022.
        old_umask = os.umask(0o022)
        self.addCleanup(os.umask, old_umask)

    def setUpPPA(self):
        self.pubconf = FakeConfigPPA(self.temp_dir, self.signing_dir,
            'ubuntu-archive', 'testing')
        self.testcase_cn = '/CN=PPA ubuntu-archive testing/'

    def setUpUefiKeys(self, create=True):
        self.key = os.path.join(self.signing_dir, "uefi.key")
        self.cert = os.path.join(self.signing_dir, "uefi.crt")
        if create:
            write_file(self.key, "")
            write_file(self.cert, "")

    def setUpKmodKeys(self, create=True):
        self.kmod_pem = os.path.join(self.signing_dir, "kmod.pem")
        self.kmod_x509 = os.path.join(self.signing_dir, "kmod.x509")
        self.kmod_genkey = os.path.join(self.signing_dir, "kmod.genkey")
        if create:
            write_file(self.kmod_pem, "")
            write_file(self.kmod_x509, "")

    def openArchive(self, loader_type, version, arch):
        self.path = os.path.join(
            self.temp_dir, "%s_%s_%s.tar.gz" % (loader_type, version, arch))
        self.buffer = open(self.path, "wb")
        self.archive = LaunchpadWriteTarFile(self.buffer)

    def assertCallCount(self, count, call):
        self.assertEqual(count, self.fake_call.caller_call_count(call))

    def process_emulate(self):
        self.archive.close()
        self.buffer.close()
        upload = SigningUpload()
        # Under no circumstances is it safe to execute actual commands.
        self.fake_call = FakeMethodGenerateKeys(upload=upload)
        self.useFixture(MonkeyPatch("subprocess.call", self.fake_call))
        upload.process(self.pubconf, self.path, self.suite)

        return upload

    def process(self):
        self.archive.close()
        self.buffer.close()
        upload = SigningUpload()
        upload.signUefi = FakeMethod()
        upload.signKmod = FakeMethod()
        # Under no circumstances is it safe to execute actual commands.
        fake_call = FakeMethod(result=0)
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload.process(self.pubconf, self.path, self.suite)
        self.assertEqual(0, fake_call.call_count)

        return upload

    def getDistsPath(self):
        return os.path.join(self.pubconf.archiveroot, "dists",
            self.suite, "main")

    def getSignedPath(self, loader_type, arch):
        return os.path.join(self.getDistsPath(), "signed",
            "%s-%s" % (loader_type, arch))

    def getUefiPath(self, loader_type, arch):
        return os.path.join(self.getDistsPath(), "uefi",
            "%s-%s" % (loader_type, arch))

    def test_archive_copy(self):
        # If there is no key/cert configuration, processing succeeds but
        # nothing is signed.
        self.pubconf = FakeConfigCopy(self.temp_dir)
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.archive.add_file("1.0/empty.ko", "")
        self.process_emulate()
        self.assertCallCount(0, 'generateUefiKeys')
        self.assertCallCount(0, 'generateKmodKeys')
        self.assertCallCount(0, 'signUefi')
        self.assertCallCount(0, 'signKmod')

    def test_archive_primary_no_keys(self):
        # If the configured key/cert are missing, processing succeeds but
        # nothing is signed.
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.archive.add_file("1.0/empty.ko", "")
        self.process_emulate()
        self.assertCallCount(0, 'generateUefiKeys')
        self.assertCallCount(0, 'generateKmodKeys')
        self.assertCallCount(0, 'signUefi')
        self.assertCallCount(0, 'signKmod')

    def test_archive_primary_keys(self):
        # If the configured key/cert are missing, processing succeeds but
        # nothing is signed.
        self.setUpUefiKeys()
        self.setUpKmodKeys()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.archive.add_file("1.0/empty.ko", "")
        self.process_emulate()
        self.assertCallCount(0, 'generateUefiKeys')
        self.assertCallCount(0, 'generateKmodKeys')
        self.assertCallCount(1, 'signUefi')
        self.assertCallCount(1, 'signKmod')

    def test_PPA_creates_keys(self):
        # If the configured key/cert are missing, processing succeeds but
        # nothing is signed.
        self.setUpPPA()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.archive.add_file("1.0/empty.ko", "")
        self.process_emulate()
        self.assertCallCount(1, 'generateUefiKeys')
        self.assertCallCount(2, 'generateKmodKeys')
        self.assertCallCount(1, 'signUefi')
        self.assertCallCount(1, 'signKmod')

    def test_no_signed_files(self):
        # Tarballs containing no *.efi files are extracted without complaint.
        # Nothing is signed.
        self.setUpUefiKeys()
        self.openArchive("empty", "1.0", "amd64")
        self.archive.add_file("1.0/hello", "world")
        upload = self.process()
        self.assertTrue(os.path.exists(os.path.join(
            self.getSignedPath("empty", "amd64"), "1.0", "hello")))
        self.assertEqual(0, upload.signUefi.call_count)
        self.assertEqual(0, upload.signKmod.call_count)

    def test_already_exists(self):
        # If the target directory already exists, processing fails.
        self.setUpUefiKeys()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        os.makedirs(os.path.join(self.getSignedPath("test", "amd64"), "1.0"))
        self.assertRaises(CustomUploadAlreadyExists, self.process)

    def test_bad_umask(self):
        # The umask must be 0o022 to avoid incorrect permissions.
        self.setUpUefiKeys()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/dir/file.efi", "foo")
        os.umask(0o002)  # cleanup already handled by setUp
        self.assertRaises(CustomUploadBadUmask, self.process)

    def test_correct_uefi_signing_command_executed(self):
        # Check that calling signUefi() will generate the expected command
        # when appropriate keys are present.
        self.setUpUefiKeys()
        fake_call = FakeMethod(result=0)
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
        self.setUpUefiKeys(create=False)
        fake_call = FakeMethod(result=0)
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
        self.setUpUefiKeys(create=False)
        fake_call = FakeMethod(result=0)
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

    def test_correct_kmod_signing_command_executed(self):
        # Check that calling signKmod() will generate the expected command
        # when appropriate keys are present.
        self.setUpKmodKeys()
        fake_call = FakeMethod(result=0)
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload = SigningUpload()
        upload.generateKmodKeys = FakeMethod()
        upload.setTargetDirectory(
            self.pubconf, "test_1.0_amd64.tar.gz", "distroseries")
        upload.signKmod('t.ko')
        self.assertEqual(1, fake_call.call_count)
        # Assert command form.
        args = fake_call.calls[0][0][0]
        expected_cmd = [
            'kmodsign', '-d', self.kmod_pem, self.kmod_x509, 't.ko'
            ]
        self.assertEqual(expected_cmd, args)
        self.assertEqual(0, upload.generateKmodKeys.call_count)

    def test_correct_kmod_signing_command_executed_no_keys(self):
        # Check that calling signKmod() will generate no commands when
        # no keys are present.
        self.setUpKmodKeys(create=False)
        fake_call = FakeMethod(result=0)
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload = SigningUpload()
        upload.generateKmodKeys = FakeMethod()
        upload.setTargetDirectory(
            self.pubconf, "test_1.0_amd64.tar.gz", "distroseries")
        upload.signUefi('t.ko')
        self.assertEqual(0, fake_call.call_count)
        self.assertEqual(0, upload.generateKmodKeys.call_count)

    def test_correct_kmod_keygen_command_executed(self):
        # Check that calling generateUefiKeys() will generate the
        # expected command.
        self.setUpPPA()
        self.setUpKmodKeys(create=False)
        fake_call = FakeMethod(result=0)
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload = SigningUpload()
        upload.setTargetDirectory(
            self.pubconf, "test_1.0_amd64.tar.gz", "distroseries")
        upload.generateKmodKeys()
        self.assertEqual(2, fake_call.call_count)
        # Assert the actual command matches.
        args = fake_call.calls[0][0][0]
        expected_cmd = [
            'openssl', 'req', '-new', '-nodes', '-utf8', '-sha512',
            '-days', '3650', '-batch', '-x509',
            '-subj', '/CN=PPA ubuntu-archive testing kmod/',
            '-config', self.kmod_genkey, '-outform', 'PEM',
            '-out', self.kmod_pem, '-keyout', self.kmod_pem
            ]
        self.assertEqual(expected_cmd, args)
        args = fake_call.calls[1][0][0]
        expected_cmd = [
            'openssl', 'x509', '-in', self.kmod_pem, '-outform', 'DER',
            '-out', self.kmod_x509
            ]
        self.assertEqual(expected_cmd, args)

    def test_signs_uefi_image(self):
        # Each image in the tarball is signed.
        self.setUpUefiKeys()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        upload = self.process()
        self.assertEqual(1, upload.signUefi.call_count)

    def test_signs_kmod_image(self):
        # Each image in the tarball is signed.
        self.setUpKmodKeys()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.ko", "")
        upload = self.process()
        self.assertEqual(1, upload.signKmod.call_count)

    def test_signs_combo_image(self):
        # Each image in the tarball is signed.
        self.setUpKmodKeys()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.archive.add_file("1.0/empty.ko", "")
        self.archive.add_file("1.0/empty2.ko", "")
        upload = self.process()
        self.assertEqual(1, upload.signUefi.call_count)
        self.assertEqual(2, upload.signKmod.call_count)

    def test_installed(self):
        # Files in the tarball are installed correctly.
        self.setUpUefiKeys()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.process()
        self.assertTrue(os.path.isdir(os.path.join(
            self.getDistsPath(), "signed")))
        self.assertTrue(os.path.islink(os.path.join(
            self.getDistsPath(), "uefi")))
        self.assertTrue(os.path.exists(os.path.join(
            self.getSignedPath("test", "amd64"), "1.0", "empty.efi")))
        self.assertTrue(os.path.exists(os.path.join(
            self.getUefiPath("test", "amd64"), "1.0", "empty.efi")))

    def test_installed_existing_uefi(self):
        # Files in the tarball are installed correctly.
        os.makedirs(os.path.join(self.getDistsPath(), "uefi"))
        self.setUpUefiKeys()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.process()
        self.assertTrue(os.path.isdir(os.path.join(
            self.getDistsPath(), "signed")))
        self.assertTrue(os.path.islink(os.path.join(
            self.getDistsPath(), "uefi")))
        self.assertTrue(os.path.exists(os.path.join(
            self.getSignedPath("test", "amd64"), "1.0", "empty.efi")))
        self.assertTrue(os.path.exists(os.path.join(
            self.getUefiPath("test", "amd64"), "1.0", "empty.efi")))

    def test_installed_existing_signing(self):
        # Files in the tarball are installed correctly.
        os.makedirs(os.path.join(self.getDistsPath(), "signing"))
        self.setUpUefiKeys()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.process()
        self.assertTrue(os.path.isdir(os.path.join(
            self.getDistsPath(), "signed")))
        self.assertTrue(os.path.islink(os.path.join(
            self.getDistsPath(), "uefi")))
        self.assertTrue(os.path.exists(os.path.join(
            self.getSignedPath("test", "amd64"), "1.0", "empty.efi")))
        self.assertTrue(os.path.exists(os.path.join(
            self.getUefiPath("test", "amd64"), "1.0", "empty.efi")))

    def test_create_uefi_keys_autokey_off(self):
        # Keys are not created.
        self.setUpUefiKeys(create=False)
        self.assertFalse(os.path.exists(self.key))
        self.assertFalse(os.path.exists(self.cert))
        fake_call = FakeMethod(result=0)
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
        self.setUpUefiKeys(create=False)
        self.assertFalse(os.path.exists(self.key))
        self.assertFalse(os.path.exists(self.cert))
        fake_call = FakeMethod(result=0)
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload = SigningUpload()
        upload.generateUefiKeys = FakeMethodGenUefiKeys(upload=upload)
        upload.setTargetDirectory(
            self.pubconf, "test_1.0_amd64.tar.gz", "distroseries")
        upload.signUefi('t.efi')
        self.assertEqual(1, upload.generateUefiKeys.call_count)
        self.assertTrue(os.path.exists(self.key))
        self.assertTrue(os.path.exists(self.cert))
