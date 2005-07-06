"""Tests for canonical.dyson.walker."""

from hct.scaffold import Scaffold, register


class WalkerBase_Logging(Scaffold):
    def testCreatesDefaultLogger(self):
        """WalkerBase creates a default logger."""
        from canonical.dyson.walker import WalkerBase
        from logging import Logger
        w = WalkerBase("/")
        self.failUnless(isinstance(w.log, Logger))

    def testCreatesChildLogger(self):
        """WalkerBase creates a child logger if given a parent."""
        from canonical.dyson.walker import WalkerBase
        from logging import getLogger
        parent = getLogger("foo")
        w = WalkerBase("/", log_parent=parent)
        self.assertEquals(w.log.parent, parent)


class WalkerBase_Base(Scaffold):
    def testSetsBase(self):
        """WalkerBase sets the base property."""
        from canonical.dyson.walker import WalkerBase
        w = WalkerBase("ftp://localhost/")
        self.assertEquals(w.base, "ftp://localhost/")

    def testSetsScheme(self):
        """WalkerBase sets the scheme property."""
        from canonical.dyson.walker import WalkerBase
        w = WalkerBase("ftp://localhost/")
        self.assertEquals(w.scheme, "ftp")

    def testSetsHost(self):
        """WalkerBase sets the host property."""
        from canonical.dyson.walker import WalkerBase
        w = WalkerBase("ftp://localhost/")
        self.assertEquals(w.host, "localhost")

    def testNoScheme(self):
        """WalkerBase works when given a URL with no scheme."""
        from canonical.dyson.walker import WalkerBase
        w = WalkerBase("/")
        self.assertEquals(w.host, "")

    def testWrongScheme(self):
        """WalkerBase raises WalkerError when given an unhandled scheme."""
        from canonical.dyson.walker import WalkerBase, WalkerError
        self.assertRaises(WalkerError, WalkerBase, "foo://localhost/")

    def testUnescapesHost(self):
        """WalkerBase unescapes the host portion."""
        from canonical.dyson.walker import WalkerBase
        w = WalkerBase("ftp://local%40host/")
        self.assertEquals(w.host, "local@host")

    def testNoUsername(self):
        """WalkerBase stores None when there is no username."""
        from canonical.dyson.walker import WalkerBase
        w = WalkerBase("ftp://localhost/")
        self.assertEquals(w.user, None)

    def testUsername(self):
        """WalkerBase splits out the username from the host portion."""
        from canonical.dyson.walker import WalkerBase
        w = WalkerBase("ftp://scott@localhost/")
        self.assertEquals(w.user, "scott")
        self.assertEquals(w.host, "localhost")

    def testUnescapesUsername(self):
        """WalkerBase unescapes the username portion."""
        from canonical.dyson.walker import WalkerBase
        w = WalkerBase("ftp://scott%3awibble@localhost/")
        self.assertEquals(w.user, "scott:wibble")
        self.assertEquals(w.host, "localhost")

    def testNoPassword(self):
        """WalkerBase stores None when there is no password."""
        from canonical.dyson.walker import WalkerBase
        w = WalkerBase("ftp://scott@localhost/")
        self.assertEquals(w.passwd, None)

    def testPassword(self):
        """WalkerBase splits out the password from the username."""
        from canonical.dyson.walker import WalkerBase
        w = WalkerBase("ftp://scott:wibble@localhost/")
        self.assertEquals(w.user, "scott")
        self.assertEquals(w.passwd, "wibble")
        self.assertEquals(w.host, "localhost")

    def testUnescapesPassword(self):
        """WalkerBase unescapes the password portion."""
        from canonical.dyson.walker import WalkerBase
        w = WalkerBase("ftp://scott:wibble%20wobble@localhost/")
        self.assertEquals(w.user, "scott")
        self.assertEquals(w.passwd, "wibble wobble")
        self.assertEquals(w.host, "localhost")

    def testPathOnly(self):
        """WalkerBase stores the path if that's all there is."""
        from canonical.dyson.walker import WalkerBase
        w = WalkerBase("/path/to/something/")
        self.assertEquals(w.path, "/path/to/something/")

    def testPathInUrl(self):
        """WalkerBase stores the path portion of a complete URL."""
        from canonical.dyson.walker import WalkerBase
        w = WalkerBase("ftp://localhost/path/to/something/")
        self.assertEquals(w.path, "/path/to/something/")

    def testAddsSlashToPath(self):
        """WalkerBase adds a trailing slash to path if ommitted."""
        from canonical.dyson.walker import WalkerBase
        w = WalkerBase("ftp://localhost/path/to/something")
        self.assertEquals(w.path, "/path/to/something/")

    def testUnescapesPath(self):
        """WalkerBase leaves the path escaped."""
        from canonical.dyson.walker import WalkerBase
        w = WalkerBase("ftp://localhost/some%20thing/")
        self.assertEquals(w.path, "/some%20thing/")

    def testStoresQuery(self):
        """WalkerBase stores the query portion of a supporting URL."""
        from canonical.dyson.walker import WalkerBase
        w = WalkerBase("http://localhost/?foo")
        self.assertEquals(w.query, "foo")

    def testStoresFragment(self):
        """WalkerBase stores the fragment portion of a supporting URL."""
        from canonical.dyson.walker import WalkerBase
        WalkerBase.FRAGMENTS = True
        try:
            w = WalkerBase("http://localhost/#foo")
            self.assertEquals(w.fragment, "foo")
        finally:
            WalkerBase.FRAGMENTS = False


