# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type


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
    # Have to import urlparse locally since imports from helpers.py
    # causes this module to be imported, and we can't import stuff from
    # webapp at that point, since webapp imports stuff from helpers.py
    # as well.
    from canonical.launchpad.webapp.url import urlparse
    (scheme, netloc, path, params, query, fragment) = urlparse(name)
    if scheme == 'sftp':
        return True
    if not (scheme and netloc):
        return False
    return True

