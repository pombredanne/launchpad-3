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

class StartStory(harness.LaunchpadTestCase):
    def setUp(self):
        """Setup the database"""
        super(StartStory, self).setUp()

    def tearDown(self):
        """But don't tear it down, so other tests in the suite can use it"""
        pass

    def test_setUpDatabase(self):
        # Fake test to ensure setUp is called. This stuff is really only
        # working by accident.
        pass

class EndStory(harness.LaunchpadTestCase):
    def setUp(self):
        """Don't setup the database - it is already"""
        self._cons = []
        pass

    def tearDown(self):
        """Tear down the database"""
        super(EndStory, self).tearDown()

    def test_tearDownDatabase(self):
        # Fake test to ensure tearDown is called.
        pass

def test_suite():
    suite = unittest.TestSuite()
    pagetestsdir = os.path.abspath(
            os.path.normpath(os.path.join(here, '..', 'pagetests'))
            )

    stories = [
        os.path.join(pagetestsdir, d) for d in os.listdir(pagetestsdir)
        if not d.startswith('.')
        ]
    stories = [d for d in stories if os.path.isdir(d)]

    for storydir in stories:
        suite.addTest(unittest.makeSuite(StartStory))
        filenames = [filename
                    for filename in os.listdir(storydir)
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
            story = os.path.basename(storydir)
            filename = os.path.join(
                    os.pardir, 'pagetests', story, filename
                    )
            suite.addTest(FunctionalDocFileSuite(filename))
        suite.addTest(unittest.makeSuite(EndStory))
    return suite

if __name__ == '__main__':
    r = unittest.TextTestRunner().run(test_suite())
