# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test enumerations used for enumcol doctests."""

__metaclass__ = type
__all__ = [
    'DBTestEnumeration',
    'InheritedTestEnumeration',
    'ExtendedTestEnumeration',
    'UnrelatedTestEnumeration',
    ]


from canonical.lazr import DBEnumeratedType, DBItem, use_template


class DBTestEnumeration(DBEnumeratedType):
    VALUE1 = DBItem(1, 'Some value')
    VALUE2 = DBItem(2, 'Some other value')


class InheritedTestEnumeration(DBTestEnumeration):
    VALUE3 = DBItem(3, 'Yet another item')


class ExtendedTestEnumeration(DBEnumeratedType):
    use_template(DBTestEnumeration)
    VALUE3 = DBItem(3, 'Yet another item')


class UnrelatedTestEnumeration(DBEnumeratedType):
    VALUE1 = DBItem(1, 'Some value')
    VALUE2 = DBItem(2, 'Some other value')
