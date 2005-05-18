# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.testing.doctestunit import DocTestSuite

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('canonical.launchpad.scripts.rosetta'))
    suite.addTest(DocTestSuite('canonical.launchpad.scripts.sort_sql'))
    return suite

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(test_suite())

