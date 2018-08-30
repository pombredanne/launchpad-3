# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.registry.scripts.productreleasefinder.walker."""

import logging
import StringIO

import responses

from lp.registry.scripts.productreleasefinder.walker import (
    combine_url,
    FTPWalker,
    HTTPWalker,
    WalkerBase,
    WalkerError,
    )
from lp.services.timeout import (
    get_default_timeout_function,
    set_default_timeout_function,
    )
from lp.testing import (
    reset_logging,
    TestCase,
    )


class WalkerBase_Logging(TestCase):

    def testCreatesDefaultLogger(self):
        """WalkerBase creates a default logger."""
        w = WalkerBase("/")
        self.assertTrue(isinstance(w.log, logging.Logger))

    def testCreatesChildLogger(self):
        """WalkerBase creates a child logger if given a parent."""
        parent = logging.getLogger("foo")
        w = WalkerBase("/", log_parent=parent)
        self.assertEqual(w.log.parent, parent)


class WalkerBase_Base(TestCase):

    def testSetsBase(self):
        """WalkerBase sets the base property."""
        w = WalkerBase("ftp://localhost/")
        self.assertEqual(w.base, "ftp://localhost/")

    def testSetsScheme(self):
        """WalkerBase sets the scheme property."""
        w = WalkerBase("ftp://localhost/")
        self.assertEqual(w.scheme, "ftp")

    def testSetsHost(self):
        """WalkerBase sets the host property."""
        w = WalkerBase("ftp://localhost/")
        self.assertEqual(w.host, "localhost")

    def testNoScheme(self):
        """WalkerBase works when given a URL with no scheme."""
        w = WalkerBase("/")
        self.assertEqual(w.host, "")

    def testWrongScheme(self):
        """WalkerBase raises WalkerError when given an unhandled scheme."""
        self.assertRaises(WalkerError, WalkerBase, "foo://localhost/")

    def testUnescapesHost(self):
        """WalkerBase unescapes the host portion."""
        w = WalkerBase("ftp://local%40host/")
        self.assertEqual(w.host, "local@host")

    def testNoUsername(self):
        """WalkerBase stores None when there is no username."""
        w = WalkerBase("ftp://localhost/")
        self.assertEqual(w.user, None)

    def testUsername(self):
        """WalkerBase splits out the username from the host portion."""
        w = WalkerBase("ftp://scott@localhost/")
        self.assertEqual(w.user, "scott")
        self.assertEqual(w.host, "localhost")

    def testUnescapesUsername(self):
        """WalkerBase unescapes the username portion."""
        w = WalkerBase("ftp://scott%3awibble@localhost/")
        self.assertEqual(w.user, "scott:wibble")
        self.assertEqual(w.host, "localhost")

    def testNoPassword(self):
        """WalkerBase stores None when there is no password."""
        w = WalkerBase("ftp://scott@localhost/")
        self.assertEqual(w.passwd, None)

    def testPassword(self):
        """WalkerBase splits out the password from the username."""
        w = WalkerBase("ftp://scott:wibble@localhost/")
        self.assertEqual(w.user, "scott")
        self.assertEqual(w.passwd, "wibble")
        self.assertEqual(w.host, "localhost")

    def testUnescapesPassword(self):
        """WalkerBase unescapes the password portion."""
        w = WalkerBase("ftp://scott:wibble%20wobble@localhost/")
        self.assertEqual(w.user, "scott")
        self.assertEqual(w.passwd, "wibble wobble")
        self.assertEqual(w.host, "localhost")

    def testPathOnly(self):
        """WalkerBase stores the path if that's all there is."""
        w = WalkerBase("/path/to/something/")
        self.assertEqual(w.path, "/path/to/something/")

    def testPathInUrl(self):
        """WalkerBase stores the path portion of a complete URL."""
        w = WalkerBase("ftp://localhost/path/to/something/")
        self.assertEqual(w.path, "/path/to/something/")

    def testAddsSlashToPath(self):
        """WalkerBase adds a trailing slash to path if ommitted."""
        w = WalkerBase("ftp://localhost/path/to/something")
        self.assertEqual(w.path, "/path/to/something/")

    def testUnescapesPath(self):
        """WalkerBase leaves the path escaped."""
        w = WalkerBase("ftp://localhost/some%20thing/")
        self.assertEqual(w.path, "/some%20thing/")

    def testStoresQuery(self):
        """WalkerBase stores the query portion of a supporting URL."""
        w = WalkerBase("http://localhost/?foo")
        self.assertEqual(w.query, "foo")

    def testStoresFragment(self):
        """WalkerBase stores the fragment portion of a supporting URL."""
        WalkerBase.FRAGMENTS = True
        try:
            w = WalkerBase("http://localhost/#foo")
            self.assertEqual(w.fragment, "foo")
        finally:
            WalkerBase.FRAGMENTS = False


