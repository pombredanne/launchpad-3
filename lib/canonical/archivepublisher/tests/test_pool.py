# Copyright 2004 Canonical Ltd.  All rights reserved.
#

"""Tests for pool.py."""

__metaclass__ = type


import os
import sys
import shutil
from tempfile import mkdtemp
import unittest

from canonical.archivepublisher.tests.util import FakeLogger
from canonical.archivepublisher.diskpool import DiskPool, poolify

class TestPoolification(unittest.TestCase):

    def testPoolificationOkay(self):
        """poolify should poolify properly"""
        cases = (
            ( "foo", "main", "main/f/foo" ),
            ( "foo", "universe", "universe/f/foo" ),
            ( "libfoo", "main", "main/libf/libfoo" )
            )
        for case in cases:
            self.assertEqual( case[2], poolify(case[0], case[1]) )


class TestPool(unittest.TestCase):
    def setUp(self):
        self.pool_path = mkdtemp()
        self.pool = DiskPool(self.pool_path, FakeLogger())
        self.pool.scan()

        # Add a file in main, and one in universe
        self.pool.checkBeforeAdd("main", "foo", "foo-1.0.deb", "")
        f = self.pool.openForAdd("main", "foo", "foo-1.0.deb")
        f.write("foo")
        f.close()
        self.pool.checkBeforeAdd("universe", "bar", "bar-1.0.deb", "")
        f = self.pool.openForAdd("universe", "bar", "bar-1.0.deb")
        f.write("bar")
        f.close()

        # Add symlinks in universe and main respectively.
        self.pool.makeSymlink("universe", "foo", "foo-1.0.deb")
        self.pool.makeSymlink("main", "bar", "bar-1.0.deb")

    def tearDown(self):
        shutil.rmtree(self.pool_path)

    def pathFor(self, component, sourcename, filename):
        """Return the full filesystem path for the file in the pool."""
        pool_name = poolify(sourcename, component)
        return os.path.join(self.pool_path, pool_name, filename)

    def testPoolEntryData(self):
        """After setup, the pool entries should have the right data."""
        def check_data(pool):
            foo = pool.getEntry("foo", "foo-1.0.deb")
            bar = pool.getEntry("bar", "bar-1.0.deb")
            self.assertEqual(foo.file_component, "main")
            self.assertEqual(bar.file_component, "universe")
            self.assertEqual(foo.symlink_components, set(["universe"]))
            self.assertEqual(bar.symlink_components, set(["main"]))

        # First we check the data we've got while adding files is right
        check_data(self.pool)

        # Then we throw away the pool, and check it scans out the right
        # data again by looking at the files
        pool = DiskPool(self.pool_path, FakeLogger())
        check_data(pool)
        
    def testSanitiseLinks(self):
        """canonical.archivepublisher.DiskPool.sanitiseLinks should work."""
        # Sanitise the links.
        self.pool.sanitiseLinks(["main", "universe", "multiverse"])

        # Ensure both files are in main and both links in universe.        
        self.assertTrue(
            os.path.islink(self.pathFor("universe", "foo", "foo-1.0.deb")))
        self.assertTrue(
            os.path.islink(self.pathFor("universe", "bar", "bar-1.0.deb")))

        self.assertTrue(
            os.path.isfile(self.pathFor("main", "foo", "foo-1.0.deb")))
        self.assertFalse(
            os.path.islink(self.pathFor("main", "foo", "foo-1.0.deb")))

        self.assertTrue(
            os.path.isfile(self.pathFor("main", "bar", "bar-1.0.deb")))
        self.assertFalse(
            os.path.islink(self.pathFor("main", "bar", "bar-1.0.deb")))

    def testRemoveFile(self):
        """canonical.archivepublisher.DiskPool.removeFile should work."""
        # Remove the symlink for bar
        size = self.pool.removeFile("main", "bar", "bar-1.0.deb")

        # Check it's gone and reported the right size for a symlink
        self.assertFalse(
            os.path.exists(self.pathFor("main", "bar", "bar-1.0.deb")))
        self.assertEqual(35, size)
        
        # Remove the file for foo
        self.pool.removeFile("main", "foo", "foo-1.0.deb")

        # Check it's gone
        self.assertFalse(
            os.path.exists(self.pathFor("main", "foo", "foo-1.0.deb")))
        
        # Check the symlink became a real file
        self.assertTrue(
            os.path.isfile(self.pathFor("universe", "foo", "foo-1.0.deb")))
        self.assertFalse(
            os.path.islink(self.pathFor("universe", "foo", "foo-1.0.deb")))

        # Delete the final copy of foo, check we reported the right size
        size = self.pool.removeFile("universe", "foo", "foo-1.0.deb")
        self.assertEqual(3, size)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
