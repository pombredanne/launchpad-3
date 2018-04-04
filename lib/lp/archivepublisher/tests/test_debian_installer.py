# Copyright 2012-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test debian-installer custom uploads.

See also lp.soyuz.tests.test_distroseriesqueue_debian_installer for
high-level tests of debian-installer upload and queue manipulation.
"""

from __future__ import absolute_import, print_function, unicode_literals

import os
from textwrap import dedent

from testtools.matchers import DirContains
from zope.component import getUtility

from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.customupload import (
    CustomUploadAlreadyExists,
    CustomUploadBadUmask,
    )
from lp.archivepublisher.debian_installer import DebianInstallerUpload
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.archivepublisher.tests.test_run_parts import RunPartsMixin
from lp.services.tarfile_helpers import LaunchpadWriteTarFile
from lp.soyuz.enums import ArchivePurpose
from lp.testing import TestCaseWithFactory
from lp.testing.layers import ZopelessDatabaseLayer


class TestDebianInstaller(RunPartsMixin, TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestDebianInstaller, self).setUp()
        self.temp_dir = self.makeTemporaryDirectory()
        self.distro = self.factory.makeDistribution()
        db_pubconf = getUtility(IPublisherConfigSet).getByDistribution(
            self.distro)
        db_pubconf.root_dir = unicode(self.temp_dir)
        self.archive = self.factory.makeArchive(
            distribution=self.distro, purpose=ArchivePurpose.PRIMARY)
        self.suite = "distroseries"
        # CustomUpload.installFiles requires a umask of 0o022.
        old_umask = os.umask(0o022)
        self.addCleanup(os.umask, old_umask)

    def openArchive(self):
        self.version = "20070214ubuntu1"
        self.arch = "i386"
        self.path = os.path.join(
            self.temp_dir,
            "debian-installer-images_%s_%s.tar.gz" % (self.version, self.arch))
        self.buffer = open(self.path, "wb")
        self.tarfile = LaunchpadWriteTarFile(self.buffer)

    def addFile(self, path, contents):
        self.tarfile.add_file(
            "installer-%s/%s/%s" % (self.arch, self.version, path), contents)

    def addSymlink(self, path, target):
        self.tarfile.add_symlink(
            "installer-%s/%s/%s" % (self.arch, self.version, path), target)

    def process(self):
        self.tarfile.close()
        self.buffer.close()
        DebianInstallerUpload().process(self.archive, self.path, self.suite)

    def getInstallerPath(self, versioned_filename=None):
        pubconf = getPubConfig(self.archive)
        installer_path = os.path.join(
            pubconf.archiveroot, "dists", self.suite, "main",
            "installer-%s" % self.arch)
        if versioned_filename is not None:
            installer_path = os.path.join(
                installer_path, self.version, versioned_filename)
        return installer_path

    def test_basic(self):
        # Processing a simple correct tar file succeeds.
        self.openArchive()
        self.addFile("hello", b"world")
        self.process()

    def test_already_exists(self):
        # If the target directory already exists, processing fails.
        self.openArchive()
        os.makedirs(self.getInstallerPath("."))
        self.assertRaises(CustomUploadAlreadyExists, self.process)

    def test_bad_umask(self):
        # The umask must be 0o022 to avoid incorrect permissions.
        self.openArchive()
        self.addFile("dir/file", b"foo")
        os.umask(0o002)  # cleanup already handled by setUp
        self.assertRaises(CustomUploadBadUmask, self.process)

    def test_current_symlink(self):
        # A "current" symlink is created to the last version.
        self.openArchive()
        self.addFile("hello", b"world")
        self.process()
        installer_path = self.getInstallerPath()
        self.assertContentEqual(
            [self.version, "current"], os.listdir(installer_path))
        self.assertEqual(
            self.version, os.readlink(os.path.join(installer_path, "current")))

    def test_correct_file(self):
        # Files in the tarball are extracted correctly.
        self.openArchive()
        directory = ("images/netboot/ubuntu-installer/i386/"
                     "pxelinux.cfg.serial-9600")
        filename = os.path.join(directory, "default")
        long_filename = os.path.join(
            directory, "very_very_very_very_very_very_long_filename")
        self.addFile(filename, b"hey")
        self.addFile(long_filename, b"long")
        self.process()
        with open(self.getInstallerPath(filename)) as f:
            self.assertEqual("hey", f.read())
        with open(self.getInstallerPath(long_filename)) as f:
            self.assertEqual("long", f.read())

    def test_correct_symlink(self):
        # Symbolic links in the tarball are extracted correctly.
        self.openArchive()
        foo_path = "images/netboot/foo"
        foo_target = "ubuntu-installer/i386/pxelinux.cfg.serial-9600/default"
        link_to_dir_path = "images/netboot/link_to_dir"
        link_to_dir_target = "ubuntu-installer/i386/pxelinux.cfg.serial-9600"
        self.addSymlink(foo_path, foo_target)
        self.addSymlink(link_to_dir_path, link_to_dir_target)
        self.process()
        self.assertEqual(
            foo_target, os.readlink(self.getInstallerPath(foo_path)))
        self.assertEqual(
            link_to_dir_target,
            os.path.normpath(os.readlink(
                self.getInstallerPath(link_to_dir_path))))

    def test_top_level_permissions(self):
        # Top-level directories are set to mode 0o755 (see bug 107068).
        self.openArchive()
        self.addFile("hello", b"world")
        self.process()
        installer_path = self.getInstallerPath()
        self.assertEqual(0o755, os.stat(installer_path).st_mode & 0o777)
        self.assertEqual(
            0o755,
            os.stat(os.path.join(installer_path, os.pardir)).st_mode & 0o777)

    def test_extracted_permissions(self):
        # Extracted files and directories are set to 0o644/0o755.
        self.openArchive()
        directory = ("images/netboot/ubuntu-installer/i386/"
                     "pxelinux.cfg.serial-9600")
        filename = os.path.join(directory, "default")
        self.addFile(filename, b"hey")
        self.process()
        self.assertEqual(
            0o644, os.stat(self.getInstallerPath(filename)).st_mode & 0o777)
        self.assertEqual(
            0o755, os.stat(self.getInstallerPath(directory)).st_mode & 0o777)

    def test_sign_with_external_run_parts(self):
        self.enableRunParts(distribution_name=self.distro.name)
        with open(os.path.join(
                self.parts_directory, self.distro.name, "sign.d",
                "10-sign"), "w") as f:
            f.write(dedent("""\
                #! /bin/sh
                touch "$OUTPUT_PATH"
                """))
            os.fchmod(f.fileno(), 0o755)
        self.openArchive()
        self.addFile("images/list", "a list")
        self.addFile("images/SHA256SUMS", "a checksum")
        self.process()
        self.assertThat(
            self.getInstallerPath("images"),
            DirContains(["list", "SHA256SUMS", "SHA256SUMS.gpg"]))

    def test_getSeriesKey_extracts_architecture(self):
        # getSeriesKey extracts the architecture from an upload's filename.
        self.openArchive()
        self.assertEqual(
            self.arch, DebianInstallerUpload.getSeriesKey(self.path))

    def test_getSeriesKey_returns_None_on_mismatch(self):
        # getSeriesKey returns None if the filename does not match the
        # expected pattern.
        self.assertIsNone(DebianInstallerUpload.getSeriesKey("argh_1.0.jpg"))

    def test_getSeriesKey_refuses_names_with_wrong_number_of_fields(self):
        # getSeriesKey requires exactly three fields.
        self.assertIsNone(DebianInstallerUpload.getSeriesKey(
            "package_1.0.tar.gz"))
        self.assertIsNone(DebianInstallerUpload.getSeriesKey(
            "one_two_three_four_5.tar.gz"))
