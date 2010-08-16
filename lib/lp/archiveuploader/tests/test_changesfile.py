# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test ChangesFile functionality."""

__metaclass__ = type

from debian.deb822 import Changes
import os

from canonical.launchpad.scripts.logger import BufferLogger
from lp.archiveuploader.changesfile import (CannotDetermineFileTypeError,
    ChangesFile, determine_file_class_and_name)
from lp.archiveuploader.dscfile import DSCFile
from lp.archiveuploader.nascentuploadfile import (
    DebBinaryUploadFile, DdebBinaryUploadFile, SourceUploadFile,
    UdebBinaryUploadFile, UploadError)
from lp.archiveuploader.uploadpolicy import AbsolutelyAnythingGoesUploadPolicy
from lp.testing import TestCase


class TestDetermineFileClassAndName(TestCase):

    def testSourceFile(self):
        # A non-DSC source file is a SourceUploadFile.
        self.assertEquals(
            ('foo', SourceUploadFile),
            determine_file_class_and_name('foo_1.0.diff.gz'))

    def testDSCFile(self):
        # A DSC is a DSCFile, since they're special.
        self.assertEquals(
            ('foo', DSCFile),
            determine_file_class_and_name('foo_1.0.dsc'))

    def testDEBFile(self):
        # A binary file is the appropriate PackageUploadFile subclass.
        self.assertEquals(
            ('foo', DebBinaryUploadFile),
            determine_file_class_and_name('foo_1.0_all.deb'))
        self.assertEquals(
            ('foo', DdebBinaryUploadFile),
            determine_file_class_and_name('foo_1.0_all.ddeb'))
        self.assertEquals(
            ('foo', UdebBinaryUploadFile),
            determine_file_class_and_name('foo_1.0_all.udeb'))

    def testUnmatchingFile(self):
        # Files with unknown extensions or none at all are not
        # identified.
        self.assertRaises(
            CannotDetermineFileTypeError,
            determine_file_class_and_name,
            'foo_1.0.notdsc')
        self.assertRaises(
            CannotDetermineFileTypeError,
            determine_file_class_and_name,
            'foo')


class ChangesFileTests(TestCase):
    """Tests for ChangesFile."""

    def setUp(self):
        super(ChangesFileTests, self).setUp()
        self.logger = BufferLogger()
        self.policy = AbsolutelyAnythingGoesUploadPolicy()

    def createChangesFile(self, filename, changes):
        tempdir = self.makeTemporaryDirectory()
        path = os.path.join(tempdir, filename)
        changes_fd = open(path, "w")
        try:
            changes.dump(changes_fd)
        finally:
            changes_fd.close()
        return ChangesFile(path, self.policy, self.logger)

    def test_checkFileName(self):
        contents = Changes()
        contents["Source"] = "mypkg"
        contents["Binary"] = "binary"
        contents["Architecture"] = "i386"
        contents["Version"] = "0.1"
        contents["Distribution"] = "zubuntu"
        contents["Maintainer"] = "Somebody"
        contents["Changes"] = "Something changed"
        contents["Files"] = [{
            "md5sum": "d2bd347b3fed184fe28e112695be491c",
            "size": "1791",
            "section": "python",
            "priority": "optional",
            "name": "dulwich_0.4.1-1.dsc"}]
        changes = self.createChangesFile("mypkg_0.1_i386.changes", contents)
        self.assertEquals([], list(changes.checkFileName()))
        changes = self.createChangesFile("mypkg_0.1.changes", contents)
        errors = list(changes.checkFileName())
        self.assertEquals(1, len(errors))
