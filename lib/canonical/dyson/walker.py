"""HTTP and FTP walker.

This module implements classes to walk HTTP and FTP sites to find files.
"""

import os
import base64
import ftplib
import httplib
import logging

from urllib import unquote_plus
from urlparse import urlsplit, urljoin
from BeautifulSoup import BeautifulSoup

from hct.util import log
from hct.util.path import as_dir, subdir, under_only


class WalkerError(Exception): pass
class FTPWalkerError(WalkerError): pass
class HTTPWalkerError(WalkerError): pass


class WalkerBase(object):
    """Base class for URL walkers.

    This class is a base class for those wishing to implement protocol
    specific walkers.  Walkers behave much like the os.walk() function,
    but taking a URL and working remotely.

    A typical usage would be:
        for (dirpath, dirnames, filenames) in ProtWalker(url):
            ...

    Sub-classes are required to implement the open(), list() and close()
    methods.
    """

    # URL schemes the walker supports, the first is the default
    URL_SCHEMES = ["ftp", "http", "https"]

    # Whether to ignore or parse fragments in the URL
    FRAGMENTS = False

    def __init__(self, base, log_parent=None):
        self.log = log.get_logger(type(self).__name__, log_parent)
        self.base = base

        (scheme, netloc, path, query, fragment) \
                 = urlsplit(base, self.URL_SCHEMES[0], self.FRAGMENTS)
        if scheme not in self.URL_SCHEMES:
            raise WalkerError, "Can't handle %s scheme" % scheme
        self.scheme = scheme
        self.full_netloc = netloc

        try:
            (user_passwd, host) = netloc.split("@", 1)
            self.host = unquote_plus(host)

            try:
                (user, passwd) = user_passwd.split(":", 1)
                self.user = unquote_plus(user)
                self.passwd = unquote_plus(passwd)
            except ValueError:
                self.user = unquote_plus(user_passwd)
                self.passwd = None
        except ValueError:
            self.host = unquote_plus(netloc)
            self.user = None
            self.passwd = None

        self.query = query
        self.fragment = fragment

        self.path = as_dir(path)

    def walk(self):
        """Walk through the URL.

        Yields (dirpath, dirnames, filenames) for each path under the base;
        dirnames can be modified as with os.walk.
        """
        self.open()

        subdirs = [self.path]
        while len(subdirs):
            subdir = subdirs.pop(0)

            (dirnames, filenames) = self.list(subdir)
            yield (subdir, dirnames, filenames)

            for dirname in dirnames:
                subdirs.append(urljoin(subdir, as_dir(dirname)))

        self.close()

    __iter__ = walk

    def open(self):
        """Open the FTP connection.

        Must be implemented by sub-classes.
        """
        raise NotImplementedError

    def close(self):
        """Close the FTP connection.

        Must be implemented by sub-classes.
        """
        raise NotImplementedError

    def list(self, dir):
        """Return listing of directory.

        Must be implemented by sub-classes to return two lists, one of
        directory names and one of file names; both underneath the directory
        given.
        """
        raise NotImplementedError


class FTPWalker(WalkerBase):
    """FTP URL scheme walker.

    This class implements a walker for the FTP URL scheme; it's fairly
    simple and just walks the FTP tree beneath the URL given using CWD
    and LIST.
    """

    # URL schemes the walker supports, the first is the default
    URL_SCHEMES = ["ftp"]

    # Whether to ignore or parse fragments in the URL
    FRAGMENTS = False

    def __init__(self, *args, **kwds):
        super(FTPWalker, self).__init__(*args, **kwds)

        if self.user is None:
            self.user = "anonymous"
        if self.passwd is None:
            self.passwd = ""

    def open(self):
        """Open the FTP connection."""
        self.log.info("Connecting to %s", self.host)
        self.ftp = ftplib.FTP()
        self.ftp.connect(self.host)

        if self.user is not None:
            self.log.info("Logging in as %s", self.user)
            self.ftp.login(self.user, self.passwd)

        pwd = self.ftp.pwd()
        self.log.info("Connected, working directory is %s", pwd)

    def close(self):
        """Close the FTP connection."""
        self.log.info("Closing connection")
        self.ftp.quit()
        del self.ftp

    def list(self, subdir):
        """Change directory and return listing.

        Returns two lists, one of directory names and one of file names
        under the path.
        """
        self.log.info("Changing directory to %s", subdir)
        self.ftp.cwd(subdir)

        listing = []
        self.log.info("Listing remote directory")
        self.ftp.retrlines("LIST", listing.append)

        dirnames = []
        filenames = []
        for line in listing:
            # XXX: Assume UNIX listings for now --keybuk 24jun05
            words = line.split(None, 8)
            if len(words) < 6:
                self.log.debug("Ignoring short line: %s", line)
                continue

            # Chomp symlinks
            filename = words[-1].lstrip()
            i = filename.find(" -> ")
            if i >= 0:
                filename = filename[:i]

            mode = words[0]
            if mode.startswith("d"):
                if filename not in (".", ".."):
                    dirnames.append(filename)
            elif mode.startswith("-") or mode.startswith("l"):
                filenames.append(filename)

        return (dirnames, filenames)


