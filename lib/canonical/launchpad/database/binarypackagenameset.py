# Zope imports
from zope.interface import implements

# interfaces and database 
from canonical.launchpad.interfaces import IBinaryPackageNameSet

#
#
#

class BinaryPackageNameSet:
    implements(IBinaryPackageNameSet)

    def query(self, name=None, distribution=None, distrorelease=None,
              distroarchrelease=None, text=None):
        if name is None and distribution is None and \
            distrorelease is None and text is None:
            raise NotImplementedError, 'must give something to the query.'
        clauseTables = Set(['BinaryPackage'])
        # XXX sabdfl 12/12/04 not done yet
