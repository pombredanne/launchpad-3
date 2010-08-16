# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Cached properties for situations where a property is computed once and
then returned each time it is asked for.

The clear_cachedproperties function can be used to wipe the cache of properties
from an instance.
"""

__metaclass__ = type

__all__ = [
    'cache_property',
    'cachedproperty',
    'clear_cachedproperties',
    'clear_property',
    ]

from zope.security.proxy import removeSecurityProxy

from canonical.lazr.utils import safe_hasattr

# XXX: JonathanLange 2010-01-11 bug=505731: Move this to lp.services.

def cachedproperty(attrname_or_fn):
    """A decorator for methods that makes them properties with their return
    value cached.

    The value is cached on the instance, using the attribute name provided.

    If you don't provide a name, the mangled name of the property is used.

    cachedproperty is not threadsafe - it should not be used on objects which
    are shared across threads / external locking should be used on those
    objects.

    >>> class CachedPropertyTest(object):
    ...
    ...     @cachedproperty('_foo_cache')
    ...     def foo(self):
    ...         print 'foo computed'
    ...         return 23
    ...
    ...     @cachedproperty
    ...     def bar(self):
    ...         print 'bar computed'
    ...         return 69

    >>> cpt = CachedPropertyTest()
    >>> getattr(cpt, '_foo_cache', None) is None
    True
    >>> cpt.foo
    foo computed
    23
    >>> cpt.foo
    23
    >>> cpt._foo_cache
    23
    >>> cpt.bar
    bar computed
    69
    >>> cpt._bar_cached_value
    69
    
    Cached properties are listed on instances.
    >>> sorted(cpt._cached_properties)
    ['_bar_cached_value', '_foo_cache']

    """
    if isinstance(attrname_or_fn, basestring):
        attrname = attrname_or_fn
        return CachedPropertyForAttr(attrname)
    else:
        fn = attrname_or_fn
        attrname = '_%s_cached_value' % fn.__name__
        return CachedProperty(attrname, fn)

def cache_property(instance, attrname, value):
    """Cache value on instance as attrname.
    
    instance._cached_properties is updated with attrname.

    >>> class CachedPropertyTest(object):
    ...
    ...     @cachedproperty('_foo_cache')
    ...     def foo(self):
    ...         return 23
    ...
    >>> instance = CachedPropertyTest()
    >>> cache_property(instance, '_foo_cache', 42)
    >>> instance.foo
    42
    >>> instance._cached_properties
    ['_foo_cache']
    Caching a new value does not duplicate the cache keys.
    >>> cache_property(instance, '_foo_cache', 84)
    >>> instance._cached_properties
    ['_foo_cache']
    And does update the cached value.
    >>> instance.foo
    84
    """
    instance = removeSecurityProxy(instance)
    clear_property(instance, attrname)
    setattr(instance, attrname, value)
    cached_properties = getattr(instance, '_cached_properties', [])
    cached_properties.append(attrname)
    instance._cached_properties = cached_properties


def clear_property(instance, attrname):
    """Remove a cached attribute from instance.

    The attribute name is removed from instance._cached_properties.

    If the property is not cached, nothing happens.

    :seealso clear_cachedproperties: For clearing all cached items at once.

    >>> class CachedPropertyTest(object):
    ...
    ...     @cachedproperty('_foo_cache')
    ...     def foo(self):
    ...         return 23
    ...
    >>> instance = CachedPropertyTest()
    >>> instance.foo
    23
    >>> clear_property(instance, '_foo_cache')
    >>> instance._cached_properties
    []
    >>> is_cached(instance, '_foo_cache')
    False
    >>> clear_property(instance, '_foo_cache')
    """
    instance = removeSecurityProxy(instance)
    if not is_cached(instance, attrname):
        return
    delattr(instance, attrname)
    instance._cached_properties.remove(attrname)


def clear_cachedproperties(instance):
    """Clear cached properties from an object.
    
    >>> class CachedPropertyTest(object):
    ...
    ...     @cachedproperty('_foo_cache')
    ...     def foo(self):
    ...         return 23
    ...
    >>> instance = CachedPropertyTest()
    >>> instance.foo
    23
    >>> instance._cached_properties
    ['_foo_cache']
    >>> clear_cachedproperties(instance)
    >>> instance._cached_properties
    []
    >>> hasattr(instance, '_foo_cache')
    False
    """
    instance = removeSecurityProxy(instance)
    cached_properties = getattr(instance, '_cached_properties', [])
    for property_name in cached_properties:
        delattr(instance, property_name)
    instance._cached_properties = []


def is_cached(instance, attrname):
    """Return True if attrname is cached on instance.

    >>> class CachedPropertyTest(object):
    ...
    ...     @cachedproperty('_foo_cache')
    ...     def foo(self):
    ...         return 23
    ...
    >>> instance = CachedPropertyTest()
    >>> instance.foo
    23
    >>> is_cached(instance, '_foo_cache')
    True
    >>> is_cached(instance, '_var_cache')
    False
    """
    instance = removeSecurityProxy(instance)
    return safe_hasattr(instance, attrname)


class CachedPropertyForAttr:
    """Curry a decorator to provide arguments to the CachedProperty."""

    def __init__(self, attrname):
        self.attrname = attrname

    def __call__(self, fn):
        return CachedProperty(self.attrname, fn)


class CachedProperty:

    # Used to detect not-yet-cached properties.
    sentinel = object()

    def __init__(self, attrname, fn):
        self.fn = fn
        self.attrname = attrname

    def __get__(self, inst, cls=None):
        if inst is None:
            return self
        cachedresult = getattr(inst, self.attrname, CachedProperty.sentinel)
        if cachedresult is CachedProperty.sentinel:
            result = self.fn(inst)
            cache_property(inst, self.attrname, result)
            return result
        else:
            return cachedresult


if __name__ == '__main__':
    import doctest
    doctest.testmod()
