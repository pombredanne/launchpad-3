# Copyright 2009 Canonical Ltd.  All rights reserved.
#
"""Tests for `CustomUploads`."""

__metaclass__ = type


import os
import shutil
import tempfile
import unittest

from lp.archivepublisher.customupload import CustomUpload


class TestCustomUpload(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix='archive_root_')

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def assertEntries(self, entries):
        self.assertEqual(
            entries, sorted(os.listdir(self.test_dir)))

    def testFixCurrentSymlink(self):
        """Test `CustomUpload.fixCurrentSymlink` behaviour.

        Ensure only 3 entries named as valid versions are kept around and
        the 'current' symbolic link is created (or updated) to point to the
        latests entry.

        Also check if it copes with entries not named as valid versions and
        leave them alone.
        """
        # Setup a bogus `CustomUpload` object with the 'targetdir' pointing
        # to the directory created for the test.
        custom_processor = CustomUpload(None, None, None)
        custom_processor.targetdir = self.test_dir

        # Let's create 4 entries named as valid versions.
        os.mkdir(os.path.join(self.test_dir, '1.0'))
        os.mkdir(os.path.join(self.test_dir, '1.1'))
        os.mkdir(os.path.join(self.test_dir, '1.2'))
        os.mkdir(os.path.join(self.test_dir, '1.3'))
        self.assertEntries(['1.0', '1.1', '1.2', '1.3'])

        # `fixCurrentSymlink` will keep only the latest 3 and create a
        # 'current' symbolic link the the highest one.
        custom_processor.fixCurrentSymlink()
        self.assertEntries(['1.1', '1.2', '1.3', 'current'])
        self.assertEqual(
            '1.3', os.readlink(os.path.join(self.test_dir, 'current')))

        # When there is a invalid version present in the directory it is
        # ignored, since it was probably put there manually. The symbolic
        # link still pointing to the latest version.
        os.mkdir(os.path.join(self.test_dir, '1.4'))
        os.mkdir(os.path.join(self.test_dir, 'alpha-5'))
        custom_processor.fixCurrentSymlink()
        self.assertEntries(['1.2', '1.3', '1.4', 'alpha-5', 'current'])
        self.assertEqual(
            '1.4', os.readlink(os.path.join(self.test_dir, 'current')))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
