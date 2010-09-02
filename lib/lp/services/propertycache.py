# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Cached properties for situations where a property is computed once and then
returned each time it is asked for.

See `doc/propertycache.txt` for documentation.
"""

__metaclass__ = type
__all__ = [
    'IPropertyCache',
    'IPropertyCacheManager',
    'cachedproperty',
    ]

from functools import partial

from zope.component import (
    adapter,
    adapts,
    getGlobalSiteManager,
    )
from zope.interface import (
    implementer,
    implements,
    Interface,
    )
from zope.schema import Object
from zope.security.proxy import removeSecurityProxy


class IPropertyCache(Interface):

    def __getattr__(name):
        """Return the cached value corresponding to `name`.

        Raise `AttributeError` if no value is cached.
        """

    def __setattr__(name, value):
        """Cache `value` for `name`."""

    def __delattr__(name):
        """Delete value for `name`.

        If no value is cached for `name` this is a no-op.
        """

    def __contains__(name):
        """Whether or not `name` is cached."""

    def __iter__():
        """Iterate over the cached names."""


class IPropertyCacheManager(Interface):

    cache = Object(IPropertyCache)

    def clear():
        """Empty the cache."""


# Register adapters with the global site manager so that they work even when
# ZCML has not been executed.
registerAdapter = getGlobalSiteManager().registerAdapter


class DefaultPropertyCache:
    """A simple cache."""

    implements(IPropertyCache)

    # __getattr__ -- well, __getattribute__ -- and __setattr__ are inherited
    # from object.

    def __delattr__(self, name):
        """See `IPropertyCache`."""
        self.__dict__.pop(name, None)

    def __contains__(self, name):
        """See `IPropertyCache`."""
        return name in self.__dict__

    def __iter__(self):
        """See `IPropertyCache`."""
        return iter(self.__dict__)


@adapter(Interface)
@implementer(IPropertyCache)
def get_default_cache(target):
    """Adapter to obtain a `DefaultPropertyCache` for any object."""
    naked_target = removeSecurityProxy(target)
    try:
        return naked_target._property_cache
    except AttributeError:
        naked_target._property_cache = DefaultPropertyCache()
        return naked_target._property_cache

registerAdapter(get_default_cache)


class PropertyCacheManager:
    """A simple `IPropertyCacheManager`.

    Should work for any `IPropertyCache` instance.
    """

    implements(IPropertyCacheManager)
    adapts(Interface)

    def __init__(self, target):
        self.cache = IPropertyCache(target)

    def clear(self):
        """See `IPropertyCacheManager`."""
        for name in list(self.cache):
            delattr(self.cache, name)

registerAdapter(PropertyCacheManager)


class DefaultPropertyCacheManager:
    """A `IPropertyCacheManager` specifically for `DefaultPropertyCache`.

    The implementation of `clear` is more efficient.
    """

    implements(IPropertyCacheManager)
    adapts(DefaultPropertyCache)

    def __init__(self, cache):
        self.cache = cache

    def clear(self):
        self.cache.__dict__.clear()

registerAdapter(DefaultPropertyCacheManager)


class CachedProperty:
    """Cached property descriptor.

    Provides only the `__get__` part of the descriptor protocol. Setting and
    clearing cached values should be done explicitly via `IPropertyCache`
    instances.
    """

    def __init__(self, populate, name):
        """Initialize this instance.

        `populate` is a callable responsible for providing the value when this
        property has not yet been cached.

        `name` is the name under which this property will cache itself.
        """
        self.populate = populate
        self.name = name

    def __get__(self, instance, cls):
        if instance is None:
            return self
        cache = IPropertyCache(instance)
        try:
            return getattr(cache, self.name)
        except AttributeError:
            value = self.populate(instance)
            setattr(cache, self.name, value)
            return value


def cachedproperty(name_or_function):
    """Decorator to create a cached property.

    See `doc/propertycache.txt` for usage.
    """
    if isinstance(name_or_function, basestring):
        name = name_or_function
        return partial(CachedProperty, name=name)
    else:
        name = name_or_function.__name__
        populate = name_or_function
        return CachedProperty(name=name, populate=populate)


# XXX: GavinPanella 2010-09-02 bug=628762: There are some weird adaption
# failures when running the full test suite, so this is a temporary non-Zope
# (almost) workaround.

_IPropertyCache = IPropertyCache
_IPropertyCacheManager = IPropertyCacheManager

def IPropertyCache(target):
    """Return the `IPropertyCache` for `target`.

    Note: this is a work-around, see bug 628762.
    """
    if _IPropertyCache.providedBy(target):
        return target
    else:
        return get_default_cache(target)

def IPropertyCacheManager(target):
    """Return the `IPropertyCacheManager` for `target`.

    Note: this is a work-around, see bug 628762.
    """
    if _IPropertyCache.providedBy(target):
        cache = target
    else:
        cache = IPropertyCache(target)

    if isinstance(cache, DefaultPropertyCache):
        return DefaultPropertyCacheManager(cache)
    else:
        return PropertyCacheManager(cache)
