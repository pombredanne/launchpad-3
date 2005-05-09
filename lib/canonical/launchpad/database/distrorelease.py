# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Database classes for a distribution release."""

__metaclass__ = type

from zope.interface import implements
from zope.component import getUtility

from sqlobject import StringCol, ForeignKey, MultipleJoin, DateTimeCol

from canonical.database.sqlbase import SQLBase, sqlvalues
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
    datereleased = DateTimeCol(notNull=True)
    parentrelease =  ForeignKey(
        dbName='parentrelease', foreignKey='DistroRelease', notNull=False)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person', notNull=True)
    lucilleconfig = StringCol(notNull=False)
    architectures = MultipleJoin(
        'DistroArchRelease', joinColumn='distrorelease')

    def parent(self):
        """See canonical.launchpad.interfaces.distrorelease.IDistroRelease."""
        if self.parentrelease:
            return self.parentrelease.title
        return ''
    parent = property(parent)

    def status(self):
        return self.releasestatus.title
    status = property(status)

    def sourcecount(self):
        query = ('SourcePackagePublishing.status = %s '
                 'AND SourcePackagePublishing.distrorelease = %s'
                 % sqlvalues(PackagePublishingStatus.PUBLISHED, self.id))
        return SourcePackagePublishing.select(query).count()
    sourcecount = property(sourcecount)

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
    binarycount = property(binarycount)

    def architecturecount(self):
        """See canonical.launchpad.interfaces.distrorelease.IDistroRelease."""
        return len(list(self.architectures))

    def potemplates(self):
        return POTemplate.selectBy(distroreleaseID=self.id)
    potemplates = property(potemplates)

    def potemplatecount(self):
        return self.potemplates.count()
    potemplatecount = property(potemplatecount)

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

    def traverse(self, name):
        """Get SourcePackages in a DistroRelease with BugTask"""
        if name == '+sources':
            from canonical.launchpad.database.sourcepackage import \
                SourcePackageSet
            return SourcePackageSet(distrorelease=self)
        elif name  == '+packages':
            return PublishedPackageSet()
        else:
            return self.__getitem__(name)

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