class HTTPWalker(WalkerBase):
    """HTTP URL scheme walker.

    This class implements a walker for the HTTP and HTTPS URL schemes.
    It works by assuming any URL ending with a / is a directory, and
    every other URL a file.  URLs are tested using HEAD to see whether
    they cause a redirect to one ending with a /.

    HTML Directory pages are parsed to find all links within them that
    lead to deeper URLs; this way it isn't tied to the Apache directory
    listing format and can actually walk arbitrary trees.
    """

    # URL schemes the walker supports, the first is the default
    URL_SCHEMES = ["http", "https"]

    # Whether to ignore or parse fragments in the URL
    FRAGMENTS = True

    def open(self):
        """Open the HTTP connection."""
        self.log.info("Connecting to %s", self.host)
        if self.scheme == "https":
            self.http = httplib.HTTPSConnection(self.host)
        else:
            self.http = httplib.HTTPConnection(self.host)

        self.http.connect()
        self.log.info("Connected")

    def close(self):
        """Close the FTP connection."""
        self.log.info("Closing connection")
        self.http.close()
        del self.http

    def request(self, method, path):
        """Make an HTTP request.

        Returns the HTTPResponse object.
        """
        tries = 2
        while tries > 0:
            self.http.putrequest(method, path)
            if self.user is not None:
                auth = base64.encodestring("%s:%s" % (self.user, self.passwd))
                self.http.putheader("Authorization", "Basic %s" % auth)
            self.http.endheaders()

            try:
                return self.http.getresponse()
            except httplib.BadStatusLine:
                self.log.error("Bad status line (did the server go away?)")

                self.open()
                tries -= 1
                if not tries:
                    raise

    def isDirectory(self, path):
        """Return whether the path is a directory.

        Assumes any path ending in a slash is a directory, and any that
        redirects to a location ending in a slash is also a directory.
        """
        if path.endswith("/"):
            return True

        self.log.info("Checking %s" % path)
        response = self.request("HEAD", path)
        response.close()
        if response.status != 301:
            return False

        url = response.getheader("location")
        (scheme, netloc, redirect_path, query, fragment) \
                 = urlsplit(url, self.scheme, self.FRAGMENTS)

        if len(scheme) and scheme != self.scheme:
            return False
        elif len(netloc) and netloc != self.full_netloc:
            return False
        elif redirect_path != as_dir(path):
            return False
        else:
            return True

    def list(self, dirname):
        """Download the HTML index at subdir and scrape for URLs.

        Returns a list of directory names (links ending with /, or
        that result in redirects to themselves ending in /) and
        filenames (everything else) that reside underneath the path.
        """
        self.log.info("Getting %s" % dirname)
        response = self.request("GET", dirname)
        try:
            soup = BeautifulSoup()
            soup.feed(response.read())
        finally:
            response.close()

        dirnames = []
        filenames = []
        for anchor in soup("a"):
            url = urljoin(self.path, anchor.get("href"))
            (scheme, netloc, path, query, fragment) \
                     = urlsplit(url, self.scheme, self.FRAGMENTS)

            # XXX: Only follow URLs that are directly underneath the one
            # we were looking at.  This avoids accidentally walking the
            # entire world-wide-web, but does mean that "download.html"
            # URLs won't work.  Better suggestions accepted. --keybuk 27jun05
            if len(scheme) and scheme != self.scheme:
                continue
            elif len(netloc) and netloc != self.full_netloc:
                continue
            elif not under_only(self.path, path):
                continue

            filename = subdir(self.path, path)
            if self.isDirectory(path):
                dirnames.append(as_dir(filename))
            else:
                filenames.append(filename)

        return (dirnames, filenames)


def walk(url):
    """Return a walker for the URL given."""
    (scheme, netloc, path, query, fragment) = urlsplit(url, "file")
    if scheme in ["ftp"]:
        return FTPWalker(url)
    elif scheme in ["http", "https"]:
        return HTTPWalker(url)
    elif scheme in ["file"]:
        return os.walk(url)
    else:
        raise WalkerError, "Unknown scheme: %s" % scheme

def combine_url(base, subdir, filename):
    """Combine a URL from the three parts returned by walk()."""
    subdir_url = urljoin(base, subdir)
    return urljoin(subdir_url, filename)
