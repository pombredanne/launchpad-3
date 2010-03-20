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
        self.copyright_file = os.path.join(self.dir_path, "copyright")
        self.changelog_file = os.path.join(self.dir_path, "changelog")
        self.changelog_dest = os.path.join(self.tmpdir, "changelog")
        self.dsc_file = self.MockDSCFile()

    def removeTempFiles(self):
        """Remove any test copyright file we may have lying around."""
        if os.path.exists(self.copyright_file):
            os.remove(self.copyright_file)
        if os.path.exists(self.changelog_file):
            os.remove(self.changelog_file)
        if os.path.exists(os.path.join(self.changelog_dest)):
            os.remove(os.path.join(self.changelog_dest))

    def testBadDebianCopyright(self):
        """Test that a symlink instead of a real file will fail."""
        os.symlink("/etc/passwd", self.copyright_file)
        errors = list(findCopyright(
            self.dsc_file, self.tmpdir, mock_logger_quiet))

        self.addCleanup(self.removeTempFiles)
        self.assertEqual(len(errors), 1)
        self.failUnless(isinstance(errors[0], UploadError))

    def testGoodDebianCopyright(self):
        copyright = "copyright for dummies"
        file = open(self.copyright_file, "w")
        file.write(copyright)
        file.close()

        errors = list(findCopyright(
            self.dsc_file, self.tmpdir, mock_logger_quiet))

        self.addCleanup(self.removeTempFiles)
        self.assertEqual(len(errors), 0)
        self.assertEqual(self.dsc_file.copyright, copyright)

    def testBadDebianChangelog(self):
        """Test that a symlink instead of a real file will fail."""
        os.symlink("/etc/passwd", self.changelog_file)
        errors = list(findAndMoveChangelog(
            self.dsc_file, self.tmpdir, self.tmpdir, mock_logger_quiet))

        self.addCleanup(self.removeTempFiles)
        self.assertEqual(len(errors), 1)
        self.failUnless(isinstance(errors[0], UploadError))

    def testGoodDebianChangelog(self):
        changelog = "changelog for dummies"
        file = open(self.changelog_file, "w")
        file.write(changelog)
        file.close()

        errors = list(findAndMoveChangelog(
            self.dsc_file, self.tmpdir, self.tmpdir, mock_logger_quiet))


        self.addCleanup(self.removeTempFiles)
        self.assertEqual(len(errors), 0)
        self.assertEqual(self.dsc_file.changelog_path,
                         self.changelog_dest)


    def testOversizedFile(self):
        """Test that a file larger than 10MiB will fail."""

        dev_zero = open("/dev/zero", "r")
        empty_file = dev_zero.read(20971520)
        dev_zero.close()

        file = open(self.changelog_file, "w")
        file.write(empty_file)
        file.close()

        errors = list(findAndMoveChangelog(
            self.dsc_file, self.tmpdir, self.tmpdir, mock_logger_quiet))

        self.addCleanup(self.removeTempFiles)

        self.failUnless(isinstance(errors[0], UploadError))
        self.assertIsInstance(errors[0], UploadError)
        self.assertEqual(
            errors[0].message,
            "debian/changelog file too large, 10MiB max")

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
