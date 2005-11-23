# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Build', 'BuildSet']

from urllib2 import URLError

from zope.interface import implements
from zope.component import getUtility

# SQLObject/SQLBase
from sqlobject import (
    StringCol, ForeignKey, IntervalCol, MultipleJoin)
from sqlobject.sqlbuilder import AND, IN

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.helpers import shortlist

from canonical.launchpad.interfaces import (
    IBuild, IBuildSet)

from canonical.launchpad.database.binarypackagerelease import (
    BinaryPackageRelease)
from canonical.launchpad.database.builder import BuildQueue

from canonical.librarian.interfaces import ILibrarianClient


from canonical.lp.dbschema import EnumCol, BuildStatus


class Build(SQLBase):
    implements(IBuild)
    _table = 'Build'

    datecreated = UtcDateTimeCol(dbName='datecreated', default=UTC_NOW)
    processor = ForeignKey(dbName='processor', foreignKey='Processor', 
        notNull=True)
    distroarchrelease = ForeignKey(dbName='distroarchrelease', 
        foreignKey='DistroArchRelease', notNull=True)
    buildstate = EnumCol(dbName='buildstate', notNull=True, schema=BuildStatus)
    sourcepackagerelease = ForeignKey(dbName='sourcepackagerelease',
        foreignKey='SourcePackageRelease', notNull=True)
    datebuilt = UtcDateTimeCol(dbName='datebuilt', default=None)
    buildduration = IntervalCol(dbName='buildduration', default=None)
    buildlog = ForeignKey(dbName='buildlog', foreignKey='LibraryFileAlias',
        default=None)
    builder = ForeignKey(dbName='builder', foreignKey='Builder',
        default=None)
    gpgsigningkey = ForeignKey(dbName='gpgsigningkey', foreignKey='GPGKey',
        default=None)
    changes = StringCol(dbName='changes', default=None)

    @property
    def buildqueue_record(self):
        """See IBuild"""
        # XXX cprov 20051025
        # Would be nice if we can use fresh sqlobject feature 'singlejoin'
        # instead, see bug # 3424
        return BuildQueue.selectOneBy(buildID=self.id)

    @property
    def distrorelease(self):
        """See IBuild"""
        return self.distroarchrelease.distrorelease

    @property
    def distribution(self):
        """See IBuild"""
        return self.distroarchrelease.distrorelease.distribution

    @property
    def title(self):
        """See IBuild"""
        return '%s build of %s %s in %s %s (%s)' % (
            self.distroarchrelease.architecturetag,
            self.sourcepackagerelease.name,
            self.sourcepackagerelease.version,
            self.distroarchrelease.distrorelease.distribution.name,
            self.distroarchrelease.distrorelease.name,
            self.datecreated.strftime('%Y-%m-%d'))

    @property
    def build_icon(self):
        """See IBuild"""
        icon_map = {
            BuildStatus.NEEDSBUILD: "/++resource++build-success",
            BuildStatus.FULLYBUILT: "/++resource++build-success",
            BuildStatus.FAILEDTOBUILD: "/++resource++build-failure",
            BuildStatus.MANUALDEPWAIT: "/++resource++build-failure",
            BuildStatus.CHROOTWAIT: "/++resource++build-failure",
            }
        return icon_map[self.buildstate]

    @property
    def distributionsourcepackagerelease(self):
        """See IBuild."""
        return DistributionSourcePackageRelease(
            distribution=self.distroarchrelease.distrorelease.distribution,
            sourcepackagerelease=self.sourcepackagerelease)

    @property
    def binarypackages(self):
        """See IBuild."""
        bpklist = shortlist(BinaryPackageRelease.selectBy(buildID=self.id))
        return sorted(bpklist, key=lambda a: a.binarypackagename.name)

    def __getitem__(self, name):
        return self.getBinaryPackageRelease(name)

    def getBinaryPackageRelease(self, name):
        """See IBuild."""
        for binpkg in self.binarypackages:
            if binpkg.name == name:
                return binpkg
        raise IndexError, 'No binary package "%s" in build' % name

    def createBinaryPackageRelease(self, binarypackagename, version,
                                   summary, description,
                                   binpackageformat, component,
                                   section, priority, shlibdeps,
                                   depends, recommends, suggests,
                                   conflicts, replaces, provides,
                                   essential, installedsize,
                                   copyright, licence,
                                   architecturespecific):
        
        """See IBuild."""
        
        return BinaryPackageRelease(buildID=self.id,
                                    binarypackagenameID=binarypackagename,
                                    version=version,
                                    summary=summary,
                                    description=description,
                                    binpackageformat=binpackageformat,
                                    componentID=component,
                                    sectionID=section,
                                    priority=priority,
                                    shlibdeps=shlibdeps,
                                    depends=depends,
                                    recommends=recommends,
                                    suggests=suggests,
                                    conflicts=conflicts,
                                    replaces=replaces,
                                    provides=provides,
                                    essential=essential,
                                    installedsize=installedsize,
                                    copyright=copyright,
                                    licence=licence,
                                    architecturespecific=architecturespecific)

    def createBuildQueueEntry(self):
        """See IBuild"""
        return BuildQueue(build=self.id)


class BuildSet:
    implements(IBuildSet)

    def getBuildBySRAndArchtag(self, sourcepackagereleaseID, archtag):
        """See IBuildSet"""
        clauseTables = ['DistroArchRelease']
        query = ('Build.sourcepackagerelease = %s '
                 'AND Build.distroarchrelease = DistroArchRelease.id '
                 'AND DistroArchRelease.architecturetag = %s'
                 % sqlvalues(sourcepackagereleaseID, archtag)
                 )

        return Build.select(query, clauseTables=clauseTables)

    def getByBuildID(self, id):
        """See IBuildSet."""
        return Build.get(id)

    def getPendingBuildsForArchSet(self, archreleases):
        """See IBuildSet."""
        archrelease_ids = [d.id for d in archreleases]

        return Build.select(
            AND(Build.q.buildstate==BuildStatus.NEEDSBUILD,
                IN(Build.q.distroarchreleaseID, archrelease_ids))
            )                                  
        
    def getBuildsForBuilder(self, builder_id, status=None):
        """See IBuildSet."""
        status_clause = ''
        if status:
            status_clause = "AND buildstate=%" % sqlvalues(status)

        return Build.select(
            "builder=%s %s" % (builder_id, status_clause),
            orderBy="-datebuilt")
