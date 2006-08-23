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


class TestPoolifier(unittest.TestCase):

    def testImport(self):
        """canonical.archivepublisher.Poolifier should be importable"""
        from canonical.archivepublisher import Poolifier

    def testInstatiate(self):
        """canonical.archivepublisher.Poolifier should be instantiatable"""
        from canonical.archivepublisher import Poolifier
        p = Poolifier()

    def testBadStyle(self):
        """canonical.archivepublisher.Poolifier should not instantiate on bad style"""
        from canonical.archivepublisher import Poolifier
        bad_style = object()
        self.assertRaises(ValueError, Poolifier, bad_style)

    def testPoolificationOkay(self):
        """canonical.archivepublisher.Poolifier.poolify should poolify properly"""
        from canonical.archivepublisher import Poolifier
        p = Poolifier()
        cases = (
            ( "foo", "main", "main/f/foo" ),
            ( "foo", "universe", "universe/f/foo" ),
            ( "libfoo", "main", "main/libf/libfoo" )
            )
        for case in cases:
            self.assertEqual( case[2], p.poolify(case[0], case[1]) )

    def testPoolificationWithNoComponent(self):
        """canonical.archivepublisher.Poolifier.poolify should raise with no component"""
        from canonical.archivepublisher import Poolifier
        p = Poolifier()
        self.assertRaises(ValueError, p.poolify, "foo")

    def testPoolificationWorksAfterComponent(self):
        """canonical.archivepublisher.Poolifier.poolify should work after a component"""
        from canonical.archivepublisher import Poolifier
        p = Poolifier()
        p.component("main")
        self.assertEqual( p.poolify("foo"), "main/f/foo" )
        self.assertEqual( p.poolify("foo","bar"), "bar/f/foo" )


class TestPool(unittest.TestCase):
    def setUp(self):
        from canonical.archivepublisher import Poolifier, DiskPool
        self.pool_path = mkdtemp()
        self.poolifier = Poolifier()
        self.pool = DiskPool(self.poolifier, self.pool_path, FakeLogger())
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
        pool_name = self.poolifier.poolify(sourcename, component)
        return os.path.join(self.pool_path, pool_name, filename)

    def testSanitiseLinks(self):
        """canonical.archivepublisher.DiskPool.sanitiseLinks should work."""
        # Sanitise the links.
        self.pool.sanitiseLinks(["main", "universe", "multiverse"])
        
        # Ensure both files are in main and both links in universe.        
        assert(os.path.islink(self.pathFor("universe", "foo", "foo-1.0.deb")))
        assert(os.path.islink(self.pathFor("universe", "bar", "bar-1.0.deb")))
        
        assert(os.path.isfile(self.pathFor("main", "foo", "foo-1.0.deb")))
        assert(not os.path.islink(self.pathFor("main", "foo", "foo-1.0.deb")))
        
        assert(os.path.isfile(self.pathFor("main", "bar", "bar-1.0.deb")))
        assert(not os.path.islink(self.pathFor("main", "bar", "bar-1.0.deb")))

    def testRemoveFile(self):
        """canonical.archivepublisher.DiskPool.removeFile should work."""
        # Remove the symlink for bar
        self.pool.removeFile("main", "bar", "bar-1.0.deb")

        # Check it's gone
        assert(not os.path.exists(self.pathFor("main", "bar", "bar-1.0.deb")))
        
        # Remove the file for foo
        self.pool.removeFile("main", "foo", "foo-1.0.deb")

        # Check it's gone
        assert(not os.path.exists(self.pathFor("main", "foo", "foo-1.0.deb")))
        
        # Check the symlink became a real file
        assert(os.path.isfile(self.pathFor("universe", "foo", "foo-1.0.deb")))
        assert(not os.path.islink(self.pathFor(
            "universe", "foo", "foo-1.0.deb")))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
