# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import MultipleJoin
from sqlobject import SQLObjectNotFound
from sqlobject import StringCol, MultipleJoin

# launchpad imports
from canonical.database.sqlbase import SQLBase

# interfaces and database 
from canonical.launchpad.interfaces import IBinaryPackageName

#
#
#

class BinaryPackageName(SQLBase):

    implements(IBinaryPackageName)
    _table = 'BinaryPackageName'
    name = StringCol(dbName='name', notNull=True, unique=True,
                     alternateID=True)

    binarypackages = MultipleJoin(
            'BinaryPackage', joinColumn='binarypackagename'
            )

    def __unicode__(self):
        return self.name

    def _ensure(klass, name):
        try:
            return klass.byName(name)
        except SQLObjectNotFound:
            return klass(name=name)
        
    ensure = classmethod(_ensure)

