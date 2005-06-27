"""Tests for canonical.dyson.filter."""

from hct.scaffold import Scaffold, register


class Filter_Logging(Scaffold):
    def testCreatesDefaultLogger(self):
        """Filter creates a default logger."""
        from canonical.dyson.filter import Filter
        from logging import Logger
        f = Filter()
        self.failUnless(isinstance(f.log, Logger))

    def testCreatesChildLogger(self):
        """Filter creates a child logger if given a parent."""
        from canonical.dyson.filter import Filter
        from logging import getLogger
        parent = getLogger("foo")
        f = Filter(log_parent=parent)
        self.assertEquals(f.log.parent, parent)


class Filter_Init(Scaffold):
    def testDefaultFiltersProperty(self):
        """Filter constructor initialises filters property to empty dict."""
        from canonical.dyson.filter import Filter
        f = Filter()
        self.assertEquals(f.filters, {})

    def testFiltersPropertyGiven(self):
        """Filter constructor accepts argument to set filters property."""
        from canonical.dyson.filter import Filter
        f = Filter("wibble")
        self.assertEquals(f.filters, "wibble")


class Filter_CheckUrl(Scaffold):
    def testNoFilters(self):
        """Filter.check returns None if there are no filters."""
        from canonical.dyson.filter import Filter
        f = Filter()
        self.assertEquals(f.check("file:///subdir/file"), None)

    def testNotMatching(self):
        """Filter.check returns None if doesn't match a filter."""
        from canonical.dyson.filter import Filter
        f = Filter({ "foo": ("", "w*") })
        self.assertEquals(f.check("file:///subdir/file"), None)

    def testOnlyFilenamePortion(self):
        """Filter.check only checks the filename portion."""
        from canonical.dyson.filter import Filter
        f = Filter({ "foo": ("", "*d*") })
        self.assertEquals(f.check("file:///subdir/file"), None)

    def testReturnsMatching(self):
        """Filter.check returns the matching keyword."""
        from canonical.dyson.filter import Filter
        f = Filter({ "foo": ("", "f*e") })
        self.assertEquals(f.check("file:///subdir/file"), "foo")

    def testReturnsMatchingBoth(self):
        """Filter.check returns the matching keyword if base matches."""
        from canonical.dyson.filter import Filter
        f = Filter({ "foo": ("file:", "f*e") })
        self.assertEquals(f.check("file:///subdir/file"), "foo")

    def testReturnsNonMatchingBase(self):
        """Filter.check returns None if the base does not match."""
        from canonical.dyson.filter import Filter
        f = Filter({ "foo": ("http:", "f*e") })
        self.assertEquals(f.check("file:///subdir/file"), None)


class Cache_Logging(Scaffold):
    def testCreatesDefaultLogger(self):
        """Cache creates a default logger."""
        from canonical.dyson.filter import Cache
        from logging import Logger
        c = Cache(self.tempname())
        self.failUnless(isinstance(c.log, Logger))

    def testCreatesChildLogger(self):
        """Cache creates a child logger if given a parent."""
        from canonical.dyson.filter import Cache
        from logging import getLogger
        parent = getLogger("foo")
        c = Cache(self.tempname(), log_parent=parent)
        self.assertEquals(c.log.parent, parent)


class Cache_Init(Scaffold):
    def testSetsPathProperty(self):
        """Cache constructor sets the path property."""
        from canonical.dyson.filter import Cache
        path = self.tempname()
        c = Cache(path)
        self.assertEquals(c.path, path)

    def testSetsFilesProperty(self):
        """Cache constructor sets the files property to an empty dictionary."""
        from canonical.dyson.filter import Cache
        c = Cache(self.tempname())
        self.assertEquals(c.files, {})

    def testReturnsFalse(self):
        """Cache works when the object isn't cached."""
        from canonical.dyson.filter import Cache
        c = Cache(self.tempname())
        self.failIf("http://localhost/foo" in c)

    def testReturnsTrue(self):
        """Cache works when the object should be cached."""
        from canonical.dyson.filter import Cache
        c = Cache(self.tempname())
        self.failIf("http://localhost/foo" in c)
        self.failUnless("http://localhost/foo" in c)

    def testReadsAndWrites(self):
        """Cache reads and writes cache files."""
        from canonical.dyson.filter import Cache
        path = self.tempname()
        c = Cache(path)
        self.write("http://localhost/foo\n", path, "fo")
        self.failUnless("http://localhost/foo" in c)
        self.failIf("http://localhost/bar" in c)
        c.save()
        self.assertEquals(self.read(path, "ba"), "http://localhost/bar\n")


register(__name__)
