# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Publisher of objects as web pages.

XXX: Much stuff from canonical.publication needs to move here.
"""

__metaclass__ = type
__all__ = ['canonical_url']

from zope.interface import implements

from canonical.launchpad.interfaces import ICanonicalUrlData, NoCanonicalUrl

# Import the launchpad.conf configuration object.
from canonical.config import config

class LaunchpadRootUrlData:
    """ICanonicalUrlData for the ILaunchpadRoot object."""

    implements(ICanonicalUrlData)

    def __init__(self, context):
        self.context = context

    path = ''

    inside = None


def canonical_url(obj, request=None):
    """Return the canonical URL string for the object.

    If the request is provided, then protocol, host and port are taken
    from the request.  If a request is not provided, the protocol, host
    and port are taken from the root_url given in launchpad.conf.

    Raises NoCanonicalUrl if a canonical url is not available.
    """
    urldata = ICanonicalUrlData(obj, None)
    if urldata is None:
        raise NoCanonicalUrl(obj, obj)
    urlparts = [urldata.path]
    while urldata.inside is not None:
        current_object = urldata.inside
        urldata = ICanonicalUrlData(current_object, None)
        if urldata is None:
            raise NoCanonicalUrl(obj, current_object)
        if urldata.path:
            urlparts.append(urldata.path)
    if request is None:
        root_url = config.launchpad.root_url
    else:
        root_url = request.getApplicationURL() + '/'
    return root_url + '/'.join(reversed(urlparts))

