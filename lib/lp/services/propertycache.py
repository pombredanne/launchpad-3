# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Cached properties for situations where a property is computed once and
then returned each time it is asked for.

    >>> from itertools import count
    >>> counter = count(1)

    >>> class Foo:
    ...     @cachedproperty
    ...     def bar(self):
    ...         return next(counter)

    >>> foo = Foo()

The property cache can be obtained via adaption.

    >>> cache = IPropertyCache(foo)

Initially it is empty. Caches can be iterated over to reveal the names of the
values cached within.

    >>> list(cache)
    []

After accessing a cached property the cache is no longer empty.

    >>> foo.bar
    1
    >>> list(cache)
    ['bar']
    >>> cache.bar
    1

Attempting to access an unknown name from the cache is an error.

    >>> cache.baz
    Traceback (most recent call last):
    ...
    AttributeError: 'DefaultPropertyCache' object has no attribute 'baz'

Values in the cache can be deleted.

    >>> del cache.bar
    >>> list(cache)
    []

Accessing the cached property causes its populate function to be called again.

    >>> foo.bar
    2
    >>> cache.bar
    2

Values in the cache can be set and updated.

    >>> cache.bar = 456
    >>> foo.bar
    456

Caches respond to membership tests.

    >>> "bar" in cache
    True

    >>> del cache.bar

    >>> "bar" in cache
    False

It is safe to delete names from the cache even if there is no value cached.

    >>> del cache.bar
    >>> del cache.bar

A cache manager can be used to empty the cache.

    >>> manager = IPropertyCacheManager(cache)

    >>> cache.bar = 123
    >>> cache.baz = 456
    >>> sorted(cache)
    ['bar', 'baz']

    >>> manager.clear()
    >>> list(cache)
    []

A cache manager can be obtained by adaption from non-cache objects too.

    >>> manager = IPropertyCacheManager(foo)
    >>> manager.cache is cache
    True

"""

__metaclass__ = type
__all__ = [
    'IPropertyCache',
    'IPropertyCacheManager',
    'cachedproperty',
    ]

from functools import partial

from zope.component import adapter, adapts
from zope.interface import Interface, implementer, implements
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


class DefaultPropertyCache:
    """A simple cache."""

    implements(IPropertyCache)

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

    A cached property can be declared with or without an explicit name. If not
    provided it will be derived from the decorated object. This name is the
    name under which values will be cached.

        >>> class Foo:
        ...     @cachedproperty("a_in_cache")
        ...     def a(self):
        ...         return 1234
        ...     @cachedproperty
        ...     def b(self):
        ...         return 5678

        >>> foo = Foo()

    `a` was declared with an explicit name of "a_in_cache" so it is known as
    "a_in_cache" in the cache.

        >>> isinstance(Foo.a, CachedProperty)
        True
        >>> Foo.a.name
        'a_in_cache'
        >>> Foo.a.populate
        <function a at 0x...>

        >>> foo.a
        1234
        >>> IPropertyCache(foo).a_in_cache
        1234

    `b` was defined without an explicit name so it is known as "b" in the
    cache too.

        >>> isinstance(Foo.b, CachedProperty)
        True
        >>> Foo.b.name
        'b'
        >>> Foo.b.populate
        <function b at 0x...>

        >>> foo.b
        5678
        >>> IPropertyCache(foo).b
        5678

    """
    if isinstance(name_or_function, basestring):
        name = name_or_function
        return partial(CachedProperty, name=name)
    else:
        name = name_or_function.__name__
        populate = name_or_function
        return CachedProperty(name=name, populate=populate)
