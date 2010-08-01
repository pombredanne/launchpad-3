# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test ChangesFile functionality."""

__metaclass__ = type

from testtools import TestCase

from lp.archiveuploader.changesfile import (CannotDetermineFileTypeError,
    determine_file_class_and_name)
from lp.archiveuploader.dscfile import DSCFile
from lp.archiveuploader.nascentuploadfile import (
    DebBinaryUploadFile, DdebBinaryUploadFile, SourceUploadFile,
    UdebBinaryUploadFile)


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

