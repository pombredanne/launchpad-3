# Copyright 2009-2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'BinaryPackageBuild',
    'BinaryPackageBuildSet',
    'COPY_ARCHIVE_SCORE_PENALTY',
    'PRIVATE_ARCHIVE_SCORE_BONUS',
    'SCORE_BY_COMPONENT',
    'SCORE_BY_POCKET',
    'SCORE_BY_URGENCY',
    ]

import datetime
from operator import (
    attrgetter,
    itemgetter,
    )

import apt_pkg
import pytz
from sqlobject import SQLObjectNotFound
from storm.expr import (
    And,
    Desc,
    Exists,
    Join,
    LeftJoin,
    Or,
    Select,
    )
from storm.locals import (
    Bool,
    DateTime,
    Int,
    Reference,
    Unicode,
    )
from storm.store import (
    EmptyResultSet,
    Store,
    )
from storm.zope import IResultSet
from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from lp.app.browser.tales import DurationFormatterAPI
from lp.app.errors import NotFoundError
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.archivepublisher.utils import get_ppa_reference
from lp.buildmaster.enums import (
    BuildFarmJobType,
    BuildStatus,
    )
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobSource
from lp.buildmaster.model.builder import Builder
from lp.buildmaster.model.buildfarmjob import (
    BuildFarmJob,
    SpecificBuildFarmJobSourceMixin,
    )
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.buildmaster.model.packagebuild import PackageBuildMixin
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.interfaces.sourcepackage import SourcePackageUrgency
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.services.config import config
from lp.services.database.bulk import load_related
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.enumcol import DBEnum
from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import (
    SQLBase,
    sqlvalues,
    )
from lp.services.librarian.browser import ProxiedLibraryFileAlias
from lp.services.librarian.model import (
    LibraryFileAlias,
    LibraryFileContent,
    )
from lp.services.mail.helpers import (
    get_contact_email_addresses,
    get_email_template,
    )
from lp.services.mail.sendmail import (
    format_address,
    simple_sendmail,
    )
from lp.services.webapp import canonical_url
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.soyuz.adapters.buildarch import determine_architectures_to_build
from lp.soyuz.interfaces.binarypackagebuild import (
    BuildSetStatus,
    CannotBeRescored,
    IBinaryPackageBuild,
    IBinaryPackageBuildSet,
    UnparsableDependencies,
    )
from lp.soyuz.interfaces.distroarchseries import IDistroArchSeries
from lp.soyuz.interfaces.packageset import IPackagesetSet
from lp.soyuz.model.binarypackagename import BinaryPackageName
from lp.soyuz.model.binarypackagerelease import BinaryPackageRelease
from lp.soyuz.model.files import BinaryPackageFile
from lp.soyuz.model.packageset import Packageset
from lp.soyuz.model.queue import (
    PackageUpload,
    PackageUploadBuild,
    )


SCORE_BY_POCKET = {
    PackagePublishingPocket.BACKPORTS: 0,
    PackagePublishingPocket.RELEASE: 1500,
    PackagePublishingPocket.PROPOSED: 3000,
    PackagePublishingPocket.UPDATES: 3000,
    PackagePublishingPocket.SECURITY: 4500,
}


SCORE_BY_COMPONENT = {
    'multiverse': 0,
    'universe': 250,
    'restricted': 750,
    'main': 1000,
    'partner': 1250,
}


SCORE_BY_URGENCY = {
    SourcePackageUrgency.LOW: 5,
    SourcePackageUrgency.MEDIUM: 10,
    SourcePackageUrgency.HIGH: 15,
    SourcePackageUrgency.EMERGENCY: 20,
}


PRIVATE_ARCHIVE_SCORE_BONUS = 10000


# Rebuilds have usually a lower priority than other builds.
# This will be subtracted from the final score, usually taking it
# below 0, ensuring they are built only when nothing else is waiting
# in the build farm.
COPY_ARCHIVE_SCORE_PENALTY = 2600


