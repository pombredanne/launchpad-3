# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['SupportContact']


from zope.interface import implements

from sqlobject import ForeignKey, IntCol

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import ISupportContact


class SupportContact(SQLBase):
    """An entry for a support contact for a ITicketTarget."""

    implements(ISupportContact)

    _defaultOrder = ['id']

    person = ForeignKey(dbName='person', notNull=True, foreignKey='Person')
    product = ForeignKey(dbName='product', notNull=False, foreignKey='Product')
    distribution = ForeignKey(
        dbName='distribution', notNull=False, foreignKey='Distribution')
    sourcepackagename = ForeignKey(
        dbName='sourcepackagename', notNull=False,
        foreignKey='SourcePackageName')
