# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['SourcePackageRelease']

import sets
import tarfile
from StringIO import StringIO
import datetime
import pytz
import re

from zope.interface import implements
from zope.component import getUtility

from sqlobject import StringCol, ForeignKey, SQLMultipleJoin

from canonical.cachedproperty import cachedproperty

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol

from canonical.lp.dbschema import (
    ArchivePurpose, SourcePackageUrgency, SourcePackageFormat,
    SourcePackageFileType, BuildStatus, PackagePublishingStatus)

from canonical.librarian.interfaces import ILibrarianClient

from canonical.launchpad.helpers import shortlist
from canonical.launchpad.searchbuilder import any
from canonical.launchpad.interfaces import (
    BugTaskSearchParams, ILaunchpadCelebrities, ISourcePackageRelease,
    ITranslationImportQueue, UNRESOLVED_BUGTASK_STATUSES
    )
from canonical.launchpad.database.build import Build
from canonical.launchpad.database.files import SourcePackageReleaseFile
from canonical.launchpad.database.publishing import (
    SourcePackagePublishingHistory)
from canonical.launchpad.scripts.queue import QueueActionError


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
    urgency = EnumCol(dbName='urgency', schema=SourcePackageUrgency,
        default=SourcePackageUrgency.LOW, notNull=True)
    dateuploaded = UtcDateTimeCol(dbName='dateuploaded', notNull=True,
        default=UTC_NOW)
    dsc = StringCol(dbName='dsc')
    copyright = StringCol(dbName='copyright', notNull=True)
    version = StringCol(dbName='version', notNull=True)
    changelog = StringCol(dbName='changelog')
    builddepends = StringCol(dbName='builddepends')
    builddependsindep = StringCol(dbName='builddependsindep')
    architecturehintlist = StringCol(dbName='architecturehintlist')
    format = EnumCol(dbName='format', schema=SourcePackageFormat,
        default=SourcePackageFormat.DPKG, notNull=True)
    uploaddistroseries = ForeignKey(foreignKey='DistroSeries',
        dbName='uploaddistrorelease')
    upload_archive = ForeignKey(
        foreignKey='Archive', dbName='upload_archive', notNull=True)

    # XXX cprov 2006-09-26: Those fields are set as notNull and required in
    # ISourcePackageRelease, however they can't be not NULL in DB since old
    # records doesn't satisfy this condition. We will sort it before using
    # landing 'NoMoreAptFtparchive' implementation for main archive. For
    # PPA (primary target) we don't need populate old records.
    dsc_maintainer_rfc822 = StringCol(dbName='dsc_maintainer_rfc822')
    dsc_standards_version = StringCol(dbName='dsc_standards_version')
    dsc_format = StringCol(dbName='dsc_format')
    dsc_binaries = StringCol(dbName='dsc_binaries')

    # MultipleJoins
    files = SQLMultipleJoin('SourcePackageReleaseFile',
        joinColumn='sourcepackagerelease', orderBy="libraryfile")
    publishings = SQLMultipleJoin('SourcePackagePublishingHistory',
        joinColumn='sourcepackagerelease', orderBy="-datecreated")

    @property
    def builds(self):
        """See `ISourcePackageRelease`."""
        # Excluding PPA builds may seem like a string thing to do but
        # when copy-package works for copying packages across archives,
        # a build may well have a different archive to the corresponding
        # sourcepackagerelease.
        return Build.select("""
            sourcepackagerelease = %s AND
            archive.id = build.archive AND
            archive.purpose != %s
            """ % sqlvalues(self.id, ArchivePurpose.PPA),
            clauseTables=['Archive'])

    @property
    def age(self):
        """See ISourcePackageRelease."""
        now = datetime.datetime.now(pytz.timezone('UTC'))
        return now - self.dateuploaded

    @property
    def latest_build(self):
        builds = self._cached_builds
        if len(builds) > 0:
            return builds[0]
        return None

    def failed_builds(self):
        return [build for build in self._cached_builds
                if build.buildstate == BuildStatus.FAILEDTOBUILD]

    @property
    def needs_building(self):
        for build in self._cached_builds:
            if build.buildstate in [BuildStatus.NEEDSBUILD,
                                    BuildStatus.MANUALDEPWAIT,
                                    BuildStatus.CHROOTWAIT]:
                return True
        return False

    @cachedproperty
    def _cached_builds(self):
        # The reason we have this as a cachedproperty is that all the
        # *build* methods here need access to it; better not to
        # recalculate it multiple times.
        return list(self.builds)

    @property
    def name(self):
        return self.sourcepackagename.name

    @property
    def sourcepackage(self):
        """See ISourcePackageRelease."""
        # By supplying the sourcepackagename instead of its string name,
        # we avoid doing an extra query doing getSourcepackage
        series = self.uploaddistroseries
        return series.getSourcePackage(self.sourcepackagename)

    @property
    def distrosourcepackage(self):
        """See ISourcePackageRelease."""
        # By supplying the sourcepackagename instead of its string name,
        # we avoid doing an extra query doing getSourcepackage
        distribution = self.uploaddistroseries.distribution
        return distribution.getSourcePackage(self.sourcepackagename)

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
        publishings = SourcePackagePublishingHistory.select(
            """
            sourcepackagerelease = %s AND
            status = %s
            """ % sqlvalues(self, PackagePublishingStatus.PUBLISHED))

        for publishing in publishings:
            # imports us, so avoid circular import
            from canonical.launchpad.database.sourcepackage import \
                 SourcePackage
            # Only process main archives to skip PPA publishings.
            if publishing.archive.purpose == ArchivePurpose.PPA:
                continue
            sp = SourcePackage(self.sourcepackagename,
                               publishing.distroseries)
            sp_series = sp.productseries
            if sp_series is not None:
                if series is None:
                    series = sp_series
                elif series != sp_series:
                    # XXX: keybuk 2005-06-22: We could warn about this.
                    pass

        # No series -- no release
        if series is None:
            return None

        # XXX: keybuk 2005-06-22:
        # Find any release with the exact same version, or which
        # we begin with and after a dash.  We could be more intelligent
        # about this, but for now this will work for most.
        for release in series.releases:
            if release.version == self.version:
                return release
            elif self.version.startswith("%s-" % release.version):
                return release
        else:
            return None

    def countOpenBugsInUploadedDistro(self, user):
        """See ISourcePackageRelease."""
        upload_distro = self.uploaddistroseries.distribution
        params = BugTaskSearchParams(sourcepackagename=self.sourcepackagename,
            user=user, status=any(*UNRESOLVED_BUGTASK_STATUSES))
        # XXX: kiko 2006-03-07:
        # We need to omit duplicates here or else our bugcounts are
        # inconsistent. This is a wart, and we need to stop spreading
        # these things over the code.
        params.omit_dupes = True
        return upload_distro.searchTasks(params).count()

    @property
    def current_publishings(self):
        """See ISourcePackageRelease."""
        from canonical.launchpad.database.distroseriessourcepackagerelease \
            import DistroSeriesSourcePackageRelease
        return [DistroSeriesSourcePackageRelease(pub.distroseries, self)
                for pub in self.publishings]

    def architecturesReleased(self, distroseries):
        # The import is here to avoid a circular import. See top of module.
        from canonical.launchpad.database.soyuz import DistroArchSeries
        clauseTables = ['BinaryPackagePublishingHistory',
                        'BinaryPackageRelease',
                        'Build']
        # XXX cprov 2006-08-23: Will distinct=True help us here?
        archSerieses = sets.Set(DistroArchSeries.select(
            """
            BinaryPackagePublishingHistory.distroarchrelease =
               DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %d AND
            BinaryPackagePublishingHistory.archive IN %s AND
            BinaryPackagePublishingHistory.binarypackagerelease =
               BinaryPackageRelease.id AND
            BinaryPackageRelease.build = Build.id AND
            Build.sourcepackagerelease = %d
            """ % (distroseries,
                   distroseries.distribution.all_distro_archive_ids,
                   self),
            clauseTables=clauseTables))

        return archSerieses

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

        return SourcePackageReleaseFile(sourcepackagerelease=self,
                                        filetype=determined_filetype,
                                        libraryfile=file)

    def createBuild(self, distroarchseries, pocket, archive, processor=None,
                    status=BuildStatus.NEEDSBUILD):
        """See ISourcePackageRelease."""
        # Guess a processor if one is not provided
        if processor is None:
            pf = distroarchseries.processorfamily
            # We guess at the first processor in the family
            processor = shortlist(pf.processors)[0]

        # force the current timestamp instead of the default
        # UTC_NOW for the transaction, avoid several row with
        # same datecreated.
        datecreated = datetime.datetime.now(pytz.timezone('UTC'))

        return Build(distroarchseries=distroarchseries,
                     sourcepackagerelease=self,
                     processor=processor,
                     buildstate=status,
                     datecreated=datecreated,
                     pocket=pocket,
                     archive=archive)

    def getBuildByArch(self, distroarchseries, archive):
        """See ISourcePackageRelease."""
        # Look for a published build
        query = """
        Build.id = BinaryPackageRelease.build AND
        BinaryPackageRelease.id =
            BinaryPackagePublishingHistory.binarypackagerelease AND
        BinaryPackagePublishingHistory.distroarchrelease = %s AND
        BinaryPackagePublishingHistory.archive = %s AND
        Build.sourcepackagerelease = %s
        """  % sqlvalues(distroarchseries, archive, self)

        tables = ['BinaryPackageRelease', 'BinaryPackagePublishingHistory']

        # We are using selectFirst() to eliminate the multiple results of
        # the same build record originated by the multiple binary join paths
        # ( a build which produces multiple binaries). The use of:
        #  select(..., distinct=True)
        # would be clearer, however the SelectResult returned would require
        # nasty code.
        build = Build.selectFirst(query, clauseTables=tables, orderBy="id")

        # If not, look for a build directly in this distroarchseries.
        if build is None:
            build = Build.selectOneBy(
                distroarchseries=distroarchseries,
                archive=archive,
                sourcepackagerelease=self)

        return build

    def override(self, component=None, section=None, urgency=None):
        """See ISourcePackageRelease."""
        if component is not None:
            self.component = component
            # See if the new component requires a new archive:
            distribution = self.uploaddistroseries.distribution
            new_archive = distribution.getArchiveByComponent(component.name)
            if new_archive is not None:
                self.upload_archive = new_archive
            else:
                raise QueueActionError(
                    "New component '%s' requires a non-existent archive.")
        if section is not None:
            self.section = section
        if urgency is not None:
            self.urgency = urgency

    @property
    def change_summary(self):
        """See ISourcePackageRelease"""
        # this regex is copied from apt-listchanges.py courtesy of MDZ
        new_stanza_line = re.compile(
            '^\S+ \((?P<version>.*)\) .*;.*urgency=(?P<urgency>\w+).*')
        logfile = StringIO(self.changelog)
        change = ''
        top_stanza = False
        for line in logfile.readlines():
            match = new_stanza_line.match(line)
            if match:
                if top_stanza:
                    break
                top_stanza = True
            change += line

        return change

    def attachTranslationFiles(self, tarball_alias, is_published,
        importer=None):
        """See ISourcePackageRelease."""
        client = getUtility(ILibrarianClient)

        tarball_file = client.getFileByAlias(tarball_alias.id)
        tarball = tarfile.open('', 'r', StringIO(tarball_file.read()))

        # Get the list of files to attach.
        filenames = [name for name in tarball.getnames()
                     if name.startswith('source/') or name.startswith('./source/')
                     if name.endswith('.pot') or name.endswith('.po')
                     ]

        if importer is None:
            importer = getUtility(ILaunchpadCelebrities).rosetta_expert

        translation_import_queue_set = getUtility(ITranslationImportQueue)

        # Attach all files
        for filename in filenames:
            # Fetch the file
            content = tarball.extractfile(filename).read()
            if len(content) == 0:
                # The file is empty, we ignore it.
                continue
            if filename.startswith('source/'):
                # Remove the special 'source/' prefix for the path.
                filename = filename[len('source/'):]
            elif filename.startswith('./source/'):
                # Remove the special './source/' prefix for the path.
                filename = filename[len('./source/'):]
            # Add it to the queue.
            translation_import_queue_set.addOrUpdateEntry(
                filename, content, is_published, importer,
                sourcepackagename=self.sourcepackagename,
                distroseries=self.uploaddistroseries)

