
# Zope interfaces
from zope.interface import implements

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase, quote


# canonical imports
from canonical.launchpad.interfaces import IPackagePublishing, \
                                           ISourcePackagePublishing, \
                                           ISourcePackagePublishingView, \
                                           IBinaryPackagePublishingView, \
                                           ISourcePackageFilePublishing, \
                                           IBinaryPackageFilePublishing

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

    
class SourcePackageFilePublishing(SQLBase):
    """Source package release files and their publishing status"""

    _idType = str

    implements(ISourcePackageFilePublishing)

    distribution = IntCol(dbName='distribution', unique=False, default=None,
                          notNull=True)

    sourcepackagepublishing = ForeignKey(dbName='sourcepackagepublishing',
                                         foreignKey='SourcePackagePublishing')

    libraryfilealias = IntCol(dbName='libraryfilealias', unique=False,
                              default=None, notNull=True)
    
    libraryfilealiasfilename = StringCol(dbName='libraryfilealiasfilename',
                                         unique=False, default=None,
                                         notNull=True)

    componentname = StringCol(dbName='componentname', unique=False,
                              default=None, notNull=True)

    sourcepackagename = StringCol(dbName='sourcepackagename', unique=False,
                                  default=None, notNull=True)

    distroreleasename = StringCol(dbName='distroreleasename', unique=False,
                                  default=None, notNull=True)

    publishingstatus = IntCol(dbName='publishingstatus', unique=False,
                              default=None, notNull=True)
    
    
class BinaryPackageFilePublishing(SQLBase):
    """A binary package file which needs publishing"""

    _idType = str

    implements(IBinaryPackageFilePublishing)

    distribution = IntCol(dbName='distribution', unique=False, default=None,
                          notNull=True)

    packagepublishing = ForeignKey(dbName='packagepublishing',
                                   foreignKey='PackagePublishing')

    libraryfilealias = IntCol(dbName='libraryfilealias', unique=False,
                              default=None, notNull=True)
    
    libraryfilealiasfilename = StringCol(dbName='libraryfilealiasfilename',
                                         unique=False, default=None,
                                         notNull=True)

    componentname = StringCol(dbName='componentname', unique=False,
                              default=None, notNull=True)

    sourcepackagename = StringCol(dbName='sourcepackagename', unique=False,
                                  default=None, notNull=True)

    distroreleasename = StringCol(dbName='distroreleasename', unique=False,
                                  default=None, notNull=True)

    publishingstatus = IntCol(dbName='publishingstatus', unique=False,
                              default=None, notNull=True)

    architecturetag = StringCol(dbName='architecturetag', unique=False,
                                default=None, notNull=True)

class SourcePackagePublishingView(SQLBase):
    """Source package information published and thus due for putting on disk"""

    implements(ISourcePackagePublishingView)

    distroreleasename = StringCol(dbName='distroreleasename', unique=False,
                                  default=None, notNull=True)
    sourcepackagename = StringCol(dbName='sourcepackagename', unique=False,
                                  default=None, notNull=True)
    componentname = StringCol(dbName='componentname', unique=False,
                              default=None, notNull=True)
    sectionname = StringCol(dbName='sectionname', unique=False, default=None,
                            notNull=True)
    distribution = IntCol(dbName='distribution', unique=False, default=None,
                          notNull=True)
    publishingstatus = IntCol(dbName='publishingstatus', unique=False,
                              default=None, notNull=True)



class BinaryPackagePublishingView(SQLBase):
    """Binary package information published and thus due for putting on disk"""

    implements(IBinaryPackagePublishingView)

    distroreleasename = StringCol(dbName='distroreleasename', unique=False,
                                  default=None, notNull=True)
    binarypackagename = StringCol(dbName='binarypackagename', unique=False,
                                  default=None, notNull=True)
    componentname = StringCol(dbName='componentname', unique=False,
                              default=None, notNull=True)
    sectionname = StringCol(dbName='sectionname', unique=False, default=None,
                            notNull=True)
    distribution = IntCol(dbName='distribution', unique=False, default=None,
                          notNull=True)
    priority = IntCol(dbName='priority', unique=False, default=None,
                      notNull=True)
    publishingstatus = IntCol(dbName='publishingstatus', unique=False,
                              default=None, notNull=True)
