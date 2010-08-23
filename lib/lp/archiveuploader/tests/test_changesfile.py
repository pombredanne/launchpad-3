# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test ChangesFile functionality."""

__metaclass__ = type

import os

from debian.deb822 import Changes

from canonical.launchpad.scripts.logger import BufferLogger
from canonical.testing import LaunchpadZopelessLayer
from lp.archiveuploader.changesfile import (
    CannotDetermineFileTypeError,
    ChangesFile,
    determine_file_class_and_name,
    )
from lp.archiveuploader.dscfile import DSCFile
from lp.archiveuploader.nascentuploadfile import (
    DdebBinaryUploadFile,
    DebBinaryUploadFile,
    SourceUploadFile,
    UdebBinaryUploadFile,
    UploadError,
    )
from lp.archiveuploader.tests import AbsolutelyAnythingGoesUploadPolicy
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

    layer = LaunchpadZopelessLayer

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

    def getBaseChanges(self):
        contents = Changes()
        contents["Source"] = "mypkg"
        contents["Binary"] = "binary"
        contents["Date"] = "Fri, 25 Jun 2010 11:20:22 -0600"
        contents["Architecture"] = "i386"
        contents["Version"] = "0.1"
        contents["Distribution"] = "nifty"
        contents["Maintainer"] = "Somebody"
        contents["Changes"] = "Something changed"
        contents["Description"] = "\n An awesome package."
        contents["Changed-By"] = "Somebody <somebody@ubuntu.com>"
        contents["Files"] = [{
            "md5sum": "d2bd347b3fed184fe28e112695be491c",
            "size": "1791",
            "section": "python",
            "priority": "optional",
            "name": "dulwich_0.4.1-1.dsc"}]
        return contents

    def test_checkFileName(self):
        # checkFileName() yields an UploadError if the filename is invalid.
        contents = self.getBaseChanges()
        changes = self.createChangesFile("mypkg_0.1_i386.changes", contents)
        self.assertEquals([], list(changes.checkFileName()))
        changes = self.createChangesFile("mypkg_0.1.changes", contents)
        errors = list(changes.checkFileName())
        self.assertIsInstance(errors[0], UploadError)
        self.assertEquals(1, len(errors))

    def test_filename(self):
        # Filename gets set to the basename of the changes file on disk.
        changes = self.createChangesFile(
            "mypkg_0.1_i386.changes", self.getBaseChanges())
        self.assertEquals("mypkg_0.1_i386.changes", changes.filename)

    def test_suite_name(self):
        # The suite name gets extracted from the changes file.
        changes = self.createChangesFile(
            "mypkg_0.1_i386.changes", self.getBaseChanges())
        self.assertEquals("nifty", changes.suite_name)

    def test_version(self):
        # The version gets extracted from the changes file.
        changes = self.createChangesFile(
            "mypkg_0.1_i386.changes", self.getBaseChanges())
        self.assertEquals("0.1", changes.version)

    def test_architectures(self):
        # The architectures get extracted from the changes file
        # and parsed correctly.
        changes = self.createChangesFile(
            "mypkg_0.1_i386.changes", self.getBaseChanges())
        self.assertEquals("i386", changes.architecture_line)
        self.assertEquals(set(["i386"]), changes.architectures)

    def test_source(self):
        # The source package name gets extracted from the changes file.
        changes = self.createChangesFile(
            "mypkg_0.1_i386.changes", self.getBaseChanges())
        self.assertEquals("mypkg", changes.source)

    def test_processAddresses(self):
        # processAddresses parses the changes file and sets the
        # changed_by field.
        contents = self.getBaseChanges()
        changes = self.createChangesFile(
            "mypkg_0.1_i386.changes", contents)
        self.assertEquals(None, changes.changed_by)
        errors = list(changes.processAddresses())
        self.assertEquals(0, len(errors), "Errors: %r" % errors)
        self.assertEquals(
            "Somebody <somebody@ubuntu.com>", changes.changed_by['rfc822'])

    def test_simulated_changelog(self):
        # The simulated_changelog property returns a changelog entry based on
        # the control fields.
        contents = self.getBaseChanges()
        changes = self.createChangesFile(
            "mypkg_0.1_i386.changes", contents)
        self.assertEquals([], list(changes.processAddresses()))
        self.assertEquals(
            "Something changed\n"
            " -- Somebody <somebody@ubuntu.com>   Fri, 25 Jun 2010 11:20:22 -0600",
            changes.simulated_changelog)

    def test_requires_changed_by(self):
        # A changes file is rejected if it does not have a Changed-By field.
        contents = self.getBaseChanges()
        del contents["Changed-By"]
        self.assertRaises(
            UploadError,
            self.createChangesFile, "mypkg_0.1_i386.changes", contents)
