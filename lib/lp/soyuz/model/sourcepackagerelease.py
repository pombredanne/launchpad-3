# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'SourcePackageRelease',
    '_filter_ubuntu_translation_file',
    ]


import apt_pkg
import datetime
from debian.changelog import (
    Changelog,
    ChangelogCreateError,
    ChangelogParseError,
    )
import operator
import re
from StringIO import StringIO

import pytz
import simplejson
from sqlobject import (
    ForeignKey,
    SQLMultipleJoin,
    StringCol,
    )
from storm.expr import Join
from storm.locals import (
    Int,
    Reference,
    )
from storm.store import Store
from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    cursor,
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.database.librarian import (
    LibraryFileAlias,
    LibraryFileContent,
    )
from canonical.launchpad.helpers import shortlist
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.archiveuploader.utils import determine_source_file_type
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.person import validate_public_person
from lp.registry.interfaces.sourcepackage import (
    SourcePackageType,
    SourcePackageUrgency,
    )
from lp.services.propertycache import cachedproperty
from lp.soyuz.enums import (
    PackageDiffStatus,
    PackagePublishingStatus,
    )
from lp.soyuz.interfaces.archive import MAIN_ARCHIVE_PURPOSES
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuildSet
from lp.soyuz.interfaces.packagediff import PackageDiffAlreadyRequested
from lp.soyuz.interfaces.sourcepackagerelease import ISourcePackageRelease
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.model.files import SourcePackageReleaseFile
from lp.soyuz.model.packagediff import PackageDiff
from lp.soyuz.model.publishing import SourcePackagePublishingHistory
from lp.soyuz.model.queue import (
    PackageUpload,
    PackageUploadSource,
    )
from lp.soyuz.scripts.queue import QueueActionError
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
    )


def _filter_ubuntu_translation_file(filename):
    """Filter for translation filenames in tarball.

    Grooms filenames of translation files in tarball, returning None or
    empty string for files that should be ignored.

    Passed to `ITranslationImportQueue.addOrUpdateEntriesFromTarball`.
    """
    source_prefix = 'source/'
    if not filename.startswith(source_prefix):
        return None

    filename = filename[len(source_prefix):]

    blocked_prefixes = [
        # Translations for use by debconf--not used in Ubuntu.
        'debian/po/',
        # Debian Installer translations--treated separately.
        'd-i/',
        # Documentation--not translatable in Launchpad.
        'help/',
        'man/po/',
        'man/po4a/',
        ]

    for prefix in blocked_prefixes:
        if filename.startswith(prefix):
            return None

    return filename


