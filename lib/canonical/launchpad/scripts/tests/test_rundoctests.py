# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.testing.doctestunit import DocTestSuite

from canonical.testing import reset_logging

def tearDown(test):
    reset_logging()

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('canonical.launchpad.scripts.sort_sql'))
    suite.addTest(DocTestSuite('lp.buildmaster.master'))
    suite.addTest(DocTestSuite(
        'canonical.launchpad.scripts.logger', tearDown=tearDown
        ))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

