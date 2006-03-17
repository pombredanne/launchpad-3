# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from urlparse import urlparse


def valid_absolute_url(name):
    """validate an absolute URL.

    It looks like this function has been deprecated by
    canonical.launchpad.interfaces.validation.

    We define this as something that can be parsed into a URL that has both
    a protocol and a network address.

    >>> valid_absolute_url('sftp://chinstrap.ubuntu.com/foo/bar')
    True
    >>> valid_absolute_url('http://www.example.com')
    True
    >>> valid_absolute_url('whatever://example.com/blah')
    False
    """
    (scheme, netloc, path, params, query, fragment) = urlparse(name)
    if scheme == 'sftp':
        return True
    if not (scheme and netloc):
        return False
    return True

