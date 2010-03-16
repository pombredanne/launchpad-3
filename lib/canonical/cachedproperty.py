# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Cached properties for situations where a property is computed once and
then returned each time it is asked for.
"""

__metaclass__ = type

# XXX: JonathanLange 2010-01-11 bug=505731: Move this to lp.services.

def cachedproperty(attrname_or_fn):
    """A decorator for methods that makes them properties with their return
    value cached.

    The value is cached on the instance, using the attribute name provided.

    If you don't provide a name, the mangled name of the property is used.

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

    """
    if isinstance(attrname_or_fn, basestring):
        attrname = attrname_or_fn
        return CachedPropertyForAttr(attrname)
    else:
        fn = attrname_or_fn
        attrname = '_%s_cached_value' % fn.__name__
        return CachedProperty(attrname, fn)


class CachedPropertyForAttr:

    def __init__(self, attrname):
        self.attrname = attrname

    def __call__(self, fn):
        return CachedProperty(self.attrname, fn)


class CachedProperty:

    def __init__(self, attrname, fn):
        self.fn = fn
        self.attrname = attrname
        self.marker = object()

    def __get__(self, inst, cls=None):
        if inst is None:
            return self
        cachedresult = getattr(inst, self.attrname, self.marker)
        if cachedresult is self.marker:
            result = self.fn(inst)
            setattr(inst, self.attrname, result)
            return result
        else:
            return cachedresult


if __name__ == '__main__':
    import doctest
    doctest.testmod()
