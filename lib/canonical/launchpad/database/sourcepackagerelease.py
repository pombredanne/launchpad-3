# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['SourcePackageRelease', 'SourcePackageReleaseSet']

import sets

from zope.interface import implements

from sqlobject import StringCol, ForeignKey, MultipleJoin

from canonical.launchpad.helpers import shortlist
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.lp.dbschema import (
    EnumCol, SourcePackageUrgency, SourcePackageFormat,
    SourcePackageFileType, BuildStatus, TicketStatus)

from canonical.launchpad.interfaces import (
    ISourcePackageRelease, ISourcePackageReleaseSet)

from canonical.launchpad.database.binarypackagerelease import (
     BinaryPackageRelease)

from canonical.launchpad.database.ticket import Ticket
from canonical.launchpad.database.build import Build
from canonical.launchpad.database.publishing import (
    SourcePackagePublishing)

from canonical.launchpad.database.files import SourcePackageReleaseFile

class SourcePackageRelease(SQLBase):
    implements(ISourcePackageRelease)
    _table = 'SourcePackageRelease'

    section = ForeignKey(foreignKey='Section', dbName='section')
    creator = ForeignKey(foreignKey='Person', dbName='creator', notNull=True)
    component = ForeignKey(foreignKey='Component', dbName='component')
    sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
        dbName='sourcepackagename', notNull=True)
    maintainer = ForeignKey(foreignKey='Person', dbName='maintainer',
        notNull=True)
    dscsigningkey = ForeignKey(foreignKey='GPGKey', dbName='dscsigningkey')
    manifest = ForeignKey(foreignKey='Manifest', dbName='manifest')
    urgency = EnumCol(dbName='urgency', schema=SourcePackageUrgency,
        default=SourcePackageUrgency.LOW, notNull=True)
    dateuploaded = UtcDateTimeCol(dbName='dateuploaded', notNull=True,
        default=UTC_NOW)
    dsc = StringCol(dbName='dsc')
    version = StringCol(dbName='version', notNull=True)
    changelog = StringCol(dbName='changelog')
    builddepends = StringCol(dbName='builddepends')
    builddependsindep = StringCol(dbName='builddependsindep')
    architecturehintlist = StringCol(dbName='architecturehintlist')
    format = EnumCol(dbName='format', schema=SourcePackageFormat,
        default=SourcePackageFormat.DPKG, notNull=True)
    uploaddistrorelease = ForeignKey(foreignKey='DistroRelease',
        dbName='uploaddistrorelease')

    builds = MultipleJoin('Build', joinColumn='sourcepackagerelease',
        orderBy=['-datecreated'])
    files = MultipleJoin('SourcePackageReleaseFile',
        joinColumn='sourcepackagerelease')
    publishings = MultipleJoin('SourcePackagePublishing',
        joinColumn='sourcepackagerelease')

    @property
    def latest_build(self):
        builds = self.builds
        if len(builds) > 0:
            return builds[0]
        return None

    @property
    def name(self):
        return self.sourcepackagename.name

    @property
    def sourcepackage(self):
        """See ISourcePackageRelease."""
        return self.uploaddistrorelease.getSourcePackage(self.name)

    @property
    def title(self):
        return '%s - %s' % (self.sourcepackagename.name, self.version)

    @property
    def productrelease(self):
        """See ISourcePackageRelease."""
        series = None

        # Use any published source package to find the product series.
        # We can do this because if we ever find out that a source package
        # release in two product series, we've almost certainly got a data
        # problem there.
        publishings = SourcePackagePublishing.selectBy(
            sourcepackagereleaseID=self.id)
        for publishing in publishings:
            # imports us, so avoid circular import
            from canonical.launchpad.database.sourcepackage import \
                 SourcePackage
            sp = SourcePackage(self.sourcepackagename,
                               publishing.distrorelease)
            sp_series = sp.productseries
            if sp_series is not None:
                if series is None:
                    series = sp_series
                elif series != sp_series:
                    # XXX: we could warn about this --keybuk 22jun05
                    pass

        # No series -- no release
        if series is None:
            return None

        # XXX: find any release with the exact same version, or which
        # we begin with and after a dash.  We could be more intelligent
        # about this, but for now this will work for most. --keybuk 22jun05
        for release in series.releases:
            if release.version == self.version:
                return release
            elif self.version.startswith("%s-" % release.version):
                return release
        else:
            return None

    @property
    def open_tickets_count(self):
        """See ISourcePackageRelease."""
        results = Ticket.select("""
            status IN (%s, %s) AND
            distribution = %s AND
            sourcepackagename = %s
            """ % sqlvalues(TicketStatus.NEW, TicketStatus.OPEN,
                            self.uploaddistrorelease.distribution.id,
                            self.sourcepackagename.id))
        return results.count()

    @property
    def binaries(self):
        clauseTables = ['SourcePackageRelease', 'BinaryPackageRelease',
                        'Build']
        query = ('SourcePackageRelease.id = Build.sourcepackagerelease'
                 ' AND BinaryPackageRelease.build = Build.id '
                 ' AND Build.sourcepackagerelease = %i' % self.id)
        return BinaryPackageRelease.select(query, clauseTables=clauseTables)

    @property
    def meta_binaries(self):
        """See ISourcePackageRelease."""        
        return [binary.build.distroarchrelease.distrorelease.getBinaryPackage(
                                    binary.binarypackagename)
                for binary in self.binaries]

    @property
    def current_publishings(self):
        """See ISourcePackageRelease."""
        from canonical.launchpad.database.distroreleasesourcepackagerelease \
            import DistroReleaseSourcePackageRelease
        return[DistroReleaseSourcePackageRelease(
            publishing.distrorelease,
            self) for publishing in self.publishings]


    def architecturesReleased(self, distroRelease):
        # The import is here to avoid a circular import. See top of module.
        from canonical.launchpad.database.soyuz import DistroArchRelease
        clauseTables = ['BinaryPackagePublishing', 'BinaryPackageRelease',
                        'Build']

        archReleases = sets.Set(DistroArchRelease.select(
            'BinaryPackagePublishing.distroarchrelease = DistroArchRelease.id '
            'AND DistroArchRelease.distrorelease = %d '
            'AND BinaryPackagePublishing.binarypackagerelease = '
            'BinaryPackageRelease.id '
            'AND BinaryPackageRelease.build = Build.id '
            'AND Build.sourcepackagerelease = %d'
            % (distroRelease.id, self.id),
            clauseTables=clauseTables))
        return archReleases

    def addFile(self, file):
        """See ISourcePackageRelease."""
        determined_filetype = None
        if file.filename.endswith(".dsc"):
            determined_filetype = SourcePackageFileType.DSC
        elif file.filename.endswith(".orig.tar.gz"):
            determined_filetype = SourcePackageFileType.ORIG
        elif file.filename.endswith(".diff.gz"):
            determined_filetype = SourcePackageFileType.DIFF
        elif file.filename.endswith(".tar.gz"):
            determined_filetype = SourcePackageFileType.TARBALL

        return SourcePackageReleaseFile(sourcepackagerelease=self.id,
                                        filetype=determined_filetype,
                                        libraryfile=file.id)

    def createBuild(self, distroarchrelease, processor=None,
                    status=BuildStatus.NEEDSBUILD):
        """See ISourcePackageRelease."""
        # Guess a processor if one is not provided
        if processor is None:
            pf = distroarchrelease.processorfamily
            # We guess at the first processor in the family
            processor = shortlist(pf.processors)[0]

        return Build(distroarchrelease=distroarchrelease.id,
                     sourcepackagerelease=self.id,
                     processor=processor.id, buildstate=status)


    def getBuildByArch(self, distroarchrelease):
        """See ISourcePackageRelease."""
        return Build.selectOneBy(sourcepackagereleaseID=self.id,
                                 distroarchreleaseID=distroarchrelease.id)


class SourcePackageReleaseSet:

    implements(ISourcePackageReleaseSet)

    def getByCreator(self, creator):
        """See ISourcePackageReleaseSet."""
        querystr = """sourcepackagerelease.creator = %d AND
                      sourcepackagerelease.sourcepackagename =
                      sourcepackagename.id""" % creator.id
        return SourcePackageRelease.select(
            querystr,
            orderBy='SourcePackageName.name',
            clauseTables=['SourcePackageName'])

    def getByMaintainer(self, maintainer):
        """See ISourcePackageReleaseSet."""
        querystr = """sourcepackagerelease.maintainer = %d AND
                      sourcepackagerelease.sourcepackagename = 
                      sourcepackagename.id""" % maintainer.id
        return SourcePackageRelease.select(
            querystr,
            orderBy='SourcePackageName.name',
            clauseTables=['SourcePackageName'])

