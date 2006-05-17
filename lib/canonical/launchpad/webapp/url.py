# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functions for working with URLs."""

__metaclass__ = type

from  urlparse import (
    urljoin, urlparse as original_urlparse, urlsplit as original_urlsplit)


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