class BinaryPackageBuild(PackageBuildMixin, SQLBase):
    implements(IBinaryPackageBuild)
    _table = 'BinaryPackageBuild'
    _defaultOrder = 'id'

    job_type = BuildFarmJobType.PACKAGEBUILD

    build_farm_job_id = Int(name='build_farm_job')
    build_farm_job = Reference(build_farm_job_id, BuildFarmJob.id)

    distro_arch_series_id = Int(name='distro_arch_series', allow_none=False)
    distro_arch_series = Reference(
        distro_arch_series_id, 'DistroArchSeries.id')
    source_package_release_id = Int(
        name='source_package_release', allow_none=False)
    source_package_release = Reference(
        source_package_release_id, 'SourcePackageRelease.id')

    archive_id = Int(name='archive', allow_none=False)
    archive = Reference(archive_id, 'Archive.id')

    pocket = DBEnum(
        name='pocket', enum=PackagePublishingPocket, allow_none=False)

    arch_indep = Bool()

    upload_log_id = Int(name='upload_log')
    upload_log = Reference(upload_log_id, 'LibraryFileAlias.id')

    dependencies = Unicode(name='dependencies')

    processor_id = Int(name='processor')
    processor = Reference(processor_id, 'Processor.id')
    virtualized = Bool(name='virtualized')

    date_created = DateTime(
        name='date_created', tzinfo=pytz.UTC, allow_none=False)
    date_started = DateTime(name='date_started', tzinfo=pytz.UTC)
    date_finished = DateTime(name='date_finished', tzinfo=pytz.UTC)
    date_first_dispatched = DateTime(
        name='date_first_dispatched', tzinfo=pytz.UTC)

    builder_id = Int(name='builder')
    builder = Reference(builder_id, 'Builder.id')

    status = DBEnum(name='status', enum=BuildStatus, allow_none=False)

    log_id = Int(name='log')
    log = Reference(log_id, 'LibraryFileAlias.id')

    failure_count = Int(name='failure_count', allow_none=False)

    distribution_id = Int(name='distribution', allow_none=False)
    distribution = Reference(distribution_id, 'Distribution.id')

    distro_series_id = Int(name='distro_series', allow_none=False)
    distro_series = Reference(distro_series_id, 'DistroSeries.id')

    is_distro_archive = Bool(name='is_distro_archive', allow_none=False)

    source_package_name_id = Int(name='source_package_name', allow_none=False)
    source_package_name = Reference(
        source_package_name_id, 'SourcePackageName.id')

    def _getLatestPublication(self):
        from lp.soyuz.model.publishing import SourcePackagePublishingHistory
        store = Store.of(self)
        results = store.find(
            SourcePackagePublishingHistory,
            SourcePackagePublishingHistory.archive == self.archive,
            SourcePackagePublishingHistory.distroseries == self.distro_series,
            SourcePackagePublishingHistory.sourcepackagerelease ==
                self.source_package_release)
        return results.order_by(
            Desc(SourcePackagePublishingHistory.id)).first()

    @property
    def current_component(self):
        """See `IBuild`."""
        latest_publication = self._getLatestPublication()
        # Production has some buggy builds without source publications.
        # They seem to have been created by early versions of gina and
        # the readding of hppa.
        if latest_publication is not None:
            return latest_publication.component

    @property
    def current_source_publication(self):
        """See `IBuild`."""
        from lp.soyuz.interfaces.publishing import active_publishing_status
        latest_publication = self._getLatestPublication()
        if (latest_publication is not None and
            latest_publication.status in active_publishing_status):
            return latest_publication
        return None

    @property
    def upload_changesfile(self):
        """See `IBuild`"""
        package_upload = self.package_upload
        if package_upload is None:
            return None
        return package_upload.changesfile

    @property
    def changesfile_url(self):
        """See `IBinaryPackageBuild`."""
        changesfile = self.upload_changesfile
        if changesfile is None:
            return None
        return ProxiedLibraryFileAlias(changesfile, self).http_url

    @property
    def package_upload(self):
        """See `IBuild`."""
        store = Store.of(self)
        # The join on 'changesfile' is used for pre-fetching the
        # corresponding library file, so callsites don't have to issue an
        # extra query.
        origin = [
            PackageUploadBuild,
            Join(PackageUpload,
                 PackageUploadBuild.packageuploadID == PackageUpload.id),
            Join(LibraryFileAlias,
                 LibraryFileAlias.id == PackageUpload.changes_file_id),
            Join(LibraryFileContent,
                 LibraryFileContent.id == LibraryFileAlias.contentID),
            ]
        results = store.using(*origin).find(
            (PackageUpload, LibraryFileAlias, LibraryFileContent),
            PackageUploadBuild.build == self,
            PackageUpload.archive == self.archive,
            PackageUpload.distroseries == self.distro_series)

        # Return the unique `PackageUpload` record that corresponds to the
        # upload of the result of this `Build`, load the `LibraryFileAlias`
        # and the `LibraryFileContent` in cache because it's most likely
        # they will be needed.
        return DecoratedResultSet(results, itemgetter(0)).one()

    @property
    def is_virtualized(self):
        """See `IBuild`"""
        return self.archive.require_virtualized

    @property
    def title(self):
        """See `IBuild`"""
        return '%s build of %s %s in %s %s %s' % (
            self.distro_arch_series.architecturetag,
            self.source_package_release.name,
            self.source_package_release.version,
            self.distribution.name, self.distro_series.name, self.pocket.name)

    @property
    def was_built(self):
        """See `IBuild`"""
        return self.status not in [BuildStatus.NEEDSBUILD,
                                   BuildStatus.BUILDING,
                                   BuildStatus.UPLOADING,
                                   BuildStatus.SUPERSEDED]

    @property
    def arch_tag(self):
        """See `IBuild`."""
        return self.distro_arch_series.architecturetag

    @property
    def log_url(self):
        """See `IPackageBuild`.

        Overridden here for the case of builds for distro archives,
        currently only supported for binary package builds.
        """
        if self.log is None:
            return None
        return ProxiedLibraryFileAlias(self.log, self).http_url

    @property
    def upload_log_url(self):
        """See `IPackageBuild`.

        Overridden here for the case of builds for distro archives,
        currently only supported for binary package builds.
        """
        if self.upload_log is None:
            return None
        return ProxiedLibraryFileAlias(self.upload_log, self).http_url

    @property
    def distributionsourcepackagerelease(self):
        """See `IBuild`."""
        from lp.soyuz.model.distributionsourcepackagerelease \
             import (
            DistributionSourcePackageRelease)

        return DistributionSourcePackageRelease(
            distribution=self.distribution,
            sourcepackagerelease=self.source_package_release)

    def calculateScore(self):
        """See `IBuildFarmJob`."""
        score = 0

        # Private builds get uber score.
        if self.archive.private:
            score += PRIVATE_ARCHIVE_SCORE_BONUS

        if self.archive.is_copy:
            score -= COPY_ARCHIVE_SCORE_PENALTY

        score += self.archive.relative_build_score

        # Language packs don't get any of the usual package-specific
        # score bumps, as they unduly delay the building of packages in
        # the main component otherwise.
        if self.source_package_release.section.name == 'translations':
            return score

        # Calculates the urgency-related part of the score.
        score += SCORE_BY_URGENCY[self.source_package_release.urgency]

        # Calculates the pocket-related part of the score.
        score += SCORE_BY_POCKET[self.pocket]

        # Calculates the component-related part of the score.
        score += SCORE_BY_COMPONENT.get(self.current_component.name, 0)

        # Calculates the package-set-related part of the score.
        package_sets = getUtility(IPackagesetSet).setsIncludingSource(
            self.source_package_release.name, distroseries=self.distro_series)
        if not self.archive.is_ppa and not package_sets.is_empty():
            score += package_sets.max(Packageset.relative_build_score)

        return score

    def getBinaryPackageNamesForDisplay(self):
        """See `IBuildView`."""
        store = Store.of(self)
        result = store.find(
            (BinaryPackageRelease, BinaryPackageName),
            BinaryPackageRelease.build == self,
            BinaryPackageRelease.binarypackagename == BinaryPackageName.id,
            BinaryPackageName.id == BinaryPackageRelease.binarypackagenameID)
        return result.order_by(
            [BinaryPackageName.name, BinaryPackageRelease.id])

    def getBinaryFilesForDisplay(self):
        """See `IBuildView`."""
        store = Store.of(self)
        result = store.find(
            (BinaryPackageRelease, BinaryPackageFile, LibraryFileAlias,
             LibraryFileContent),
            BinaryPackageRelease.build == self,
            BinaryPackageRelease.id ==
                BinaryPackageFile.binarypackagereleaseID,
            LibraryFileAlias.id == BinaryPackageFile.libraryfileID,
            LibraryFileContent.id == LibraryFileAlias.contentID)
        return result.order_by(
            [LibraryFileAlias.filename, BinaryPackageRelease.id]).config(
            distinct=True)

    @property
    def binarypackages(self):
        """See `IBuild`."""
        return BinaryPackageRelease.select("""
            BinaryPackageRelease.build = %s AND
            BinaryPackageRelease.binarypackagename = BinaryPackageName.id
            """ % sqlvalues(self),
            clauseTables=["BinaryPackageName"],
            orderBy=["BinaryPackageName.name", "BinaryPackageRelease.id"],
            prejoins=["binarypackagename", "component", "section"])

    @property
    def distroarchseriesbinarypackages(self):
        """See `IBuild`."""
        # Avoid circular import by importing locally.
        from lp.soyuz.model.distroarchseriesbinarypackagerelease import (
            DistroArchSeriesBinaryPackageRelease)
        return [DistroArchSeriesBinaryPackageRelease(
            self.distro_arch_series, bp)
            for bp in self.binarypackages]

    @property
    def can_be_retried(self):
        """See `IBuild`."""
        # First check that the slave scanner would pick up the build record
        # if we reset it.
        if not self.archive.canModifySuite(self.distro_series, self.pocket):
            # The slave scanner would not pick this up, so it cannot be
            # re-tried.
            return False

        failed_statuses = [
            BuildStatus.FAILEDTOBUILD,
            BuildStatus.MANUALDEPWAIT,
            BuildStatus.CHROOTWAIT,
            BuildStatus.FAILEDTOUPLOAD,
            BuildStatus.CANCELLED,
            ]

        # If the build is currently in any of the failed states,
        # it may be retried.
        return self.status in failed_statuses

    @property
    def can_be_rescored(self):
        """See `IBuild`."""
        return self.status is BuildStatus.NEEDSBUILD

    @property
    def can_be_cancelled(self):
        """See `IBuild`."""
        if not self.buildqueue_record:
            return False

        cancellable_statuses = [
            BuildStatus.BUILDING,
            BuildStatus.NEEDSBUILD,
            ]
        return self.status in cancellable_statuses

    def retry(self):
        """See `IBuild`."""
        assert self.can_be_retried, "Build %s cannot be retried" % self.id
        self.build_farm_job.status = self.status = BuildStatus.NEEDSBUILD
        self.build_farm_job.date_finished = self.date_finished = None
        self.date_started = None
        self.build_farm_job.builder = self.builder = None
        self.log = None
        self.upload_log = None
        self.dependencies = None
        self.failure_count = 0
        self.queueBuild()

    def rescore(self, score):
        """See `IBuild`."""
        if not self.can_be_rescored:
            raise CannotBeRescored("Build cannot be rescored.")

        self.buildqueue_record.manualScore(score)

    @property
    def api_score(self):
        """See `IBinaryPackageBuild`."""
        # Score of the related buildqueue record (if any)
        if self.buildqueue_record is None:
            return None
        else:
            return self.buildqueue_record.lastscore

    def cancel(self):
        """See `IBinaryPackageBuild`."""
        if not self.can_be_cancelled:
            return
        # BuildQueue.cancel() will decide whether to go straight to
        # CANCELLED, or go through CANCELLING to let buildd-manager
        # clean up the slave.
        self.buildqueue_record.cancel()

    def _parseDependencyToken(self, token):
        """Parse the given token.

        Raises AssertionError if the given token couldn't be parsed.

        Return a triple containing the corresponding (name, version,
        relation) for the given dependency token.
        """
        # XXX cprov 2006-02-27: it may not work for and'd and or'd syntax.
        try:
            name, version, relation = token[0]
        except ValueError:
            raise AssertionError(
                "APT is not dealing correctly with a dependency token "
                "'%r' from %s (%s) with the following dependencies: %s\n"
                "It is expected to be a tuple containing only another "
                "tuple with 3 elements  (name, version, relation)."
                % (token, self.title, self.id, self.dependencies))
        # Map relations to the canonical form used in control files.
        if relation == '<':
            relation = '<<'
        elif relation == '>':
            relation = '>>'
        return (name, version, relation)

    def _checkDependencyVersion(self, available, required, relation):
        """Return True if the available version satisfies the context."""
        # This dict maps the package version relationship syntax in lambda
        # functions which returns boolean according to the results of
        # apt_pkg.version_compare function (see the order above).
        # For further information about pkg relationship syntax see:
        #
        # http://www.debian.org/doc/debian-policy/ch-relationships.html
        #
        version_relation_map = {
            # any version is acceptable if no relationship is given
            '': lambda x: True,
            # strictly later
            '>>': lambda x: x == 1,
            # later or equal
            '>=': lambda x: x >= 0,
            # strictly equal
            '=': lambda x: x == 0,
            # earlier or equal
            '<=': lambda x: x <= 0,
            # strictly earlier
            '<<': lambda x: x == -1,
            }

        # Use apt_pkg function to compare versions
        # it behaves similar to cmp, i.e. returns negative
        # if first < second, zero if first == second and
        # positive if first > second.
        dep_result = apt_pkg.version_compare(available, required)

        return version_relation_map[relation](dep_result)

    def _isDependencySatisfied(self, token):
        """Check if the given dependency token is satisfied.

        Check if the dependency exists and that its version constraint is
        satisfied.
        """
        name, version, relation = self._parseDependencyToken(token)

        # There may be several published versions in the available
        # archives and pockets. If any one of them satisifies our
        # constraints, the dependency is satisfied.
        dep_candidates = self.archive.findDepCandidates(
            self.distro_arch_series, self.pocket, self.current_component,
            self.source_package_release.sourcepackagename.name, name)

        for dep_candidate in dep_candidates:
            if self._checkDependencyVersion(
                dep_candidate.binarypackagerelease.version, version,
                relation):
                return True

        return False

    def _toAptFormat(self, token):
        """Rebuild dependencies line in apt format."""
        name, version, relation = self._parseDependencyToken(token)
        if relation and version:
            return '%s (%s %s)' % (name, relation, version)
        return '%s' % name

    def updateDependencies(self):
        """See `IBuild`."""

        # apt_pkg requires init_system to get version_compare working
        # properly.
        apt_pkg.init_system()

        # Check package build dependencies using apt_pkg
        try:
            parsed_deps = apt_pkg.parse_depends(self.dependencies)
        except (ValueError, TypeError):
            raise UnparsableDependencies(
                "Build dependencies for %s (%s) could not be parsed: '%s'\n"
                "It indicates that something is wrong in buildd-slaves."
                % (self.title, self.id, self.dependencies))

        remaining_deps = [
            self._toAptFormat(token) for token in parsed_deps
            if not self._isDependencySatisfied(token)]

        # Update dependencies line
        self.dependencies = u", ".join(remaining_deps)

    def __getitem__(self, name):
        return self.getBinaryPackageRelease(name)

    def getBinaryPackageRelease(self, name):
        """See `IBuild`."""
        for binpkg in self.binarypackages:
            if binpkg.name == name:
                return binpkg
        raise NotFoundError('No binary package "%s" in build' % name)

    def createBinaryPackageRelease(
        self, binarypackagename, version, summary, description,
        binpackageformat, component, section, priority, installedsize,
        architecturespecific, shlibdeps=None, depends=None, recommends=None,
        suggests=None, conflicts=None, replaces=None, provides=None,
        pre_depends=None, enhances=None, breaks=None, essential=False,
        debug_package=None, user_defined_fields=None, homepage=None):
        """See IBuild."""
        return BinaryPackageRelease(
            build=self, binarypackagename=binarypackagename, version=version,
            summary=summary, description=description,
            binpackageformat=binpackageformat,
            component=component, section=section, priority=priority,
            shlibdeps=shlibdeps, depends=depends, recommends=recommends,
            suggests=suggests, conflicts=conflicts, replaces=replaces,
            provides=provides, pre_depends=pre_depends, enhances=enhances,
            breaks=breaks, essential=essential, installedsize=installedsize,
            architecturespecific=architecturespecific,
            debug_package=debug_package,
            user_defined_fields=user_defined_fields, homepage=homepage)

    def estimateDuration(self):
        """See `IPackageBuild`."""
        # Always include the primary archive when looking for
        # past build times (just in case that none can be found
        # in a PPA or copy archive).
        archives = [self.archive.id]
        if self.archive.purpose != ArchivePurpose.PRIMARY:
            archives.append(self.distro_arch_series.main_archive.id)

        # Look for all sourcepackagerelease instances that match the name
        # and get the (successfully built) build records for this
        # package.
        completed_builds = Store.of(self).find(
            BinaryPackageBuild,
            BinaryPackageBuild.archive_id.is_in(archives),
            BinaryPackageBuild.distro_arch_series == self.distro_arch_series,
            BinaryPackageBuild.source_package_name == self.source_package_name,
            BinaryPackageBuild.date_finished != None,
            BinaryPackageBuild.status == BuildStatus.FULLYBUILT,
            BinaryPackageBuild.id != self.id)
        most_recent_build = completed_builds.order_by(
            Desc(BinaryPackageBuild.date_finished),
            Desc(BinaryPackageBuild.id)).first()
        if most_recent_build is not None and most_recent_build.duration:
            # Historic build data exists, use the most recent value -
            # assuming it has valid data.
            return most_recent_build.duration

        # Estimate the build duration based on package size if no
        # historic build data exists.
        # Get the package size in KB.
        package_size = self.source_package_release.getPackageSize()
        if package_size > 0:
            # Analysis of previous build data shows that a build rate
            # of 6 KB/second is realistic. Furthermore we have to add
            # another minute for generic build overhead.
            estimate = int(package_size / 6.0 / 60 + 1)
        else:
            # No historic build times and no package size available,
            # assume a build time of 5 minutes.
            estimate = 5
        return datetime.timedelta(minutes=estimate)

    def verifySuccessfulUpload(self):
        return bool(self.binarypackages)

    def notify(self, extra_info=None):
        """See `IPackageBuild`.

        If config.buildmaster.build_notification is disable, simply
        return.

        If config.builddmaster.notify_owner is enabled and SPR.creator
        has preferredemail it will send an email to the creator, Bcc:
        to the config.builddmaster.default_recipient. If one of the
        conditions was not satisfied, no preferredemail found (autosync
        or untouched packages from debian) or config options disabled,
        it will only send email to the specified default recipient.

        This notification will contain useful information about
        the record in question (all states are supported), see
        doc/build-notification.txt for further information.
        """

        if not config.builddmaster.send_build_notification:
            return
        if self.status == BuildStatus.FULLYBUILT:
            return

        recipients = set()

        fromaddress = format_address(
            config.builddmaster.default_sender_name,
            config.builddmaster.default_sender_address)

        extra_headers = {
            'X-Launchpad-Archive': self.archive.reference,
            'X-Launchpad-Build-State': self.status.name,
            'X-Launchpad-Build-Component': self.current_component.name,
            'X-Launchpad-Build-Arch':
                self.distro_arch_series.architecturetag,
            }

        # XXX cprov 2006-10-27: Temporary extra debug info about the
        # SPR.creator in context, to be used during the service quarantine,
        # notify_owner will be disabled to avoid *spamming* Debian people.
        creator = self.source_package_release.creator
        extra_headers['X-Creator-Recipient'] = ",".join(
            get_contact_email_addresses(creator))

        # Currently there are 7038 SPR published in edgy which the creators
        # have no preferredemail. They are the autosync ones (creator = katie,
        # 3583 packages) and the untouched sources since we have migrated from
        # DAK (the rest). We should not spam Debian maintainers.

        # Please note that both the package creator and the package uploader
        # will be notified of failures if:
        #     * the 'notify_owner' flag is set
        #     * the package build (failure) occurred in the original
        #       archive.
        package_was_not_copied = (
            self.archive == self.source_package_release.upload_archive)

        if package_was_not_copied and config.builddmaster.notify_owner:
            if (self.archive.is_ppa and creator.inTeam(self.archive.owner)
                or
                not self.archive.is_ppa):
                # If this is a PPA, the package creator should only be
                # notified if they are the PPA owner or in the PPA team.
                # (see bug 375757)
                # Non-PPA notifications inform the creator regardless.
                recipients = recipients.union(
                    get_contact_email_addresses(creator))
            dsc_key = self.source_package_release.dscsigningkey
            if dsc_key:
                recipients = recipients.union(
                    get_contact_email_addresses(dsc_key.owner))

        # Modify notification contents according to the targeted archive.
        # 'Archive Tag', 'Subject' and 'Source URL' are customized for PPA.
        # We only send build-notifications to 'buildd-admin' celebrity for
        # main archive candidates.
        # For PPA build notifications we include the archive.owner
        # contact_address.
        subject = "[Build #%d] %s" % (self.id, self.title)
        if not self.archive.is_ppa:
            buildd_admins = getUtility(ILaunchpadCelebrities).buildd_admin
            recipients = recipients.union(
                get_contact_email_addresses(buildd_admins))
            source_url = canonical_url(self.distributionsourcepackagerelease)
        else:
            recipients = recipients.union(
                get_contact_email_addresses(self.archive.owner))
            # For PPAs we run the risk of having no available contact_address,
            # for instance, when both, SPR.creator and Archive.owner have
            # not enabled it.
            if len(recipients) == 0:
                return
            subject += ' [%s]' % self.archive.reference
            source_url = 'not available'
            # The deprecated PPA reference header is included for Ubuntu
            # PPAs to avoid breaking existing consumers.
            if self.archive.distribution.name == u'ubuntu':
                extra_headers['X-Launchpad-PPA'] = get_ppa_reference(
                    self.archive)

        # XXX cprov 2006-08-02: pending security recipients for SECURITY
        # pocket build. We don't build SECURITY yet :(

        # XXX cprov 2006-08-02: find out a way to glue parameters reported
        # with the state in the build worflow, maybe by having an
        # IBuild.statusReport property, which could also be used in the
        # respective page template.
        if self.status in [
            BuildStatus.NEEDSBUILD, BuildStatus.SUPERSEDED]:
            # untouched builds
            buildduration = 'not available'
            buildlog_url = 'not available'
            builder_url = 'not available'
        elif self.status == BuildStatus.UPLOADING:
            buildduration = 'uploading'
            buildlog_url = 'see builder page'
            builder_url = 'not available'
        elif self.status == BuildStatus.BUILDING:
            # build in process
            buildduration = 'not finished'
            buildlog_url = 'see builder page'
            builder_url = canonical_url(self.buildqueue_record.builder)
        else:
            # completed states (success and failure)
            buildduration = DurationFormatterAPI(
                self.duration).approximateduration()
            buildlog_url = self.log_url
            builder_url = canonical_url(self.builder)

        if self.status == BuildStatus.FAILEDTOUPLOAD:
            assert extra_info is not None, (
                'Extra information is required for FAILEDTOUPLOAD '
                'notifications.')
            extra_info = 'Upload log:\n%s' % extra_info
        else:
            extra_info = ''

        template = get_email_template('build-notification.txt', app='soyuz')
        replacements = {
            'source_name': self.source_package_release.name,
            'source_version': self.source_package_release.version,
            'architecturetag': self.distro_arch_series.architecturetag,
            'build_state': self.status.title,
            'build_duration': buildduration,
            'buildlog_url': buildlog_url,
            'builder_url': builder_url,
            'build_title': self.title,
            'build_url': canonical_url(self),
            'source_url': source_url,
            'extra_info': extra_info,
            'archive_tag': self.archive.reference,
            'component_tag': self.current_component.name,
            }
        message = template % replacements

        for toaddress in recipients:
            simple_sendmail(
                fromaddress, toaddress, subject, message,
                headers=extra_headers)

    def _getDebByFileName(self, filename):
        """Helper function to get a .deb LFA in the context of this build."""
        bpf = self.getBinaryPackageFileByName(filename)
        if bpf is not None:
            return bpf.libraryfile
        else:
            return None

    def getFileByName(self, filename):
        """See `IBuild`."""
        if filename.endswith('.changes'):
            file_object = self.upload_changesfile
        elif filename.endswith('.txt.gz'):
            file_object = self.log
        elif filename.endswith('_log.txt'):
            file_object = self.upload_log
        elif filename.endswith('deb'):
            file_object = self._getDebByFileName(filename)
        else:
            raise NotFoundError(filename)

        if file_object is not None and file_object.filename == filename:
            return file_object

        raise NotFoundError(filename)

    def getBinaryPackageFileByName(self, filename):
        """See `IBuild`."""
        return Store.of(self).find(
            BinaryPackageFile,
            BinaryPackageRelease.build == self.id,
            BinaryPackageFile.binarypackagerelease == BinaryPackageRelease.id,
            LibraryFileAlias.id == BinaryPackageFile.libraryfileID,
            LibraryFileAlias.filename == filename).one()

    def getUploader(self, changes):
        """See `IBinaryPackageBuild`."""
        return changes.signer


