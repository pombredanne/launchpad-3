# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['Build', 'BuildSet']


import apt_pkg
from cStringIO import StringIO
from datetime import datetime, timedelta
import logging

from zope.interface import implements
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from sqlobject import (
    StringCol, ForeignKey, IntervalCol, SQLObjectNotFound)
from sqlobject.sqlbuilder import AND, IN

from storm.expr import Desc, In, LeftJoin
from storm.references import Reference
from storm.store import Store

from canonical.config import config

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import cursor, quote_like, SQLBase, sqlvalues

from canonical.archivepublisher.utils import get_ppa_reference
from lp.soyuz.adapters.archivedependencies import (
    get_components_for_building)
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet)
from lp.soyuz.model.binarypackagerelease import (
    BinaryPackageRelease)
from lp.soyuz.model.builder import Builder
from lp.soyuz.model.buildqueue import BuildQueue
from lp.soyuz.model.publishing import (
    SourcePackagePublishingHistory)
from canonical.launchpad.database.librarian import (
    LibraryFileAlias, LibraryFileContent)
from lp.soyuz.model.queue import PackageUploadBuild
from canonical.launchpad.helpers import (
     get_contact_email_addresses, filenameToContentType, get_email_template)
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.build import (
    BuildStatus, BuildSetStatus, IBuild, IBuildSet)
from lp.soyuz.interfaces.builder import IBuilderSet
from canonical.launchpad.interfaces.launchpad import (
    NotFoundError, ILaunchpadCelebrities)
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from lp.soyuz.interfaces.publishing import (
    PackagePublishingPocket, active_publishing_status)
from canonical.launchpad.mail import simple_sendmail, format_address
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.launchpad.webapp.tales import DurationFormatterAPI


class Build(SQLBase):
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
    estimated_build_duration = IntervalCol(default=None)

    buildqueue_record = Reference("<primary key>", BuildQueue.buildID,
                                  on_remote=True)
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

    @property
    def current_component(self):
        """See `IBuild`."""
        pub = self.current_source_publication
        if pub is not None:
            return pub.component
        return self.sourcepackagerelease.component

    @property
    def current_source_publication(self):
        """See `IBuild`."""
        store = Store.of(self)
        results = store.find(
            SourcePackagePublishingHistory,
            SourcePackagePublishingHistory.archive == self.archive,
            SourcePackagePublishingHistory.distroseries == self.distroseries,
            SourcePackagePublishingHistory.sourcepackagerelease ==
                self.sourcepackagerelease,
            SourcePackagePublishingHistory.status.is_in(
                active_publishing_status))

        current_publication = results.order_by(
            Desc(SourcePackagePublishingHistory.id)).first()

        return current_publication

    @property
    def changesfile(self):
        """See `IBuild`"""
        queue_item = PackageUploadBuild.selectOneBy(build=self)
        if queue_item is None:
            return None
        return queue_item.packageupload.changesfile

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

    @property
    def package_upload(self):
        """See `IBuild`."""
        packageuploadbuild = PackageUploadBuild.selectOneBy(build=self.id)
        if packageuploadbuild is None:
            return None
        else:
            return packageuploadbuild.packageupload

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
                EXTRACT(EPOCH FROM SUM(Build.estimated_build_duration))
            FROM
                Archive
                JOIN Build ON
                    Build.archive = Archive.id
                JOIN BuildQueue ON
                    Build.id = BuildQueue.build
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
            result = datetime.utcnow() + timedelta(seconds=start_time)

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
                        (Build.estimated_build_duration -
                        (NOW() - BuildQueue.buildstart))) AS INTEGER)
                    AS remainder
            FROM
                Archive
                JOIN Build ON
                    Build.archive = Archive.id
                JOIN BuildQueue ON
                    Build.id = BuildQueue.build
                JOIN Builder ON
                    Builder.id = BuildQueue.builder
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
                % (token, self.title, self.id, self.depedencies))
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
                % (self.title, self.id, self.depedencies))

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

    def createBuildQueueEntry(self):
        """See `IBuild`"""
        return BuildQueue(build=self)

    def notify(self, extra_info=None):
        """See `IBuild`"""
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

    def getFileByName(self, filename):
        """See `IBuild`."""
        if filename.endswith('.changes'):
            file_object = self.changesfile
        elif filename.endswith('.txt.gz'):
            file_object = self.buildlog
        elif filename.endswith('_log.txt'):
            file_object = self.upload_log
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

    def getPendingBuildsForArchSet(self, archserieses):
        """See `IBuildSet`."""
        if not archserieses:
            return None

        archseries_ids = [d.id for d in archserieses]

        return Build.select(
            AND(Build.q.buildstate==BuildStatus.NEEDSBUILD,
                IN(Build.q.distroarchseriesID, archseries_ids))
            )

    def _handleOptionalParams(
        self, queries, tables, status=None, name=None, pocket=None):
        """Construct query clauses needed/shared by all getBuild..() methods.

        :param queries: container to which to add any resulting query clauses.
        :param tables: container to which to add joined tables.
        :param status: optional build state for which to add a query clause if
            present.
        :param name: optional source package release name for which to add a
            query clause if present.
        :param pocket: optional pocket for which to add a query clause if
            present.
        """
        # Add query clause that filters on build state if the latter is
        # provided.
        if status is not None:
            queries.append('buildstate=%s' % sqlvalues(status))

        # Add query clause that filters on pocket if the latter is provided.
        if pocket:
            queries.append('pocket=%s' % sqlvalues(pocket))

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
                            user=None):
        """See `IBuildSet`."""
        queries = []
        clauseTables = []

        self._handleOptionalParams(queries, clauseTables, status, name)

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
                            pocket=None):
        """See `IBuildSet`."""
        queries = []
        clauseTables = []

        self._handleOptionalParams(
            queries, clauseTables, status, name, pocket)

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
            condition_clauses.append('BuildQueue.build = Build.id')
        elif status == BuildStatus.SUPERSEDED or status is None:
            orderBy = ["-Build.datecreated"]
        else:
            orderBy = ["-Build.datebuilt"]

        # End of duplication (see XXX cprov 2006-09-25 above).

        self._handleOptionalParams(
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
