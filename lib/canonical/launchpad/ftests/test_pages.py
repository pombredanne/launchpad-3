# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Run all of the pagetests, in priority order.

Set up the test data in the database first.
"""
__metaclass__ = type

import os, sys
import unittest
import sets
import harness

from canonical.functional import FunctionalDocFileSuite

here = os.path.dirname(os.path.realpath(__file__))

class SetUpPTs(harness.LaunchpadTestCase):
    def setUp(self):
        """Setup the database"""
        super(SetUpPTs, self).setUp()

    def tearDown(self):
        """But don't tear it down, so other tests in the suite can use it"""
        pass

    def test_setUpDatabase(self):
        # Fake test to ensure setUp is called. This stuff is really only
        # working by accident.
        pass

class TearDownPTs(harness.LaunchpadTestCase):
    def setUp(self):
        """Don't setup the database - it is already"""
        self._cons = []
        pass

    def tearDown(self):
        """Tear down the database"""
        super(TearDownPTs, self).tearDown()

    def test_tearDownDatabase(self):
        # Fake test to ensure tearDown is called.
        pass
'''

class SetUpPTs(unittest.TestCase):

    def test_setUpDatabase(self):
        # Not really a test

        # Run make on the Makefile in launchpad/database/schema.
        # `make -f` won't work, because it relies on being run it its own
        # directory.
        schemadir = os.path.normpath(os.path.join(
            here, '..', '..', '..', '..', 'database', 'schema'))
        result = os.system('cd %s; make > /dev/null 2>&1' % schemadir)
        self.assertEquals(result, 0)


class TearDownPTs(unittest.TestCase):

    def test_tearDownDatabase(self):
        pass
'''


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SetUpPTs))
    pagetestsdir = os.path.normpath(os.path.join(here, '..', 'pagetests'))
    filenames = [filename
                 for filename in os.listdir(pagetestsdir)
                 if filename.lower().endswith('.txt')
                 ]
    filenames = sets.Set(filenames)
    numberedfilenames = [filename for filename in filenames
                         if len(filename) > 4
                         and filename[:2].isdigit()
                         and filename[2] == '-']
    numberedfilenames = sets.Set(numberedfilenames)
    unnumberedfilenames = filenames - numberedfilenames

    # A predictable order is important, even if it remains officially
    # undefined for un-numbered filenames.
    numberedfilenames = list(numberedfilenames)
    numberedfilenames.sort()
    unnumberedfilenames = list(unnumberedfilenames)
    unnumberedfilenames.sort()

    for filename in unnumberedfilenames + numberedfilenames:
        suite.addTest(
            FunctionalDocFileSuite(
                os.path.normpath(os.path.join('..', 'pagetests', filename)))
            )
    suite.addTest(unittest.makeSuite(TearDownPTs))
    return suite

if __name__ == '__main__':
    r = unittest.TextTestRunner().run(test_suite())
