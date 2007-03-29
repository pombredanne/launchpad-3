"""Test enumerations used for enumcol doctests."""

from canonical.launchpad.webapp.enum import DBEnumeratedType, DBItem, extends

__all__ = [
    'DBTestEnumeration',
    'InheritedTestEnumeration',
    'ExtendedTestEnumeration',
    'UnrelatedTestEnumeration',
    ]

class DBTestEnumeration(DBEnumeratedType):
    VALUE1 = DBItem(1, 'Some value')
    VALUE2 = DBItem(2, 'Some other value')

class InheritedTestEnumeration(DBTestEnumeration):
    VALUE3 = DBItem(3, 'Yet another item')

class ExtendedTestEnumeration(DBEnumeratedType):
    extends(DBTestEnumeration)
    VALUE3 = DBItem(3, 'Yet another item')

class UnrelatedTestEnumeration(DBEnumeratedType):
    VALUE1 = DBItem(1, 'Some value')
    VALUE2 = DBItem(2, 'Some other value')
