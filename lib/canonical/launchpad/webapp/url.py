# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functions for working with URLs."""

__metaclass__ = type
__all__ = ['Url', 'urlappend', 'urlparse', 'urlsplit']

from  urlparse import (
    urljoin, urlparse as original_urlparse, urlsplit as original_urlsplit)


class Url:
    """A class for url operations."""

    def __init__(self, url, query=None):
        self.url = url
        if query is not None:
            self.url += '?%s' % query
        urlparts = iter(urlparse(self.url))
        self.addressingscheme = urlparts.next()
        self.networklocation = urlparts.next()
        if ':' in self.networklocation:
            self.hostname, port = self.networklocation.split(':', 1)
            self.port = int(port)
        else:
            self.hostname = self.networklocation
            self.port = None
        self.path = urlparts.next()
        if self.path.endswith('/'):
            self.pathslash = self.path
            self.pathnoslash = self.path[:-1]
        else:
            self.pathslash = self.path + '/'
            self.pathnoslash = self.path
        self.parameters = urlparts.next()
        self.query = urlparts.next()
        self.fragmentids = urlparts.next()

    @property
    def protohost(self):
        """Returns the addressing scheme and network location."""
        return '%s://%s' % (self.addressingscheme, self.networklocation)

    def __repr__(self):
        return '<Url %s>' % self.url

    def is_inside(self, otherurl):
        return (self.protohost == otherurl.protohost and
                self.pathslash.startswith(otherurl.pathslash))

    def __eq__(self, otherurl):
        return (otherurl.protohost == self.protohost and
                otherurl.pathslash == self.pathslash and
                otherurl.query == self.query)

    def __ne__(self, otherurl):
        return not self.__eq__(self, otherurl)


def urlappend(baseurl, path):
    """Append the given path to baseurl.

    The path must not start with a slash, but a slash is added to baseurl
    (before appending the path), in case it doesn't end with a slash.

    >>> urlappend('http://foo.bar', 'spam/eggs')
    'http://foo.bar/spam/eggs'
    >>> urlappend('http://localhost:11375/foo', 'bar/baz')
    'http://localhost:11375/foo/bar/baz'
    """
    assert not path.startswith('/')
    if not baseurl.endswith('/'):
        baseurl += '/'
    return urljoin(baseurl, path)


def urlparse(url, scheme='', allow_fragments=True):
    """Convert url to a str object and call the original urlparse function.

    The url parameter should contain ASCII characters only. This
    function ensures that the original urlparse is called always with a
    str object, and never unicode.

        >>> urlparse(u'http://foo.com/bar')
        ('http', 'foo.com', '/bar', '', '', '')

        >>> urlparse('http://foo.com/bar')
        ('http', 'foo.com', '/bar', '', '', '')

        >>> original_urlparse('http://foo.com/bar')
        ('http', 'foo.com', '/bar', '', '', '')

    This is needed since external libraries might expect that the original
    urlparse returns a str object if it is given a str object. However,
    that might not be the case, since urlparse has a cache, and treats
    unicode and str as equal. (http://sourceforge.net/tracker/index.php?
    func=detail&aid=1313119&group_id=5470&atid=105470)
    """
    return original_urlparse(
        url.encode('ascii'), scheme=scheme, allow_fragments=allow_fragments)


def urlsplit(url, scheme='', allow_fragments=True):
    """Convert url to a str object and call the original urlsplit function.

    The url parameter should contain ASCII characters only. This
    function ensures that the original urlsplit is called always with a
    str object, and never unicode.

        >>> urlsplit(u'http://foo.com/baz')
        ('http', 'foo.com', '/baz', '', '')

        >>> urlsplit('http://foo.com/baz')
        ('http', 'foo.com', '/baz', '', '')

        >>> original_urlsplit('http://foo.com/baz')
        ('http', 'foo.com', '/baz', '', '')

    """
    return original_urlsplit(
        url.encode('ascii'), scheme=scheme, allow_fragments=allow_fragments)
