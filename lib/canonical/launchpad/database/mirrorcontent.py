# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from canonical.database.sqlbase import SQLBase
from sqlobject import ForeignKey

#
#
#

class MirrorContent(SQLBase):
    implements(IMirrorContent)
    _table = 'MirrorContent'

    mirror = ForeignKey(foreignKey='Mirror', dbName='mirror', notNull=True)
    distroarchrelease = ForeignKey(foreignKey='DistroArchRelease',
                                   dbName='distroarchrelease',
                                   notNull=True)
    component = ForeignKey(foreignKey='Component',
                           dbName='component',
                           notNull=True)
