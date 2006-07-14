# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Run all of the pagetests, in priority order.

Set up the test data in the database first.
"""
__metaclass__ = type

import os, sys
import unittest
import sets
import sqlos.connection
import transaction

from canonical.functional import PageTestDocFileSuite, SpecialOutputChecker
from canonical.testing import PageTestLayer
from canonical.launchpad.ftests.harness import (
        _disconnect_sqlos, _reconnect_sqlos
        )
from canonical.launchpad.ftests import logout
from canonical.launchpad.ftests.harness import LaunchpadTestSetup
from canonical.launchpad.ftests import logout

here = os.path.dirname(os.path.realpath(__file__))

_db_is_setup = False


class PageTestError(Exception):
    pass


class StartStory(unittest.TestCase):
    layer = PageTestLayer
    def setUp(self):
        """Setup the database"""
        PageTestLayer.startStory()
        #logout() # Other tests are leaving crud :-(
        #LaunchpadTestSetup().setUp()
        #global _db_is_setup
        #_db_is_setup = True

    def tearDown(self):
        """But don't tear it down, so other tests in the suite can use it"""
        pass

    def test_setUpDatabase(self):
        # Fake test to ensure setUp is called. This stuff is really only
        # working by accident.
        pass


class EndStory(unittest.TestCase):
    layer = PageTestLayer
    def setUp(self):
        """Don't setup the database - it is already"""
        pass

    def tearDown(self):
        """Tear down the database"""
        PageTestLayer.endStory()
        #transaction.abort()
        #LaunchpadTestSetup().tearDown()
        #global _db_is_setup
        #_db_is_setup = False

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
        LaunchpadTestSetup().setUp()

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
        LaunchpadTestSetup().tearDown()


class PageTestCase(unittest.TestCase):
    """A test case that represents a pagetest
    
    This can be either a story of pagetests, or a single 
    'standalone' pagetest.

    This is achieved by holding a testsuite for the story, and
    delegating responsiblity for most methods to it.
    We want this to be a TestCase instance and not a TestSuite
    instance to be compatible with various test runners that
    filter tests - they generally ignore test suites and may
    select individual tests - but stories cannot be split up.
    """
    def __init__(self, storydir_or_single_test, package=None):
        """Create a PageTest for storydir_or_single_test.

        storydir_or_single_test should be an package relative file path.
        package is the python package the page test is found under, it
        defaults to canonical.launchpad
        """
        # we do not run the super __init__ because we are not using any of
        # the base classes functionality, and we'd just have to give it a
        # meaningless method.
        self._description = storydir_or_single_test
        self._suite = unittest.makeSuite(StartStory)
        if package is None:
            self._package = 'canonical.launchpad'
        else:
            self._package = package
        if not os.path.isdir(storydir_or_single_test):
            test_scripts = [os.path.basename(storydir_or_single_test)]
            storydir_or_single_test = os.path.dirname(storydir_or_single_test)
        else:
            filenames = [filename
                        for filename in os.listdir(storydir_or_single_test)
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
            numberedfilenames = sorted(numberedfilenames)
            unnumberedfilenames = sorted(unnumberedfilenames)
            test_scripts = unnumberedfilenames + numberedfilenames
    
        modules = self._package.split('.')
        if len(modules) == 0:
            raise PageTestError('Invalid package: ' + self._package)
        segments = storydir_or_single_test.split('/')
        # either modules is in segments somewhere, or its not a valid package
        # for the filename. 
        # TODO ? split this into a method or make it a helper/part of the 
        # FunctionalDocFileSuite facility.
        while len(segments) > 0 and segments[:len(modules)] != modules:
            segments.pop(0)
        if not len(segments):
            raise PageTestError('Test script dir %s not in packages %s' % (
                storydir_or_single_test, self._package
                ))
        relative_dir = '/'.join(segments[len(modules):])
        checker = SpecialOutputChecker()
        for leaf_filename in test_scripts:
            filename = os.path.join(relative_dir, leaf_filename)
            self._suite.addTest(PageTestDocFileSuite(
                filename, package=self._package, checker=checker
                ))
        self._suite.addTest(unittest.makeSuite(EndStory))

    def countTestCases(self):
        return self._suite.countTestCases()

    def shortDescription(self):
        return "pagetest: %s" % self._description

    def id(self):
        # XXX Andrew Bennetts 2006-02-15:
        # Because Zope's test runner assumes tests are named
        # "package.module.class.method", it ignores everything before the last
        # "." when matching.  Hence we strip the trailing ".txt" from test names
        # so that developers have a reasonably unique testname to filter on.
        id = self.shortDescription()
        if id.endswith('.txt'):
            id = id[:-len('.txt')]
        return id

    def __str__(self):
        return self.shortDescription()

    def __repr__(self):
        return "<%s storydir=%s>" % (self.__class__.__name__, self._description)

    def run(self, result=None):
        if result is None:
            result = self.defaultTestResult()
        # TODO RBC 20060117 we can hook in pre and post story actions
        # here much more tidily (and in self.debug too)
        # - probably via self.setUp and self.tearDown
        self._suite.run(result)

    def debug(self):
        self._suite.debug()


def test_suite():
    pagetestsdir = os.path.abspath(
            os.path.normpath(os.path.join(here, '..', 'pagetests'))
            )

    stories = [
        os.path.join(pagetestsdir, d) for d in os.listdir(pagetestsdir)
        if not d.startswith('.')
        ]
    stories = [d for d in stories if os.path.isdir(d)]
    stories.sort()

    standalone_suite = unittest.TestSuite()
    standalone_suite.layer = PageTestLayer
    story_suite = unittest.TestSuite()
    story_suite.layer = PageTestLayer

    for storydir in stories:
        if not storydir.endswith('standalone'):
            story_suite.addTest(
                    PageTestCase(os.path.join('pagetests', storydir))
                    )
        else:
            filenames = [filename
                        for filename in os.listdir(storydir)
                        if filename.lower().endswith('.txt')
                        ]
            for filename in filenames:
                standalone_suite.addTest(
                        PageTestCase(os.path.join(storydir, filename))
                        )

    suite = unittest.TestSuite()
    suite.addTest(standalone_suite)
    suite.addTest(story_suite)
    return suite

if __name__ == '__main__':
    r = unittest.TextTestRunner().run(test_suite())
