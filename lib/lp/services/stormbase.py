# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'StormBase',
    ]

from lazr.restful.interfaces import IRepresentationCache
from storm.base import Storm

from lp.services.propertycache import clear_property_cache

class StormBase(Storm):
    """A cache "safe" version of storm.base.Storm
    
    This class adds storm cache management functions to base.Storm.
    """

    def __storm_flushed__(self):
        """Invalidate the web service cache."""
        cache = getUtility(IRepresentationCache)
        cache.delete(self)

    def __storm_invalidated__(self):
        """Flush cached properties."""
        # TODO: Fix this?
        # XXX: jcsackett 2011-01-20 bug=622648: Much as with the SQLBase,
        # this is not tested.
        clear_property_cache(self)
