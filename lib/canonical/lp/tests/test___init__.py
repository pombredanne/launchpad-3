# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: 99d90369-f89f-4aff-acbb-913bc1ac346d

import unittest
from zope.testing.doctestunit import DocTestSuite

def test_decorates():
    """
    >>> from canonical.lp import decorates
    >>> from zope.interface import Interface, Attribute

    >>> class IFoo0(Interface):
    ...     spoo = Attribute('attribute in IFoo0')
    ...

    >>> class IFoo(IFoo0):
    ...     def bar():
    ...         "some method"
    ...     baz = Attribute("some attribute")
    ...

    >>> decorates(IFoo)
    Traceback (most recent call last):
    ...
    TypeError: decorates can be used only from a class definition.

    >>> class BaseFoo0:
    ...     spoo = 'some spoo'

    >>> class BaseFoo(BaseFoo0):
    ...     def bar(self):
    ...         return 'bar'
    ...     baz = 'hi baz!'
    ...

    >>> class SomeClassicClass:
    ...     decorates(IFoo)
    ...
    Traceback (most recent call last):
    ...
    TypeError: cannot use decorates() on a classic class: canonical.lp.tests.test___init__.SomeClassicClass

    >>> class SomeClass(object):
    ...     decorates(IFoo)
    ...     def __init__(self, context):
    ...         self.context = context
    ...

    >>> f = BaseFoo()
    >>> s = SomeClass(f)
    >>> s.bar()
    'bar'
    >>> s.baz
    'hi baz!'
    >>> s.spoo
    'some spoo'
    >>> IFoo.providedBy(s)
    True

    >>> class SomeOtherClass(object):
    ...     decorates(IFoo, context='myfoo')
    ...     def __init__(self, foo):
    ...         self.myfoo = foo
    ...     spoo = 'spoo from SomeOtherClass'

    >>> f = BaseFoo()
    >>> s = SomeOtherClass(f)
    >>> s.bar()
    'bar'
    >>> s.baz
    'hi baz!'
    >>> s.spoo
    'spoo from SomeOtherClass'

    >>> s.baz = 'fish'
    >>> s.baz
    'fish'
    >>> f.baz
    'fish'

    """

def test_Passthrough():
    """
    >>> from canonical.lp import Passthrough
    >>> p = Passthrough('foo', 'mycontext')
    >>> p2 = Passthrough('clsmethod', 'mycontext')
    >>> class Base:
    ...     foo = 'foo from Base'
    ...     def clsmethod(cls):
    ...         return str(cls)
    ...     clsmethod = classmethod(clsmethod)
    ...
    >>> base = Base()
    >>> class Adapter:
    ...     mycontext = base
    ...
    >>> adapter = Adapter()
    >>> p.__get__(adapter)
    'foo from Base'
    >>> p.__get__(None, Adapter) is p
    True
    >>> p2.__get__(adapter)()
    'canonical.lp.tests.test___init__.Base'

    >>> p.__set__(adapter, 'new value')
    >>> base.foo
    'new value'
    >>> p.__delete__(adapter)
    Traceback (most recent call last):
    ...
    NotImplementedError

    """

def test_suite():
    suite = DocTestSuite()
    return suite


if __name__ == '__main__':
    unittest.main()
