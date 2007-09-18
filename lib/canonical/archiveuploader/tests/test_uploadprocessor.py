# Copyright 2006 Canonical Ltd.  All rights reserved.
#

"""Tests for uploadprocessor.py."""

__metaclass__ = type

import os
import shutil
import sys
from tempfile import mkdtemp
import traceback
import unittest


class MockOptions:
    """Use in place of an options object, adding more attributes if needed."""
    keep = False
    dryrun = False


class MockLogger:
    """Pass as a log object. Record debug calls for later checking."""
    def __init__(self):
        self.lines = []

    def debug(self, s, exc_info=False):
        self.lines.append(s)
        if exc_info:
            for err_msg in traceback.format_exception(*sys.exc_info()):
                self.lines.append(err_msg)

    info = debug
    warn = debug
    error = debug

    def exception(self, s):
        self.debug(s, exc_info=True)

class TestUploadProcessor(unittest.TestCase):
    """Tests for uploadprocessor.py."""
    def setUp(self):
        self.options = MockOptions()
        self.log = MockLogger()

    def testImport(self):
        """UploadProcessor should be importable"""
        from canonical.archiveuploader.uploadprocessor import UploadProcessor

    def testInstantiate(self):
        """UploadProcessor should instantiate"""
        from canonical.archiveuploader.uploadprocessor import UploadProcessor
        up = UploadProcessor(self.options, None, self.log)

    def testLocateDirectories(self):
        """locateDirectories should return a list of subdirs in a directory.

        We don't test that we block on the lockfile, as this is trivial
        code but tricky to test.
        """
        testdir = mkdtemp()
        try:
            os.mkdir("%s/dir1" % testdir)
            os.mkdir("%s/dir2" % testdir)

            from canonical.archiveuploader.uploadprocessor import UploadProcessor
            up = UploadProcessor(self.options, None, self.log)
            located_dirs = up.locateDirectories(testdir)
            self.assertEqual(sorted(located_dirs), ["dir1", "dir2"])
        finally:
            shutil.rmtree(testdir)

    def testLocateChangesFiles(self):
        """locateChangesFiles should return the .changes files in a folder."""
        testdir = mkdtemp()
        try:
            open("%s/1.changes" % testdir, "w").close()
            open("%s/2.changes" % testdir, "w").close()
            open("%s/3.not_changes" % testdir, "w").close()
            from canonical.archiveuploader.uploadprocessor import UploadProcessor
            up = UploadProcessor(self.options, None, self.log)
            located_files = up.locateChangesFiles(testdir)
            self.assertEqual(sorted(located_files), ["1.changes", "2.changes"])
        finally:
            shutil.rmtree(testdir)

    def testMoveUpload(self):
        """moveUpload should move the upload directory and .distro file."""
        testdir = mkdtemp()
        try:
            # Create an upload, a .distro and a target to move it to.
            upload = mkdtemp(dir=testdir)
            upload_name = os.path.basename(upload)
            distro = upload + ".distro"
            f = open(distro, mode="w")
            f.write("foo")
            f.close()
            target = mkdtemp(dir=testdir)
            target_name = os.path.basename(target)

            # Move it
            from canonical.archiveuploader.uploadprocessor import UploadProcessor
            self.options.base_fsroot = testdir
            up = UploadProcessor(self.options, None, self.log)
            up.moveUpload(upload, target_name)

            # Check it moved
            self.assertTrue(os.path.exists(os.path.join(target, upload_name)))
            self.assertTrue(os.path.exists(os.path.join(
                target, upload_name + ".distro")))
            self.assertFalse(os.path.exists(upload))
            self.assertFalse(os.path.exists(distro))
        finally:
            shutil.rmtree(testdir)

    def testOrderFilenames(self):
        """orderFilenames sorts _source.changes ahead of other files."""
        from canonical.archiveuploader.uploadprocessor import UploadProcessor
        up = UploadProcessor(self.options, None, self.log)

        self.assertEqual(["d_source.changes", "a", "b", "c"],
            up.orderFilenames(["b", "a", "d_source.changes", "c"]))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

