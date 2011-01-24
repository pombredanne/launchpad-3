# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'StormBase',
    ]

from lazr.restful.interfaces import IRepresentationCache
from storm.base import Storm
from zope.component import getUtility

from lp.services.propertycache import clear_property_cache


class StormBase(Storm):
    """A safe version of storm.base.Storm to use in launchpad.

    This class adds storm cache management functions to base.Storm.
    """

    # XXX: jcsackett 2011-01-20 bug=622648: Much as with the SQLBase,
    # this is not tested.
    def __storm_flushed__(self):
        """Invalidate the web service cache."""
        cache = getUtility(IRepresentationCache)
        cache.delete(self)

    def __storm_invalidated__(self):
        """Flush cached properties."""
        clear_property_cache(self)
