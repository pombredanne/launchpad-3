# Copyright 2007 Canonical Ltd.  All rights reserved.

"""FAQ document models."""

__metaclass__ = type

__all__ = [
    'FAQ',
    ]

from sqlobject import ForeignKey, StringCol

from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.interfaces import IFAQ


class FAQ(SQLBase):
    """See `IFAQ`."""

    implements(IFAQ)

    _table = 'FAQ'
    _defaultOrder = ['date_created', 'id']

    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    
    title = StringCol(notNull=True)
    
    summary = StringCol(notNull=True)
    
    keywords = StringCol(notNull=False, default=None)
    
    content = StringCol(notNull=False, default=None)
    
    url = StringCol(notNull=False, default=None)
    
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    
    last_updated_by = ForeignKey(
        dbName='last_updated_by', foreignKey='Person', notNull=False,
        default=None)

    date_last_updated = UtcDateTimeCol(notNull=False, default=None)

    product = ForeignKey(
        dbName='product', foreignKey='Product', notNull=False, default=None)
        
    distribution = ForeignKey(
        dbName='distribution', foreignKey='Distribution', notNull=False,
        default=None)

    @property
    def target(self):
        """See `IFAQ`."""
        return None
