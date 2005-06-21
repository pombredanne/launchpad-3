#!/usr/bin/env python

# Copyright 2004 Canonical Ltd.  All rights reserved.
#

import unittest
import sys
import os
import shutil

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


def test_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestPool))
    return suite

def main(argv):
    suite = test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    if not runner.run(suite).wasSuccessful():
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