class FTPWalker_Base(Scaffold):
    def testFtpScheme(self):
        """FTPWalker works when initialised with an ftp-scheme URL."""
        from canonical.dyson.walker import FTPWalker
        w = FTPWalker("ftp://localhost/")
        self.assertEquals(w.host, "localhost")

    def testNoScheme(self):
        """FTPWalker works when given a URL with no scheme."""
        from canonical.dyson.walker import FTPWalker
        w = FTPWalker("/")
        self.assertEquals(w.host, "")

    def testWrongScheme(self):
        """FTPWalker raises WalkerError when given an unhandled scheme."""
        from canonical.dyson.walker import FTPWalker, WalkerError
        self.assertRaises(WalkerError, FTPWalker, "http://localhost/")

    def testNoUsername(self):
        """FTPWalker stores 'anonymous' when there is no username."""
        from canonical.dyson.walker import FTPWalker
        w = FTPWalker("ftp://localhost/")
        self.assertEquals(w.user, "anonymous")

    def testNoPassword(self):
        """FTPWalker stores empty string when there is no password."""
        from canonical.dyson.walker import FTPWalker
        w = FTPWalker("ftp://scott@localhost/")
        self.assertEquals(w.passwd, "")


class HTTPWalker_Base(Scaffold):
    def testHttpScheme(self):
        """HTTPWalker works when initialised with an http-scheme URL."""
        from canonical.dyson.walker import HTTPWalker
        w = HTTPWalker("http://localhost/")
        self.assertEquals(w.host, "localhost")

    def testHttpsScheme(self):
        """HTTPWalker works when initialised with an https-scheme URL."""
        from canonical.dyson.walker import HTTPWalker
        w = HTTPWalker("https://localhost/")
        self.assertEquals(w.host, "localhost")

    def testNoScheme(self):
        """HTTPWalker works when given a URL with no scheme."""
        from canonical.dyson.walker import HTTPWalker
        w = HTTPWalker("/")
        self.assertEquals(w.host, "")

    def testWrongScheme(self):
        """HTTPWalker raises WalkerError when given an unhandled scheme."""
        from canonical.dyson.walker import HTTPWalker, WalkerError
        self.assertRaises(WalkerError, HTTPWalker, "ftp://localhost/")


class Walker_CombineUrl(Scaffold):
    def testConstructsUrl(self):
        """combine_url constructs the URL correctly."""
        from canonical.dyson.walker import combine_url
        self.assertEquals(combine_url("file:///base", "/subdir/", "file"),
                          "file:///subdir/file")


register(__name__)
