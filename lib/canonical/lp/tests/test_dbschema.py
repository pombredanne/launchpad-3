# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: 59b05113-a166-4c57-abf0-1b4155b968ff

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

    An Item has an informative representation.

    >>> print repr(SomeClass.attribute)
    <Item attribute (2) from canonical.lp.tests.test_dbschema.SomeClass>

    """

def test_decorator():
    """
    >>> from canonical.lp.dbschema import BugSeverity, Item

    We can iterate over the Items in a DBSchema class

    >>> for s in BugSeverity.items:
    ...     assert isinstance(s, Item)
    ...     print s.name
    ...
    CRITICAL
    MAJOR
    NORMAL
    MINOR
    WISHLIST

    We can retrieve an Item by value

    >>> BugSeverity.items[1].name
    'CRITICAL'

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
