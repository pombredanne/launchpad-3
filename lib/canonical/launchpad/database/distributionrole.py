# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import ForeignKey, IntCol

from canonical.database.sqlbase import SQLBase
from canonical.lp import dbschema

# interfaces and database 
from canonical.launchpad.interfaces import IDistributionRole

#
#
#

class DistributionRole(SQLBase):

    implements(IDistributionRole)

    _table = 'DistributionRole'
    _columns = [
        ForeignKey(name='person', dbName='person', foreignKey='Person',
                   notNull=True),
        ForeignKey(name='distribution', dbName='distribution',
                   foreignKey='Distribution', notNull=True),
        IntCol('role', dbName='role')
        ]

    def _rolename(self):
        for role in dbschema.DistributionRole.items:
            if role.value == self.role:
                return role.title
        return 'Unknown (%d)' %self.role
    
    rolename = property(_rolename)
        

