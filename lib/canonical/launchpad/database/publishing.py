# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BinaryPackagePublishing', 'SourcePackagePublishing',
           'SourcePackageFilePublishing', 'BinaryPackageFilePublishing',
           'SourcePackagePublishingView', 'BinaryPackagePublishingView',
           'SecureSourcePackagePublishingHistory',
           'SecureBinaryPackagePublishingHistory',
           'SourcePackagePublishingHistory',
           'BinaryPackagePublishingHistory'
           ]

from zope.interface import implements

from sqlobject import ForeignKey, IntCol, StringCol, BoolCol
from canonical.database.sqlbase import SQLBase
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.interfaces import ( IBinaryPackagePublishing,
    ISourcePackagePublishing, ISourcePackagePublishingView,
    IBinaryPackagePublishingView, ISourcePackageFilePublishing,
    IBinaryPackageFilePublishing,
    ISecureSourcePackagePublishingHistory,
    ISecureBinaryPackagePublishingHistory,
    ISourcePackagePublishingHistory, IBinaryPackagePublishingHistory )

from canonical.lp.dbschema import \
    EnumCol, PackagePublishingPriority, PackagePublishingStatus, \
    PackagePublishingPocket

from warnings import warn


class BinaryPackagePublishing(SQLBase):
    """A binary package publishing record."""

    implements(IBinaryPackagePublishing)

    binarypackagerelease = ForeignKey(foreignKey='BinaryPackageRelease',
                                      dbName='binarypackagerelease')
    distroarchrelease = ForeignKey(foreignKey='DistroArchRelease',
                                   dbName='distroarchrelease')
    component = ForeignKey(foreignKey='Component', dbName='component')
    section = ForeignKey(foreignKey='Section', dbName='section')
    priority = EnumCol(dbName='priority', schema=PackagePublishingPriority)
    status = EnumCol(dbName='status', schema=PackagePublishingStatus)
    scheduleddeletiondate = UtcDateTimeCol(default=None)
    datepublished = UtcDateTimeCol(default=None)
    pocket = EnumCol(dbName='pocket', schema=PackagePublishingPocket)


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
    scheduleddeletiondate = UtcDateTimeCol(default=None)
    datepublished = UtcDateTimeCol(default=None)
    pocket = EnumCol(dbName='pocket', schema=PackagePublishingPocket)


class SourcePackageFilePublishing(SQLBase):
    """Source package release files and their publishing status"""

    _idType = str

    implements(ISourcePackageFilePublishing)

    distribution = IntCol(dbName='distribution', unique=False, default=None,
                          notNull=True)

    sourcepackagepublishing = ForeignKey(dbName='sourcepackagepublishing',
         foreignKey='SecureSourcePackagePublishingHistory')

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

    pocket = EnumCol(dbName='pocket', unique=False,
                     default=None, notNull=True,
                     schema=PackagePublishingPocket)

class BinaryPackageFilePublishing(SQLBase):
    """A binary package file which needs publishing"""

    _idType = str

    implements(IBinaryPackageFilePublishing)

    distribution = IntCol(dbName='distribution', unique=False, default=None,
                          notNull=True, immutable=True)

    binarypackagepublishing = ForeignKey(dbName='binarypackagepublishing',
        foreignKey='SecureBinaryPackagePublishingHistory', immutable=True)

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

    pocket = EnumCol(dbName='pocket', unique=False,
                     default=None, notNull=True,
                     schema=PackagePublishingPocket)


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
    pocket = EnumCol(dbName='pocket', unique=False, default=None,
                     notNull=True, immutable=True,
                     schema=PackagePublishingPocket)



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
    pocket = EnumCol(dbName='pocket', unique=False, default=None,
                     notNull=True, immutable=True,
                     schema=PackagePublishingPocket)


class SecureSourcePackagePublishingHistory(SQLBase):
    """A source package release publishing record."""

    implements(ISecureSourcePackagePublishingHistory)

    sourcepackagerelease = ForeignKey(foreignKey='SourcePackageRelease',
                                      dbName='sourcepackagerelease')
    distrorelease = ForeignKey(foreignKey='DistroRelease',
                               dbName='distrorelease')
    component = ForeignKey(foreignKey='Component', dbName='component')
    section = ForeignKey(foreignKey='Section', dbName='section')
    status = EnumCol(schema=PackagePublishingStatus)
    scheduleddeletiondate = UtcDateTimeCol(default=None)
    datepublished = UtcDateTimeCol(default=None)
    datecreated = UtcDateTimeCol(default=None)
    datesuperseded = UtcDateTimeCol(default=None)
    supersededby = ForeignKey(foreignKey='SourcePackageRelease',
                              dbName='supersededby', default=None)
    datemadepending = UtcDateTimeCol(default=None)
    dateremoved = UtcDateTimeCol(default=None)
    pocket = EnumCol(dbName='pocket', schema=PackagePublishingPocket,
                     default=PackagePublishingPocket.RELEASE,
                     notNull=True)
    embargo = BoolCol(dbName='embargo', default=False, notNull=True)
    embargolifted = UtcDateTimeCol(default=None)

    @classmethod
    def selectBy(cls, *args, **kwargs):
        """Prevent selecting embargo packages by default"""
        if 'embargo' in kwargs:
            if kwargs['embargo']:
                warn("SecureSourcePackagePublishingHistory.selectBy called "
                     "with embargo argument set to True",
                     stacklevel=2)
        kwargs['embargo'] = False
        return super(SecureSourcePackagePublishingHistory,
                     cls).selectBy(*args, **kwargs)

    @classmethod
    def selectByWithEmbargoedEntries(cls, *args, **kwargs):
        return super(SecureSourcePackagePublishingHistory,
                     cls).selectBy(*args, **kwargs)


