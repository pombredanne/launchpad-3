# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['PackagePublishing', 'SourcePackagePublishing',
           'SourcePackageFilePublishing', 'BinaryPackageFilePublishing',
           'SourcePackagePublishingView', 'BinaryPackagePublishingView',
           'SourcePackagePublishingHistory'
           ]

from zope.interface import implements

from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import \
    IPackagePublishing, ISourcePackagePublishing, \
    ISourcePackagePublishingView, IBinaryPackagePublishingView, \
    ISourcePackageFilePublishing, IBinaryPackageFilePublishing

from canonical.lp.dbschema import \
    EnumCol, BinaryPackagePriority, PackagePublishingStatus


class PackagePublishing(SQLBase):
    """A binary package publishing record."""

    implements(IPackagePublishing)

    binarypackage = ForeignKey(foreignKey='BinaryPackage',
                               dbName='binarypackage')
    distroarchrelease = ForeignKey(foreignKey='DistroArchRelease',
                                   dbName='distroarchrelease')
    component = ForeignKey(foreignKey='Component', dbName='component')
    section = ForeignKey(foreignKey='Section', dbName='section')
    priority = EnumCol(dbName='priority', schema=BinaryPackagePriority)
    status = EnumCol(dbName='status', schema=PackagePublishingStatus)
    scheduleddeletiondate = DateTimeCol(default=None)
    datepublished = DateTimeCol(default=None)


class SourcePackagePublishing(SQLBase):
    """A source package release publishing record."""

    implements(ISourcePackagePublishing)

    sourcepackagerelease = ForeignKey(foreignKey='SourcePackageRelease',
                                      dbName='sourcepackagerelease')
    distrorelease = ForeignKey(foreignKey='DistroRelease',
                               dbName='distrorelease')
    component = ForeignKey(foreignKey='Component', dbName='component')
    section = ForeignKey(foreignKey='Section', dbName='section')
    status = EnumCol(schema=PackagePublishingStatus)
    scheduleddeletiondate = DateTimeCol(default=None)
    datepublished = DateTimeCol(default=None)


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

    publishingstatus = EnumCol(dbName='publishingstatus', unique=False,
                               default=None, notNull=True,
                               schema=PackagePublishingStatus)


class BinaryPackageFilePublishing(SQLBase):
    """A binary package file which needs publishing"""

    implements(IBinaryPackageFilePublishing)

    distribution = IntCol(dbName='distribution', unique=False, default=None,
                          notNull=True, immutable=True)

    packagepublishing = ForeignKey(dbName='packagepublishing',
                                   foreignKey='PackagePublishing',
                                   immutable=True)

    libraryfilealias = IntCol(dbName='libraryfilealias', unique=False,
                              default=None, notNull=True, immutable=True)

    libraryfilealiasfilename = StringCol(dbName='libraryfilealiasfilename',
                                         unique=False, default=None,
                                         notNull=True, immutable=True)

    componentname = StringCol(dbName='componentname', unique=False,
                              default=None, notNull=True, immutable=True)

    sourcepackagename = StringCol(dbName='sourcepackagename', unique=False,
                                  default=None, notNull=True, immutable=True)

    distroreleasename = StringCol(dbName='distroreleasename', unique=False,
                                  default=None, notNull=True, immutable=True)

    publishingstatus = EnumCol(dbName='publishingstatus', unique=False,
                               default=None, notNull=True, immutable=True,
                               schema=PackagePublishingStatus)

    architecturetag = StringCol(dbName='architecturetag', unique=False,
                                default=None, notNull=True, immutable=True)


class SourcePackagePublishingView(SQLBase):
    """Source package information published and thus due for putting on disk.
    """

    implements(ISourcePackagePublishingView)

    distroreleasename = StringCol(dbName='distroreleasename', unique=False,
                                  default=None, notNull=True, immutable=True)
    sourcepackagename = StringCol(dbName='sourcepackagename', unique=False,
                                  default=None, notNull=True, immutable=True)
    componentname = StringCol(dbName='componentname', unique=False,
                              default=None, notNull=True, immutable=True)
    sectionname = StringCol(dbName='sectionname', unique=False, default=None,
                            notNull=True, immutable=True)
    distribution = IntCol(dbName='distribution', unique=False, default=None,
                          notNull=True, immutable=True)
    publishingstatus = EnumCol(dbName='publishingstatus', unique=False,
                               default=None, notNull=True, immutable=True,
                               schema=PackagePublishingStatus)



class BinaryPackagePublishingView(SQLBase):
    """Binary package information published and thus due for putting on disk.
    """

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
    publishingstatus = EnumCol(dbName='publishingstatus', unique=False,
                               default=None, notNull=True,
                               schema=PackagePublishingStatus)


class SourcePackagePublishingHistory(SQLBase):
    """A source package release publishing record."""

    implements(ISourcePackagePublishing)

    sourcepackagerelease = ForeignKey(foreignKey='SourcePackageRelease',
                                      dbName='sourcepackagerelease'),
    distrorelease = ForeignKey(foreignKey='DistroRelease',
                               dbName='distrorelease'),
    component = ForeignKey(foreignKey='Component', dbName='component'),
    section = ForeignKey(foreignKey='Section', dbName='section'),
    status = EnumCol(schema=PackagePublishingStatus),
    scheduleddeletiondate = DateTimeCol(default=None),
    datepublished = DateTimeCol(default=None)

