# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.testing.doctestunit import DocTestSuite

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('canonical.launchpad.scripts.sort_sql'))
    suite.addTest(DocTestSuite('canonical.launchpad.scripts.builddmaster'))
    suite.addTest(DocTestSuite('canonical.launchpad.scripts.logger'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

