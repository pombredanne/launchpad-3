
# Zope imports
from zope.interface import implements
from zope.exceptions import NotFoundError

# SQLObject/SQLBase
from sqlobject import SQLObjectNotFound
from sqlobject import StringCol, ForeignKey, IntCol, DateTimeCol

# interfaces and database 
from canonical.launchpad.interfaces import ISourcePackageNameSet
from canonical.launchpad.database.sourcepackagename import SourcePackageName
#
#
#

class SourcePackageNameSet(object):
    implements(ISourcePackageNameSet)

    def __getitem__(self, name):
        """See canonical.launchpad.interfaces.ISourcePackageNameSet."""
        try:
            return SourcePackageName.byName(name)
        except SQLObjectNotFound:
            raise KeyError, name

    def __iter__(self):
        """See canonical.launchpad.interfaces.ISourcePackageNameSet."""
        for sourcepackagename in SourcePackageName.select():
            yield sourcepackagename

    def get(self, sourcepackagenameid):
        """See canonical.launchpad.interfaces.ISourcePackageNameSet."""
        try:
            return SourcePackageName.get(sourcepackagenameid)
        except SQLObjectNotFound:
            raise NotFoundError(sourcepackagenameid)


