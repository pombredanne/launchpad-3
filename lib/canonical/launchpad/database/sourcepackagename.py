# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import SQLObjectNotFound
from sqlobject import StringCol, ForeignKey, IntCol, DateTimeCol

from canonical.database.sqlbase import SQLBase

# interfaces and database 
from canonical.launchpad.interfaces import ISourcePackageName
    
    

#
#
#

class SourcePackageName(SQLBase):
    implements(ISourcePackageName)
    _table = 'SourcePackageName'

    name = StringCol(dbName='name', notNull=True, unique=True,
        alternateID=True)

    def __unicode__(self):
        return self.name

    def _ensure(klass, name):
        try:
            return klass.byName(name)
        except SQLObjectNotFound:
            return klass(name=name)

    ensure = classmethod(_ensure)

