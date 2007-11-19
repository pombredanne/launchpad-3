# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['CveReference']

from zope.interface import implements

from sqlobject import ForeignKey, StringCol

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import ICveReference


class CveReference(SQLBase):
    """A CVE reference to some other tracking system."""

    implements(ICveReference)

    _table = 'CveReference'

    # db field names
    cve = ForeignKey(dbName='cve', foreignKey='Cve', notNull=True)
    source = StringCol(notNull=True)
    content = StringCol(notNull=True)
    url = StringCol(notNull=False, default=None)


