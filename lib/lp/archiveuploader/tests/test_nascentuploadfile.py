# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test NascentUploadFile functionality."""

__metaclass__ = type

from debian.deb822 import Changes
import hashlib
import os

from canonical.launchpad.scripts.logger import BufferLogger
from lp.archiveuploader.changesfile import ChangesFile
from lp.archiveuploader.nascentuploadfile import CustomUploadFile
from lp.archiveuploader.uploadpolicy import AbsolutelyAnythingGoesUploadPolicy
from lp.soyuz.interfaces.queue import PackageUploadCustomFormat
from lp.testing import TestCase
from canonical.testing import LaunchpadZopelessLayer


class NascentUploadFileTestCase(TestCase):

    def setUp(self):
        super(NascentUploadFileTestCase, self).setUp()
        self.logger = BufferLogger()
        self.policy = AbsolutelyAnythingGoesUploadPolicy()
        class MockArchive:

            private = False
        self.policy.archive = MockArchive()

    def writeUploadFile(self, filename, contents):
        """Write a temporary file but with a specific filename.

        :param filename: Filename to use
        :param contents: Contents of the file
        :return: Tuple with path, digest and size
        """
        path = os.path.join(self.makeTemporaryDirectory(), filename)
        f = open(path, 'w')
        try:
            f.write(contents)
        finally:
            f.close()
        return (path, hashlib.sha1(contents), len(contents))


class CustomUploadFileTests(NascentUploadFileTestCase):

    layer = LaunchpadZopelessLayer

    def createCustomUploadFile(self, filename, contents,
        component_and_section, priority_name):
        (path, digest, size) = self.writeUploadFile(filename, contents)
        uploadfile = CustomUploadFile(path, digest, size, component_and_section,
            priority_name, self.policy, self.logger)
        return uploadfile

    def test_custom_type(self):
        uploadfile = self.createCustomUploadFile("bla.txt", "data",
            "main/raw-installer", "extra")
        self.assertEquals(PackageUploadCustomFormat.DEBIAN_INSTALLER,
            uploadfile.custom_type)

    def test_storeInDatabase(self):
        uploadfile = self.createCustomUploadFile("bla.txt", "data",
            "main/raw-installer", "extra")
        self.assertEquals("application/octet-stream", uploadfile.content_type)
        libraryfile = uploadfile.storeInDatabase()
        self.assertEquals("bla.txt", libraryfile.filename)
        self.assertEquals("application/octet-stream", libraryfile.mimetype)


class PackageUploadFileTestCase(NascentUploadFileTestCase):

    def getBaseChanges(self):
        contents = Changes()
        contents["Source"] = "mypkg"
        contents["Binary"] = "binary"
        contents["Architecture"] = "i386"
        contents["Version"] = "0.1"
        contents["Distribution"] = "nifty"
        contents["Maintainer"] = "Somebody"
        contents["Changes"] = "Something changed"
        contents["Files"] = [{
            "md5sum": "d2bd347b3fed184fe28e112695be491c",
            "size": "1791",
            "section": "python",
            "priority": "optional",
            "name": "dulwich_0.4.1-1.dsc"}]
        return contents

    def createChangesFile(self, filename, changes):
        tempdir = self.makeTemporaryDirectory()
        path = os.path.join(tempdir, filename)
        changes_fd = open(path, "w")
        try:
            changes.dump(changes_fd)
        finally:
            changes_fd.close()
        return ChangesFile(path, self.policy, self.logger)