class SourcePackageRelease(SQLBase):
    implements(ISourcePackageRelease)
    _table = 'SourcePackageRelease'

    section = ForeignKey(foreignKey='Section', dbName='section')
    creator = ForeignKey(
        dbName='creator', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    component = ForeignKey(foreignKey='Component', dbName='component')
    sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
        dbName='sourcepackagename', notNull=True)
    maintainer = ForeignKey(
        dbName='maintainer', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    dscsigningkey = ForeignKey(foreignKey='GPGKey', dbName='dscsigningkey')
    urgency = EnumCol(dbName='urgency', schema=SourcePackageUrgency,
        default=SourcePackageUrgency.LOW, notNull=True)
    dateuploaded = UtcDateTimeCol(dbName='dateuploaded', notNull=True,
        default=UTC_NOW)
    dsc = StringCol(dbName='dsc')
    version = StringCol(dbName='version', notNull=True)
    changelog = ForeignKey(foreignKey='LibraryFileAlias', dbName='changelog')
    changelog_entry = StringCol(dbName='changelog_entry')
    builddepends = StringCol(dbName='builddepends')
    builddependsindep = StringCol(dbName='builddependsindep')
    build_conflicts = StringCol(dbName='build_conflicts')
    build_conflicts_indep = StringCol(dbName='build_conflicts_indep')
    architecturehintlist = StringCol(dbName='architecturehintlist')
    homepage = StringCol(dbName='homepage')
    format = EnumCol(dbName='format', schema=SourcePackageType,
        default=SourcePackageType.DPKG, notNull=True)
    upload_distroseries = ForeignKey(foreignKey='DistroSeries',
        dbName='upload_distroseries')
    upload_archive = ForeignKey(
        foreignKey='Archive', dbName='upload_archive', notNull=True)

    source_package_recipe_build_id = Int(name='sourcepackage_recipe_build')
    source_package_recipe_build = Reference(
        source_package_recipe_build_id, 'SourcePackageRecipeBuild.id')

    # XXX cprov 2006-09-26: Those fields are set as notNull and required in
    # ISourcePackageRelease, however they can't be not NULL in DB since old
    # records doesn't satisfy this condition. We will sort it before using
    # 'NoMoreAptFtparchive' implementation for PRIMARY archive. For PPA
    # (primary target) we don't need to populate old records.
    dsc_maintainer_rfc822 = StringCol(dbName='dsc_maintainer_rfc822')
    dsc_standards_version = StringCol(dbName='dsc_standards_version')
    dsc_format = StringCol(dbName='dsc_format')
    dsc_binaries = StringCol(dbName='dsc_binaries')

    # MultipleJoins
    files = SQLMultipleJoin('SourcePackageReleaseFile',
        joinColumn='sourcepackagerelease', orderBy="libraryfile")
    publishings = SQLMultipleJoin('SourcePackagePublishingHistory',
        joinColumn='sourcepackagerelease', orderBy="-datecreated")
    package_diffs = SQLMultipleJoin(
        'PackageDiff', joinColumn='to_source', orderBy="-date_requested")

    _user_defined_fields = StringCol(dbName='user_defined_fields')

    def __init__(self, *args, **kwargs):
        if 'user_defined_fields' in kwargs:
            kwargs['_user_defined_fields'] = simplejson.dumps(
                kwargs['user_defined_fields'])
            del kwargs['user_defined_fields']
        # copyright isn't on the Storm class, since we don't want it
        # loaded every time. Set it separately.
        if 'copyright' in kwargs:
            copyright = kwargs.pop('copyright')
        super(SourcePackageRelease, self).__init__(*args, **kwargs)
        self.copyright = copyright

    @property
    def copyright(self):
        """See `ISourcePackageRelease`."""
        store = Store.of(self)
        store.flush()
        return store.execute(
            "SELECT copyright FROM sourcepackagerelease WHERE id=%s",
            (self.id,)).get_one()[0]

    @copyright.setter
    def copyright(self, content):
        """See `ISourcePackageRelease`."""
        store = Store.of(self)
        store.flush()
        store.execute(
            "UPDATE sourcepackagerelease SET copyright=%s WHERE id=%s",
            (content, self.id))

    @property
    def user_defined_fields(self):
        """See `IBinaryPackageRelease`."""
        if self._user_defined_fields is None:
            return []
        return simplejson.loads(self._user_defined_fields)

    @property
    def builds(self):
        """See `ISourcePackageRelease`."""
        # Excluding PPA builds may seem like a strange thing to do but
        # when copy-package works for copying packages across archives,
        # a build may well have a different archive to the corresponding
        # sourcepackagerelease.
        return BinaryPackageBuild.select("""
            source_package_release = %s AND
            package_build = packagebuild.id AND
            archive.id = packagebuild.archive AND
            packagebuild.build_farm_job = buildfarmjob.id AND
            archive.purpose IN %s
            """ % sqlvalues(self.id, MAIN_ARCHIVE_PURPOSES),
            orderBy=['-buildfarmjob.date_created', 'id'],
            clauseTables=['Archive', 'PackageBuild', 'BuildFarmJob'])

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
            if build.status in [BuildStatus.NEEDSBUILD,
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
        # we avoid doing an extra query doing getSourcepackage.
        # XXX 2008-06-16 mpt bug=241298: cprov says this property "won't be as
        # useful as it looks once we start supporting derivation ... [It] is
        # dangerous and should be renamed (or removed)".
        series = self.upload_distroseries
        return series.getSourcePackage(self.sourcepackagename)

    @property
    def distrosourcepackage(self):
        """See ISourcePackageRelease."""
        # By supplying the sourcepackagename instead of its string name,
        # we avoid doing an extra query doing getSourcepackage
        distribution = self.upload_distroseries.distribution
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
            from lp.registry.model.sourcepackage import \
                 SourcePackage
            # Only process main archives and skip PPA/copy archives.
            if publishing.archive.purpose not in MAIN_ARCHIVE_PURPOSES:
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

    @property
    def current_publishings(self):
        """See ISourcePackageRelease."""
        from lp.soyuz.model.distroseriessourcepackagerelease \
            import DistroSeriesSourcePackageRelease
        return [DistroSeriesSourcePackageRelease(pub.distroseries, self)
                for pub in self.publishings]

    @property
    def published_archives(self):
        """See `ISourcePackageRelease`."""
        archives = set(
            pub.archive for pub in self.publishings.prejoin(['archive']))
        return sorted(archives, key=operator.attrgetter('id'))

    def addFile(self, file):
        """See ISourcePackageRelease."""
        return SourcePackageReleaseFile(
            sourcepackagerelease=self,
            filetype=determine_source_file_type(file.filename),
            libraryfile=file)

    def getPackageSize(self):
        """See ISourcePackageRelease."""
        size_query = """
            SELECT
                SUM(LibraryFileContent.filesize)/1024.0
            FROM
                SourcePackagereLease
                JOIN SourcePackageReleaseFile ON
                    SourcePackageReleaseFile.sourcepackagerelease =
                    SourcePackageRelease.id
                JOIN LibraryFileAlias ON
                    SourcePackageReleaseFile.libraryfile =
                    LibraryFileAlias.id
                JOIN LibraryFileContent ON
                    LibraryFileAlias.content = LibraryFileContent.id
            WHERE
                SourcePackageRelease.id = %s
            """ % sqlvalues(self)

        cur = cursor()
        cur.execute(size_query)
        results = cur.fetchone()

        if len(results) == 1 and results[0] is not None:
            return float(results[0])
        else:
            return 0.0

    def createBuild(self, distro_arch_series, pocket, archive, processor=None,
                    status=None):
        """See ISourcePackageRelease."""
        # Guess a processor if one is not provided
        if processor is None:
            pf = distro_arch_series.processorfamily
            # We guess at the first processor in the family
            processor = shortlist(pf.processors)[0]

        if status is None:
            status = BuildStatus.NEEDSBUILD

        # Force the current timestamp instead of the default
        # UTC_NOW for the transaction, avoid several row with
        # same datecreated.
        date_created = datetime.datetime.now(pytz.timezone('UTC'))

        return getUtility(IBinaryPackageBuildSet).new(
            distro_arch_series=distro_arch_series,
            source_package_release=self,
            processor=processor,
            status=status,
            date_created=date_created,
            pocket=pocket,
            archive=archive)

    def getBuildByArch(self, distroarchseries, archive):
        """See ISourcePackageRelease."""
        # First we try to follow any binaries built from the given source
        # in a distroarchseries with the given architecturetag and published
        # in the given (distroarchseries, archive) location.
        clauseTables = [
            'BinaryPackagePublishingHistory', 'BinaryPackageRelease',
            'DistroArchSeries']

        query = """
            BinaryPackageBuild.source_package_release = %s AND
            BinaryPackageRelease.build = BinaryPackageBuild.id AND
            DistroArchSeries.id = BinaryPackageBuild.distro_arch_series AND
            DistroArchSeries.architecturetag = %s AND
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackagePublishingHistory.distroarchseries = %s AND
            BinaryPackagePublishingHistory.archive = %s
        """ % sqlvalues(self, distroarchseries.architecturetag,
                        distroarchseries, archive)

        select_results = BinaryPackageBuild.select(
            query, clauseTables=clauseTables, distinct=True,
            orderBy='-BinaryPackageBuild.id')

        # XXX cprov 20080216: this if/elif/else block could be avoided or,
        # at least, simplified if SelectOne accepts 'distinct' argument.
        # The query above results in multiple identical builds for ..
        results = list(select_results)
        if len(results) == 1:
            # If there was any published binary we can use its original build.
            # This case covers the situations when both, source and binaries
            # got copied from another location.
            return results[0]
        elif len(results) > 1:
            # If more than one distinct build was found we have a problem.
            # A build was created when it shouldn't, possible due to bug
            # #181736. The broken build should be manually removed.
            raise AssertionError(
                    "Found more than one build candidate: %s. It possibly "
                    "means we have a serious problem in out DB model, "
                    "further investigation is required." %
                    [build.id for build in results])
        else:
            # If there was no published binary we have to try to find a
            # suitable build in all possible location across the distroseries
            # inheritance tree. See bellow.
            pass

        queries = [
            "BinaryPackageBuild.package_build = PackageBuild.id AND "
            "PackageBuild.build_farm_job = BuildFarmJob.id AND "
            "DistroArchSeries.id = BinaryPackageBuild.distro_arch_series AND "
            "PackageBuild.archive = %s AND "
            "DistroArchSeries.architecturetag = %s AND "
            "BinaryPackageBuild.source_package_release = %s" % (
            sqlvalues(archive.id, distroarchseries.architecturetag, self))]

        # Query only the last build record for this sourcerelease
        # across all possible locations.
        query = " AND ".join(queries)

        return BinaryPackageBuild.selectFirst(
            query, clauseTables=[
                'BuildFarmJob', 'PackageBuild', 'DistroArchSeries'],
            orderBy=['-BuildFarmJob.date_created'])

    def override(self, component=None, section=None, urgency=None):
        """See ISourcePackageRelease."""
        if component is not None:
            self.component = component
            # See if the new component requires a new archive:
            distribution = self.upload_distroseries.distribution
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
    def upload_changesfile(self):
        """See `ISourcePackageRelease`."""
        package_upload = self.package_upload
        # Cope with `SourcePackageRelease`s imported by gina, they do not
        # have a corresponding `PackageUpload` record.
        if package_upload is None:
            return None
        return package_upload.changesfile

    @property
    def package_upload(self):
        """See `ISourcepackageRelease`."""
        store = Store.of(self)
        # The join on 'changesfile' is not only used only for
        # pre-fetching the corresponding library file, so callsites
        # don't have to issue an extra query. It is also important
        # for excluding delayed-copies, because they might match
        # the publication context but will not contain as changesfile.
        origin = [
            PackageUploadSource,
            Join(PackageUpload,
                 PackageUploadSource.packageuploadID == PackageUpload.id),
            Join(LibraryFileAlias,
                 LibraryFileAlias.id == PackageUpload.changesfileID),
            Join(LibraryFileContent,
                 LibraryFileContent.id == LibraryFileAlias.contentID),
            ]
        results = store.using(*origin).find(
            (PackageUpload, LibraryFileAlias, LibraryFileContent),
            PackageUploadSource.sourcepackagerelease == self,
            PackageUpload.archive == self.upload_archive,
            PackageUpload.distroseries == self.upload_distroseries)

        # Return the unique `PackageUpload` record that corresponds to the
        # upload of this `SourcePackageRelease`, load the `LibraryFileAlias`
        # and the `LibraryFileContent` in cache because it's most likely
        # they will be needed.
        return DecoratedResultSet(results, operator.itemgetter(0)).one()

    @property
    def uploader(self):
        """See `ISourcePackageRelease`"""
        if self.source_package_recipe_build is not None:
            return self.source_package_recipe_build.requester
        if self.dscsigningkey is not None:
            return self.dscsigningkey.owner
        return None

    @property
    def change_summary(self):
        """See ISourcePackageRelease"""
        # this regex is copied from apt-listchanges.py courtesy of MDZ
        new_stanza_line = re.compile(
            '^\S+ \((?P<version>.*)\) .*;.*urgency=(?P<urgency>\w+).*')
        logfile = StringIO(self.changelog_entry)
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

    def attachTranslationFiles(self, tarball_alias, by_maintainer,
                               importer=None):
        """See ISourcePackageRelease."""
        tarball = tarball_alias.read()

        if importer is None:
            importer = getUtility(ILaunchpadCelebrities).rosetta_experts

        queue = getUtility(ITranslationImportQueue)

        only_templates = self.sourcepackage.has_sharing_translation_templates
        queue.addOrUpdateEntriesFromTarball(
            tarball, by_maintainer, importer,
            sourcepackagename=self.sourcepackagename,
            distroseries=self.upload_distroseries,
            filename_filter=_filter_ubuntu_translation_file,
            only_templates=only_templates)

    def getDiffTo(self, to_sourcepackagerelease):
        """See ISourcePackageRelease."""
        return PackageDiff.selectOneBy(
            from_source=self, to_source=to_sourcepackagerelease)

    def requestDiffTo(self, requester, to_sourcepackagerelease):
        """See ISourcePackageRelease."""
        candidate = self.getDiffTo(to_sourcepackagerelease)

        if candidate is not None:
            raise PackageDiffAlreadyRequested(
                "%s was already requested by %s"
                % (candidate.title, candidate.requester.displayname))

        if self.sourcepackagename.name == 'udev':
            # XXX 2009-11-23 Julian bug=314436
            # Currently diff output for udev will fill disks.  It's
            # disabled until diffutils is fixed in that bug.
            status = PackageDiffStatus.FAILED
        else:
            status = PackageDiffStatus.PENDING

        return PackageDiff(
            from_source=self, to_source=to_sourcepackagerelease,
            requester=requester, status=status)

    def aggregate_changelog(self, since_version):
        """See `ISourcePackagePublishingHistory`."""
        if self.changelog is None:
            return None

        apt_pkg.InitSystem()
        output = ""
        changelog = self.changelog
        try:
            for block in Changelog(changelog.read()):
                version = block._raw_version
                if (since_version and
                    apt_pkg.VersionCompare(version,  since_version) <= 0):
                    break
                try:
                    output += str(block)
                except ChangelogCreateError:
                    continue
                if not since_version:
                    # If a particular version was not requested we just
                    # return the most recent changelog entry.
                    break
        except ChangelogParseError:
            return None

        return output
