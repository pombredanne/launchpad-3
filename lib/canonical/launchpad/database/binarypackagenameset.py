# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import SQLObjectNotFound

# LP imports
from canonical.database.sqlbase import quote

# interfaces and database 
from canonical.launchpad.interfaces import IBinaryPackageNameSet
from canonical.launchpad.database.binarypackagename import \
     BinaryPackageName

#
#
#

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