class WalkerBase_walk(TestCase):
    """Test the walk() method."""

    def tearDown(self):
        reset_logging()
        super(WalkerBase_walk, self).tearDown()

    def test_walk_UnicodeEncodeError(self):
        """Verify that a UnicodeEncodeError is logged."""

        class TestWalker(WalkerBase):

            def list(self, sub_dir):
                # Force the walker to handle an exception.
                raise UnicodeEncodeError(
                    'utf-8', u'source text', 0, 1, 'reason')

            def open(self):
                pass

            def close(self):
                pass

        log_output = StringIO.StringIO()
        logger = logging.getLogger()
        self.addCleanup(logger.setLevel, logger.level)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.StreamHandler(log_output))
        walker = TestWalker('http://example.org/foo', logger)
        list(walker)
        self.assertEqual(
            "Unicode error parsing http://example.org/foo page '/foo/'\n",
            log_output.getvalue())

    def test_walk_open_fail(self):
        # The walker handles an exception raised during open().

        class TestWalker(WalkerBase):

            def list(self, sub_dir):
                pass

            def open(self):
                raise IOError("Test failure.")

            def close(self):
                pass

        log_output = StringIO.StringIO()
        logger = logging.getLogger()
        self.addCleanup(logger.setLevel, logger.level)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.StreamHandler(log_output))
        walker = TestWalker('ftp://example.org/foo', logger)
        list(walker)
        self.assertEqual(
            "Could not connect to ftp://example.org/foo\n"
            "Failure: Test failure.\n",
            log_output.getvalue())


class FTPWalker_Base(TestCase):

    def testFtpScheme(self):
        """FTPWalker works when initialized with an ftp-scheme URL."""
        w = FTPWalker("ftp://localhost/")
        self.assertEqual(w.host, "localhost")

    def testNoScheme(self):
        """FTPWalker works when given a URL with no scheme."""
        w = FTPWalker("/")
        self.assertEqual(w.host, "")

    def testWrongScheme(self):
        """FTPWalker raises WalkerError when given an unhandled scheme."""
        self.assertRaises(WalkerError, FTPWalker, "http://localhost/")

    def testNoUsername(self):
        """FTPWalker stores 'anonymous' when there is no username."""
        w = FTPWalker("ftp://localhost/")
        self.assertEqual(w.user, "anonymous")

    def testNoPassword(self):
        """FTPWalker stores empty string when there is no password."""
        w = FTPWalker("ftp://scott@localhost/")
        self.assertEqual(w.passwd, "")


class HTTPWalker_Base(TestCase):

    def testHttpScheme(self):
        """HTTPWalker works when initialized with an http-scheme URL."""
        w = HTTPWalker("http://localhost/")
        self.assertEqual(w.host, "localhost")

    def testHttpsScheme(self):
        """HTTPWalker works when initialized with an https-scheme URL."""
        w = HTTPWalker("https://localhost/")
        self.assertEqual(w.host, "localhost")

    def testNoScheme(self):
        """HTTPWalker works when given a URL with no scheme."""
        w = HTTPWalker("/")
        self.assertEqual(w.host, "")

    def testWrongScheme(self):
        """HTTPWalker raises WalkerError when given an unhandled scheme."""
        self.assertRaises(WalkerError, HTTPWalker, "foo://localhost/")


