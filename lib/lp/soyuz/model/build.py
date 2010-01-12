# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['Build', 'BuildSet']


import apt_pkg
from cStringIO import StringIO
import datetime
import logging
import operator

from zope.interface import implements
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy
from storm.expr import (
    Desc, In, Join, LeftJoin)
from storm.store import Store
from sqlobject import (
    StringCol, ForeignKey, IntervalCol, SQLObjectNotFound)
from sqlobject.sqlbuilder import AND, IN

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    cursor, quote_like, SQLBase, sqlvalues)
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet)
from canonical.launchpad.database.librarian import (
    LibraryFileAlias, LibraryFileContent)
from canonical.launchpad.helpers import (
     get_contact_email_addresses, filenameToContentType, get_email_template)
from canonical.launchpad.interfaces.launchpad import (
    NotFoundError, ILaunchpadCelebrities)
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.mail import (
    simple_sendmail, format_address)
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.launchpad.webapp.tales import DurationFormatterAPI
from lp.archivepublisher.utils import get_ppa_reference
from lp.buildmaster.interfaces.buildfarmjob import BuildFarmJobType
from lp.buildmaster.model.buildbase import BuildBase
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.job.model.job import Job
from lp.soyuz.adapters.archivedependencies import get_components_for_building
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.build import (
    BuildStatus, BuildSetStatus, CannotBeRescored, IBuild, IBuildSet)
from lp.soyuz.interfaces.builder import IBuilderSet
from lp.soyuz.interfaces.publishing import active_publishing_status
from lp.soyuz.model.binarypackagerelease import BinaryPackageRelease
from lp.soyuz.model.builder import Builder
from lp.soyuz.model.buildpackagejob import BuildPackageJob
from lp.soyuz.model.buildqueue import BuildQueue
from lp.soyuz.model.files import BinaryPackageFile
from lp.soyuz.model.publishing import SourcePackagePublishingHistory
from lp.soyuz.model.queue import (
    PackageUpload, PackageUploadBuild)


