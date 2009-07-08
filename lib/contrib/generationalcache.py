"""GenerationalCache implementation from the Storm trunk.

XXX stub bug=392016: When we update to Storm 0.15 or later, this copy
of the implementation should be removed and use the one in storm.cache
instead.
"""

class GenerationalCache(object):
    """Generational replacement for Storm's LRU cache.

    This cache approximates LRU without keeping exact track.  Instead,
    it keeps a primary dict of "recently used" objects plus a similar,
    secondary dict of objects used in a previous timeframe.

    When the "most recently used" dict reaches its size limit, it is
    demoted to secondary dict and a fresh primary dict is set up.  The
    previous secondary dict is evicted in its entirety.

    Use this to replace the LRU cache for sizes where LRU tracking
    overhead becomes too large (e.g. 100,000 objects) or the
    `StupidCache` when it eats up too much memory.
    """

    def __init__(self, size=1000):
        """Create a generational cache with the given size limit.

        The size limit applies not to the overall cache, but to the
        primary one only.  When this reaches the size limit, the real
        number of cached objects will be somewhere between size and
        2*size depending on how much overlap there is between the
        primary and secondary caches.
        """
        self._size = size
        self._new_cache = {}
        self._old_cache = {}

    def clear(self):
        """See `storm.store.Cache.clear`.

        Clears both the primary and the secondary caches.
        """
        self._new_cache.clear()
        self._old_cache.clear()

    def _bump_generation(self):
        """Start a new generation of the cache.

        The primary generation becomes the secondary one, and the old
        secondary generation is evicted.

        Kids at home: do not try this for yourself.  We are trained
        professionals working with specially-bred generations.  This
        would not be an appropriate way of treating older generations
        of actual people.
        """
        self._old_cache, self._new_cache = self._new_cache, self._old_cache
        self._new_cache.clear()

    def add(self, obj_info):
        """See `storm.store.Cache.add`."""
        if self._size != 0 and obj_info not in self._new_cache:
            if len(self._new_cache) >= self._size:
                self._bump_generation()
            self._new_cache[obj_info] = obj_info.get_obj()

    def remove(self, obj_info):
        """See `storm.store.Cache.remove`."""
        in_new_cache = self._new_cache.pop(obj_info, None) is not None
        in_old_cache = self._old_cache.pop(obj_info, None) is not None
        return in_new_cache or in_old_cache

    def set_size(self, size):
        """See `storm.store.Cache.set_size`.

        After calling this, the cache may still contain more than `size`
        objects, but no more than twice that number.
        """
        self._size = size
        cache = itertools.islice(itertools.chain(self._new_cache.iteritems(),
                                                 self._old_cache.iteritems()),
                                 0, size)
        self._new_cache = dict(cache)
        self._old_cache.clear()

    def get_cached(self):
        """See `storm.store.Cache.get_cached`.

        The result is a loosely-ordered list.  Any object in the primary
        generation comes before any object that is only in the secondary
        generation, but objects within a generation are not ordered and
        there is no indication of the boundary between the two.

        Objects that are in both the primary and the secondary
        generation are listed only as part of the primary generation.
        """
        cached = self._new_cache.copy()
        cached.update(self._old_cache)
        return list(cached)
