"""Tests for canonical.launchpad.scripts.productreleasefinder.hose."""

import unittest
from hct.scaffold import Scaffold


class Hose_Logging(unittest.TestCase):
    def testCreatesDefaultLogger(self):
        """Hose creates a default logger."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        from logging import Logger
        h = Hose()
        self.failUnless(isinstance(h.log, Logger))

    def testCreatesChildLogger(self):
        """Hose creates a child logger if given a parent."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        from logging import getLogger
        parent = getLogger("foo")
        h = Hose(log_parent=parent)
        self.assertEquals(h.log.parent, parent)


class Hose_Filter(unittest.TestCase):
    def testCreatesFilterObject(self):
        """Hose creates a Filter object."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        from canonical.launchpad.scripts.productreleasefinder.filter import (
            Filter)
        h = Hose()
        self.failUnless(isinstance(h.filter, Filter))

    def testDefaultsFiltersToEmptyDict(self):
        """Hose creates Filter object with empty dictionary."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        h = Hose()
        self.assertEquals(h.filter.filters, [])

    def testCreatesFiltersWithGiven(self):
        """Hose creates Filter object with dictionary given."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        from canonical.launchpad.scripts.productreleasefinder.filter import (
            FilterPattern)
        pattern = FilterPattern("foo", "http:", "e*")
        h = Hose([pattern])
        self.assertEquals(len(h.filter.filters), 1)
        self.assertEquals(h.filter.filters[0], pattern)


class Hose_Urls(Scaffold):
    def testCallsReduceWork(self):
        """Hose constructor calls reduceWork function."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        h = self.wrapped(Hose)
        self.assertEquals(h.called["reduceWork"], True)

    def testPassesUrlList(self):
        """Hose constructor passes url list to reduceWork."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        from canonical.launchpad.scripts.productreleasefinder.filter import (
            FilterPattern)
        pattern = FilterPattern("foo", "http://archive.ubuntu.com/", "e*")
        h = self.wrapped(Hose, [pattern])
        self.assertEquals(h.called_args["reduceWork"][0][0],
                          ["http://archive.ubuntu.com/"])

    def testSetsUrlProperty(self):
        """Hose constructor sets urls property to reduceWork return value."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        class TestHose(Hose):
            def reduceWork(self, url_list):
                return "wibble"

        h = TestHose()
        self.assertEquals(h.urls, "wibble")


class Hose_ReduceWork(unittest.TestCase):
    def testEmptyList(self):
        """Hose.reduceWork returns empty list when given one."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        h = Hose()
        self.assertEquals(h.reduceWork([]), [])

    def testReducedList(self):
        """Hose.reduceWork returns same list when nothing to do."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        h = Hose()
        self.assertEquals(h.reduceWork(["http://localhost/", "file:///usr/"]),
                          ["http://localhost/", "file:///usr/"])

    def testReducesList(self):
        """Hose.reduceWork removes children elements from list."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        h = Hose()
        self.assertEquals(h.reduceWork(["http://localhost/",
                                        "http://localhost/foo/bar/",
                                        "http://localhost/wibble/",
                                        "file:///usr/"]),
                          ["http://localhost/", "file:///usr/"])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
