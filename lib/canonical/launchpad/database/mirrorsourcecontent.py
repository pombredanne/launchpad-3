# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from canonical.database.sqlbase import SQLBase
from sqlobject import ForeignKey

#
#
#

class MirrorSourceContent(SQLBase):
    implements(IMirrorSourceContent)
    _table = 'MirrorSourceContent'

    mirror = ForeignKey(foreignKey='Mirror', dbName='mirror', notNull=True)
    distrorelease = ForeignKey(foreignKey='DistroRelease',
                                   dbName='distrorelease',
                                   notNull=True)
    component = ForeignKey(foreignKey='Component',
                           dbName='component',
                           notNull=True)
