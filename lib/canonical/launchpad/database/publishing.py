
# Zope interfaces
from zope.interface import implements

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase, quote


# canonical imports
from canonical.launchpad.interfaces import IPackagePublishing, \
                                           ISourcePackagePublishing

from canonical.launchpad.database import DistroRelease, DistroArchRelease

class PackagePublishing(SQLBase):
    """A binary package publishing record."""

    implements(IPackagePublishing)

    _columns = [
        # XXX: Daniel Silverstone 2004-10-15: Need to fix up the CamelCaseNess
        # of the table classes. They should be CamelCase not Initialcapital
        ForeignKey(name='binarypackage', foreignKey='BinaryPackage', dbName='binarypackage'),
        ForeignKey(name='distroarchrelease', foreignKey='DistroArchRelease', dbName='distroarchrelease'),
        ForeignKey(name='component', foreignKey='Component', dbName='component'),
        ForeignKey(name='section', foreignKey='Section', dbName='section'),
        IntCol('priority'),
        IntCol('status'),
        DateTimeCol('scheduleddeletiondate', default=None)
    ]

class SourcePackagePublishing(SQLBase):
    """A source package release publishing record."""

    implements(ISourcePackagePublishing)

    _columns = [
        ForeignKey(name='sourcepackagerelease', foreignKey='SourcePackageRelease', dbName='sourcepackagerelease'),
        ForeignKey(name='distrorelease', foreignKey='DistroRelease', dbName='distroarchrelease'),
        ForeignKey(name='component', foreignKey='Component', dbName='component'),
        ForeignKey(name='section', foreignKey='Section', dbName='section'),
        IntCol('priority'),
        IntCol('status'),
        DateTimeCol('scheduleddeletiondate', default=None)
    ]

    
