#!/usr/bin/env python

# Copyright 2004 Canonical Ltd.  All rights reserved.
#

import unittest
import sys
import os
import shutil
import time
from optparse import OptionParser
from tempfile import mkdtemp, mkstemp

from contrib.glock import GlobalLock
from canonical.archivepublisher.tests.util import dist, drs

class MockOptions:
    """Use as options object, adding more attributes if needed."""
    keep = False
    dryrun = False


class MockLogger:
    """Pass as a log object. Record debug calls for later checking."""
    def __init__(self):
        self.lines = []
        
    def debug(self, s):
        self.lines.append(s)

class TestUploadProcessor(unittest.TestCase):

    def setUp(self):
        self.options = MockOptions()
        self.log = MockLogger()
        
    def testImport(self):
        """canonical.archivepublisher.UploadProcessor should be importable"""
        from canonical.archivepublisher import UploadProcessor

    def testInstantiate(self):
        """canonical.archivepublisher.UploadProcessor should instantiate"""
        from canonical.archivepublisher import UploadProcessor
        up = UploadProcessor(self.options, None, self.log)

    def testLocateFolders(self):
        """locateFolders should return a list of folders in a folder.

        We don't test that we block on the lockfile, as this is trivial
        code but tricky to test.
        """
        testdir = mkdtemp()
        folder_names = []
        folder_names.append(mkdtemp(dir=testdir))
        folder_names.append(mkdtemp(dir=testdir))
        folder_names.append(mkdtemp(dir=testdir))
        try:
            from canonical.archivepublisher import UploadProcessor
            up = UploadProcessor(self.options, None, self.log)
            located_folders = up.locateFolders(testdir)
            self.assertEqual(located_folders.sort(), folder_names.sort())
        finally:
            shutil.rmtree(testdir)

    def testLocateChangesFiles(self):
        """locateChangesFiles should return the .changes files in a folder."""
        testdir = mkdtemp()
        changes_files = []
        changes_files.append(mkstemp(dir=testdir, suffix=".changes"))
        changes_files.append(mkstemp(dir=testdir, suffix=".changes"))
        mkstemp(dir=testdir, suffix=".notchanges")
        try:
            from canonical.archivepublisher import UploadProcessor
            up = UploadProcessor(self.options, None, self.log)
            located_files = up.locateChangesFiles(testdir)
            self.assertEqual(located_files.sort(), changes_files.sort())
        finally:
            shutil.rmtree(testdir)

    def testMoveUpload(self):
        """moveUpload should move the upload folder and .distro file."""
        testdir = mkdtemp()

        # Create an upload, a .distro and a target to move it to.
        target = mkdtemp(dir=testdir)
        target_name = os.path.basename(target)
        upload = mkdtemp()
        upload_name = os.path.basename(upload)
        distro = upload + ".distro"
        f = open(distro, mode="w")
        f.write("foo")
        f.close()
        
        try:
            from canonical.archivepublisher import UploadProcessor
            self.options.base_fsroot = testdir
            up = UploadProcessor(self.options, None, self.log)
            up.moveUpload(upload, target_name)
            
            self.assertTrue(os.path.exists(os.path.join(target, upload_name)))
            self.assertTrue(os.path.exists(os.path.join(
                target, upload_name + ".distro")))
            self.assertFalse(os.path.exists(upload))
            self.assertFalse(os.path.exists(distro))
            
        finally:
            shutil.rmtree(testdir)
        
    def testOrderFilenames(self):
        """orderFilenames sorts _source.changes ahead of other files."""
        from canonical.archivepublisher import UploadProcessor
        up = UploadProcessor(self.options, None, self.log)

        self.assertEqual(["d_source.changes", "a", "b", "c"],
            up.orderFilenames(["b", "a", "d_source.changes", "c"]))


def test_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestUploadProcessor))
    return suite

def main(argv):
    suite = test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    if not runner.run(suite).wasSuccessful():
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

