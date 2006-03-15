# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['SupportContact']


from zope.interface import implements

from sqlobject import ForeignKey, IntCol

from canonical.launchpad.interfaces import ISupportContact

from canonical.database.sqlbase import SQLBase


class SupportContact(SQLBase):
    """See ISupportContact."""

    implements(ISupportContact)

    _defaultOrder = ['id']

    person = ForeignKey(dbName='person', notNull=True, foreignKey='Person')
    product = ForeignKey(dbName='product', notNull=False, foreignKey='Product')
    distribution = ForeignKey(
        dbName='distribution', notNull=False, foreignKey='Distribution')
    sourcepackagename = ForeignKey(
        dbName='sourcepackagename', notNull=False,
        foreignKey='SourcePackageName')
