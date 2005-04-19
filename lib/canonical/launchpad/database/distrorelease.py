# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Database classes for a distribution release."""

__metaclass__ = type

from sets import Set

# Zope imports
from zope.interface import implements
from zope.component import getUtility

# SQLObject/SQLBase
from sqlobject import MultipleJoin
from sqlobject import StringCol, ForeignKey, MultipleJoin, BoolCol

from canonical.database.sqlbase import SQLBase
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.lp.dbschema import PackagePublishingStatus, BugTaskStatus, \
     EnumCol, DistributionReleaseStatus

# interfaces and database
from canonical.launchpad.interfaces import IDistroRelease, IPOTemplateSet, \
     IDistroReleaseSet, ISourcePackageName

from canonical.launchpad.database.sourcepackageindistro \
        import SourcePackageInDistro
from canonical.launchpad.database.publishedpackage import PublishedPackageSet
from canonical.launchpad.database.publishing \
        import PackagePublishing, SourcePackagePublishing
from canonical.launchpad.database import SourcePackageSet

from canonical.launchpad.database.distroarchrelease import DistroArchRelease
from canonical.launchpad.database.potemplate import POTemplate

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
    shortdesc = StringCol(notNull=True)
    description = StringCol(notNull=True)
    version = StringCol(notNull=True)
    components = ForeignKey(
        dbName='components', foreignKey='Schema', notNull=True)
    sections = ForeignKey(
        dbName='sections', foreignKey='Schema', notNull=True)
    releasestatus = EnumCol(notNull=True,
                            schema=DistributionReleaseStatus)
    datereleased = UtcDateTimeCol(notNull=True)
    parentrelease =  ForeignKey(
        dbName='parentrelease', foreignKey='DistroRelease', notNull=False)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person', notNull=True)
    lucilleconfig = StringCol(notNull=False)
    architectures = MultipleJoin('DistroArchRelease',
            joinColumn='distrorelease')

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
                 % (PackagePublishingStatus.PUBLISHED.value,
                    self.id))
        return SourcePackagePublishing.select(query).count()
    sourcecount = property(sourcecount)

    def binarycount(self):
        """See canonical.launchpad.interfaces.distrorelease.IDistroRelease."""
        clauseTables = ('DistroArchRelease',)
        query = ('PackagePublishing.status = %s '
                 'AND PackagePublishing.distroarchrelease = '
                 'DistroArchRelease.id '
                 'AND DistroArchRelease.distrorelease = %s'
                 % (PackagePublishingStatus.PUBLISHED.value,
                    self.id))
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
                 %(self.id,
                   BugTaskStatus.FIXED,
                   BugTaskStatus.REJECTED))

        return SourcePackageInDistro.select(
            query, clauseTables=clauseTables, distinct=True)

    def findSourcesByName(self, pattern):
        """Get SourcePackages in a DistroRelease with BugTask"""
        srcset = getUtility(ISourcePackageSet)
        return srcset.findByNameInDistroRelease(self.id, pattern)

    def traverse(self, name):
        """Get SourcePackages in a DistroRelease with BugTask"""
        if name == '+sources':
            return SourcePackageSet(distrorelease=self)
        elif name  == '+packages':
            return PublishedPackageSet()
        else:
            return self.__getitem__(name)

    def __getitem__(self, arch):
        """Get SourcePackages in a DistroRelease with BugTask"""
        try:
            return DistroArchRelease.selectBy(distroreleaseID=self.id,
                                              architecturetag=arch)[0]
        except:
            raise KeyError, 'Unknown architecture %s for %s %s' % (
                      arch,
                      self.distribution.name,
                      self.name )
            
    def getPublishedReleases(self, sourcepackage_or_name):
        """See IDistroRelease."""
        if ISourcePackageName.providedBy(sourcepackage_or_name):
            sourcepackage = sourcepackage_or_name
        else:
            sourcepackage = sourcepackage_or_name.name
        published = SourcePackagePublishing.select(
            """
            distrorelease = %d AND
            status = %d AND
            sourcepackagerelease = sourcepackagerelease.id AND
            sourcepackagerelease.sourcepackagename = %d
            """ % (self.id,
                   PackagePublishingStatus.PUBLISHED.value,
                   sourcepackage.id),
            clauseTables = [ 'SourcePackageRelease' ])
        return list(published)

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