class SecureBinaryPackagePublishingHistory(SQLBase):
    """A binary package publishing record."""

    implements(ISecureBinaryPackagePublishingHistory)

    binarypackagerelease = ForeignKey(foreignKey='BinaryPackageRelease',
                                      dbName='binarypackagerelease')
    distroarchrelease = ForeignKey(foreignKey='DistroArchRelease',
                                   dbName='distroarchrelease')
    component = ForeignKey(foreignKey='Component', dbName='component')
    section = ForeignKey(foreignKey='Section', dbName='section')
    priority = EnumCol(dbName='priority', schema=PackagePublishingPriority)
    status = EnumCol(dbName='status', schema=PackagePublishingStatus)
    scheduleddeletiondate = UtcDateTimeCol(default=None)
    datepublished = UtcDateTimeCol(default=None)
    datecreated = UtcDateTimeCol(default=None)
    datesuperseded = UtcDateTimeCol(default=None)
    supersededby = ForeignKey(foreignKey='Build', dbName='supersededby',
                              default=None)
    datemadepending = UtcDateTimeCol(default=None)
    dateremoved = UtcDateTimeCol(default=None)
    pocket = EnumCol(dbName='pocket', schema=PackagePublishingPocket)
    embargo = BoolCol(dbName='embargo', default=False, notNull=True)
    embargolifted = UtcDateTimeCol(default=None)

    @classmethod
    def selectBy(cls, *args, **kwargs):
        """Prevent selecting embargo packages by default"""
        if 'embargo' in kwargs:
            if kwargs['embargo']:
                warn("SecureBinaryPackagePublishingHistory.selectBy called "
                     "with embargo argument set to True",
                     stacklevel=2)
        kwargs['embargo'] = False
        return super(SecureBinaryPackagePublishingHistory,
                     cls).selectBy(*args, **kwargs)

    @classmethod
    def selectByWithEmbargoedEntries(cls, *args, **kwargs):
        return super(SecureBinaryPackagePublishingHistory,
                     cls).selectBy(*args, **kwargs)
    
class SourcePackagePublishingHistory(SQLBase):
    """A source package release publishing record. (excluding embargoed stuff)"""

    implements(ISourcePackagePublishingHistory)

    sourcepackagerelease = ForeignKey(foreignKey='SourcePackageRelease',
                                      dbName='sourcepackagerelease')
    distrorelease = ForeignKey(foreignKey='DistroRelease',
                               dbName='distrorelease')
    component = ForeignKey(foreignKey='Component', dbName='component')
    section = ForeignKey(foreignKey='Section', dbName='section')
    status = EnumCol(schema=PackagePublishingStatus)
    scheduleddeletiondate = UtcDateTimeCol(default=None)
    datepublished = UtcDateTimeCol(default=None)
    datecreated = UtcDateTimeCol(default=None)
    datesuperseded = UtcDateTimeCol(default=None)
    supersededby = ForeignKey(foreignKey='SourcePackageRelease',
                              dbName='supersededby', default=None)
    datemadepending = UtcDateTimeCol(default=None)
    dateremoved = UtcDateTimeCol(default=None)
    pocket = EnumCol(dbName='pocket', schema=PackagePublishingPocket)

class BinaryPackagePublishingHistory(SQLBase):
    """A binary package publishing record. (excluding embargoed packages)"""

    implements(IBinaryPackagePublishingHistory)

    binarypackagerelease = ForeignKey(foreignKey='BinaryPackageRelease',
                                      dbName='binarypackagerelease')
    distroarchrelease = ForeignKey(foreignKey='DistroArchRelease',
                                   dbName='distroarchrelease')
    component = ForeignKey(foreignKey='Component', dbName='component')
    section = ForeignKey(foreignKey='Section', dbName='section')
    priority = EnumCol(dbName='priority', schema=PackagePublishingPriority)
    status = EnumCol(dbName='status', schema=PackagePublishingStatus)
    scheduleddeletiondate = UtcDateTimeCol(default=None)
    datepublished = UtcDateTimeCol(default=None)
    datecreated = UtcDateTimeCol(default=None)
    datesuperseded = UtcDateTimeCol(default=None)
    supersededby = ForeignKey(foreignKey='Build', dbName='supersededby',
                              default=None)
    datemadepending = UtcDateTimeCol(default=None)
    dateremoved = UtcDateTimeCol(default=None)
    pocket = EnumCol(dbName='pocket', schema=PackagePublishingPocket)
