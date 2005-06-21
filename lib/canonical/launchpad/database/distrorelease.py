# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Database classes for a distribution release."""

__metaclass__ = type

from zope.interface import implements
from zope.component import getUtility

from sqlobject import StringCol, ForeignKey, MultipleJoin

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.lp.dbschema import \
    PackagePublishingStatus, BugTaskStatus, EnumCol, DistributionReleaseStatus

from canonical.launchpad.interfaces import \
    IDistroRelease, IDistroReleaseSet, ISourcePackageName

from canonical.launchpad.database.sourcepackageindistro \
        import SourcePackageInDistro
from canonical.launchpad.database.publishedpackage import PublishedPackageSet
from canonical.launchpad.database.publishing \
        import PackagePublishing, SourcePackagePublishing

from canonical.launchpad.database.distroarchrelease import DistroArchRelease
from canonical.launchpad.database.potemplate import POTemplate

from canonical.launchpad.helpers import shortlist


class DistroRelease(SQLBase):
    """A particular release of a distribution."""
    implements(IDistroRelease)

    _table = 'DistroRelease'
    distribution = ForeignKey(dbName='distribution',
                              foreignKey='Distribution', notNull=True)
    bugtasks = MultipleJoin('BugTask', joinColumn='distrorelease')
    name = StringCol(notNull=True)
    displayname = StringCol(notNull=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    description = StringCol(notNull=True)
    version = StringCol(notNull=True)
    components = ForeignKey(
        dbName='components', foreignKey='Schema', notNull=True)
    sections = ForeignKey(
        dbName='sections', foreignKey='Schema', notNull=True)
    releasestatus = EnumCol(notNull=True, schema=DistributionReleaseStatus)
    datereleased = UtcDateTimeCol(notNull=False)
    parentrelease =  ForeignKey(
        dbName='parentrelease', foreignKey='DistroRelease', notNull=False)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person', notNull=True)
    lucilleconfig = StringCol(notNull=False)
    architectures = MultipleJoin(
        'DistroArchRelease', joinColumn='distrorelease')
    datelastlangpack = UtcDateTimeCol(dbName='datelastlangpack', notNull=False,
                                   default=None)

    @property
    def parent(self):
        """See canonical.launchpad.interfaces.distrorelease.IDistroRelease."""
        if self.parentrelease:
            return self.parentrelease.title
        return ''

    @property
    def status(self):
        return self.releasestatus.title

    @property
    def sourcecount(self):
        query = ('SourcePackagePublishing.status = %s '
                 'AND SourcePackagePublishing.distrorelease = %s'
                 % sqlvalues(PackagePublishingStatus.PUBLISHED, self.id))
        return SourcePackagePublishing.select(query).count()

    @property
    def binarycount(self):
        """See canonical.launchpad.interfaces.distrorelease.IDistroRelease."""
        clauseTables = ['DistroArchRelease']
        query = ('PackagePublishing.status = %s '
                 'AND PackagePublishing.distroarchrelease = '
                 'DistroArchRelease.id '
                 'AND DistroArchRelease.distrorelease = %s'
                 % sqlvalues(PackagePublishingStatus.PUBLISHED, self.id))
        return PackagePublishing.select(
            query, clauseTables=clauseTables).count()

    @property
    def architecturecount(self):
        """See canonical.launchpad.interfaces.distrorelease.IDistroRelease."""
        return len(list(self.architectures))

    @property
    def potemplates(self):
        result = POTemplate.selectBy(distroreleaseID=self.id)
        result = list(result)
        result.sort(key=lambda x: x.potemplatename.name)
        return result

    @property
    def potemplatecount(self):
        return len(self.potemplates)

    def getBugSourcePackages(self):
        """See canonical.launchpad.interfaces.distrorelease.IDistroRelease."""
        clauseTables=["BugTask",]
        query = ("VSourcePackageInDistro.distrorelease = %i AND "
                 "VSourcePackageInDistro.distro = BugTask.distribution AND "
                 "VSourcePackageInDistro.name = BugTask.sourcepackagename AND "
                 "(BugTask.status != %i OR BugTask.status != %i)"
                 % sqlvalues(
                    self.id, BugTaskStatus.FIXED, BugTaskStatus.REJECTED))

        return SourcePackageInDistro.select(
            query, clauseTables=clauseTables, distinct=True)

    def findSourcesByName(self, pattern):
        """Get SourcePackages in a DistroRelease with BugTask"""
        srcset = getUtility(ISourcePackageSet)
        return srcset.findByNameInDistroRelease(self.id, pattern)

    def __getitem__(self, arch):
        """Get SourcePackages in a DistroRelease with BugTask"""
        item = DistroArchRelease.selectOneBy(
            distroreleaseID=self.id, architecturetag=arch)
        if item is None:
            raise KeyError, 'Unknown architecture %s for %s %s' % (
                arch, self.distribution.name, self.name )
        return item

    def getPublishedReleases(self, sourcepackage_or_name):
        """See IDistroRelease."""
        if ISourcePackageName.providedBy(sourcepackage_or_name):
            sourcepackage = sourcepackage_or_name
        else:
            sourcepackage = sourcepackage_or_name.name
        published = SourcePackagePublishing.select(
            """
            distrorelease = %s AND
            status = %s AND
            sourcepackagerelease = sourcepackagerelease.id AND
            sourcepackagerelease.sourcepackagename = %s
            """ % sqlvalues(self.id,
                            PackagePublishingStatus.PUBLISHED,
                            sourcepackage.id),
            clauseTables = ['SourcePackageRelease'])
        return shortlist(published)


class DistroReleaseSet:
    implements(IDistroReleaseSet)

    def get(self, distroreleaseid):
        return DistroRelease.get(distroreleaseid)

    def translatables(self):
        return DistroRelease.select(
            "POTemplate.distrorelease=DistroRelease.id",
            clauseTables=['POTemplate'], distinct=True)

    def findByName(self, name):
        """See IDistroReleaseSet."""
        return DistroRelease.selectBy(name=name)

    def findByVersion(self, version):
        """See IDistroReleaseSet."""
        return DistroRelease.selectBy(version=version)
