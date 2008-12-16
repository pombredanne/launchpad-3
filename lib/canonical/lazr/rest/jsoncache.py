# Copyright 2008 Canonical Ltd.  All rights reserved.
#
"""A class for storing resources where they can be seen by a template."""

__metaclass__ = type

__all__ = [
    'JSONRequestCache'
    ]

from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.lazr.interfaces.rest import (
    IJSONRequestCache, LAZR_WEBSERVICE_NS)

from zope.component import getUtility
from zope.interface import implements

class JSONRequestCache:

    implements(IJSONRequestCache)

    LAZR_OBJECT_JSON_CACHE = ("%s.object-json-cache"
                              % LAZR_WEBSERVICE_NS)
    LAZR_LINK_JSON_CACHE = ("%s.link-json-cache"
                            % LAZR_WEBSERVICE_NS)

    def __init__(self, request):
        """Initialize with a request."""
        self.objects = request.annotations.setdefault(
            self.LAZR_OBJECT_JSON_CACHE, {})

        default = {}
        user = getUtility(ILaunchBag).user
        if user is not None:
            default['me'] = user
        self.links = request.annotations.setdefault(
            self.LAZR_LINK_JSON_CACHE, default)
