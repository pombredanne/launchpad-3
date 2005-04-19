# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from canonical.database.sqlbase import SQLBase
from canonical.database.datetimecol import UtcDateTimeCol
from sqlobject import StringCol, ForeignKey, BoolCol

from canonical.lp.dbschema import EnumCol
from canonical.lp.dbschema import MirrorFreshness

#
#
#

class Mirror(SQLBase):
    implements(IMirror)
    _table = 'Mirror'
    
    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=True)
    baseurl = StringCol(dbName='baseurl', notNull=True)
    country = ForeignKey(foreignKey='Country', dbName='country', notNull=True)
    name = StringCol(dbName='name', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    freshness = EnumCol(dbName='freshness', notNull=True, default=99,
                        schema=MirrorFreshness)
    lastcheckeddate = UtcDateTimeCol(dbName='lastcheckeddate')
    approved = BoolCol(dbName='approved', notNull=True, default=False),

