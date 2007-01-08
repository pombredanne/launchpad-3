# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from textwrap import dedent

from canonical.launchpad import _
from canonical.launchpad.validators import LaunchpadValidationError

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
    # note that URL checking is also done inside the database, in
    # trusted.sql, the valid_absolute_url function, and that code uses
    # stdlib urlparse, not our customized version.
    if not (scheme and netloc):
        return False
    return True

def valid_builder_url(url):
    """validate a url for a builder.

    Builder urls must be http://host/ or http://host:port/
    (with or without the trailing slash) only.

    >>> valid_builder_url('http://example.com:54321/')
    True
    >>> valid_builder_url('http://example.com/foo')
    False
    >>> valid_builder_url('ftp://foo.com/')
    False
    """
    # Have to import urlparse locally since imports from helpers.py
    # causes this module to be imported, and we can't import stuff from
    # webapp at that point, since webapp imports stuff from helpers.py
    # as well.
    from canonical.launchpad.webapp.url import urlparse
    (scheme, netloc, path, params, query, fragment) = urlparse(url)
    if scheme != 'http':
        return False
    if params or query or fragment:
        return False
    if path and path != '/':
        return False
    return True

def builder_url_validator(url):
    """Return True if the url is valid, or raise a LaunchpadValidationError"""
    if not valid_builder_url(url):
        raise LaunchpadValidationError(_(dedent("""
            Invalid builder url '%s'. Builder urls must be
            http://host/ or http://host:port/ only.
            """)), url)
    return True