class BinaryPackageBuildSet(SpecificBuildFarmJobSourceMixin):
    implements(IBinaryPackageBuildSet)

    def new(self, source_package_release, archive, distro_arch_series, pocket,
            arch_indep=None, status=BuildStatus.NEEDSBUILD, builder=None):
        """See `IBinaryPackageBuildSet`."""
        # Force the current timestamp instead of the default UTC_NOW for
        # the transaction, avoid several row with same datecreated.
        if arch_indep is None:
            arch_indep = distro_arch_series.isNominatedArchIndep
        date_created = datetime.datetime.now(pytz.timezone('UTC'))
        # Create the BuildFarmJob for the new BinaryPackageBuild.
        build_farm_job = getUtility(IBuildFarmJobSource).new(
            BinaryPackageBuild.job_type, status, date_created, builder,
            archive)
        return BinaryPackageBuild(
            build_farm_job=build_farm_job,
            distro_arch_series=distro_arch_series,
            source_package_release=source_package_release,
            archive=archive, pocket=pocket, arch_indep=arch_indep,
            status=status, processor=distro_arch_series.processor,
            virtualized=archive.require_virtualized, builder=builder,
            is_distro_archive=archive.is_main,
            distribution=distro_arch_series.distroseries.distribution,
            distro_series=distro_arch_series.distroseries,
            source_package_name=source_package_release.sourcepackagename,
            date_created=date_created)

    def getByID(self, id):
        """See `IBinaryPackageBuildSet`."""
        try:
            return BinaryPackageBuild.get(id)
        except SQLObjectNotFound as e:
            raise NotFoundError(str(e))

    def getByBuildFarmJob(self, build_farm_job):
        """See `ISpecificBuildFarmJobSource`."""
        return Store.of(build_farm_job).find(
            BinaryPackageBuild, build_farm_job_id=build_farm_job.id).one()

    def preloadBuildsData(self, builds):
        # Circular imports.
        from lp.soyuz.model.distroarchseries import DistroArchSeries
        from lp.registry.model.distroseries import DistroSeries
        from lp.registry.model.distribution import Distribution
        from lp.soyuz.model.archive import Archive
        from lp.registry.model.person import Person
        self._prefetchBuildData(builds)
        das = load_related(DistroArchSeries, builds, ['distro_arch_series_id'])
        archives = load_related(Archive, builds, ['archive_id'])
        load_related(Person, archives, ['ownerID'])
        distroseries = load_related(DistroSeries, das, ['distroseriesID'])
        load_related(Distribution, distroseries, ['distributionID'])

    def getByBuildFarmJobs(self, build_farm_jobs):
        """See `ISpecificBuildFarmJobSource`."""
        if len(build_farm_jobs) == 0:
            return EmptyResultSet()
        rows = Store.of(build_farm_jobs[0]).find(
            BinaryPackageBuild,
            BinaryPackageBuild.build_farm_job_id.is_in(
                bfj.id for bfj in build_farm_jobs))
        return DecoratedResultSet(rows, pre_iter_hook=self.preloadBuildsData)

    def getBySourceAndLocation(self, source_package_release, archive,
                               distro_arch_series):
        return IStore(BinaryPackageBuild).find(
            BinaryPackageBuild,
            source_package_release=source_package_release,
            archive=archive, distro_arch_series=distro_arch_series).one()

    def handleOptionalParamsForBuildQueries(
        self, clauses, origin, status=None, name=None, pocket=None,
        arch_tag=None):
        """Construct query clauses needed/shared by all getBuild..() methods.

        This method is not exposed via the public interface as it is only
        used to DRY-up trusted code.

        :param clauses: container to which to add any resulting query clauses.
        :param origin: container to which to add joined tables.
        :param status: optional build state for which to add a query clause if
            present.
        :param name: optional source package release name (or list of source
            package release names) for which to add a query clause if
            present.
        :param pocket: optional pocket (or list of pockets) for which to add a
            query clause if present.
        :param arch_tag: optional architecture tag for which to add a
            query clause if present.
        """
        # Circular. :(
        from lp.soyuz.model.distroarchseries import DistroArchSeries

        origin.append(BinaryPackageBuild)

        # Add query clause that filters on build state if the latter is
        # provided.
        if status is not None:
            clauses.append(BinaryPackageBuild.status == status)

        # Add query clause that filters on pocket if the latter is provided.
        if pocket:
            if not isinstance(pocket, (list, tuple)):
                pocket = (pocket,)
            clauses.append(BinaryPackageBuild.pocket.is_in(pocket))

        # Add query clause that filters on architecture tag if provided.
        if arch_tag is not None:
            clauses.append(
                BinaryPackageBuild.distro_arch_series_id ==
                    DistroArchSeries.id)
            if not isinstance(arch_tag, (list, tuple)):
                arch_tag = (arch_tag,)
            clauses.append(DistroArchSeries.architecturetag.is_in(arch_tag))
            origin.append(DistroArchSeries)

        # Add query clause that filters on source package release name if the
        # latter is provided.
        if name is not None:
            clauses.append(
                BinaryPackageBuild.source_package_name_id ==
                    SourcePackageName.id)
            origin.extend([SourcePackageName])
            if not isinstance(name, (list, tuple)):
                clauses.append(
                    SourcePackageName.name.contains_string(name))
            else:
                clauses.append(SourcePackageName.name.is_in(name))

    def getBuildsForBuilder(self, builder_id, status=None, name=None,
                            pocket=None, arch_tag=None, user=None):
        """See `IBinaryPackageBuildSet`."""
        # Circular. :(
        from lp.soyuz.model.archive import (
            Archive, get_archive_privacy_filter)

        clauses = [
            BinaryPackageBuild.archive_id == Archive.id,
            BinaryPackageBuild.builder_id == builder_id,
            get_archive_privacy_filter(user)]
        origin = [Archive]

        self.handleOptionalParamsForBuildQueries(
            clauses, origin, status, name, pocket, arch_tag=arch_tag)

        return IStore(BinaryPackageBuild).using(*origin).find(
            BinaryPackageBuild, *clauses).order_by(
                Desc(BinaryPackageBuild.date_finished),
                BinaryPackageBuild.id)

    def getBuildsForArchive(self, archive, status=None, name=None,
                            pocket=None, arch_tag=None):
        """See `IBinaryPackageBuildSet`."""
        clauses = [BinaryPackageBuild.archive_id == archive.id]
        origin = []

        self.handleOptionalParamsForBuildQueries(
            clauses, origin, status, name, pocket, arch_tag)

        # Ordering according status
        # * SUPERSEDED & All by -datecreated
        # * FULLYBUILT & FAILURES by -datebuilt
        # It should present the builds in a more natural order.
        if status == BuildStatus.SUPERSEDED or status is None:
            orderBy = [Desc(BinaryPackageBuild.date_created)]
        else:
            orderBy = [Desc(BinaryPackageBuild.date_finished)]
        # All orders fallback to id if the primary order doesn't succeed
        orderBy.append(BinaryPackageBuild.id)

        return self._decorate_with_prejoins(
            IStore(BinaryPackageBuild).using(*origin).find(
                BinaryPackageBuild, *clauses).order_by(*orderBy))

    def getBuildsForDistro(self, context, status=None, name=None,
                           pocket=None, arch_tag=None):
        """See `IBinaryPackageBuildSet`."""
        if IDistribution.providedBy(context):
            col = BinaryPackageBuild.distribution_id
        elif IDistroSeries.providedBy(context):
            col = BinaryPackageBuild.distro_series_id
        elif IDistroArchSeries.providedBy(context):
            col = BinaryPackageBuild.distro_arch_series_id
        else:
            raise AssertionError("Unsupported context: %r" % context)
        condition_clauses = [
            col == context.id, BinaryPackageBuild.is_distro_archive]

        # XXX cprov 2006-09-25: It would be nice if we could encapsulate
        # the chunk of code below (which deals with the optional paramenters)
        # and share it with ISourcePackage.getBuildRecords()

        # exclude gina-generated and security (dak-made) builds
        # status == FULLYBUILT && datebuilt == null
        if status == BuildStatus.FULLYBUILT:
            condition_clauses.append(BinaryPackageBuild.date_finished != None)
        else:
            condition_clauses.append(Or(
                BinaryPackageBuild.status != BuildStatus.FULLYBUILT,
                BinaryPackageBuild.date_finished != None))

        # Ordering according status
        # * NEEDSBUILD, BUILDING & UPLOADING by -lastscore
        # * SUPERSEDED & All by -BinaryPackageBuild.id
        #   (nearly equivalent to -datecreated, but much more
        #   efficient.)
        # * FULLYBUILT & FAILURES by -datebuilt
        # It should present the builds in a more natural order.
        clauseTables = []
        order_by_table = None
        if status in [
            BuildStatus.NEEDSBUILD,
            BuildStatus.BUILDING,
            BuildStatus.UPLOADING]:
            order_by = [Desc(BuildQueue.lastscore), BinaryPackageBuild.id]
            order_by_table = BuildQueue
            clauseTables.append(BuildQueue)
            condition_clauses.append(
                BuildQueue._build_farm_job_id ==
                    BinaryPackageBuild.build_farm_job_id)
        elif status == BuildStatus.SUPERSEDED or status is None:
            order_by = [Desc(BinaryPackageBuild.id)]
        else:
            order_by = [Desc(BinaryPackageBuild.date_finished),
                        BinaryPackageBuild.id]

        # End of duplication (see XXX cprov 2006-09-25 above).

        self.handleOptionalParamsForBuildQueries(
            condition_clauses, clauseTables, status, name, pocket, arch_tag)

        find_spec = (BinaryPackageBuild,)
        if order_by_table:
            find_spec = find_spec + (order_by_table,)
        result_set = IStore(BinaryPackageBuild).using(*clauseTables).find(
            find_spec, *condition_clauses)
        result_set.order_by(*order_by)

        return self._decorate_with_prejoins(
            DecoratedResultSet(result_set, result_decorator=itemgetter(0)))

    def _decorate_with_prejoins(self, result_set):
        """Decorate build records with related data prefetch functionality."""
        # Grab the native storm result set.
        result_set = IResultSet(result_set)
        decorated_results = DecoratedResultSet(
            result_set, pre_iter_hook=self._prefetchBuildData)
        return decorated_results

    def getBuildsBySourcePackageRelease(self, sourcepackagerelease_ids,
                                        buildstate=None):
        """See `IBinaryPackageBuildSet`."""
        if (sourcepackagerelease_ids is None or
            len(sourcepackagerelease_ids) == 0):
            return []
        query = [
            BinaryPackageBuild.source_package_release_id.is_in(
                sourcepackagerelease_ids),
            BinaryPackageBuild.is_distro_archive,
            ]

        if buildstate is not None:
            query.append(BinaryPackageBuild.status == buildstate)

        resultset = IStore(BinaryPackageBuild).find(BinaryPackageBuild, *query)
        resultset.order_by(
            Desc(BinaryPackageBuild.date_created), BinaryPackageBuild.id)
        return resultset

    def findBuiltOrPublishedBySourceAndArchive(self, sourcepackagerelease,
                                               archive):
        """See `IBinaryPackageBuildSet`."""
        from lp.soyuz.model.publishing import BinaryPackagePublishingHistory

        published_query = Select(
            1,
            tables=(
                BinaryPackagePublishingHistory,
                Join(
                    BinaryPackageRelease,
                    BinaryPackageRelease.id ==
                        BinaryPackagePublishingHistory.binarypackagereleaseID)
                ),
            where=And(
                BinaryPackagePublishingHistory.archive == archive,
                BinaryPackageRelease.build == BinaryPackageBuild.id))
        builds = list(IStore(BinaryPackageBuild).find(
            BinaryPackageBuild,
            BinaryPackageBuild.status == BuildStatus.FULLYBUILT,
            BinaryPackageBuild.source_package_release == sourcepackagerelease,
            Or(
                BinaryPackageBuild.archive == archive,
                Exists(published_query))))
        arch_map = {
            build.distro_arch_series.architecturetag: build
            for build in builds}
        if len(arch_map) != len(builds):
            raise AssertionError(
                "Multiple successful builds for a single archtag. "
                "Something is probably corrupt.")
        return arch_map

    def getStatusSummaryForBuilds(self, builds):
        """See `IBinaryPackageBuildSet`."""
        # Create a small helper function to collect the builds for a given
        # list of build states:
        def collect_builds(*states):
            wanted = []
            for state in states:
                candidates = [build for build in builds
                                if build.status == state]
                wanted.extend(candidates)
            return wanted

        failed = collect_builds(BuildStatus.FAILEDTOBUILD,
                                BuildStatus.MANUALDEPWAIT,
                                BuildStatus.CHROOTWAIT,
                                BuildStatus.FAILEDTOUPLOAD)
        needsbuild = collect_builds(BuildStatus.NEEDSBUILD)
        building = collect_builds(BuildStatus.BUILDING,
                                  BuildStatus.UPLOADING)
        successful = collect_builds(BuildStatus.FULLYBUILT)

        # Note: the BuildStatus DBItems are used here to summarize the
        # status of a set of builds:s
        if len(building) != 0:
            return {
                'status': BuildSetStatus.BUILDING,
                'builds': building,
                }
        elif len(needsbuild) != 0:
            return {
                'status': BuildSetStatus.NEEDSBUILD,
                'builds': needsbuild,
                }
        elif len(failed) != 0:
            return {
                'status': BuildSetStatus.FAILEDTOBUILD,
                'builds': failed,
                }
        else:
            return {
                'status': BuildSetStatus.FULLYBUILT,
                'builds': successful,
                }

    def _prefetchBuildData(self, results):
        """Used to pre-populate the cache with build related data.

        When dealing with a group of Build records we can't use the
        prejoin facility to also fetch BuildQueue, SourcePackageRelease
        and LibraryFileAlias records in a single query because the
        result set is too large and the queries time out too often.

        So this method receives a list of Build instances and fetches the
        corresponding SourcePackageRelease and LibraryFileAlias rows
        (prejoined with the appropriate SourcePackageName and
        LibraryFileContent respectively) as well as builders related to the
        Builds at hand.
        """
        from lp.registry.model.sourcepackagename import (
            SourcePackageName)
        from lp.soyuz.model.sourcepackagerelease import (
            SourcePackageRelease)

        # Prefetching is not needed if the original result set is empty.
        if len(results) == 0:
            return

        build_ids = [build.id for build in results]
        origin = (
            BinaryPackageBuild,
            Join(
                SourcePackageRelease,
                (SourcePackageRelease.id ==
                    BinaryPackageBuild.source_package_release_id)),
            Join(
                SourcePackageName,
                SourcePackageName.id
                    == SourcePackageRelease.sourcepackagenameID),
            LeftJoin(LibraryFileAlias,
                     LibraryFileAlias.id == BinaryPackageBuild.log_id),
            LeftJoin(LibraryFileContent,
                     LibraryFileContent.id == LibraryFileAlias.contentID),
            LeftJoin(Builder, Builder.id == BinaryPackageBuild.builder_id),
            )
        result_set = IStore(BinaryPackageBuild).using(*origin).find(
            (SourcePackageRelease, LibraryFileAlias, SourcePackageName,
             LibraryFileContent, Builder),
            BinaryPackageBuild.id.is_in(build_ids))

        # Force query execution so that the ancillary data gets fetched
        # and added to StupidCache.
        # We are doing this here because there is no "real" caller of
        # this (pre_iter_hook()) method that will iterate over the
        # result set and force the query execution that way.
        return list(result_set)

    def getByQueueEntry(self, queue_entry):
        """See `IBinaryPackageBuildSet`."""
        bfj_id = removeSecurityProxy(queue_entry)._build_farm_job_id
        return IStore(BinaryPackageBuild).find(
            BinaryPackageBuild, build_farm_job_id=bfj_id).one()

    @staticmethod
    def addCandidateSelectionCriteria(processor, virtualized):
        """See `ISpecificBuildFarmJobSource`."""
        private_statuses = (
            PackagePublishingStatus.PUBLISHED,
            PackagePublishingStatus.SUPERSEDED,
            PackagePublishingStatus.DELETED,
            )
        return """
            SELECT TRUE FROM Archive, BinaryPackageBuild, DistroArchSeries
            WHERE
            BinaryPackageBuild.build_farm_job = BuildQueue.build_farm_job AND
            BinaryPackageBuild.distro_arch_series =
                DistroArchSeries.id AND
            BinaryPackageBuild.archive = Archive.id AND
            ((Archive.private IS TRUE AND
              EXISTS (
                  SELECT SourcePackagePublishingHistory.id
                  FROM SourcePackagePublishingHistory
                  WHERE
                      SourcePackagePublishingHistory.distroseries =
                         DistroArchSeries.distroseries AND
                      SourcePackagePublishingHistory.sourcepackagerelease =
                         BinaryPackageBuild.source_package_release AND
                      SourcePackagePublishingHistory.archive = Archive.id AND
                      SourcePackagePublishingHistory.status IN %s))
              OR
              archive.private IS FALSE) AND
            BinaryPackageBuild.status = %s
        """ % sqlvalues(private_statuses, BuildStatus.NEEDSBUILD)

    @staticmethod
    def postprocessCandidate(job, logger):
        """See `ISpecificBuildFarmJobSource`."""
        # Mark build records targeted to old source versions as SUPERSEDED
        # and build records target to SECURITY pocket or against an OBSOLETE
        # distroseries without a flag as FAILEDTOBUILD.
        # Builds in those situation should not be built because they will
        # be wasting build-time.  In the former case, there is already a
        # newer source; the latter case needs an overhaul of the way
        # security builds are handled (by copying from a PPA) to avoid
        # creating duplicate builds.
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(job)
        distroseries = build.distro_arch_series.distroseries
        if (
            build.pocket == PackagePublishingPocket.SECURITY or
            (distroseries.status == SeriesStatus.OBSOLETE and
                not build.archive.permit_obsolete_series_uploads)):
            # We never build anything in the security pocket, or for obsolete
            # series without the flag set.
            logger.debug(
                "Build %s FAILEDTOBUILD, queue item %s REMOVED"
                % (build.id, job.id))
            build.updateStatus(BuildStatus.FAILEDTOBUILD)
            job.destroySelf()
            return False

        publication = build.current_source_publication
        if publication is None:
            # The build should be superseded if it no longer has a
            # current publishing record.
            logger.debug(
                "Build %s SUPERSEDED, queue item %s REMOVED"
                % (build.id, job.id))
            build.updateStatus(BuildStatus.SUPERSEDED)
            job.destroySelf()
            return False

        return True

    def _getAllowedArchitectures(self, archive, available_archs):
        """Filter out any restricted architectures not specifically allowed
        for an archive.

        :param available_archs: Architectures to consider
        :return: Sequence of `IDistroArch` instances.
        """
        # Return all distroarches with unrestricted processors or with
        # processors the archive is explicitly associated with.
        return [distroarch for distroarch in available_archs
            if not distroarch.processor.restricted or
               distroarch.processor in archive.enabled_restricted_processors]

    def createForSource(self, sourcepackagerelease, archive, distroseries,
                        pocket, architectures_available=None, logger=None):
        """See `ISourcePackagePublishingHistory`."""

        # Exclude any architectures which already have built or copied
        # binaries. A new built can never succeed; its files would
        # conflict during upload.
        relevant_builds = self.findBuiltOrPublishedBySourceAndArchive(
            sourcepackagerelease, archive).values()

        # Find any architectures that already have a build that exactly
        # matches, regardless of status. We can't create a second build
        # with the same (SPR, Archive, DAS).
        # XXX wgrant 2014-11-06: Should use a bulk query.
        for das in distroseries.architectures:
            build = self.getBySourceAndLocation(
                sourcepackagerelease, archive, das)
            if build is not None:
                relevant_builds.append(build)

        # Work out if another build has taken the arch-indep role. If
        # not, we should assign it to one of our new builds.
        need_arch_indep = not any(bpb.arch_indep for bpb in relevant_builds)
        skip_archtags = set(
            bpb.distro_arch_series.architecturetag for bpb in relevant_builds)

        # Find the architectures for which the source should end up with
        # binaries, parsing architecturehintlist as you'd expect.
        # For an architecturehintlist of just 'all', this will
        # be the current nominatedarchindep if need_arch_indep,
        # otherwise nothing.
        if architectures_available is None:
            architectures_available = list(
                distroseries.buildable_architectures)
        architectures_available = self._getAllowedArchitectures(
            archive, architectures_available)
        candidate_architectures = determine_architectures_to_build(
            sourcepackagerelease.architecturehintlist, archive, distroseries,
            architectures_available, need_arch_indep)

        # Filter out any architectures for which we earlier found sufficient
        # build.
        needed_architectures = [
            das for das in candidate_architectures
            if das.architecturetag not in skip_archtags]
        if not needed_architectures:
            return []

        arch_indep_das = None
        if need_arch_indep:
            # The ideal arch_indep build is nominatedarchindep. But if
            # that isn't a build we would otherwise create, use the DAS
            # with the lowest Processor.id.
            # XXX wgrant 2014-11-06: The fact that production's
            # Processor 1 is i386, a good arch-indep candidate, is a
            # total coincidence and this isn't a hack. I promise.
            if distroseries.nominatedarchindep in needed_architectures:
                arch_indep_das = distroseries.nominatedarchindep
            else:
                arch_indep_das = sorted(
                    needed_architectures, key=attrgetter('processor.id'))[0]

        # Create builds for the remaining architectures.
        new_builds = []
        for das in needed_architectures:
            build = self.new(
                source_package_release=sourcepackagerelease,
                distro_arch_series=das, archive=archive, pocket=pocket,
                arch_indep=das == arch_indep_das)
            new_builds.append(build)
            # Create the builds in suspended mode for disabled archives.
            build_queue = build.queueBuild(suspended=not archive.enabled)
            Store.of(build).flush()
            if logger is not None:
                logger.debug(
                    "Created %s [%d] in %s (%d)"
                    % (build.title, build.id, build.archive.displayname,
                    build_queue.lastscore))
        return new_builds
