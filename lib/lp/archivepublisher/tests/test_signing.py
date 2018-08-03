# Copyright 2012-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test UEFI custom uploads."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

import os
import re
import stat
import tarfile

from fixtures import MonkeyPatch
import scandir
from testtools.matchers import (
    Contains,
    Equals,
    FileContains,
    Matcher,
    MatchesAll,
    MatchesDict,
    Mismatch,
    Not,
    StartsWith,
    )
from testtools.twistedsupport import AsynchronousDeferredRunTest
from twisted.internet import defer
from zope.component import getUtility

from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.customupload import (
    CustomUploadAlreadyExists,
    CustomUploadBadUmask,
    )
from lp.archivepublisher.interfaces.archivesigningkey import (
    IArchiveSigningKey,
    )
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.archivepublisher.signing import (
    SigningUpload,
    UefiUpload,
    )
from lp.archivepublisher.tests.test_run_parts import RunPartsMixin
from lp.services.osutils import write_file
from lp.services.tarfile_helpers import LaunchpadWriteTarFile
from lp.soyuz.enums import ArchivePurpose
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod
from lp.testing.gpgkeys import gpgkeysdir
from lp.testing.keyserver import InProcessKeyServerFixture
from lp.testing.layers import ZopelessDatabaseLayer


class SignedMatches(Matcher):
    """Matches if a signing result directory is valid."""

    def __init__(self, expected):
        self.expected = expected

    def match(self, base):
        content = []
        for root, dirs, files in scandir.walk(base):
            content.extend(
                [os.path.relpath(os.path.join(root, f), base) for f in files])

        left_over = sorted(set(content) - set(self.expected))
        missing = sorted(set(self.expected) - set(content))
        if left_over != [] or missing != []:
            mismatch = ''
            if left_over:
                mismatch += " unexpected files: " + str(left_over)
            if missing:
                mismatch += " missing files: " + str(missing)
            return Mismatch("SignedMatches:" + mismatch)
        return None


