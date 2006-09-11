"""Tests for canonical.launchpad.scripts.productreleasefinder.filter."""

import unittest


class Filter_Logging(unittest.TestCase):
    def testCreatesDefaultLogger(self):
        """Filter creates a default logger."""
        from canonical.launchpad.scripts.productreleasefinder.filter import (
            Filter)
        from logging import Logger
        f = Filter()
        self.failUnless(isinstance(f.log, Logger))

    def testCreatesChildLogger(self):
        """Filter creates a child logger if given a parent."""
        from canonical.launchpad.scripts.productreleasefinder.filter import (
            Filter)
        from logging import getLogger
        parent = getLogger("foo")
        f = Filter(log_parent=parent)
        self.assertEquals(f.log.parent, parent)


class Filter_Init(unittest.TestCase):
    def testDefaultFiltersProperty(self):
        """Filter constructor initialises filters property to empty dict."""
        from canonical.launchpad.scripts.productreleasefinder.filter import (
            Filter)
        f = Filter()
        self.assertEquals(f.filters, [])

    def testFiltersPropertyGiven(self):
        """Filter constructor accepts argument to set filters property."""
        from canonical.launchpad.scripts.productreleasefinder.filter import (
            Filter, FilterPattern)
        f = Filter(["wibble"])
        self.assertEquals(len(f.filters), 1)
        self.assertEquals(f.filters[0], "wibble")


class Filter_CheckUrl(unittest.TestCase):
    def testNoFilters(self):
        """Filter.check returns None if there are no filters."""
        from canonical.launchpad.scripts.productreleasefinder.filter import (
            Filter)
        f = Filter()
        self.assertEquals(f.check("file:///subdir/file"), None)

    def testNotMatching(self):
        """Filter.check returns None if doesn't match a filter."""
        from canonical.launchpad.scripts.productreleasefinder.filter import (
            Filter, FilterPattern)
        pattern = FilterPattern("foo", "file:///subdir", "w*")
        f = Filter([pattern])
        self.assertEquals(f.check("file:///subdir/file"), None)

    def testNoMatchingSlashes(self):
        """Filter.check that the glob does not match slashes."""
        from canonical.launchpad.scripts.productreleasefinder.filter import (
            Filter, FilterPattern)
        pattern = FilterPattern("foo", "file:///", "*d*")
        f = Filter([pattern])
        self.assertEquals(f.check("file:///subdir/file"), None)

    def testReturnsMatching(self):
        """Filter.check returns the matching keyword."""
        from canonical.launchpad.scripts.productreleasefinder.filter import (
            Filter, FilterPattern)
        pattern = FilterPattern("foo", "file:///subdir", "f*e")
        f = Filter([pattern])
        self.assertEquals(f.check("file:///subdir/file"), "foo")

    def testGlobSubdir(self):
        # Filter.glob can contain slashes to match subdirs
        from canonical.launchpad.scripts.productreleasefinder.filter import (
            Filter, FilterPattern)
        pattern = FilterPattern("foo", "file:///", "sub*/f*e")
        f = Filter([pattern])
        self.assertEquals(f.check("file:///subdir/file"), "foo")

    def testReturnsNonMatchingBase(self):
        """Filter.check returns None if the base does not match."""
        from canonical.launchpad.scripts.productreleasefinder.filter import (
            Filter, FilterPattern)
        pattern = FilterPattern("foo", "http:", "f*e")
        f = Filter([pattern])
        self.assertEquals(f.check("file:///subdir/file"), None)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
