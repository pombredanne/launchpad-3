# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test dscfile.py"""

__metaclass__ = type

import os
import unittest

from lp.archiveuploader.dscfile import findAndMoveChangelog, findCopyright
from lp.archiveuploader.nascentuploadfile import UploadError
from lp.archiveuploader.tests import mock_logger_quiet
from lp.testing import TestCase


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
        """Test that a symlink instead of a real file will fail."""
        os.symlink("/etc/passwd", self.copyright_path)
        errors = list(findCopyright(
            self.dsc_file, self.tmpdir, mock_logger_quiet))

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], UploadError)
        self.assertEqual(
            errors[0].message,
            "Symbolic link for debian/copyright not allowed")
        self.failUnless(isinstance(errors[0], UploadError))

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
        """Test that a symlink instead of a real file will fail.

        This prevents a symlink in the uploaded package to be used from
        grabbing files in the system processing the source package."""
        os.symlink("/etc/passwd", self.changelog_path)
        errors = list(findAndMoveChangelog(
            self.dsc_file, self.tmpdir, self.tmpdir, mock_logger_quiet))

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], UploadError)
        self.assertEqual(
            errors[0].message,
            "Symbolic link for debian/changelog not allowed")
        self.failUnless(isinstance(errors[0], UploadError))

    def testGoodDebianChangelog(self):
        """Test that a proper changelog file will be accepted

        This prevents a symlink in the uploaded package to be used from
        grabbing files in the system processing the source package."""
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
        """Test that a file larger than 10MiB will fail."""

        dev_zero = open("/dev/zero", "r")
        empty_file = dev_zero.read(20971520)
        dev_zero.close()

        file = open(self.changelog_path, "w")
        file.write(empty_file)
        file.close()

        errors = list(findAndMoveChangelog(
            self.dsc_file, self.tmpdir, self.tmpdir, mock_logger_quiet))


        self.failUnless(isinstance(errors[0], UploadError))
        self.assertIsInstance(errors[0], UploadError)
        self.assertEqual(
            errors[0].message,
            "debian/changelog file too large, 10MiB max")

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
