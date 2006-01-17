# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Run all of the pagetests, in priority order.

Set up the test data in the database first.
"""
__metaclass__ = type

import os, sys
import unittest
import sets
from harness import LaunchpadFunctionalTestSetup
import sqlos.connection

from canonical.functional import FunctionalDocFileSuite
from canonical.launchpad.ftests.harness import _disconnect_sqlos
from canonical.launchpad.ftests.harness import _reconnect_sqlos
from canonical.librarian.ftests.harness import LibrarianTestSetup
from canonical.launchpad.ftests import logout

here = os.path.dirname(os.path.realpath(__file__))

_db_is_setup = False

class StartStory(unittest.TestCase):
    def setUp(self):
        """Setup the database"""
        logout() # Other tests are leaving crud :-(
        LaunchpadFunctionalTestSetup().setUp()
        LibrarianTestSetup().setUp()
        global _db_is_setup
        _db_is_setup = True

    def tearDown(self):
        """But don't tear it down, so other tests in the suite can use it"""
        pass

    def test_setUpDatabase(self):
        # Fake test to ensure setUp is called. This stuff is really only
        # working by accident.
        pass


class EndStory(unittest.TestCase):
    def setUp(self):
        """Don't setup the database - it is already"""
        pass

    def tearDown(self):
        """Tear down the database"""
        LibrarianTestSetup().tearDown()
        LaunchpadFunctionalTestSetup().tearDown()
        global _db_is_setup
        _db_is_setup = False

    def test_tearDownDatabase(self):
        # Fake test to ensure tearDown is called.
        pass


def setUp(test):
    """Single page setUp.
    
    Handle SQLOS 'ickyness. Also take this opertunity to setup the
    db if necessary, which is the case if we are running a single page
    test.
    """
    global _db_is_setup
    if _db_is_setup:
        _reconnect_sqlos()
    else:
        LaunchpadFunctionalTestSetup().setUp()

def tearDown(test):
    """Single page tearDown.
    
    Handle SQLOS 'ickyness. Also teardown the database if we are running
    a single standalone page test.
    """
    # Tear down the DB if we are running a single page test
    global _db_is_setup
    if _db_is_setup:
        _disconnect_sqlos()
    else:
        LaunchpadFunctionalTestSetup().tearDown()


class TestStory(unittest.TestCase):
    """A test case that represents a story of doctests.

    This is achieved by holding a testsuite for the story, and
    delegating responsiblity for most methods to it.
    We want this to be a TestCase instance and not a TestSuite
    instance to be compatible with various test runners that
    filter tests - they generally ignore test suites and may
    select individual tests - but stories cannot be split up.
    """

    def __init__(self, storydir):
        # we do not run the super __init__ because we are not using any of
        # the base classes functionality, and we'd just have to give it a
        # meaningless method.
        self._storydir = storydir
        self._suite = unittest.makeSuite(StartStory)
        filenames = [filename
                    for filename in os.listdir(self._storydir)
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
            story = os.path.basename(self._storydir)
            filename = os.path.join(
                    os.pardir, 'pagetests', story, filename
                    )
            self._suite.addTest(FunctionalDocFileSuite(
                filename, setUp=setUp, tearDown=tearDown
                ))
        self._suite.addTest(unittest.makeSuite(EndStory))

    def countTestCases(self):
        return self._suite.countTestCases()

    def shortDescription(self):
        return "Story: %s" % self._storydir

    def id(self):
        return self.shortDescription()

    def __str__(self):
        return self.shortDescription()

    def __repr__(self):
        return "<%s storydir=%s>" % \
               (_strclass(self.__class__), self._storydir)

    def run(self, result=None):
        if result is None: result = self.defaultTestResult()
        # TODO RBC 20060117 we can hook in pre and post story actions
        # here much more tidily (and in self.debug too)
        # - probably via self.setUp and self.tearDown
        self._suite.run(result)

    def debug(self):
        self._suite.debug()


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
    stories.sort()

    for storydir in stories:
        suite.addTest(TestStory(storydir))
    return suite

if __name__ == '__main__':
    r = unittest.TextTestRunner().run(test_suite())