class FakeMethodCallLog(FakeMethod):
    """Fake execution general commands."""
    def __init__(self, upload=None, *args, **kwargs):
        super(FakeMethodCallLog, self).__init__(*args, **kwargs)
        self.upload = upload
        self.callers = {
            "UEFI signing": 0,
            "UEFI keygen": 0,
            "Kmod signing": 0,
            "Kmod keygen key": 0,
            "Kmod keygen cert": 0,
            "Opal signing": 0,
            "Opal keygen key": 0,
            "Opal keygen cert": 0,
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

        elif description == "UEFI keygen":
            write_file(self.upload.uefi_key, "")
            write_file(self.upload.uefi_cert, "")

        elif description == "Kmod signing":
            filename = cmdl[-1]
            if filename.endswith(".ko.sig"):
                write_file(filename, "")

        elif description == "Kmod keygen cert":
            write_file(self.upload.kmod_x509, "")

        elif description == "Kmod keygen key":
            write_file(self.upload.kmod_pem, "")

        elif description == "Opal signing":
            filename = cmdl[-1]
            if filename.endswith(".opal.sig"):
                write_file(filename, "")

        elif description == "Opal keygen cert":
            write_file(self.upload.opal_x509, "")

        elif description == "Opal keygen key":
            write_file(self.upload.opal_pem, "")

        else:
            raise AssertionError("unknown command executed cmd=(%s)" %
                " ".join(cmdl))

        return 0

    def caller_count(self, caller):
        return self.callers.get(caller, 0)

    def caller_list(self):
        return [(caller, n) for (caller, n) in self.callers.items() if n != 0]


class TestSigningHelpers(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer
    run_tests_with = AsynchronousDeferredRunTest.make_factory(timeout=10)

    def setUp(self):
        super(TestSigningHelpers, self).setUp()
        self.temp_dir = self.makeTemporaryDirectory()
        self.distro = self.factory.makeDistribution()
        db_pubconf = getUtility(IPublisherConfigSet).getByDistribution(
            self.distro)
        db_pubconf.root_dir = unicode(self.temp_dir)
        self.archive = self.factory.makeArchive(
            distribution=self.distro, purpose=ArchivePurpose.PRIMARY)
        self.signing_dir = os.path.join(
            self.temp_dir, self.distro.name + "-signing")
        self.suite = "distroseries"
        pubconf = getPubConfig(self.archive)
        if not os.path.exists(pubconf.temproot):
            os.makedirs(pubconf.temproot)
        # CustomUpload.installFiles requires a umask of 0o022.
        old_umask = os.umask(0o022)
        self.addCleanup(os.umask, old_umask)

    def setUpPPA(self):
        self.pushConfig(
            "personalpackagearchive", root=self.temp_dir,
            signing_keys_root=self.temp_dir)
        owner = self.factory.makePerson(name="signing-owner")
        self.archive = self.factory.makeArchive(
            distribution=self.distro, owner=owner, name="testing",
            purpose=ArchivePurpose.PPA)
        self.signing_dir = os.path.join(
            self.temp_dir, "signing", "signing-owner", "testing")
        self.testcase_cn = '/CN=PPA signing-owner testing/'
        pubconf = getPubConfig(self.archive)
        if not os.path.exists(pubconf.temproot):
            os.makedirs(pubconf.temproot)

    @defer.inlineCallbacks
    def setUpArchiveKey(self):
        with InProcessKeyServerFixture() as keyserver:
            yield keyserver.start()
            key_path = os.path.join(gpgkeysdir, 'ppa-sample@canonical.com.sec')
            yield IArchiveSigningKey(self.archive).setSigningKey(
                key_path, async_keyserver=True)

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

    def setUpOpalKeys(self, create=True):
        self.opal_pem = os.path.join(self.signing_dir, "opal.pem")
        self.opal_x509 = os.path.join(self.signing_dir, "opal.x509")
        if create:
            write_file(self.opal_pem, "")
            write_file(self.opal_x509, "")

    def openArchive(self, loader_type, version, arch):
        self.path = os.path.join(
            self.temp_dir, "%s_%s_%s.tar.gz" % (loader_type, version, arch))
        self.buffer = open(self.path, "wb")
        self.tarfile = LaunchpadWriteTarFile(self.buffer)

    def getDistsPath(self):
        pubconf = getPubConfig(self.archive)
        return os.path.join(pubconf.archiveroot, "dists", self.suite, "main")


class TestSigning(RunPartsMixin, TestSigningHelpers):

    def getSignedPath(self, loader_type, arch):
        return os.path.join(self.getDistsPath(), "signed",
            "%s-%s" % (loader_type, arch))

    def process_emulate(self):
        self.tarfile.close()
        self.buffer.close()
        upload = SigningUpload()
        # Under no circumstances is it safe to execute actual commands.
        self.fake_call = FakeMethod(result=0)
        upload.callLog = FakeMethodCallLog(upload=upload)
        self.useFixture(MonkeyPatch("subprocess.call", self.fake_call))
        upload.process(self.archive, self.path, self.suite)

        return upload

    def process(self):
        self.tarfile.close()
        self.buffer.close()
        upload = SigningUpload()
        upload.signUefi = FakeMethod()
        upload.signKmod = FakeMethod()
        upload.signOpal = FakeMethod()
        # Under no circumstances is it safe to execute actual commands.
        fake_call = FakeMethod(result=0)
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload.process(self.archive, self.path, self.suite)
        self.assertEqual(0, fake_call.call_count)

        return upload

    def test_archive_copy(self):
        # If there is no key/cert configuration, processing succeeds but
        # nothing is signed.
        self.archive = self.factory.makeArchive(
            distribution=self.distro, purpose=ArchivePurpose.COPY)
        pubconf = getPubConfig(self.archive)
        if not os.path.exists(pubconf.temproot):
            os.makedirs(pubconf.temproot)
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/empty.efi", b"")
        self.tarfile.add_file("1.0/empty.ko", b"")
        self.tarfile.add_file("1.0/empty.opal", b"")
        upload = self.process_emulate()
        self.assertContentEqual([], upload.callLog.caller_list())

    def test_archive_primary_no_keys(self):
        # If the configured key/cert are missing, processing succeeds but
        # nothing is signed.
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/empty.efi", b"")
        self.tarfile.add_file("1.0/empty.ko", b"")
        self.tarfile.add_file("1.0/empty.opal", b"")
        upload = self.process_emulate()
        self.assertContentEqual([], upload.callLog.caller_list())

    def test_archive_primary_keys(self):
        # If the configured key/cert are missing, processing succeeds but
        # nothing is signed.
        self.setUpUefiKeys()
        self.setUpKmodKeys()
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/empty.efi", b"")
        self.tarfile.add_file("1.0/empty.ko", b"")
        self.tarfile.add_file("1.0/empty.opal", b"")
        upload = self.process_emulate()
        expected_callers = [
            ('UEFI signing', 1),
            ('Kmod signing', 1),
        ]
        self.assertContentEqual(expected_callers, upload.callLog.caller_list())

    def test_PPA_creates_keys(self):
        # If the configured key/cert are missing, processing succeeds but
        # nothing is signed.
        self.setUpPPA()
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/empty.efi", b"")
        self.tarfile.add_file("1.0/empty.ko", b"")
        self.tarfile.add_file("1.0/empty.opal", b"")
        upload = self.process_emulate()
        expected_callers = [
            ('UEFI keygen', 1),
            ('Kmod keygen key', 1),
            ('Kmod keygen cert', 1),
            ('Opal keygen key', 1),
            ('Opal keygen cert', 1),
            ('UEFI signing', 1),
            ('Kmod signing', 1),
            ('Opal signing', 1),
        ]
        self.assertContentEqual(expected_callers, upload.callLog.caller_list())

    def test_common_name_plain(self):
        upload = SigningUpload()
        common_name = upload.generateKeyCommonName('testing-team', 'ppa')
        self.assertEqual('PPA testing-team ppa', common_name)

    def test_common_name_suffix(self):
        upload = SigningUpload()
        common_name = upload.generateKeyCommonName(
            'testing-team', 'ppa', 'kmod')
        self.assertEqual('PPA testing-team ppa kmod', common_name)

    def test_common_name_plain_just_short(self):
        upload = SigningUpload()
        common_name = upload.generateKeyCommonName('t' * 30, 'p' * 29)
        expected_name = 'PPA ' + 't' * 30 + ' ' + 'p' * 29
        self.assertEqual(expected_name, common_name)
        self.assertEqual(64, len(common_name))

    def test_common_name_suffix_just_short(self):
        upload = SigningUpload()
        common_name = upload.generateKeyCommonName('t' * 30, 'p' * 24, 'kmod')
        expected_name = 'PPA ' + 't' * 30 + ' ' + 'p' * 24 + ' kmod'
        self.assertEqual(expected_name, common_name)
        self.assertEqual(64, len(common_name))

    def test_common_name_plain_long(self):
        upload = SigningUpload()
        common_name = upload.generateKeyCommonName('t' * 40, 'p' * 40)
        expected_name = 'PPA ' + 't' * 40 + ' ' + 'p' * 19
        self.assertEqual(expected_name, common_name)
        self.assertEqual(64, len(common_name))

    def test_common_name_suffix_long(self):
        upload = SigningUpload()
        common_name = upload.generateKeyCommonName(
            't' * 40, 'p' * 40, 'kmod-plus')
        expected_name = 'PPA ' + 't' * 40 + ' ' + 'p' * 9 + ' kmod-plus'
        self.assertEqual(expected_name, common_name)
        self.assertEqual(64, len(common_name))

    def test_options_handling_none(self):
        # If the configured key/cert are missing, processing succeeds but
        # nothing is signed.
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/control/options", b"")
        upload = self.process_emulate()
        self.assertContentEqual([], upload.signing_options.keys())

    def test_options_handling_single(self):
        # If the configured key/cert are missing, processing succeeds but
        # nothing is signed.
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/control/options", b"first\n")
        upload = self.process_emulate()
        self.assertContentEqual(['first'], upload.signing_options.keys())

    def test_options_handling_multiple(self):
        # If the configured key/cert are missing, processing succeeds but
        # nothing is signed.
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/control/options", b"first\nsecond\n")
        upload = self.process_emulate()
        self.assertContentEqual(['first', 'second'],
            upload.signing_options.keys())

    def test_options_none(self):
        # Specifying no options should leave us with an open tree.
        self.setUpUefiKeys()
        self.setUpKmodKeys()
        self.setUpOpalKeys()
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/empty.efi", b"")
        self.tarfile.add_file("1.0/empty.ko", b"")
        self.tarfile.add_file("1.0/empty.opal", b"")
        self.process_emulate()
        self.assertThat(self.getSignedPath("test", "amd64"), SignedMatches([
            "1.0/SHA256SUMS",
            "1.0/empty.efi", "1.0/empty.efi.signed", "1.0/control/uefi.crt",
            "1.0/empty.ko", "1.0/empty.ko.sig", "1.0/control/kmod.x509",
            "1.0/empty.opal", "1.0/empty.opal.sig", "1.0/control/opal.x509",
            ]))

    def test_options_tarball(self):
        # Specifying the "tarball" option should create an tarball in
        # the tmpdir.
        self.setUpUefiKeys()
        self.setUpKmodKeys()
        self.setUpOpalKeys()
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/control/options", b"tarball")
        self.tarfile.add_file("1.0/empty.efi", b"")
        self.tarfile.add_file("1.0/empty.ko", b"")
        self.tarfile.add_file("1.0/empty.opal", b"")
        self.process_emulate()
        self.assertThat(self.getSignedPath("test", "amd64"), SignedMatches([
            "1.0/SHA256SUMS",
            "1.0/signed.tar.gz",
            ]))
        tarfilename = os.path.join(self.getSignedPath("test", "amd64"),
            "1.0", "signed.tar.gz")
        with tarfile.open(tarfilename) as tarball:
            self.assertContentEqual([
                '1.0', '1.0/control', '1.0/control/options',
                '1.0/empty.efi', '1.0/empty.efi.signed',
                '1.0/control/uefi.crt',
                '1.0/empty.ko', '1.0/empty.ko.sig', '1.0/control/kmod.x509',
                '1.0/empty.opal', '1.0/empty.opal.sig',
                '1.0/control/opal.x509',
                ], tarball.getnames())

    def test_options_signed_only(self):
        # Specifying the "signed-only" option should trigger removal of
        # the source files leaving signatures only.
        self.setUpUefiKeys()
        self.setUpKmodKeys()
        self.setUpOpalKeys()
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/control/options", b"signed-only")
        self.tarfile.add_file("1.0/empty.efi", b"")
        self.tarfile.add_file("1.0/empty.ko", b"")
        self.tarfile.add_file("1.0/empty.opal", b"")
        self.process_emulate()
        self.assertThat(self.getSignedPath("test", "amd64"), SignedMatches([
            "1.0/SHA256SUMS", "1.0/control/options",
            "1.0/empty.efi.signed", "1.0/control/uefi.crt",
            "1.0/empty.ko.sig", "1.0/control/kmod.x509",
            "1.0/empty.opal.sig", "1.0/control/opal.x509",
            ]))

    def test_options_tarball_signed_only(self):
        # Specifying the "tarball" option should create an tarball in
        # the tmpdir.  Adding signed-only should trigger removal of the
        # original files.
        self.setUpUefiKeys()
        self.setUpKmodKeys()
        self.setUpOpalKeys()
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/control/options", b"tarball\nsigned-only")
        self.tarfile.add_file("1.0/empty.efi", b"")
        self.tarfile.add_file("1.0/empty.ko", b"")
        self.tarfile.add_file("1.0/empty.opal", b"")
        self.process_emulate()
        self.assertThat(self.getSignedPath("test", "amd64"), SignedMatches([
            "1.0/SHA256SUMS",
            "1.0/signed.tar.gz",
            ]))
        tarfilename = os.path.join(self.getSignedPath("test", "amd64"),
            "1.0", "signed.tar.gz")
        with tarfile.open(tarfilename) as tarball:
            self.assertContentEqual([
                '1.0', '1.0/control', '1.0/control/options',
                '1.0/empty.efi.signed', '1.0/control/uefi.crt',
                '1.0/empty.ko.sig', '1.0/control/kmod.x509',
                '1.0/empty.opal.sig', '1.0/control/opal.x509',
                ], tarball.getnames())

    def test_no_signed_files(self):
        # Tarballs containing no *.efi files are extracted without complaint.
        # Nothing is signed.
        self.setUpUefiKeys()
        self.openArchive("empty", "1.0", "amd64")
        self.tarfile.add_file("1.0/hello", b"world")
        upload = self.process()
        self.assertTrue(os.path.exists(os.path.join(
            self.getSignedPath("empty", "amd64"), "1.0", "hello")))
        self.assertEqual(0, upload.signUefi.call_count)
        self.assertEqual(0, upload.signKmod.call_count)

    def test_already_exists(self):
        # If the target directory already exists, processing fails.
        self.setUpUefiKeys()
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/empty.efi", b"")
        os.makedirs(os.path.join(self.getSignedPath("test", "amd64"), "1.0"))
        self.assertRaises(CustomUploadAlreadyExists, self.process)

    def test_bad_umask(self):
        # The umask must be 0o022 to avoid incorrect permissions.
        self.setUpUefiKeys()
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/dir/file.efi", b"foo")
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
            self.archive, "test_1.0_amd64.tar.gz", "distroseries")
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
            self.archive, "test_1.0_amd64.tar.gz", "distroseries")
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
            self.archive, "test_1.0_amd64.tar.gz", "distroseries")
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

    def test_correct_kmod_openssl_config(self):
        # Check that calling generateOpensslConfig() will return an appropriate
        # openssl configuration.
        upload = SigningUpload()
        text = upload.generateOpensslConfig('Kmod', 'something-unique')

        cn_re = re.compile(r'\bCN\s*=\s*something-unique\b')
        eku_re = re.compile(
            r'\bextendedKeyUsage\s*=\s*'
            r'codeSigning,1.3.6.1.4.1.2312.16.1.2\s*\b')

        self.assertIn('[ req ]', text)
        self.assertIsNotNone(cn_re.search(text))
        self.assertIsNotNone(eku_re.search(text))

    def test_correct_kmod_signing_command_executed(self):
        # Check that calling signKmod() will generate the expected command
        # when appropriate keys are present.
        self.setUpKmodKeys()
        fake_call = FakeMethod(result=0)
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload = SigningUpload()
        upload.generateKmodKeys = FakeMethod()
        upload.setTargetDirectory(
            self.archive, "test_1.0_amd64.tar.gz", "distroseries")
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
            self.archive, "test_1.0_amd64.tar.gz", "distroseries")
        upload.signKmod('t.ko')
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
            self.archive, "test_1.0_amd64.tar.gz", "distroseries")
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

    def test_correct_opal_openssl_config(self):
        # Check that calling generateOpensslConfig() will return an appropriate
        # openssl configuration.
        upload = SigningUpload()
        text = upload.generateOpensslConfig('Opal', 'something-unique')

        cn_re = re.compile(r'\bCN\s*=\s*something-unique\b')

        self.assertIn('[ req ]', text)
        self.assertIsNotNone(cn_re.search(text))
        self.assertNotIn('extendedKeyUsage', text)

    def test_correct_opal_signing_command_executed(self):
        # Check that calling signOpal() will generate the expected command
        # when appropriate keys are present.
        self.setUpOpalKeys()
        fake_call = FakeMethod(result=0)
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload = SigningUpload()
        upload.generateOpalKeys = FakeMethod()
        upload.setTargetDirectory(
            self.archive, "test_1.0_amd64.tar.gz", "distroseries")
        upload.signOpal('t.opal')
        self.assertEqual(1, fake_call.call_count)
        # Assert command form.
        args = fake_call.calls[0][0][0]
        expected_cmd = [
            'kmodsign', '-D', 'sha512', self.opal_pem, self.opal_x509,
            't.opal', 't.opal.sig'
            ]
        self.assertEqual(expected_cmd, args)
        self.assertEqual(0, upload.generateOpalKeys.call_count)

    def test_correct_opal_signing_command_executed_no_keys(self):
        # Check that calling signOpal() will generate no commands when
        # no keys are present.
        self.setUpOpalKeys(create=False)
        fake_call = FakeMethod(result=0)
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload = SigningUpload()
        upload.generateOpalKeys = FakeMethod()
        upload.setTargetDirectory(
            self.archive, "test_1.0_amd64.tar.gz", "distroseries")
        upload.signOpal('t.opal')
        self.assertEqual(0, fake_call.call_count)
        self.assertEqual(0, upload.generateOpalKeys.call_count)

    def test_correct_opal_keygen_command_executed(self):
        # Check that calling generateOpalKeys() will generate the
        # expected command.
        self.setUpPPA()
        self.setUpOpalKeys(create=False)
        fake_call = FakeMethod(result=0)
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload = SigningUpload()
        upload.setTargetDirectory(
            self.archive, "test_1.0_amd64.tar.gz", "distroseries")
        upload.generateOpalKeys()
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
            '-out', self.opal_pem, '-keyout', self.opal_pem
            ]
        self.assertEqual(expected_cmd, args)
        args = fake_call.calls[1][0][0]
        expected_cmd = [
            'openssl', 'x509', '-in', self.opal_pem, '-outform', 'DER',
            '-out', self.opal_x509
            ]
        self.assertEqual(expected_cmd, args)

    def test_signs_uefi_image(self):
        # Each image in the tarball is signed.
        self.setUpUefiKeys()
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/empty.efi", b"")
        upload = self.process()
        self.assertEqual(1, upload.signUefi.call_count)

    def test_signs_kmod_image(self):
        # Each image in the tarball is signed.
        self.setUpKmodKeys()
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/empty.ko", b"")
        upload = self.process()
        self.assertEqual(1, upload.signKmod.call_count)

    def test_signs_opal_image(self):
        # Each image in the tarball is signed.
        self.setUpOpalKeys()
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/empty.opal", b"")
        upload = self.process()
        self.assertEqual(1, upload.signOpal.call_count)

    def test_signs_combo_image(self):
        # Each image in the tarball is signed.
        self.setUpKmodKeys()
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/empty.efi", b"")
        self.tarfile.add_file("1.0/empty.ko", b"")
        self.tarfile.add_file("1.0/empty2.ko", b"")
        self.tarfile.add_file("1.0/empty.opal", b"")
        self.tarfile.add_file("1.0/empty2.opal", b"")
        self.tarfile.add_file("1.0/empty3.opal", b"")
        upload = self.process()
        self.assertEqual(1, upload.signUefi.call_count)
        self.assertEqual(2, upload.signKmod.call_count)
        self.assertEqual(3, upload.signOpal.call_count)

    def test_installed(self):
        # Files in the tarball are installed correctly.
        self.setUpUefiKeys()
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/empty.efi", b"")
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
        self.tarfile.add_file("1.0/empty.efi", b"")
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
        self.tarfile.add_file("1.0/empty.efi", b"")
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
            self.archive, "test_1.0_amd64.tar.gz", "distroseries")
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
            self.archive, "test_1.0_amd64.tar.gz", "distroseries")
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
            self.archive, "test_1.0_amd64.tar.gz", "distroseries")
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
            self.archive, "test_1.0_amd64.tar.gz", "distroseries")
        upload.signKmod(os.path.join(self.makeTemporaryDirectory(), 't.ko'))
        self.assertEqual(1, upload.callLog.caller_count('Kmod keygen key'))
        self.assertEqual(1, upload.callLog.caller_count('Kmod keygen cert'))
        self.assertTrue(os.path.exists(self.kmod_pem))
        self.assertTrue(os.path.exists(self.kmod_x509))
        self.assertEqual(stat.S_IMODE(os.stat(self.kmod_pem).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(self.kmod_x509).st_mode), 0o644)

    def test_create_opal_keys_autokey_off(self):
        # Keys are not created.
        self.setUpOpalKeys(create=False)
        self.assertFalse(os.path.exists(self.opal_pem))
        self.assertFalse(os.path.exists(self.opal_x509))
        fake_call = FakeMethod(result=0)
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload = SigningUpload()
        upload.callLog = FakeMethodCallLog(upload=upload)
        upload.setTargetDirectory(
            self.archive, "test_1.0_amd64.tar.gz", "distroseries")
        upload.signOpal(os.path.join(self.makeTemporaryDirectory(), 't.opal'))
        self.assertEqual(0, upload.callLog.caller_count('Opal keygen key'))
        self.assertEqual(0, upload.callLog.caller_count('Opal keygen cert'))
        self.assertFalse(os.path.exists(self.opal_pem))
        self.assertFalse(os.path.exists(self.opal_x509))

    def test_create_opal_keys_autokey_on(self):
        # Keys are created on demand.
        self.setUpPPA()
        self.setUpOpalKeys(create=False)
        self.assertFalse(os.path.exists(self.opal_pem))
        self.assertFalse(os.path.exists(self.opal_x509))
        fake_call = FakeMethod(result=0)
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload = SigningUpload()
        upload.callLog = FakeMethodCallLog(upload=upload)
        upload.setTargetDirectory(
            self.archive, "test_1.0_amd64.tar.gz", "distroseries")
        upload.signOpal(os.path.join(self.makeTemporaryDirectory(), 't.opal'))
        self.assertEqual(1, upload.callLog.caller_count('Opal keygen key'))
        self.assertEqual(1, upload.callLog.caller_count('Opal keygen cert'))
        self.assertTrue(os.path.exists(self.opal_pem))
        self.assertTrue(os.path.exists(self.opal_x509))
        self.assertEqual(stat.S_IMODE(os.stat(self.opal_pem).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(self.opal_x509).st_mode), 0o644)

    def test_checksumming_tree(self):
        # Specifying no options should leave us with an open tree,
        # confirm it is checksummed.
        self.setUpUefiKeys()
        self.setUpKmodKeys()
        self.setUpOpalKeys()
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/empty.efi", b"")
        self.tarfile.add_file("1.0/empty.ko", b"")
        self.tarfile.add_file("1.0/empty.opal", b"")
        self.process_emulate()
        sha256file = os.path.join(self.getSignedPath("test", "amd64"),
             "1.0", "SHA256SUMS")
        self.assertTrue(os.path.exists(sha256file))

    @defer.inlineCallbacks
    def test_checksumming_tree_signed(self):
        # Specifying no options should leave us with an open tree,
        # confirm it is checksummed.  Supply an archive signing key
        # which should trigger signing of the checksum file.
        yield self.setUpArchiveKey()
        self.setUpUefiKeys()
        self.setUpKmodKeys()
        self.setUpOpalKeys()
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/empty.efi", b"")
        self.tarfile.add_file("1.0/empty.ko", b"")
        self.tarfile.add_file("1.0/empty.opal", b"")
        self.process_emulate()
        sha256file = os.path.join(self.getSignedPath("test", "amd64"),
             "1.0", "SHA256SUMS")
        self.assertTrue(os.path.exists(sha256file))
        self.assertThat(
            sha256file + '.gpg',
            FileContains(
                matcher=StartsWith('-----BEGIN PGP SIGNATURE-----\n')))

    @defer.inlineCallbacks
    def test_checksumming_tree_signed_options_tarball(self):
        # Specifying no options should leave us with an open tree,
        # confirm it is checksummed.  Supply an archive signing key
        # which should trigger signing of the checksum file.
        yield self.setUpArchiveKey()
        self.setUpUefiKeys()
        self.setUpKmodKeys()
        self.setUpOpalKeys()
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/control/options", b"tarball")
        self.tarfile.add_file("1.0/empty.efi", b"")
        self.tarfile.add_file("1.0/empty.ko", b"")
        self.tarfile.add_file("1.0/empty.opal", b"")
        self.process_emulate()
        sha256file = os.path.join(self.getSignedPath("test", "amd64"),
             "1.0", "SHA256SUMS")
        self.assertTrue(os.path.exists(sha256file))
        self.assertThat(
            sha256file + '.gpg',
            FileContains(
                matcher=StartsWith('-----BEGIN PGP SIGNATURE-----\n')))

        tarfilename = os.path.join(self.getSignedPath("test", "amd64"),
            "1.0", "signed.tar.gz")
        with tarfile.open(tarfilename) as tarball:
            self.assertThat(tarball.getnames(), MatchesAll(*[
              Not(Contains(name)) for name in [
                  "1.0/SHA256SUMS", "1.0/SHA256SUMS.gpg",
                  "1.0/signed.tar.gz",
                  ]]))

    def test_checksumming_tree_signed_with_external_run_parts(self):
        # Checksum files can be signed using an external run-parts helper.
        # We disable subprocess.call because there's just too much going on,
        # so we can't test this completely, but we can at least test that
        # run_parts is called.
        self.enableRunParts(distribution_name=self.distro.name)
        run_parts_fixture = self.useFixture(MonkeyPatch(
            "lp.archivepublisher.archivesigningkey.run_parts", FakeMethod()))
        self.setUpUefiKeys()
        self.setUpKmodKeys()
        self.setUpOpalKeys()
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/empty.efi", "")
        self.tarfile.add_file("1.0/empty.ko", "")
        self.tarfile.add_file("1.0/empty.opal", "")
        self.process_emulate()
        sha256file = os.path.join(self.getSignedPath("test", "amd64"),
             "1.0", "SHA256SUMS")
        self.assertTrue(os.path.exists(sha256file))
        self.assertEqual(1, run_parts_fixture.new_value.call_count)
        args, kwargs = run_parts_fixture.new_value.calls[-1]
        self.assertEqual((self.distro.name, "sign.d"), args)
        self.assertThat(kwargs["env"], MatchesDict({
            "ARCHIVEROOT": Equals(
                os.path.join(self.temp_dir, self.distro.name)),
            "INPUT_PATH": Equals(sha256file),
            "OUTPUT_PATH": Equals("%s.gpg" % sha256file),
            "MODE": Equals("detached"),
            "DISTRIBUTION": Equals(self.distro.name),
            "SUITE": Equals(self.suite),
            }))


class TestUefi(TestSigningHelpers):

    def getSignedPath(self, loader_type, arch):
        return os.path.join(self.getDistsPath(), "uefi",
            "%s-%s" % (loader_type, arch))

    def process(self):
        self.tarfile.close()
        self.buffer.close()
        upload = UefiUpload()
        upload.signUefi = FakeMethod()
        upload.signKmod = FakeMethod()
        # Under no circumstances is it safe to execute actual commands.
        fake_call = FakeMethod(result=0)
        self.useFixture(MonkeyPatch("subprocess.call", fake_call))
        upload.process(self.archive, self.path, self.suite)
        self.assertEqual(0, fake_call.call_count)

        return upload

    def test_installed(self):
        # Files in the tarball are installed correctly.
        self.setUpUefiKeys()
        self.openArchive("test", "1.0", "amd64")
        self.tarfile.add_file("1.0/empty.efi", b"")
        self.process()
        self.assertTrue(os.path.isdir(os.path.join(
            self.getDistsPath(), "uefi")))
        self.assertTrue(os.path.exists(os.path.join(
            self.getSignedPath("test", "amd64"), "1.0", "empty.efi")))
