
# Zope interfaces
from zope.interface import implements

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase, quote


# canonical imports
from canonical.launchpad.interfaces import IPackagePublishing, \
                                           ISourcePackagePublishing, \
                                           ISourcePackageFilesToPublish, \
                                           IBinaryPackageFilesToPublish, \
                                           IPublishedSourcePackageOverrides, \
                                           IPublishedBinaryPackageOverrides

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
        ForeignKey(name='distrorelease', foreignKey='DistroRelease', dbName='distrorelease'),
        ForeignKey(name='component', foreignKey='Component', dbName='component'),
        ForeignKey(name='section', foreignKey='Section', dbName='section'),
        IntCol('status'),
        DateTimeCol('scheduleddeletiondate', default=None)
    ]

    
class SourcePackageFilesToPublish(SQLBase):
    """A source package file which needs publishing"""

    _idType = str

    implements(ISourcePackageFilesToPublish)

    drd = IntCol(dbName='drd', unique=False, default=None, notNull=True)

    pp = ForeignKey(dbName='sppid', foreignKey='SourcePackagePublishing')

    pfalias = IntCol(dbName='pfalias', unique=False, default=None,
                       notNull=True)
    
    lfaname = StringCol(dbName='lfaname', unique=False, default=None,
                        notNull=True)

    cname = StringCol(dbName='cname', unique=False, default=None,
                        notNull=True)

    spname = StringCol(dbName='spname', unique=False, default=None,
                        notNull=True)

class BinaryPackageFilesToPublish(SQLBase):
    """A binary package file which needs publishing"""

    _idType = str

    implements(IBinaryPackageFilesToPublish)

    drd = IntCol(dbName='drd', unique=False, default=None, notNull=True)

    pp = ForeignKey(dbName='ppid', foreignKey='PackagePublishing')

    pfalias = IntCol(dbName='pfalias', unique=False, default=None,
                       notNull=True)
    
    lfaname = StringCol(dbName='lfaname', unique=False, default=None,
                        notNull=True)

    cname = StringCol(dbName='cname', unique=False, default=None,
                        notNull=True)

    spname = StringCol(dbName='spname', unique=False, default=None,
                        notNull=True)


class PublishedSourcePackageOverrides(SQLBase):
    """Source package overrides published and thus due for putting on disk"""

    implements(IPublishedSourcePackageOverrides)

    drname = StringCol(dbName='drname', unique=False, default=None,
                       notNull=True)
    spname = StringCol(dbName='spname', unique=False, default=None,
                       notNull=True)
    cname = StringCol(dbName='cname', unique=False, default=None,
                       notNull=True)
    sname = StringCol(dbName='sname', unique=False, default=None,
                       notNull=True)
    distro = IntCol(dbName='distro', unique=False, default=None, notNull=True)



class PublishedBinaryPackageOverrides(SQLBase):
    """Binary package overrides published and thus due for putting on disk"""

    implements(IPublishedBinaryPackageOverrides)

    drname = StringCol(dbName='drname', unique=False, default=None,
                       notNull=True)
    bpname = StringCol(dbName='bpname', unique=False, default=None,
                       notNull=True)
    cname = StringCol(dbName='cname', unique=False, default=None,
                       notNull=True)
    sname = StringCol(dbName='sname', unique=False, default=None,
                       notNull=True)
    distro = IntCol(dbName='distro', unique=False, default=None, notNull=True)
    priority = IntCol(dbName='priority', unique=False, default=None,
                      notNull=True)
