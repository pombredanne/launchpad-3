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


class TestPool(unittest.TestCase):

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

    def testSanitiseLinks(self):
        """canonical.archivepublisher.DiskPool.sanitiseLinks should work."""

        # Set up a pool
        from canonical.archivepublisher import Poolifier, DiskPool
        rootpath = mkdtemp()
        try:
            poolifier = Poolifier()
            pool = DiskPool(poolifier, rootpath, FakeLogger())
            pool.scan()
            
            # Add a file in universe, and one in main
            pool.checkBeforeAdd("main", "foo", "foo-1.0.deb", "")
            f = pool.openForAdd("main", "foo", "foo-1.0.deb")
            f.write("foo")
            f.close()
            pool.checkBeforeAdd("universe", "bar", "bar-1.0.deb", "")
            f = pool.openForAdd("universe", "bar", "bar-1.0.deb")
            f.write("bar")
            f.close()
            
            # Add symlinks in main and universe respectively
            pool.makeSymlink("universe", "foo", "foo-1.0.deb")
            pool.makeSymlink("main", "bar", "bar-1.0.deb")
            
            # Sanitise the links
            pool.sanitiseLinks(["main", "universe", "multiverse"])
            
            # Ensure both files are in main and both links in universe
            def pathFor(component, sourcename, filename):
                pool_name = poolifier.poolify(sourcename, component)
                return os.path.join(rootpath, pool_name, filename)

            assert(os.path.islink(pathFor("universe", "foo", "foo-1.0.deb")))
            assert(os.path.islink(pathFor("universe", "bar", "bar-1.0.deb")))

            assert(os.path.isfile(pathFor("main", "foo", "foo-1.0.deb")))
            assert(not os.path.islink(pathFor("main", "foo", "foo-1.0.deb")))

            assert(os.path.isfile(pathFor("main", "bar", "bar-1.0.deb")))
            assert(not os.path.islink(pathFor("main", "bar", "bar-1.0.deb")))
        finally:
            shutil.rmtree(rootpath)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
