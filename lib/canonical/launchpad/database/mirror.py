# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from canonical.database.sqlbase import SQLBase
from sqlobject import StringCol, ForeignKey, IntCol, DateTimeCol, BoolCol

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
    freshness = IntCol(dbName='freshness', notNull=True, default=99)
    lastcheckeddate = DateTimeCol(dbName='lastcheckeddate')
    approved = BoolCol(dbName='approved', notNull=True, default=False),

