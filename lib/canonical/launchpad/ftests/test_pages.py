# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Run all of the pagetests, in priority order.

Set up the test data in the database first.
"""
__metaclass__ = type

import doctest
import os
import unittest

from BeautifulSoup import BeautifulSoup

from canonical.functional import PageTestDocFileSuite, SpecialOutputChecker
from canonical.testing import PageTestLayer

here = os.path.dirname(os.path.realpath(__file__))

def find_tag_by_id(content, id):
    """Find and return the tags with the given ID"""
    soup = BeautifulSoup(content)
    return soup.find(attrs={'id': id})

def find_tags_by_class(content, class_):
    """Find and return the tags matching the given class(s)"""
    match_classes = set(class_.split())
    def class_matcher(value):
        if value is None: return False
        classes = set(value.split())
        return match_classes.issubset(classes)
    soup = BeautifulSoup(content)
    return soup.findAll(attrs={'class': class_matcher})

def find_portlet(content, name):
    """Find and return the portlet with the given title"""
    soup = BeautifulSoup(content)
    for portlet in soup.findAll(attrs={'class': 'portlet'}):
        portlet_title = portlet.find('h4').renderContents()
        if name == portlet_title:
            return portlet
    return None

def find_main_content(content):
    """Find and return the main content area of the page"""
    soup = BeautifulSoup(content)
    tag = soup.find(attrs={'id': 'region-content'})
    if tag:
        return tag
    return soup.find(attrs={'id': 'content'})

def setUpGlobs(test):
    test.globs['find_tag_by_id'] = find_tag_by_id
    test.globs['find_tags_by_class'] = find_tags_by_class
    test.globs['find_portlet'] = find_portlet
    test.globs['find_main_content'] = find_main_content


class PageStoryTestCase(unittest.TestCase):
    """A test case that represents a pagetest story
    
    This is achieved by holding a testsuite for the story, and
    delegating responsiblity for most methods to it.
    We want this to be a TestCase instance and not a TestSuite
    instance to be compatible with various test runners that
    filter tests - they generally ignore test suites and may
    select individual tests - but stories cannot be split up.
    """

    layer = PageTestLayer

    def __init__(self, storydir, package=None):
        """Create a PageTest story for storydir.

        storydir should be an package relative file path.
        package is the python package the page test is found under, it
        defaults to the caller's package.
        """
        # we do not run the super __init__ because we are not using any of
        # the base classes functionality, and we'd just have to give it a
        # meaningless method.
        self._description = storydir
        self._suite = unittest.TestSuite()

        # we need to normalise the package name here, because it
        # involves checking the parent stack frame.  Otherwise the
        # files would be looked up relative to this module.
        package = doctest._normalize_module(package)
        abs_storydir = doctest._module_relative_path(package, storydir)

        filenames = set(filename
                        for filename in os.listdir(abs_storydir)
                        if filename.lower().endswith('.txt'))
        numberedfilenames = set(filename for filename in filenames
                                if len(filename) > 4
                                and filename[:2].isdigit()
                                and filename[2] == '-')
        unnumberedfilenames = filenames - numberedfilenames

        # A predictable order is important, even if it remains officially
        # undefined for un-numbered filenames.
        numberedfilenames = sorted(numberedfilenames)
        unnumberedfilenames = sorted(unnumberedfilenames)
        test_scripts = unnumberedfilenames + numberedfilenames
    
        checker = SpecialOutputChecker()
        for leaf_filename in test_scripts:
            filename = os.path.join(storydir, leaf_filename)
            self._suite.addTest(PageTestDocFileSuite(
                filename, package=package, checker=checker, setUp=setUpGlobs
                ))

    def countTestCases(self):
        return self._suite.countTestCases()

    def shortDescription(self):
        return "pagetest: %s" % self._description

    def id(self):
        return self.shortDescription()

    def __str__(self):
        return self.shortDescription()

    def __repr__(self):
        return "<%s storydir=%s>" % (self.__class__.__name__, self._description)

    def run(self, result=None):
        if result is None:
            result = self.defaultTestResult()
        PageTestLayer.startStory()
        try:
            # TODO RBC 20060117 we can hook in pre and post story actions
            # here much more tidily (and in self.debug too)
            # - probably via self.setUp and self.tearDown
            self._suite.run(result)
        finally:
            PageTestLayer.endStory()

    def debug(self):
        self._suite.debug()


def test_suite():
    pagetestsdir = os.path.join('..', 'pagetests')
    abs_pagetestsdir = os.path.abspath(
        os.path.normpath(os.path.join(here, pagetestsdir)))

    stories = [
        (os.path.join(pagetestsdir, d), os.path.join(abs_pagetestsdir, d))
        for d in os.listdir(abs_pagetestsdir)
        if not d.startswith('.') and
           os.path.isdir(os.path.join(abs_pagetestsdir, d))
        ]
    stories.sort()

    standalone_suite = unittest.TestSuite()
    story_suite = unittest.TestSuite()

    for (storydir, abs_storydir) in stories:
        if not storydir.endswith('standalone'):
            story_suite.addTest(PageStoryTestCase(storydir))
        else:
            # For standalone page tests, we just create normal
            # PageTestDocFileSuite instances.
            filenames = sorted(filename
                               for filename in os.listdir(abs_storydir)
                               if filename.lower().endswith('.txt'))
            checker = SpecialOutputChecker()
            for filename in filenames:
                standalone_suite.addTest(PageTestDocFileSuite(
                    os.path.join(storydir, filename),
                    checker=checker, layer=PageTestLayer,
                    setUp=setUpGlobs))

    suite = unittest.TestSuite()
    suite.addTest(standalone_suite)
    suite.addTest(story_suite)
    return suite

if __name__ == '__main__':
    r = unittest.TextTestRunner().run(test_suite())
