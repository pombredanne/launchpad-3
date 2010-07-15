# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test dscfile.py"""

__metaclass__ = type

import os
import unittest

from canonical.config import config
from canonical.launchpad.scripts.logger import QuietFakeLogger
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.archiveuploader.dscfile import (
    DSCFile, findAndMoveChangelog, findCopyright)
from lp.archiveuploader.nascentuploadfile import UploadError
from lp.archiveuploader.tests import mock_logger_quiet
from lp.archiveuploader.uploadpolicy import BuildDaemonUploadPolicy
from lp.testing import TestCase, TestCaseWithFactory


class TestDscFile(TestCase):

    class MockDSCFile:
        copyright = None

    def setUp(self):
        super(TestDscFile, self).setUp()
        self.tmpdir = self.makeTemporaryDirectory()
        self.dir_path = os.path.join(self.tmpdir, "foo", "debian")
        os.makedirs(self.dir_path)
        self.copyright_path = os.path.join(self.dir_path, "copyright")
        self.changelog_path = os.path.join(self.dir_path, "changelog")
        self.changelog_dest = os.path.join(self.tmpdir, "changelog")
        self.dsc_file = self.MockDSCFile()

    def testBadDebianCopyright(self):
        """Test that a symlink as debian/copyright will fail.

        This is a security check, to make sure its not possible to use a
        dangling symlink in an attempt to try and access files on the system
        processing the source packages."""
        os.symlink("/etc/passwd", self.copyright_path)
        errors = list(findCopyright(
            self.dsc_file, self.tmpdir, mock_logger_quiet))

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], UploadError)
        self.assertEqual(
            errors[0].args[0],
            "Symbolic link for debian/copyright not allowed")

    def testGoodDebianCopyright(self):
        """Test that a proper copyright file will be accepted"""
        copyright = "copyright for dummies"
        file = open(self.copyright_path, "w")
        file.write(copyright)
        file.close()

        errors = list(findCopyright(
            self.dsc_file, self.tmpdir, mock_logger_quiet))

        self.assertEqual(len(errors), 0)
        self.assertEqual(self.dsc_file.copyright, copyright)

    def testBadDebianChangelog(self):
        """Test that a symlink as debian/changelog will fail.

        This is a security check, to make sure its not possible to use a
        dangling symlink in an attempt to try and access files on the system
        processing the source packages."""
        os.symlink("/etc/passwd", self.changelog_path)
        errors = list(findAndMoveChangelog(
            self.dsc_file, self.tmpdir, self.tmpdir, mock_logger_quiet))

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], UploadError)
        self.assertEqual(
            errors[0].args[0],
            "Symbolic link for debian/changelog not allowed")

    def testGoodDebianChangelog(self):
        """Test that a proper changelog file will be accepted"""
        changelog = "changelog for dummies"
        file = open(self.changelog_path, "w")
        file.write(changelog)
        file.close()

        errors = list(findAndMoveChangelog(
            self.dsc_file, self.tmpdir, self.tmpdir, mock_logger_quiet))

        self.assertEqual(len(errors), 0)
        self.assertEqual(self.dsc_file.changelog_path,
                         self.changelog_dest)


    def testOversizedFile(self):
        """Test that a file larger than 10MiB will fail.

        This check exists to prevent a possible denial of service attack
        against launchpad by overloaded the database or librarian with massive
        changelog and copyright files. 10MiB was set as a sane lower limit
        which is incredibly unlikely to be hit by normal files in the
        archive"""
        dev_zero = open("/dev/zero", "r")
        ten_MiB = 2**20 * 10
        empty_file = dev_zero.read(ten_MiB + 1)
        dev_zero.close()

        file = open(self.changelog_path, "w")
        file.write(empty_file)
        file.close()

        errors = list(findAndMoveChangelog(
            self.dsc_file, self.tmpdir, self.tmpdir, mock_logger_quiet))

        self.assertIsInstance(errors[0], UploadError)
        self.assertEqual(
            errors[0].args[0],
            "debian/changelog file too large, 10MiB max")


class TestDscFileLibrarian(TestCaseWithFactory):
    """Tests for DscFile that may use the Librarian."""

    layer = LaunchpadZopelessLayer

    def getDscFile(self, name):
        dsc_path = os.path.join(config.root,
            "lib/lp/archiveuploader/tests/data/suite", name, name + '.dsc')
        class Changes:
            architectures = ['source']
        logger = QuietFakeLogger()
        policy = BuildDaemonUploadPolicy()
        policy.distroseries = self.factory.makeDistroSeries()
        policy.archive = self.factory.makeArchive()
        policy.distro = policy.distroseries.distribution
        return DSCFile(dsc_path, 'digest', 0, 'main/editors',
            'priority', 'package', 'version', Changes, policy, logger)

    def test_ReadOnlyCWD(self):
        """Processing a file should work when cwd is read-only."""
        tempdir = self.useTempDir()
        os.chmod(tempdir, 0555)
        try:
            list(self.getDscFile('bar_1.0-1').verify())
        finally:
            os.chmod(tempdir, 0755)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