class HTTPWalker_ListDir(TestCase):

    def setUp(self):
        super(HTTPWalker_ListDir, self).setUp()
        self.addCleanup(reset_logging)
        original_timeout_function = get_default_timeout_function()
        set_default_timeout_function(lambda: 60.0)
        self.addCleanup(
            set_default_timeout_function, original_timeout_function)

    @responses.activate
    def testApacheListing(self):
        # Test that list() handles a standard Apache dir listing.
        content = '''
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html>
 <head>
  <title>Index of /pub/GNOME/sources/gnome-gpg/0.5</title>
 </head>
 <body>
<h1>Index of /pub/GNOME/sources/gnome-gpg/0.5</h1>
<pre><img src="/icons/blank.gif" alt="Icon " width="24" height="24"> <a href="?C=N;O=D">Name</a>                          <a href="?C=M;O=A">Last modified</a>      <a href="?C=S;O=A">Size</a>  <a href="?C=D;O=A">Description</a><hr><a href="/pub/GNOME/sources/gnome-gpg/"><img src="http://www.gnome.org/img/24x24/parent.png" alt="[DIR]" width="24" height="24"></a> <a href="/pub/GNOME/sources/gnome-gpg/">Parent Directory</a>                                   -

<a href="LATEST-IS-0.5.0"><img src="http://www.gnome.org/img/24x24/default.png" alt="[   ]" width="24" height="24"></a> <a href="LATEST-IS-0.5.0">LATEST-IS-0.5.0</a>               02-Sep-2006 08:58   81K
<a href="gnome-gpg-0.5.0.md5sum"><img src="http://www.gnome.org/img/24x24/default.png" alt="[   ]" width="24" height="24"></a> <a href="gnome-gpg-0.5.0.md5sum">gnome-gpg-0.5.0.md5sum</a>        02-Sep-2006 08:58  115
<a href="gnome-gpg-0.5.0.tar.bz2"><img src="http://www.gnome.org/img/24x24/archive.png" alt="[   ]" width="24" height="24"></a> <a href="gnome-gpg-0.5.0.tar.bz2">gnome-gpg-0.5.0.tar.bz2</a>       02-Sep-2006 08:58   68K
<a href="gnome-gpg-0.5.0.tar.gz"><img src="http://www.gnome.org/img/24x24/archive.png" alt="[   ]" width="24" height="24"></a> <a href="gnome-gpg-0.5.0.tar.gz">gnome-gpg-0.5.0.tar.gz</a>        02-Sep-2006 08:58   81K
<hr></pre>

<address>Apache/2.2.3 (Unix) Server at <a href="mailto:ftp-adm@acc.umu.se">ftp.acc.umu.se</a> Port 80</address>
</body></html>
        '''
        listing_url = 'http://ftp.gnome.org/pub/GNOME/sources/gnome-gpg/0.5/'
        responses.add('GET', listing_url, body=content)
        expected_filenames = [
            'LATEST-IS-0.5.0',
            'gnome-gpg-0.5.0.md5sum',
            'gnome-gpg-0.5.0.tar.bz2',
            'gnome-gpg-0.5.0.tar.gz',
            ]
        for filename in expected_filenames:
            responses.add('HEAD', listing_url + filename)
        walker = HTTPWalker(listing_url, logging.getLogger())
        dirnames, filenames = walker.list('/pub/GNOME/sources/gnome-gpg/0.5/')
        self.assertEqual(dirnames, [])
        self.assertEqual(filenames, expected_filenames)

    @responses.activate
    def testSquidFtpListing(self):
        # Test that a Squid FTP listing can be parsed.
        content = '''
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<!-- HTML listing generated by Squid 2.5.STABLE12 -->
<!-- Wed, 06 Sep 2006 11:04:02 GMT -->
<HTML><HEAD><TITLE>
FTP Directory: ftp://ftp.gnome.org/pub/GNOME/sources/gnome-gpg/0.5/
</TITLE>
<STYLE type="text/css"><!--BODY{background-color:#ffffff;font-family:verdana,sans-serif}--></STYLE>
</HEAD><BODY>
<H2>
FTP Directory: <A HREF="/">ftp://ftp.gnome.org</A>/<A HREF="/pub/">pub</A>/<A HREF="/pub/GNOME/">GNOME</A>/<A HREF="/pub/GNOME/sources/">sources</A>/<A HREF="/pub/GNOME/sources/gnome-gpg/">gnome-gpg</A>/<A HREF="/pub/GNOME/sources/gnome-gpg/0.5/">0.5</A>/</H2>
<PRE>
<A HREF="../"><IMG border="0" SRC="http://squid:3128/squid-internal-static/icons/anthony-dirup.gif" ALT="[DIRUP]"></A> <A HREF="../">Parent Directory</A>
<A HREF="LATEST-IS-0.5.0"><IMG border="0" SRC="http://squid:3128/squid-internal-static/icons/anthony-link.gif" ALT="[LINK]"></A> <A HREF="LATEST-IS-0.5.0">LATEST-IS-0.5.0</A>. . . . . . . . . Sep 02 07:07         <A HREF="LATEST-IS-0.5.0;type=a"><IMG border="0" SRC="http://squid:3128/squid-internal-static/icons/anthony-text.gif" ALT="[VIEW]"></A> <A HREF="LATEST-IS-0.5.0;type=i"><IMG border="0" SRC="http://squid:3128/squid-internal-static/icons/anthony-box.gif" ALT="[DOWNLOAD]"></A> -> <A HREF="gnome-gpg-0.5.0.tar.gz">gnome-gpg-0.5.0.tar.gz</A>
<A HREF="gnome-gpg-0.5.0.md5sum"><IMG border="0" SRC="http://squid:3128/squid-internal-static/icons/anthony-unknown.gif" ALT="[FILE]"></A> <A HREF="gnome-gpg-0.5.0.md5sum">gnome-gpg-0.5.0.md5sum</A> . . . . . Sep 02 06:58    115  <A HREF="gnome-gpg-0.5.0.md5sum;type=a"><IMG border="0" SRC="http://squid:3128/squid-internal-static/icons/anthony-text.gif" ALT="[VIEW]"></A> <A HREF="gnome-gpg-0.5.0.md5sum;type=i"><IMG border="0" SRC="http://squid:3128/squid-internal-static/icons/anthony-box.gif" ALT="[DOWNLOAD]"></A>
<A HREF="gnome-gpg-0.5.0.tar.bz2"><IMG border="0" SRC="http://squid:3128/squid-internal-static/icons/anthony-compressed.gif" ALT="[FILE]"></A> <A HREF="gnome-gpg-0.5.0.tar.bz2">gnome-gpg-0.5.0.tar.bz2</A>. . . . . Sep 02 06:58     68K <A HREF="gnome-gpg-0.5.0.tar.bz2;type=i"><IMG border="0" SRC="http://squid:3128/squid-internal-static/icons/anthony-box.gif" ALT="[DOWNLOAD]"></A>
<A HREF="gnome-gpg-0.5.0.tar.gz"><IMG border="0" SRC="http://squid:3128/squid-internal-static/icons/anthony-tar.gif" ALT="[FILE]"></A> <A HREF="gnome-gpg-0.5.0.tar.gz">gnome-gpg-0.5.0.tar.gz</A> . . . . . Sep 02 06:58     81K <A HREF="gnome-gpg-0.5.0.tar.gz;type=i"><IMG border="0" SRC="http://squid:3128/squid-internal-static/icons/anthony-box.gif" ALT="[DOWNLOAD]"></A>
</PRE>
<HR noshade size="1px">
<ADDRESS>
Generated Wed, 06 Sep 2006 11:04:02 GMT by squid (squid/2.5.STABLE12)
</ADDRESS></BODY></HTML>
        '''
        listing_url = 'ftp://ftp.gnome.org/pub/GNOME/sources/gnome-gpg/0.5/'
        responses.add('GET', listing_url, body=content)
        walker = HTTPWalker(listing_url, logging.getLogger())
        dirnames, filenames = walker.list('/pub/GNOME/sources/gnome-gpg/0.5/')
        self.assertEqual(dirnames, [])
        self.assertEqual(filenames, ['LATEST-IS-0.5.0',
                                     'gnome-gpg-0.5.0.md5sum',
                                     'gnome-gpg-0.5.0.tar.bz2',
                                     'gnome-gpg-0.5.0.tar.gz'])

    @responses.activate
    def testNonAsciiListing(self):
        # Test that list() handles non-ASCII output.
        content = b'''
        <html>
          <head>
            <title>Listing</title>
            <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
          </head>
          <body>
          <p>A non-breaking space: \xc2\xa0</p>
          <p><a href="/elsewhere">Somewhere else on the site</a></p>
          <!-- intentionally unclosed anchor below -->
          <p><a href="/foo/file99">Absolute path</p>

          <pre>
          <a href="../">Parent directory</a>
          <a href="subdir1/">subdir 1</a>
          <a href="subdir2/">subdir 2</a>
          <a href="subdir3/">subdir 3</a>
          <a href="file3">file 3</a>
          <a href="file2">file 2</a>
          <a href="file1">file 1</a>
          </pre>
        </html>
        '''
        listing_url = 'http://example.com/foo/'
        responses.add('GET', listing_url, body=content)
        expected_filenames = ['file1', 'file2', 'file3', 'file99']
        for filename in expected_filenames:
            responses.add('HEAD', listing_url + filename)
        walker = HTTPWalker(listing_url, logging.getLogger())
        dirnames, filenames = walker.list('/foo/')
        self.assertEqual(dirnames, ['subdir1/', 'subdir2/', 'subdir3/'])
        self.assertEqual(filenames, expected_filenames)

    @responses.activate
    def testDotPaths(self):
        # Test that paths containing dots are handled correctly.
        #
        # We expect the returned directory and file names to only
        # include those links http://example.com/foo/ even in the
        # presence of "." and ".." path segments.
        content = '''
        <html>
          <head>
            <title>Listing</title>
            <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
          </head>
          <body>
          <pre>
          <a href="../">Up a level</a>
          <a href="/foo/../">The same again</a>
          <a href="file1/../file2">file2</a>
          <a href=".">This directory</a>
          <a href="dir/.">A subdirectory</a>
          </pre>
        </html>
        '''
        listing_url = 'http://example.com/foo/'
        responses.add('GET', listing_url, body=content)
        responses.add('HEAD', listing_url + 'file2')
        walker = HTTPWalker(listing_url, logging.getLogger())
        dirnames, filenames = walker.list('/foo/')
        self.assertEqual(dirnames, ['dir/'])
        self.assertEqual(filenames, ['file2'])

    @responses.activate
    def testNamedAnchors(self):
        # Test that the directory listing parser code handles named anchors.
        # These are <a> tags without an href attribute.
        content = '''
        <html>
          <head>
            <title>Listing</title>
          </head>
          <body>
          <a name="top"></a>
          <pre>
          <a href="file1">file1</a>
          <a href="dir1/">dir1/</a>
          <a href="#top">Go to top</a>
          </pre>
        </html>
        '''
        listing_url = 'http://example.com/foo/'
        responses.add('GET', listing_url, body=content)
        responses.add('HEAD', listing_url + 'file1')
        walker = HTTPWalker(listing_url, logging.getLogger())
        dirnames, filenames = walker.list('/foo/')
        self.assertEqual(dirnames, ['dir1/'])
        self.assertEqual(filenames, ['file1'])

    @responses.activate
    def testGarbageListing(self):
        # Make sure that garbage doesn't trip up the dir lister.
        content = b'\x01\x02\x03\x00\xff\xf2\xablkjsdflkjsfkljfds'
        listing_url = 'http://example.com/foo/'
        responses.add('GET', listing_url, body=content)
        walker = HTTPWalker(listing_url, logging.getLogger())
        dirnames, filenames = walker.list('/foo/')
        self.assertEqual(dirnames, [])
        self.assertEqual(filenames, [])


class HTTPWalker_IsDirectory(TestCase):

    def tearDown(self):
        reset_logging()
        super(HTTPWalker_IsDirectory, self).tearDown()

    def testFtpIsDirectory(self):
        # Test that no requests are made by isDirectory() when walking
        # FTP sites.
        test = self

        class TestHTTPWalker(HTTPWalker):

            def request(self, method, path):
                test.fail('%s was requested with method %s' % (path, method))

        logging.basicConfig(level=logging.CRITICAL)
        walker = TestHTTPWalker('ftp://ftp.gnome.org/', logging.getLogger())

        self.assertEqual(walker.isDirectory('/foo/'), True)
        self.assertEqual(walker.isDirectory('/foo'), False)


class Walker_CombineUrl(TestCase):

    def testConstructsUrl(self):
        """combine_url constructs the URL correctly."""
        self.assertEqual(combine_url("file:///base", "/subdir/", "file"),
                         "file:///subdir/file")
        self.assertEqual(combine_url("file:///base", "/subdir", "file"),
                         "file:///subdir/file")
