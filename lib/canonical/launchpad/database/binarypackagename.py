# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import MultipleJoin
from sqlobject import SQLObjectNotFound
from sqlobject import StringCol, MultipleJoin

# launchpad imports
from canonical.database.sqlbase import SQLBase, quote

# interfaces and database 
from canonical.launchpad.interfaces import IBinaryPackageName
from canonical.launchpad.interfaces import IBinaryPackageNameSet

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


class BinaryPackageNameSet:
    implements(IBinaryPackageNameSet)

    def __getitem__(self, name):
        """See canonical.launchpad.interfaces.IBinaryPackageNameSet."""
        try:
            return BinaryPackageName.byName(name)
        except SQLObjectNotFound:
            raise KeyError, name

    def __iter__(self):
        """See canonical.launchpad.interfaces.IBinaryPackageNameSet."""
        for binarypackagename in BinaryPackageName.select():
            yield binarypackagename

    def findByName(self, name):
        """Find binarypackagenames by its name or part of it"""
        name = name.replace('%', '%%')
        query = ('name ILIKE %s'
                 %quote('%%' +name+ '%%'))
        return BinaryPackageName.select(query)

    def query(self, name=None, distribution=None, distrorelease=None,
              distroarchrelease=None, text=None):
        if name is None and distribution is None and \
            distrorelease is None and text is None:
            raise NotImplementedError, 'must give something to the query.'
        clauseTables = Set(['BinaryPackage'])
        # XXX sabdfl 12/12/04 not done yet
