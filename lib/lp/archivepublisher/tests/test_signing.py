# Copyright 2012-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test UEFI custom uploads."""

__metaclass__ = type

import os
import stat
import tarfile

from fixtures import MonkeyPatch

from lp.archivepublisher.customupload import (
    CustomUploadAlreadyExists,
    CustomUploadBadUmask,
    )
from lp.archivepublisher.signing import (
    SigningUpload,
    UefiUpload,
    )
from lp.services.osutils import write_file
from lp.services.tarfile_helpers import LaunchpadWriteTarFile
from lp.testing import TestCase
from lp.testing.fakemethod import FakeMethod


class FakeMethodCallLog(FakeMethod):
    """Fake execution general commands."""
    def __init__(self, upload=None, *args, **kwargs):
        super(FakeMethodCallLog, self).__init__(*args, **kwargs)
        self.upload = upload
        self.callers = {
            "UEFI signing": 0,
            "Kmod signing": 0,
            "UEFI keygen": 0,
            "Kmod keygen key": 0,
            "Kmod keygen cert": 0,
            }

    def __call__(self, *args, **kwargs):
        super(FakeMethodCallLog, self).__call__(*args, **kwargs)

        description = args[0]
        cmdl = args[1]
        self.callers[description] += 1
        if description == "UEFI signing":
            filename = cmdl[-1]
            if filename.endswith(".efi"):
                write_file(filename + ".signed", "")

        elif description == "Kmod signing":
            filename = cmdl[-1]
            if filename.endswith(".ko.sig"):
                write_file(filename, "")

        elif description == "Kmod keygen cert":
            write_file(self.upload.kmod_x509, "")

        elif description == "Kmod keygen key":
            write_file(self.upload.kmod_pem, "")

        elif description == "UEFI keygen":
            write_file(self.upload.uefi_key, "")
            write_file(self.upload.uefi_cert, "")

        else:
            raise AssertionError("unknown command executed cmd=(%s)" %
                " ".join(cmdl))

        return 0

    def caller_count(self, caller):
        return self.callers.get(caller, 0)


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


class TestSigningHelpers(TestCase):

    def setUp(self):
        super(TestSigningHelpers, self).setUp()
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
        if create:
            write_file(self.kmod_pem, "")
            write_file(self.kmod_x509, "")

    def openArchive(self, loader_type, version, arch):
        self.path = os.path.join(
            self.temp_dir, "%s_%s_%s.tar.gz" % (loader_type, version, arch))
        self.buffer = open(self.path, "wb")
        self.archive = LaunchpadWriteTarFile(self.buffer)

    def getDistsPath(self):
        return os.path.join(self.pubconf.archiveroot, "dists",
            self.suite, "main")


