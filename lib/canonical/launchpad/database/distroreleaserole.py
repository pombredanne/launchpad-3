# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import ForeignKey, IntCol

from canonical.database.sqlbase import SQLBase
from canonical.lp import dbschema

# interfaces and database 
from canonical.launchpad.interfaces import IDistroReleaseRole

#
#
#

class DistroReleaseRole(SQLBase):

    implements(IDistroReleaseRole)

    _table = 'DistroReleaseRole'
    _columns = [
        ForeignKey(name='person', dbName='person', foreignKey='Person',
                   notNull=True),
        ForeignKey(name='distrorelease', dbName='distrorelease',
                   foreignKey='DistroRelease',
                   notNull=True),
        IntCol('role', dbName='role')
        ]

    def _rolename(self):
        for role in dbschema.DistroReleaseRole.items:
            if role.value == self.role:
                return role.title
        return 'Unknown (%d)' %self.role

    rolename = property(_rolename)

