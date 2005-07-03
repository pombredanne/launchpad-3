"""Tests for canonical.dyson.hose."""

from hct.scaffold import Scaffold, register


class Hose_Logging(Scaffold):
    def testCreatesDefaultLogger(self):
        """Hose creates a default logger."""
        from canonical.dyson.hose import Hose
        from logging import Logger
        h = Hose()
        self.failUnless(isinstance(h.log, Logger))

    def testCreatesChildLogger(self):
        """Hose creates a child logger if given a parent."""
        from canonical.dyson.hose import Hose
        from logging import getLogger
        parent = getLogger("foo")
        h = Hose(log_parent=parent)
        self.assertEquals(h.log.parent, parent)


class Hose_Filter(Scaffold):
    def testCreatesFilterObject(self):
        """Hose creates a Filter object."""
        from canonical.dyson.hose import Hose
        from canonical.dyson.filter import Filter
        h = Hose()
        self.failUnless(isinstance(h.filter, Filter))

    def testDefaultsFiltersToEmptyDict(self):
        """Hose creates Filter object with empty dictionary."""
        from canonical.dyson.hose import Hose
        from canonical.dyson.filter import Filter
        h = Hose()
        self.assertEquals(h.filter.filters, {})

    def testCreatesFiltersWithGiven(self):
        """Hose creates Filter object with dictionary given."""
        from canonical.dyson.hose import Hose
        from canonical.dyson.filter import Filter
        h = Hose({"foo": ("http:", "e*")})
        self.assertEquals(h.filter.filters, {"foo": ("http:", "e*")})


class Hose_Cache(Scaffold):
    def testNoCache(self):
        """Hose does not use up a cache if none given."""
        from canonical.dyson.hose import Hose
        h = Hose()
        self.assertEquals(h.cache, None)

    def testCacheObjectPath(self):
        """Hose sets up Cache object to that given."""
        from canonical.dyson.hose import Hose
        path = self.tempname()
        h = Hose(cache="wibble")
        self.assertEquals(h.cache, "wibble")


class Hose_Urls(Scaffold):
    def testCallsReduceWork(self):
        """Hose constructor calls reduceWork function."""
        from canonical.dyson.hose import Hose
        h = self.wrapped(Hose)
        self.assertEquals(h.called["reduceWork"], True)

    def testPassesUrlList(self):
        """Hose constructor passes url list to reduceWork."""
        from canonical.dyson.hose import Hose
        h = self.wrapped(Hose, {"foo": ("http:", "e*")})
        self.assertEquals(h.called_args["reduceWork"][0][0], ["http:"])

    def testSetsUrlProperty(self):
        """Hose constructor sets urls property to reduceWork return value."""
        from canonical.dyson.hose import Hose
        class TestHose(Hose):
            def reduceWork(self, url_list):
                return "wibble"

        h = TestHose()
        self.assertEquals(h.urls, "wibble")


class Hose_ReduceWork(Scaffold):
    def testEmptyList(self):
        """Hose.reduceWork returns empty list when given one."""
        from canonical.dyson.hose import Hose
        h = Hose()
        self.assertEquals(h.reduceWork([]), [])

    def testReducedList(self):
        """Hose.reduceWork returns same list when nothing to do."""
        from canonical.dyson.hose import Hose
        h = Hose()
        self.assertEquals(h.reduceWork(["http://localhost/", "file:///usr/"]),
                          ["http://localhost/", "file:///usr/"])

    def testReducesList(self):
        """Hose.reduceWork removes children elements from list."""
        from canonical.dyson.hose import Hose
        h = Hose()
        self.assertEquals(h.reduceWork(["http://localhost/",
                                        "http://localhost/foo/bar/",
                                        "http://localhost/wibble/",
                                        "file:///usr/"]),
                          ["http://localhost/", "file:///usr/"])


register(__name__)