class Build(BuildBase, SQLBase):
    implements(IBuild)
    _table = 'Build'
    _defaultOrder = 'id'

    datecreated = UtcDateTimeCol(dbName='datecreated', default=UTC_NOW)
    processor = ForeignKey(dbName='processor', foreignKey='Processor',
        notNull=True)
    distroarchseries = ForeignKey(dbName='distroarchseries',
        foreignKey='DistroArchSeries', notNull=True)
    buildstate = EnumCol(dbName='buildstate', notNull=True,
                         schema=BuildStatus)
    sourcepackagerelease = ForeignKey(dbName='sourcepackagerelease',
        foreignKey='SourcePackageRelease', notNull=True)
    datebuilt = UtcDateTimeCol(dbName='datebuilt', default=None)
    buildduration = IntervalCol(dbName='buildduration', default=None)
    buildlog = ForeignKey(dbName='buildlog', foreignKey='LibraryFileAlias',
        default=None)
    builder = ForeignKey(dbName='builder', foreignKey='Builder',
        default=None)
    pocket = EnumCol(dbName='pocket', schema=PackagePublishingPocket,
                     notNull=True)
    dependencies = StringCol(dbName='dependencies', default=None)
    archive = ForeignKey(foreignKey='Archive', dbName='archive', notNull=True)

    date_first_dispatched = UtcDateTimeCol(dbName='date_first_dispatched')

    upload_log = ForeignKey(
        dbName='upload_log', foreignKey='LibraryFileAlias', default=None)

    def _getProxiedFileURL(self, library_file):
        """Return the 'http_url' of a `ProxiedLibraryFileAlias`."""
        # Avoiding circular imports.
        from canonical.launchpad.browser.librarian import (
            ProxiedLibraryFileAlias)

        proxied_file = ProxiedLibraryFileAlias(library_file, self)
        return proxied_file.http_url

    @property
    def buildqueue_record(self):
        """See `IBuild`."""
        store = Store.of(self)
        results = store.find(
            BuildQueue,
            BuildPackageJob.job == BuildQueue.jobID,
            BuildPackageJob.build == self.id)
        return results.one()

    @property
    def upload_log_url(self):
        """See `IBuild`."""
        if self.upload_log is None:
            return None
        return self._getProxiedFileURL(self.upload_log)

    @property
    def build_log_url(self):
        """See `IBuild`."""
        if self.buildlog is None:
            return None
        return self._getProxiedFileURL(self.buildlog)

    def _getLatestPublication(self):
        store = Store.of(self)
        results = store.find(
            SourcePackagePublishingHistory,
            SourcePackagePublishingHistory.archive == self.archive,
            SourcePackagePublishingHistory.distroseries == self.distroseries,
            SourcePackagePublishingHistory.sourcepackagerelease ==
                self.sourcepackagerelease)
        return results.order_by(
            Desc(SourcePackagePublishingHistory.id)).first()

    @property
    def current_component(self):
        """See `IBuild`."""
        latest_publication = self._getLatestPublication()

        # XXX cprov 2009-06-06 bug=384220:
        # This assertion works fine in production, since all build records
        # are legitimate and have a corresponding source publishing record
        # (which triggered their creation, in first place). However our
        # sampledata is severely broken in this area and depends heavily
        # on the fallback to the source package original component.
        #assert latest_publication is not None, (
        #    'Build %d lacks a corresponding source publication.' % self.id)
        if latest_publication is None:
            return self.sourcepackagerelease.component

        return latest_publication.component

    @property
    def current_source_publication(self):
        """See `IBuild`."""
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
    def package_upload(self):
        """See `IBuild`."""
        store = Store.of(self)
        # The join on 'changesfile' is not only used only for
        # pre-fetching the corresponding library file, so callsites
        # don't have to issue an extra query. It is also important
        # for excluding delayed-copies, because they might match
        # the publication context but will not contain as changesfile.
        origin = [
            PackageUploadBuild,
            Join(PackageUpload,
                 PackageUploadBuild.packageuploadID == PackageUpload.id),
            Join(LibraryFileAlias,
                 LibraryFileAlias.id == PackageUpload.changesfileID),
            Join(LibraryFileContent,
                 LibraryFileContent.id == LibraryFileAlias.contentID),
            ]
        results = store.using(*origin).find(
            (PackageUpload, LibraryFileAlias, LibraryFileContent),
            PackageUploadBuild.build == self,
            PackageUpload.archive == self.archive,
            PackageUpload.distroseries == self.distroseries)

        # Return the unique `PackageUpload` record that corresponds to the
        # upload of the result of this `Build`, load the `LibraryFileAlias`
        # and the `LibraryFileContent` in cache because it's most likely
        # they will be needed.
        return DecoratedResultSet(results, operator.itemgetter(0)).one()

    @property
    def distroseries(self):
        """See `IBuild`"""
        return self.distroarchseries.distroseries

    @property
    def distribution(self):
        """See `IBuild`"""
        return self.distroarchseries.distroseries.distribution

    @property
    def is_virtualized(self):
        """See `IBuild`"""
        return self.archive.require_virtualized

    @property
    def is_private(self):
        """See `IBuildBase`"""
        return self.archive.private

    @property
    def title(self):
        """See `IBuild`"""
        return '%s build of %s %s in %s %s %s' % (
            self.distroarchseries.architecturetag,
            self.sourcepackagerelease.name,
            self.sourcepackagerelease.version,
            self.distribution.name, self.distroseries.name, self.pocket.name)

    @property
    def was_built(self):
        """See `IBuild`"""
        return self.buildstate not in [BuildStatus.NEEDSBUILD,
                                       BuildStatus.BUILDING,
                                       BuildStatus.SUPERSEDED]

    @property
    def arch_tag(self):
        """See `IBuild`."""
        return self.distroarchseries.architecturetag

    @property
    def distributionsourcepackagerelease(self):
        """See `IBuild`."""
        from lp.soyuz.model.distributionsourcepackagerelease \
             import (
            DistributionSourcePackageRelease)

        return DistributionSourcePackageRelease(
            distribution=self.distroarchseries.distroseries.distribution,
            sourcepackagerelease=self.sourcepackagerelease)

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
        from canonical.launchpad.database import (
            DistroArchSeriesBinaryPackageRelease)
        return [DistroArchSeriesBinaryPackageRelease(
            self.distroarchseries, bp)
            for bp in self.binarypackages]

    @property
    def can_be_retried(self):
        """See `IBuild`."""
        # First check that the slave scanner would pick up the build record
        # if we reset it.  PPA and Partner builds are always ok.
        if (self.archive.purpose == ArchivePurpose.PRIMARY and
            not self.distroseries.canUploadToPocket(self.pocket)):
            # The slave scanner would not pick this up, so it cannot be
            # re-tried.
            return False

        failed_buildstates = [
            BuildStatus.FAILEDTOBUILD,
            BuildStatus.MANUALDEPWAIT,
            BuildStatus.CHROOTWAIT,
            BuildStatus.FAILEDTOUPLOAD,
            ]

        # If the build is currently in any of the failed states,
        # it may be retried.
        return self.buildstate in failed_buildstates

    @property
    def can_be_rescored(self):
        """See `IBuild`."""
        return self.buildstate is BuildStatus.NEEDSBUILD

    @property
    def calculated_buildstart(self):
        """See `IBuild`."""
        assert self.datebuilt and self.buildduration, (
            "value is not suitable for this build record (%d)"
            % self.id)
        return self.datebuilt - self.buildduration

    def retry(self):
        """See `IBuild`."""
        assert self.can_be_retried, "Build %s cannot be retried" % self.id
        self.buildstate = BuildStatus.NEEDSBUILD
        self.datebuilt = None
        self.buildduration = None
        self.builder = None
        self.buildlog = None
        self.upload_log = None
        self.dependencies = None
        self.createBuildQueueEntry()

    def rescore(self, score):
        """See `IBuild`."""
        if not self.can_be_rescored:
            raise CannotBeRescored("Build cannot be rescored.")

        self.buildqueue_record.manualScore(score)

    def getEstimatedBuildStartTime(self):
        """See `IBuild`.

        The estimated dispatch time for the build job at hand is
        calculated from the following ingredients:
            * the start time for the head job (job at the
              head of the respective build queue)
            * the estimated build durations of all jobs that
              precede the job at hand in the build queue
              (divided by the number of machines in the respective
              build pool)
        If either of the above cannot be determined the estimated
        dispatch is not known in which case the EPOCH time stamp
        is returned.
        """
        # This method may only be invoked for pending jobs.
        if self.buildstate != BuildStatus.NEEDSBUILD:
            raise AssertionError(
                "The start time is only estimated for pending builds.")

        # A None value indicates that the estimated dispatch time is not
        # available.
        result = None

        cur = cursor()
        # For a given build job in position N in the build queue the
        # query below sums up the estimated build durations for the
        # jobs [1 .. N-1] i.e. for the jobs that are ahead of job N.
        sum_query = """
            SELECT
                EXTRACT(EPOCH FROM SUM(BuildQueue.estimated_duration))
            FROM
                Archive
                JOIN Build ON
                    Build.archive = Archive.id
                JOIN BuildPackageJob ON
                    Build.id = BuildPackageJob.build
                JOIN BuildQueue ON
                    BuildPackageJob.job = BuildQueue.job
            WHERE
                Build.buildstate = 0 AND
                Build.processor = %s AND
                Archive.require_virtualized = %s AND
                Archive.enabled = TRUE AND
                ((BuildQueue.lastscore > %s) OR
                 ((BuildQueue.lastscore = %s) AND
                  (Build.id < %s)))
             """ % sqlvalues(self.processor, self.is_virtualized,
                      self.buildqueue_record.lastscore,
                      self.buildqueue_record.lastscore, self)

        cur.execute(sum_query)
        # Get the sum of the estimated build time for jobs that are
        # ahead of us in the queue.
        [sum_of_delays] = cur.fetchone()

        # Get build dispatch time for job at the head of the queue.
        headjob_delay = self._getHeadjobDelay()

        # Get the number of machines that are available in the build
        # pool for this build job.
        pool_size = getUtility(IBuilderSet).getBuildersForQueue(
            self.processor, self.is_virtualized).count()

        # The estimated dispatch time can only be calculated for
        # non-zero-sized build pools.
        if pool_size > 0:
            # This is the estimated build job start time in seconds
            # from now.
            start_time = 0

            if sum_of_delays is None:
                # This job is the head job.
                start_time = headjob_delay
            else:
                # There are jobs ahead of us. Divide the delay total by
                # the number of machines available in the build pool.
                # Please note: we need the pool size to be a floating
                # pointer number for the purpose of the division below.
                pool_size = float(pool_size)
                start_time = headjob_delay + int(sum_of_delays/pool_size)

            result = (
                datetime.datetime.utcnow() +
                datetime.timedelta(seconds=start_time))

        return result

    def _getHeadjobDelay(self):
        """Get estimated dispatch time for job at the head of the queue."""
        cur = cursor()
        # The query below yields the remaining build times (in seconds
        # since EPOCH) for the jobs that are currently building on the
        # machine pool of interest.
        delay_query = """
            SELECT
                CAST (EXTRACT(EPOCH FROM
                        (BuildQueue.estimated_duration -
                        (NOW() - Job.date_started))) AS INTEGER)
                    AS remainder
            FROM
                Archive
                JOIN Build ON
                    Build.archive = Archive.id
                JOIN BuildPackageJob ON
                    Build.id = BuildPackageJob.build
                JOIN BuildQueue ON
                    BuildQueue.job = BuildPackageJob.job
                JOIN Builder ON
                    Builder.id = BuildQueue.builder
                JOIN Job ON
                    Job.id = BuildPackageJob.job
            WHERE
                Archive.require_virtualized = %s AND
                Archive.enabled = TRUE AND
                Build.buildstate = %s AND
                Builder.processor = %s
            ORDER BY
                remainder;
            """ % sqlvalues(self.is_virtualized, BuildStatus.BUILDING,
                    self.processor)

        cur.execute(delay_query)
        # Get the remaining build times for the jobs currently
        # building on the respective machine pool (current build
        # set).
        remainders = cur.fetchall()
        build_delays = set([int(row[0]) for row in remainders if row[0]])

        # This is the head job delay in seconds. Initialize it here.
        if len(build_delays):
            headjob_delay = max(build_delays)
        else:
            headjob_delay = 0

        # Did all currently building jobs overdraw their estimated
        # time budget?
        if headjob_delay < 0:
            # Yes, this is the case. Reset the head job delay to two
            # minutes.
            headjob_delay = 120

        for delay in reversed(sorted(build_delays)):
            if delay < 0:
                # This job is currently building and taking longer
                # than estimated i.e. we don't have a clue when it
                # will be finished. Make a wild guess (2 minutes?).
                delay = 120
            if delay < headjob_delay:
                headjob_delay = delay

        return headjob_delay

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
        return (name, version, relation)

    def _checkDependencyVersion(self, available, required, relation):
        """Return True if the available version satisfies the context."""
        # This dict maps the package version relationship syntax in lambda
        # functions which returns boolean according the results of
        # apt_pkg.VersionCompare function (see the order above).
        # For further information about pkg relationship syntax see:
        #
        # http://www.debian.org/doc/debian-policy/ch-relationships.html
        #
        version_relation_map = {
            # any version is acceptable if no relationship is given
            '': lambda x: True,
            # stricly later
            '>>': lambda x: x == 1,
            # later or equal
            '>=': lambda x: x >= 0,
            # stricly equal
            '=': lambda x: x == 0,
            # earlier or equal
            '<=': lambda x: x <= 0,
            # strictly earlier
            '<<': lambda x: x == -1
            }

        # Use apt_pkg function to compare versions
        # it behaves similar to cmp, i.e. returns negative
        # if first < second, zero if first == second and
        # positive if first > second.
        dep_result = apt_pkg.VersionCompare(available, required)

        return version_relation_map[relation](dep_result)

    def _isDependencySatisfied(self, token):
        """Check if the given dependency token is satisfied.

        Check if the dependency exists, if its version constraint is
        satisfied and if it is reachable in the build context.
        """
        name, version, relation = self._parseDependencyToken(token)

        dep_candidate = self.archive.findDepCandidateByName(
            self.distroarchseries, name)

        if not dep_candidate:
            return False

        if not self._checkDependencyVersion(
            dep_candidate.binarypackageversion, version, relation):
            return False

        # Only PRIMARY archive build dependencies should be restricted
        # to the ogre_components. Both PARTNER and PPA can reach
        # dependencies from all components in the PRIMARY archive.
        # Moreover, PARTNER and PPA component domain is single, i.e,
        # PARTNER only contains packages in 'partner' component and PPAs
        # only contains packages in 'main' component.
        ogre_components = get_components_for_building(self)
        if (self.archive.purpose == ArchivePurpose.PRIMARY and
            dep_candidate.component not in ogre_components):
            return False

        return True

    def _toAptFormat(self, token):
        """Rebuild dependencies line in apt format."""
        name, version, relation = self._parseDependencyToken(token)
        if relation and version:
            return '%s (%s %s)' % (name, relation, version)
        return '%s' % name

    def updateDependencies(self):
        """See `IBuild`."""

        # apt_pkg requires InitSystem to get VersionCompare working properly.
        apt_pkg.InitSystem()

        # Check package build dependencies using apt_pkg
        try:
            parsed_deps = apt_pkg.ParseDepends(self.dependencies)
        except (ValueError, TypeError):
            raise AssertionError(
                "Build dependencies for %s (%s) could not be parsed: '%s'\n"
                "It indicates that something is wrong in buildd-slaves."
                % (self.title, self.id, self.dependencies))

        remaining_deps = [
            self._toAptFormat(token) for token in parsed_deps
            if not self._isDependencySatisfied(token)]

        # Update dependencies line
        self.dependencies = ", ".join(remaining_deps)

    def __getitem__(self, name):
        return self.getBinaryPackageRelease(name)

    def getBinaryPackageRelease(self, name):
        """See `IBuild`."""
        for binpkg in self.binarypackages:
            if binpkg.name == name:
                return binpkg
        raise NotFoundError, 'No binary package "%s" in build' % name

    def createBinaryPackageRelease(
        self, binarypackagename, version, summary, description,
        binpackageformat, component,section, priority, shlibdeps,
        depends, recommends, suggests, conflicts, replaces, provides,
        pre_depends, enhances, breaks, essential, installedsize,
        architecturespecific):
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
            architecturespecific=architecturespecific)

    def _estimateDuration(self):
        """Estimate the build duration."""
        # Always include the primary archive when looking for
        # past build times (just in case that none can be found
        # in a PPA or copy archive).
        archives = [self.archive.id]
        if self.archive.purpose != ArchivePurpose.PRIMARY:
            archives.append(self.distroarchseries.main_archive.id)

        # Look for all sourcepackagerelease instances that match the name
        # and get the (successfully built) build records for this
        # package.
        completed_builds = Build.select("""
            Build.sourcepackagerelease = SourcePackageRelease.id AND
            Build.id != %s AND
            Build.buildduration IS NOT NULL AND
            SourcePackageRelease.sourcepackagename = SourcePackageName.id AND
            SourcePackageName.name = %s AND
            distroarchseries = %s AND
            archive IN %s AND
            buildstate = %s
            """ % sqlvalues(self, self.sourcepackagerelease.name,
                            self.distroarchseries, archives,
                            BuildStatus.FULLYBUILT),
            orderBy=['-datebuilt', '-id'],
            clauseTables=['SourcePackageName', 'SourcePackageRelease'])

        if completed_builds.count() > 0:
            # Historic build data exists, use the most recent value.
            most_recent_build = completed_builds[0]
            estimated_duration = most_recent_build.buildduration
        else:
            # Estimate the build duration based on package size if no
            # historic build data exists.

            # Get the package size in KB.
            package_size = self.sourcepackagerelease.getPackageSize()

            if package_size > 0:
                # Analysis of previous build data shows that a build rate
                # of 6 KB/second is realistic. Furthermore we have to add
                # another minute for generic build overhead.
                estimate = int(package_size/6.0/60 + 1)
            else:
                # No historic build times and no package size available,
                # assume a build time of 5 minutes.
                estimate = 5
            estimated_duration = datetime.timedelta(minutes=estimate)

        return estimated_duration

    def createBuildQueueEntry(self):
        """See `IBuild`"""
        store = Store.of(self)
        job = Job()
        store.add(job)
        specific_job = BuildPackageJob()
        specific_job.build = self.id
        specific_job.job = job.id
        store.add(specific_job)
        duration_estimate = self._estimateDuration()
        queue_entry = BuildQueue(
            estimated_duration=duration_estimate,
            job_type=BuildFarmJobType.PACKAGEBUILD,
            job=job.id)
        store.add(queue_entry)
        return queue_entry

    def notify(self, extra_info=None):
        """See `IBuildBase`.

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

        recipients = set()

        fromaddress = format_address(
            config.builddmaster.default_sender_name,
            config.builddmaster.default_sender_address)

        extra_headers = {
            'X-Launchpad-Build-State': self.buildstate.name,
            'X-Launchpad-Build-Component' : self.current_component.name,
            'X-Launchpad-Build-Arch' : self.distroarchseries.architecturetag,
            }

        # XXX cprov 2006-10-27: Temporary extra debug info about the
        # SPR.creator in context, to be used during the service quarantine,
        # notify_owner will be disabled to avoid *spamming* Debian people.
        creator = self.sourcepackagerelease.creator
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
            self.archive == self.sourcepackagerelease.upload_archive)

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
            dsc_key = self.sourcepackagerelease.dscsigningkey
            if dsc_key:
                recipients = recipients.union(
                    get_contact_email_addresses(dsc_key.owner))

        # Modify notification contents according the targeted archive.
        # 'Archive Tag', 'Subject' and 'Source URL' are customized for PPA.
        # We only send build-notifications to 'buildd-admin' celebrity for
        # main archive candidates.
        # For PPA build notifications we include the archive.owner
        # contact_address.
        if not self.archive.is_ppa:
            buildd_admins = getUtility(ILaunchpadCelebrities).buildd_admin
            recipients = recipients.union(
                get_contact_email_addresses(buildd_admins))
            archive_tag = '%s primary archive' % self.distribution.name
            subject = "[Build #%d] %s" % (self.id, self.title)
            source_url = canonical_url(self.distributionsourcepackagerelease)
        else:
            recipients = recipients.union(
                get_contact_email_addresses(self.archive.owner))
            # For PPAs we run the risk of having no available contact_address,
            # for instance, when both, SPR.creator and Archive.owner have
            # not enabled it.
            if len(recipients) == 0:
                return
            archive_tag = '%s PPA' % get_ppa_reference(self.archive)
            subject = "[Build #%d] %s (%s)" % (
                self.id, self.title, archive_tag)
            source_url = 'not available'
            extra_headers['X-Launchpad-PPA'] = get_ppa_reference(self.archive)

        # XXX cprov 2006-08-02: pending security recipients for SECURITY
        # pocket build. We don't build SECURITY yet :(

        # XXX cprov 2006-08-02: find out a way to glue parameters reported
        # with the state in the build worflow, maybe by having an
        # IBuild.statusReport property, which could also be used in the
        # respective page template.
        if self.buildstate in [
            BuildStatus.NEEDSBUILD, BuildStatus.SUPERSEDED]:
            # untouched builds
            buildduration = 'not available'
            buildlog_url = 'not available'
            builder_url = 'not available'
        elif self.buildstate == BuildStatus.BUILDING:
            # build in process
            buildduration = 'not finished'
            buildlog_url = 'see builder page'
            builder_url = canonical_url(self.buildqueue_record.builder)
        else:
            # completed states (success and failure)
            buildduration = DurationFormatterAPI(
                self.buildduration).approximateduration()
            buildlog_url = self.build_log_url
            builder_url = canonical_url(self.builder)

        if self.buildstate == BuildStatus.FAILEDTOUPLOAD:
            assert extra_info is not None, (
                'Extra information is required for FAILEDTOUPLOAD '
                'notifications.')
            extra_info = 'Upload log:\n%s' % extra_info
        else:
            extra_info = ''

        template = get_email_template('build-notification.txt')
        replacements = {
            'source_name': self.sourcepackagerelease.name,
            'source_version': self.sourcepackagerelease.version,
            'architecturetag': self.distroarchseries.architecturetag,
            'build_state': self.buildstate.title,
            'build_duration': buildduration,
            'buildlog_url': buildlog_url,
            'builder_url': builder_url,
            'build_title': self.title,
            'build_url': canonical_url(self),
            'source_url': source_url,
            'extra_info': extra_info,
            'archive_tag': archive_tag,
            'component_tag' : self.current_component.name,
            }
        message = template % replacements

        for toaddress in recipients:
            simple_sendmail(
                fromaddress, toaddress, subject, message,
                headers=extra_headers)

    def storeUploadLog(self, content):
        """See `IBuild`."""
        assert self.upload_log is None, (
            "Upload log information already exist and cannot be overridden.")

        filename = 'upload_%s_log.txt' % self.id
        contentType = filenameToContentType(filename)
        file_size = len(content)
        file_content = StringIO(content)
        restricted = self.archive.private

        library_file = getUtility(ILibraryFileAliasSet).create(
            filename, file_size, file_content, contentType=contentType,
            restricted=restricted)
        self.upload_log = library_file

    def _getDebByFileName(self, filename):
        """Helper function to get a .deb LFA in the context of this build."""
        store = Store.of(self)
        return store.find(
            LibraryFileAlias,
            BinaryPackageRelease.build == self.id,
            BinaryPackageFile.binarypackagerelease == BinaryPackageRelease.id,
            LibraryFileAlias.id == BinaryPackageFile.libraryfileID,
            LibraryFileAlias.filename == filename
            ).one()

    def getFileByName(self, filename):
        """See `IBuild`."""
        if filename.endswith('.changes'):
            file_object = self.upload_changesfile
        elif filename.endswith('.txt.gz'):
            file_object = self.buildlog
        elif filename.endswith('_log.txt'):
            file_object = self.upload_log
        elif filename.endswith('deb'):
            file_object = self._getDebByFileName(filename)
        else:
            raise NotFoundError(filename)

        if file_object is not None and file_object.filename == filename:
            return file_object

        raise NotFoundError(filename)


class BuildSet:
    implements(IBuildSet)

    def getBuildBySRAndArchtag(self, sourcepackagereleaseID, archtag):
        """See `IBuildSet`"""
        clauseTables = ['DistroArchSeries']
        query = ('Build.sourcepackagerelease = %s '
                 'AND Build.distroarchseries = DistroArchSeries.id '
                 'AND DistroArchSeries.architecturetag = %s'
                 % sqlvalues(sourcepackagereleaseID, archtag)
                 )

        return Build.select(query, clauseTables=clauseTables)

    def getByBuildID(self, id):
        """See `IBuildSet`."""
        try:
            return Build.get(id)
        except SQLObjectNotFound, e:
            raise NotFoundError(str(e))

    def getPendingBuildsForArchSet(self, archseries):
        """See `IBuildSet`."""
        if not archseries:
            return None

        archseries_ids = [d.id for d in archseries]

        return Build.select(
            AND(Build.q.buildstate==BuildStatus.NEEDSBUILD,
                IN(Build.q.distroarchseriesID, archseries_ids))
            )

    def handleOptionalParamsForBuildQueries(
        self, queries, tables, status=None, name=None, pocket=None,
        arch_tag=None):
        """Construct query clauses needed/shared by all getBuild..() methods.

        This method is not exposed via the public interface as it is only
        used to DRY-up trusted code.

        :param queries: container to which to add any resulting query clauses.
        :param tables: container to which to add joined tables.
        :param status: optional build state for which to add a query clause if
            present.
        :param name: optional source package release name for which to add a
            query clause if present.
        :param pocket: optional pocket for which to add a query clause if
            present.
        :param arch_tag: optional architecture tag for which to add a
            query clause if present.
        """

        # Add query clause that filters on build state if the latter is
        # provided.
        if status is not None:
            queries.append('Build.buildstate=%s' % sqlvalues(status))

        # Add query clause that filters on pocket if the latter is provided.
        if pocket:
            queries.append('Build.pocket=%s' % sqlvalues(pocket))

        # Add query clause that filters on architecture tag if provided.
        if arch_tag is not None:
            queries.append('''
                Build.distroarchseries = DistroArchSeries.id AND
                DistroArchSeries.architecturetag = %s
            ''' % sqlvalues(arch_tag))
            tables.extend(['DistroArchSeries'])

        # Add query clause that filters on source package release name if the
        # latter is provided.
        if name is not None:
            queries.append('''
                Build.sourcepackagerelease = SourcePackageRelease.id AND
                SourcePackageRelease.sourcepackagename = SourcePackageName.id
                AND SourcepackageName.name LIKE '%%' || %s || '%%'
            ''' % quote_like(name))
            tables.extend(['SourcePackageRelease', 'SourcePackageName'])

    def getBuildsForBuilder(self, builder_id, status=None, name=None,
                            arch_tag=None, user=None):
        """See `IBuildSet`."""
        queries = []
        clauseTables = []

        self.handleOptionalParamsForBuildQueries(
            queries, clauseTables, status, name, pocket=None,
            arch_tag=arch_tag)

        # This code MUST match the logic in the Build security adapter,
        # otherwise users are likely to get 403 errors, or worse.
        queries.append("Archive.id = Build.archive")
        clauseTables.append('Archive')
        if user is not None:
            if not user.inTeam(getUtility(ILaunchpadCelebrities).admin):
                queries.append("""
                (Archive.private = FALSE
                 OR %s IN (SELECT TeamParticipation.person
                       FROM TeamParticipation
                       WHERE TeamParticipation.person = %s
                           AND TeamParticipation.team = Archive.owner)
                )""" % sqlvalues(user, user))
        else:
            queries.append("Archive.private = FALSE")

        queries.append("builder=%s" % builder_id)

        return Build.select(" AND ".join(queries), clauseTables=clauseTables,
                            orderBy=["-Build.datebuilt", "id"])

    def getBuildsForArchive(self, archive, status=None, name=None,
                            pocket=None, arch_tag=None):
        """See `IBuildSet`."""
        queries = []
        clauseTables = []

        self.handleOptionalParamsForBuildQueries(
            queries, clauseTables, status, name, pocket, arch_tag)

        # Ordering according status
        # * SUPERSEDED & All by -datecreated
        # * FULLYBUILT & FAILURES by -datebuilt
        # It should present the builds in a more natural order.
        if status == BuildStatus.SUPERSEDED or status is None:
            orderBy = ["-Build.datecreated"]
        else:
            orderBy = ["-Build.datebuilt"]
        # All orders fallback to id if the primary order doesn't succeed
        orderBy.append("id")

        queries.append("archive=%s" % sqlvalues(archive))
        clause = " AND ".join(queries)

        return self._decorate_with_prejoins(
            Build.select(clause, clauseTables=clauseTables, orderBy=orderBy))

    def getBuildsByArchIds(self, arch_ids, status=None, name=None,
                           pocket=None):
        """See `IBuildSet`."""
        # If not distroarchseries was found return empty list
        if not arch_ids:
            # XXX cprov 2006-09-08: returning and empty SelectResult to make
            # the callsites happy as bjorn suggested. However it would be
            # much clearer if we have something like SQLBase.empty() for this
            return Build.select("2=1")

        clauseTables = []

        # format clause according single/multiple architecture(s) form
        if len(arch_ids) == 1:
            condition_clauses = [('distroarchseries=%s'
                                  % sqlvalues(arch_ids[0]))]
        else:
            condition_clauses = [('distroarchseries IN %s'
                                  % sqlvalues(arch_ids))]

        # XXX cprov 2006-09-25: It would be nice if we could encapsulate
        # the chunk of code below (which deals with the optional paramenters)
        # and share it with ISourcePackage.getBuildRecords()

        # exclude gina-generated and security (dak-made) builds
        # buildstate == FULLYBUILT && datebuilt == null
        if status == BuildStatus.FULLYBUILT:
            condition_clauses.append("Build.datebuilt IS NOT NULL")
        else:
            condition_clauses.append(
                "(Build.buildstate <> %s OR Build.datebuilt IS NOT NULL)"
                % sqlvalues(BuildStatus.FULLYBUILT))

        # Ordering according status
        # * NEEDSBUILD & BUILDING by -lastscore
        # * SUPERSEDED & All by -datecreated
        # * FULLYBUILT & FAILURES by -datebuilt
        # It should present the builds in a more natural order.
        if status in [BuildStatus.NEEDSBUILD, BuildStatus.BUILDING]:
            orderBy = ["-BuildQueue.lastscore", "Build.id"]
            clauseTables.append('BuildQueue')
            clauseTables.append('BuildPackageJob')
            condition_clauses.append('BuildPackageJob.build = Build.id')
            condition_clauses.append('BuildPackageJob.job = BuildQueue.job')
        elif status == BuildStatus.SUPERSEDED or status is None:
            orderBy = ["-Build.datecreated"]
        else:
            orderBy = ["-Build.datebuilt"]

        # End of duplication (see XXX cprov 2006-09-25 above).

        self.handleOptionalParamsForBuildQueries(
            condition_clauses, clauseTables, status, name, pocket)

        # Only pick builds from the distribution's main archive to
        # exclude PPA builds
        clauseTables.append("Archive")
        condition_clauses.append("""
            Archive.purpose IN (%s) AND
            Archive.id = Build.archive
            """ % ','.join(
                sqlvalues(ArchivePurpose.PRIMARY, ArchivePurpose.PARTNER)))

        return self._decorate_with_prejoins(
            Build.select(' AND '.join(condition_clauses),
            clauseTables=clauseTables, orderBy=orderBy))

    def _decorate_with_prejoins(self, result_set):
        """Decorate build records with related data prefetch functionality."""
        # Grab the native storm result set.
        result_set = removeSecurityProxy(result_set)._result_set
        decorated_results = DecoratedResultSet(
            result_set, pre_iter_hook=self._prefetchBuildData)
        return decorated_results

    def retryDepWaiting(self, distroarchseries):
        """See `IBuildSet`. """
        # XXX cprov 20071122: use the root logger once bug 164203 is fixed.
        logger = logging.getLogger('retry-depwait')

        # Get the MANUALDEPWAIT records for all archives.
        candidates = Build.selectBy(
            buildstate=BuildStatus.MANUALDEPWAIT,
            distroarchseries=distroarchseries)

        candidates_count = candidates.count()
        if candidates_count == 0:
            logger.info("No MANUALDEPWAIT record found.")
            return

        logger.info(
            "Found %d builds in MANUALDEPWAIT state." % candidates_count)

        for build in candidates:
            if not build.can_be_retried:
                continue
            build.updateDependencies()
            if build.dependencies:
                logger.debug(
                    "Skipping %s: %s" % (build.title, build.dependencies))
                continue
            logger.info("Retrying %s" % build.title)
            build.retry()
            build.buildqueue_record.score()

    def getBuildsBySourcePackageRelease(self, sourcepackagerelease_ids,
                                        buildstate=None):
        """See `IBuildSet`."""
        if (sourcepackagerelease_ids is None or
            len(sourcepackagerelease_ids) == 0):
            return []

        query = """
            sourcepackagerelease IN %s AND
            archive.id = build.archive AND
            archive.purpose != %s
            """ % sqlvalues(sourcepackagerelease_ids, ArchivePurpose.PPA)

        if buildstate is not None:
            query += "AND buildstate = %s" % sqlvalues(buildstate)

        return Build.select(
            query, orderBy=["-datecreated", "id"],
            clauseTables=["Archive"])

    def getStatusSummaryForBuilds(self, builds):
        """See `IBuildSet`."""
        # Create a small helper function to collect the builds for a given
        # list of build states:
        def collect_builds(*states):
            wanted = []
            for state in states:
                candidates = [build for build in builds
                                if build.buildstate == state]
                wanted.extend(candidates)
            return wanted

        failed = collect_builds(BuildStatus.FAILEDTOBUILD,
                                BuildStatus.MANUALDEPWAIT,
                                BuildStatus.CHROOTWAIT,
                                BuildStatus.FAILEDTOUPLOAD)
        needsbuild = collect_builds(BuildStatus.NEEDSBUILD)
        building = collect_builds(BuildStatus.BUILDING)
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
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        origin = (
            Build,
            LeftJoin(
                SourcePackageRelease,
                SourcePackageRelease.id == Build.sourcepackagereleaseID),
            LeftJoin(
                SourcePackageName,
                SourcePackageName.id
                    == SourcePackageRelease.sourcepackagenameID),
            LeftJoin(LibraryFileAlias,
                     LibraryFileAlias.id == Build.buildlogID),
            LeftJoin(LibraryFileContent,
                     LibraryFileContent.id == LibraryFileAlias.contentID),
            LeftJoin(
                Builder,
                Builder.id == Build.builderID),
            )
        result_set = store.using(*origin).find(
            (SourcePackageRelease, LibraryFileAlias, SourcePackageName,
             LibraryFileContent, Builder),
            In(Build.id, build_ids))

        # Force query execution so that the ancillary data gets fetched
        # and added to StupidCache.
        # We are doing this here because there is no "real" caller of
        # this (pre_iter_hook()) method that will iterate over the
        # result set and force the query execution that way.
        return list(result_set)

    def getByQueueEntry(self, queue_entry):
        """See `IBuildSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        result_set = store.find(
            Build,
            BuildPackageJob.build == Build.id,
            BuildPackageJob.job == BuildQueue.jobID,
            BuildQueue.job == queue_entry.job)

        return result_set.one()

    def storeBuildInfo(self, queueItem, librarian, slave_status):
        """See `IBuildBase`."""
        super(Build, self).storeBuildInfo(queueItem, librarian, slave_status)
        self.dependencies = slave_status.get('dependencies')

    def _handleStatus_OK(self, queueItem, librarian, slave_status, logger):
        """Handle a package that built successfully.

        Once built successfully, we pull the files, store them in a
        directory, store build information and push them through the
        uploader.
        """
        # XXX cprov 2007-07-11 bug=129487: untested code path.
        buildid = slave_status['build_id']
        filemap = slave_status['filemap']
        dependencies = slave_status['dependencies']

        logger.debug("Processing successful build %s" % buildid)
        # Explode before collect a binary that is denied in this
        # distroseries/pocket
        if not self.archive.allowUpdatesToReleasePocket():
            assert self.distroseries.canUploadToPocket(self.pocket), (
                "%s (%s) can not be built for pocket %s: illegal status"
                % (self.title, self.id, self.pocket.name))

        # ensure we have the correct build root as:
        # <BUILDMASTER_ROOT>/incoming/<UPLOAD_LEAF>/<TARGET_PATH>/[FILES]
        root = os.path.abspath(config.builddmaster.root)
        incoming = os.path.join(root, 'incoming')

        # create a single directory to store build result files
        # UPLOAD_LEAF: <TIMESTAMP>-<BUILD_ID>-<BUILDQUEUE_ID>
        upload_leaf = "%s-%s" % (time.strftime("%Y%m%d-%H%M%S"), buildid)
        upload_dir = os.path.join(incoming, upload_leaf)
        logger.debug("Storing build result at '%s'" % upload_dir)

        # Build the right UPLOAD_PATH so the distribution and archive
        # can be correctly found during the upload:
        #       <archive_id>/distribution_name
        # for all destination archive types.
        archive = self.archive
        distribution_name = self.distribution.name
        target_path = '%s/%s' % (archive.id, distribution_name)
        upload_path = os.path.join(upload_dir, target_path)
        os.makedirs(upload_path)

        slave = removeSecurityProxy(queueItem.builder.slave)
        for filename in filemap:
            slave_file = slave.getFile(filemap[filename])
            out_file_name = os.path.join(upload_path, filename)
            out_file = open(out_file_name, "wb")
            copy_and_close(slave_file, out_file)

        uploader_argv = list(config.builddmaster.uploader.split())
        uploader_logfilename = os.path.join(upload_dir, 'uploader.log')
        logger.debug("Saving uploader log at '%s'"
                     % uploader_logfilename)

        # add extra arguments for processing a binary upload
        extra_args = [
            "--log-file", "%s" %  uploader_logfilename,
            "-d", "%s" % self.distribution.name,
            "-s", "%s" % (self.distroseries.name +
                          pocketsuffix[self.pocket]),
            "-b", "%s" % self.id,
            "-J", "%s" % upload_leaf,
            "%s" % root,
            ]

        uploader_argv.extend(extra_args)

        logger.debug("Invoking uploader on %s" % root)
        logger.debug("%s" % uploader_argv)

        uploader_process = subprocess.Popen(
            uploader_argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Nothing should be written to the stdout/stderr.
        upload_stdout, upload_stderr = uploader_process.communicate()

        # XXX cprov 2007-04-17: we do not check uploader_result_code
        # anywhere. We need to find out what will be best strategy
        # when it failed HARD (there is a huge effort in process-upload
        # to not return error, it only happen when the code is broken).
        uploader_result_code = uploader_process.returncode
        logger.debug("Uploader returned %d" % uploader_result_code)

        # Quick and dirty hack to carry on on process-upload failures
        if os.path.exists(upload_dir):
            logger.debug("The upload directory did not get moved.")
            failed_dir = os.path.join(root, "failed-to-move")
            if not os.path.exists(failed_dir):
                os.mkdir(failed_dir)
            os.rename(upload_dir, os.path.join(failed_dir, upload_leaf))

        # The famous 'flush_updates + clear_cache' will make visible
        # the DB changes done in process-upload, considering that the
        # transaction was set with ISOLATION_LEVEL_READ_COMMITED
        # isolation level.
        cur = cursor()
        cur.execute('SHOW transaction_isolation')
        isolation_str = cur.fetchone()[0]
        assert isolation_str == 'read committed', (
            'BuildMaster/BuilderGroup transaction isolation should be '
            'ISOLATION_LEVEL_READ_COMMITTED (not "%s")' % isolation_str)

        original_slave = queueItem.builder.slave

        # XXX: Add XXX
        # XXX Robert Collins, Celso Providelo 2007-05-26:
        # 'Refreshing' objects  procedure  is forced on us by using a
        # different process to do the upload, but as that process runs
        # in the same unix account, it is simply double handling and we
        # would be better off to do it within this process.
        flush_database_updates()
        clear_current_connection_cache()

        # XXX cprov 2007-06-15: Re-issuing removeSecurityProxy is forced on
        # us by sqlobject refreshing the builder object during the
        # transaction cache clearing. Once we sort the previous problem
        # this step should probably not be required anymore.
        queueItem.builder.setSlaveForTesting(
            removeSecurityProxy(original_slave))

        # Store build information, build record was already updated during
        # the binary upload.
        self.storeBuildInfo(queueItem, librarian, slave_status)

        # Retrive the up-to-date build record and perform consistency
        # checks. The build record should be updated during the binary
        # upload processing, if it wasn't something is broken and needs
        # admins attention. Even when we have a FULLYBUILT build record,
        # if it is not related with at least one binary, there is also
        # a problem.
        # For both situations we will mark the builder as FAILEDTOUPLOAD
        # and the and update the build details (datebuilt, duration,
        # buildlog, builder) in LP. A build-failure-notification will be
        # sent to the lp-build-admin celebrity and to the sourcepackagerelease
        # uploader about this occurrence. The failure notification will
        # also contain the information required to manually reprocess the
        # binary upload when it was the case.
        if (self.buildstate != BuildStatus.FULLYBUILT or
            self.binarypackages.count() == 0):
            logger.debug("Build %s upload failed." % self.id)
            self.buildstate = BuildStatus.FAILEDTOUPLOAD
            # Retrieve log file content.
            possible_locations = (
                'failed', 'failed-to-move', 'rejected', 'accepted')
            for location_dir in possible_locations:
                upload_final_location = os.path.join(
                    root, location_dir, upload_leaf)
                if os.path.exists(upload_final_location):
                    log_filepath = os.path.join(
                        upload_final_location, 'uploader.log')
                    uploader_log_file = open(log_filepath)
                    try:
                        uploader_log_content = uploader_log_file.read()
                    finally:
                        uploader_log_file.close()
                    break
            else:
                uploader_log_content = 'Could not find upload log file'
            # Store the upload_log_contents in librarian so it can be
            # accessed by anyone with permission to see the build.
            self.storeUploadLog(uploader_log_content)
            # Notify the build failure.
            self.notify(extra_info=uploader_log_content)
        else:
            logger.debug(
                "Gathered build %s completely" %
                self.sourcepackagerelease.name)

        # Release the builder for another job.
        queueItem.builder.cleanSlave()
        # Remove BuildQueue record.
        queueItem.destroySelf()