class TestSigning(TestSigningHelpers):

    def getSignedPath(self, loader_type, arch):
        return os.path.join(self.getDistsPath(), "signed",
            "%s-%s" % (loader_type, arch))

    def process_emulate(self):
        self.archive.close()
        self.buffer.close()
        upload = SigningUpload()
        # Under no circumstances is it safe to execute actual commands.
        self.fake_call = FakeMethod(result=0)
        upload.callLog = FakeMethodCallLog(upload=upload)
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

    def test_archive_copy(self):
        # If there is no key/cert configuration, processing succeeds but
        # nothing is signed.
        self.pubconf = FakeConfigCopy(self.temp_dir)
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.archive.add_file("1.0/empty.ko", "")
        upload = self.process_emulate()
        self.assertEqual(0, upload.callLog.caller_count('UEFI keygen'))
        self.assertEqual(0, upload.callLog.caller_count('Kmod keygen key'))
        self.assertEqual(0, upload.callLog.caller_count('Kmod keygen cert'))
        self.assertEqual(0, upload.callLog.caller_count('UEFI signing'))
        self.assertEqual(0, upload.callLog.caller_count('Kmod signing'))

    def test_archive_primary_no_keys(self):
        # If the configured key/cert are missing, processing succeeds but
        # nothing is signed.
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.archive.add_file("1.0/empty.ko", "")
        upload = self.process_emulate()
        self.assertEqual(0, upload.callLog.caller_count('UEFI keygen'))
        self.assertEqual(0, upload.callLog.caller_count('Kmod keygen key'))
        self.assertEqual(0, upload.callLog.caller_count('Kmod keygen cert'))
        self.assertEqual(0, upload.callLog.caller_count('UEFI signing'))
        self.assertEqual(0, upload.callLog.caller_count('Kmod signing'))

    def test_archive_primary_keys(self):
        # If the configured key/cert are missing, processing succeeds but
        # nothing is signed.
        self.setUpUefiKeys()
        self.setUpKmodKeys()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.archive.add_file("1.0/empty.ko", "")
        upload = self.process_emulate()
        self.assertEqual(0, upload.callLog.caller_count('UEFI keygen'))
        self.assertEqual(0, upload.callLog.caller_count('Kmod keygen key'))
        self.assertEqual(0, upload.callLog.caller_count('Kmod keygen cert'))
        self.assertEqual(1, upload.callLog.caller_count('UEFI signing'))
        self.assertEqual(1, upload.callLog.caller_count('Kmod signing'))

    def test_PPA_creates_keys(self):
        # If the configured key/cert are missing, processing succeeds but
        # nothing is signed.
        self.setUpPPA()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.archive.add_file("1.0/empty.ko", "")
        upload = self.process_emulate()
        self.assertEqual(1, upload.callLog.caller_count('UEFI keygen'))
        self.assertEqual(1, upload.callLog.caller_count('Kmod keygen key'))
        self.assertEqual(1, upload.callLog.caller_count('Kmod keygen cert'))
        self.assertEqual(1, upload.callLog.caller_count('UEFI signing'))
        self.assertEqual(1, upload.callLog.caller_count('Kmod signing'))

    def test_options_handling_none(self):
        # If the configured key/cert are missing, processing succeeds but
        # nothing is signed.
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/control/options", "")
        upload = self.process_emulate()
        self.assertContentEqual([], upload.signing_options.keys())

    def test_options_handling_single(self):
        # If the configured key/cert are missing, processing succeeds but
        # nothing is signed.
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/control/options", "first\n")
        upload = self.process_emulate()
        self.assertContentEqual(['first'], upload.signing_options.keys())

    def test_options_handling_multiple(self):
        # If the configured key/cert are missing, processing succeeds but
        # nothing is signed.
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/control/options", "first\nsecond\n")
        upload = self.process_emulate()
        self.assertContentEqual(['first', 'second'],
            upload.signing_options.keys())

    def test_options_none(self):
        # Specifying no options should leave us with an open tree.
        self.setUpUefiKeys()
        self.setUpKmodKeys()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.archive.add_file("1.0/empty.ko", "")
        self.process_emulate()
        self.assertTrue(os.path.exists(os.path.join(
            self.getSignedPath("test", "amd64"), "1.0", "empty.efi")))
        self.assertTrue(os.path.exists(os.path.join(
            self.getSignedPath("test", "amd64"), "1.0", "empty.efi.signed")))
        self.assertTrue(os.path.exists(os.path.join(
            self.getSignedPath("test", "amd64"), "1.0", "empty.ko")))
        self.assertTrue(os.path.exists(os.path.join(
            self.getSignedPath("test", "amd64"), "1.0", "empty.ko.sig")))

    def test_options_tarball(self):
        # Specifying the "tarball" option should create an tarball in
        # the tmpdir.
        self.setUpUefiKeys()
        self.setUpKmodKeys()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/control/options", "tarball")
        self.archive.add_file("1.0/empty.efi", "")
        self.archive.add_file("1.0/empty.ko", "")
        self.process_emulate()
        self.assertFalse(os.path.exists(os.path.join(
            self.getSignedPath("test", "amd64"), "1.0", "empty.efi")))
        self.assertFalse(os.path.exists(os.path.join(
            self.getSignedPath("test", "amd64"), "1.0", "empty.ko")))
        tarfilename = os.path.join(self.getSignedPath("test", "amd64"),
            "1.0", "signed.tar.gz")
        self.assertTrue(os.path.exists(tarfilename))
        with tarfile.open(tarfilename) as tarball:
            self.assertContentEqual([
                '1.0', '1.0/control', '1.0/control/kmod.x509',
                '1.0/control/uefi.crt', '1.0/empty.efi',
                '1.0/empty.efi.signed', '1.0/empty.ko', '1.0/empty.ko.sig',
                '1.0/control/options',
                ], tarball.getnames())

    def test_options_signed_only(self):
        # Specifying the "signed-only" option should trigger removal of
        # the source files leaving signatures only.
        self.setUpUefiKeys()
        self.setUpKmodKeys()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/control/options", "signed-only")
        self.archive.add_file("1.0/empty.efi", "")
        self.archive.add_file("1.0/empty.ko", "")
        self.process_emulate()
        self.assertFalse(os.path.exists(os.path.join(
            self.getSignedPath("test", "amd64"), "1.0", "empty.efi")))
        self.assertTrue(os.path.exists(os.path.join(
            self.getSignedPath("test", "amd64"), "1.0", "empty.efi.signed")))
        self.assertFalse(os.path.exists(os.path.join(
            self.getSignedPath("test", "amd64"), "1.0", "empty.ko")))
        self.assertTrue(os.path.exists(os.path.join(
            self.getSignedPath("test", "amd64"), "1.0", "empty.ko.sig")))

    def test_options_tarball_signed_only(self):
        # Specifying the "tarball" option should create an tarball in
        # the tmpdir.  Adding signed-only should trigger removal of the
        # original files.
        self.setUpUefiKeys()
        self.setUpKmodKeys()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/control/options",
            "tarball\nsigned-only")
        self.archive.add_file("1.0/empty.efi", "")
        self.archive.add_file("1.0/empty.ko", "")
        self.process_emulate()
        tarfilename = os.path.join(self.getSignedPath("test", "amd64"),
            "1.0", "signed.tar.gz")
        self.assertTrue(os.path.exists(tarfilename))
        with tarfile.open(tarfilename) as tarball:
            self.assertContentEqual([
                '1.0', '1.0/control', '1.0/control/kmod.x509',
                '1.0/control/uefi.crt', '1.0/empty.efi.signed',
                '1.0/empty.ko.sig', '1.0/control/options',
                ], tarball.getnames())

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
            'kmodsign', '-D', 'sha512', self.kmod_pem, self.kmod_x509,
            't.ko', 't.ko.sig'
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
        # Sanitise the keygen tmp file.
        if args[11].endswith('.keygen'):
            args[11] = 'XXX.keygen'
        expected_cmd = [
            'openssl', 'req', '-new', '-nodes', '-utf8', '-sha512',
            '-days', '3650', '-batch', '-x509',
            '-config', 'XXX.keygen', '-outform', 'PEM',
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
        self.assertTrue(os.path.exists(os.path.join(
            self.getSignedPath("test", "amd64"), "1.0", "empty.efi")))

    def test_installed_existing_uefi(self):
        # Files in the tarball are installed correctly.
        os.makedirs(os.path.join(self.getDistsPath(), "uefi"))
        self.setUpUefiKeys()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.process()
        self.assertTrue(os.path.isdir(os.path.join(
            self.getDistsPath(), "signed")))
        self.assertTrue(os.path.exists(os.path.join(
            self.getSignedPath("test", "amd64"), "1.0", "empty.efi")))

    def test_installed_existing_signing(self):
        # Files in the tarball are installed correctly.
        os.makedirs(os.path.join(self.getDistsPath(), "signing"))
        self.setUpUefiKeys()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.process()
        self.assertTrue(os.path.isdir(os.path.join(
            self.getDistsPath(), "signed")))
        self.assertTrue(os.path.exists(os.path.join(
            self.getSignedPath("test", "amd64"), "1.0", "empty.efi")))

    def test_create_uefi_keys_autokey_off(self):
        # Keys are not created.
        self.setUpUefiKeys(create=False)
        self.assertFalse(os.path.exists(self.key))
        self.assertFalse(os.path.exists(self.cert))
        fake_call = FakeMethod(result=0)
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload = SigningUpload()
        upload.callLog = FakeMethodCallLog(upload=upload)
        upload.setTargetDirectory(
            self.pubconf, "test_1.0_amd64.tar.gz", "distroseries")
        upload.signUefi(os.path.join(self.makeTemporaryDirectory(), 't.efi'))
        self.assertEqual(0, upload.callLog.caller_count('UEFI keygen'))
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
        upload.callLog = FakeMethodCallLog(upload=upload)
        upload.setTargetDirectory(
            self.pubconf, "test_1.0_amd64.tar.gz", "distroseries")
        upload.signUefi(os.path.join(self.makeTemporaryDirectory(), 't.efi'))
        self.assertEqual(1, upload.callLog.caller_count('UEFI keygen'))
        self.assertTrue(os.path.exists(self.key))
        self.assertTrue(os.path.exists(self.cert))
        self.assertEqual(stat.S_IMODE(os.stat(self.key).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(self.cert).st_mode), 0o644)

    def test_create_kmod_keys_autokey_off(self):
        # Keys are not created.
        self.setUpKmodKeys(create=False)
        self.assertFalse(os.path.exists(self.kmod_pem))
        self.assertFalse(os.path.exists(self.kmod_x509))
        fake_call = FakeMethod(result=0)
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload = SigningUpload()
        upload.callLog = FakeMethodCallLog(upload=upload)
        upload.setTargetDirectory(
            self.pubconf, "test_1.0_amd64.tar.gz", "distroseries")
        upload.signKmod(os.path.join(self.makeTemporaryDirectory(), 't.ko'))
        self.assertEqual(0, upload.callLog.caller_count('Kmod keygen key'))
        self.assertEqual(0, upload.callLog.caller_count('Kmod keygen cert'))
        self.assertFalse(os.path.exists(self.kmod_pem))
        self.assertFalse(os.path.exists(self.kmod_x509))

    def test_create_kmod_keys_autokey_on(self):
        # Keys are created on demand.
        self.setUpPPA()
        self.setUpKmodKeys(create=False)
        self.assertFalse(os.path.exists(self.kmod_pem))
        self.assertFalse(os.path.exists(self.kmod_x509))
        fake_call = FakeMethod(result=0)
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload = SigningUpload()
        upload.callLog = FakeMethodCallLog(upload=upload)
        upload.setTargetDirectory(
            self.pubconf, "test_1.0_amd64.tar.gz", "distroseries")
        upload.signKmod(os.path.join(self.makeTemporaryDirectory(), 't.ko'))
        self.assertEqual(1, upload.callLog.caller_count('Kmod keygen key'))
        self.assertEqual(1, upload.callLog.caller_count('Kmod keygen cert'))
        self.assertTrue(os.path.exists(self.kmod_pem))
        self.assertTrue(os.path.exists(self.kmod_x509))
        self.assertEqual(stat.S_IMODE(os.stat(self.kmod_pem).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(self.kmod_x509).st_mode), 0o644)

    def test_checksumming_tree(self):
        # Specifying no options should leave us with an open tree,
        # confirm it is checksummed.
        self.setUpUefiKeys()
        self.setUpKmodKeys()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.archive.add_file("1.0/empty.ko", "")
        self.process_emulate()
        sha256file = os.path.join(self.getSignedPath("test", "amd64"),
             "1.0", "SHA256SUMS")
        self.assertTrue(os.path.exists(sha256file))


class TestUefi(TestSigningHelpers):

    def getSignedPath(self, loader_type, arch):
        return os.path.join(self.getDistsPath(), "uefi",
            "%s-%s" % (loader_type, arch))

    def process(self):
        self.archive.close()
        self.buffer.close()
        upload = UefiUpload()
        upload.signUefi = FakeMethod()
        upload.signKmod = FakeMethod()
        # Under no circumstances is it safe to execute actual commands.
        fake_call = FakeMethod(result=0)
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload.process(self.pubconf, self.path, self.suite)
        self.assertEqual(0, fake_call.call_count)

        return upload

    def test_installed(self):
        # Files in the tarball are installed correctly.
        self.setUpUefiKeys()
        self.openArchive("test", "1.0", "amd64")
        self.archive.add_file("1.0/empty.efi", "")
        self.process()
        self.assertTrue(os.path.isdir(os.path.join(
            self.getDistsPath(), "uefi")))
        self.assertTrue(os.path.exists(os.path.join(
            self.getSignedPath("test", "amd64"), "1.0", "empty.efi")))
