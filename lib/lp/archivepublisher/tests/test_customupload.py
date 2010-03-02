# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `CustomUploads`."""

__metaclass__ = type


import cStringIO
import os
import shutil
import tarfile
import tempfile
import unittest

from lp.archivepublisher.customupload import (
    CustomUpload, CustomUploadTarballInvalidFileType,
    CustomUploadTarballBadFile, CustomUploadTarballBadSymLink)


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


class TestTarfileVerification(unittest.TestCase):

    tarfile_path = "/tmp/_verify_extract"

    def setUp(self):
        self.custom_processor = CustomUpload(None, self.tarfile_path, None)
        self.custom_processor.tmpdir = "/tmp/_extract_test"

    def createTarfile(self):
        tar_fileobj = cStringIO.StringIO()
        return tarfile.open(name=None, mode="w", fileobj=tar_fileobj)

    def createTarfileWithSymlink(self, target):
        info = tarfile.TarInfo(name="i_am_a_symlink")
        info.type = tarfile.SYMTYPE
        info.linkname = target
        tar_file = self.createTarfile()
        tar_file.addfile(info)
        return tar_file

    def createTarfileWithFile(self, file_type, name="testfile"):
        info = tarfile.TarInfo(name=name)
        info.type = file_type
        tar_file = self.createTarfile()
        tar_file.addfile(info)
        return tar_file

    def testFailsToExtractBadSymlink(self):
        """Fail if a symlink's target is outside the tmp tree."""
        tar_file = self.createTarfileWithSymlink(target="/etc/passwd")
        self.assertRaises(
            CustomUploadTarballBadSymLink,
            self.custom_processor.verifyBeforeExtracting, tar_file)

    def testFailsToExtractBadFileType(self):
        """Fail if a file in a tarfile is not a regular file or a symlink."""
        tar_file = self.createTarfileWithFile(tarfile.FIFOTYPE)
        self.assertRaises(
            CustomUploadTarballInvalidFileType,
            self.custom_processor.verifyBeforeExtracting, tar_file)

    def testFailsToExtractBadFileLocation(self):
        """Fail if the file resolves to a path outside the tmp tree."""
        tar_file = self.createTarfileWithFile(tarfile.REGTYPE, "../outside")
        self.assertRaises(
            CustomUploadTarballBadFile,
            self.custom_processor.verifyBeforeExtracting, tar_file)

    def testRegularFileDoesntRaise(self):
        """Adding a normal file should pass inspection."""
        tar_file = self.createTarfileWithFile(tarfile.REGTYPE)
        self.custom_processor.verifyBeforeExtracting(tar_file)

    def testDirectoryDoesntRaise(self):
        """Adding a directory should pass inspection."""
        tar_file = self.createTarfileWithFile(tarfile.DIRTYPE)
        self.custom_processor.verifyBeforeExtracting(tar_file)

    def testSymlinkDoesntRaise(self):
        """Adding a symlink should pass inspection."""
        tar_file = self.createTarfileWithSymlink(target="something/blah")
        self.custom_processor.verifyBeforeExtracting(tar_file)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
