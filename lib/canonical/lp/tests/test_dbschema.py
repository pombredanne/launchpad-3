# Copyright 2004 Canonical Ltd.  All rights reserved.
#

import unittest
from zope.testing.doctestunit import DocTestSuite

def test_constructor():
    """
    >>> from canonical.lp.dbschema import Item

    An Item can be created only within a class suite, and its first arg
    must be an int.

    >>> item = Item(2, 'a foo', 'description of a foo')
    Traceback (most recent call last):
    ...
    TypeError: Item can be used only from a class definition.
    >>> class SomeClass:
    ...    attribute = Item('foo', 'a foo', 'description of a foo')
    ...
    Traceback (most recent call last):
    ...
    TypeError: value must be an int, not 'foo'
    >>> class SomeClass:
    ...    description = "Description of some class"
    ...    attribute = Item(2, 'a foo', 'description of a foo')
    ...    attr3 = Item(3, '''
    ...        Some item title
    ...
    ...        Description.
    ...        ''')
    ...
    >>> SomeClass.attribute.value
    2
    >>> SomeClass.attribute.name
    'attribute'
    >>> SomeClass.attribute.title
    'a foo'
    >>> SomeClass.attribute.description
    'description of a foo'

    An Item can be cast into an int or a string, for use as a replacement in
    SQL statements.

    >>> print "SELECT * from Foo where Foo.id = '%d';" % SomeClass.attribute
    SELECT * from Foo where Foo.id = '2';
    >>> print "SELECT * from Foo where Foo.id = '%s';" % SomeClass.attribute
    SELECT * from Foo where Foo.id = '2';

    An Item is comparable to ints.

    >>> 1 == SomeClass.attribute
    False
    >>> 1 != SomeClass.attribute
    True
    >>> 2 == SomeClass.attribute
    True
    >>> SomeClass.attribute == 1
    False
    >>> SomeClass.attribute == 2
    True
    >>> hash(SomeClass.attribute)
    2
    >>> SomeClass._items[2] is SomeClass.attribute
    True

    An Item compares properly when security proxied.

    >>> item = SomeClass.attribute
    >>> from zope.security.checker import ProxyFactory, NamesChecker
    >>> checker = NamesChecker(['value', 'schema'])
    >>> proxied_item = ProxyFactory(item, checker=checker)
    >>> proxied_item is item
    False
    >>> proxied_item == item
    True
    >>> item == proxied_item
    True
    >>> item != proxied_item
    False

    An Item has an informative representation.

    >>> print repr(SomeClass.attribute)
    <Item attribute (2) from canonical.lp.tests.test_dbschema.SomeClass>

    An Item can tell you its class.

    >>> SomeClass.attribute.schema is SomeClass
    True

    An Item knows how to represent itself for use in SQL queries by SQLObject.
    The 'None' value passed in is the database type (I think).

    >>> SomeClass.attribute.__sqlrepr__(None)
    '2'

    An Item will not compare equal to an Item from a different schema.

    To test this, we'll create another schema, then compare items.

    >>> class SomeOtherClass:
    ...    description = "Description of some other class"
    ...    attr3 = Item(3, 'an other foo', 'description of an other foo')
    ...
    >>> SomeClass.attr3.value == SomeOtherClass.attr3.value
    True
    >>> SomeOtherClass.attr3 == SomeClass.attr3
    False

    """

def test_decorator():
    """
    >>> from canonical.lp.dbschema import BugSeverity, Item

    We can iterate over the Items in a DBSchema class

    >>> for s in BugSeverity.items:
    ...     assert isinstance(s, Item)
    ...     print s.name
    ...
    WISHLIST
    MINOR
    NORMAL
    MAJOR
    CRITICAL

    We can retrieve an Item by value

    >>> BugSeverity.items[50].name
    'CRITICAL'

    We can also retrieve an Item by name.

    >>> BugSeverity.items['CRITICAL'].title
    'Critical'

    If we don't ask for the item by its name or its value, we get a KeyError.

    >>> BugSeverity.items['foo']
    Traceback (most recent call last):
    ...
    KeyError: 'foo'

    """

def test_suite():
    suite = DocTestSuite()
    suite.addTest(DocTestSuite('canonical.lp.dbschema'))
    return suite

def _test():
    import doctest, test_dbschema
    return doctest.testmod(test_dbschema)

if __name__ == "__main__":
    _test()

if __name__ == '__main__':
    unittest.main()
