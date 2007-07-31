# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Build', 'BuildSet']


from zope.interface import implements
from zope.component import getUtility

from sqlobject import (
    StringCol, ForeignKey, IntervalCol, SQLObjectNotFound)
from sqlobject.sqlbuilder import AND, IN

from canonical.config import config

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues, quote, quote_like
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.lp.dbschema import (
    ArchivePurpose, BuildStatus, PackagePublishingPocket)

from canonical.launchpad.database.binarypackagerelease import (
    BinaryPackageRelease)
from canonical.launchpad.database.buildqueue import BuildQueue
from canonical.launchpad.database.queue import PackageUploadBuild
from canonical.launchpad.helpers import (
    get_email_template, contactEmailAddresses)
from canonical.launchpad.interfaces import (
    IBuild, IBuildSet, NotFoundError, ILaunchpadCelebrities)
from canonical.launchpad.mail import simple_sendmail, format_address
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.tales import DurationFormatterAPI



class Build(SQLBase):
    implements(IBuild)
    _table = 'Build'
    _defaultOrder = 'id'

    datecreated = UtcDateTimeCol(dbName='datecreated', default=UTC_NOW)
    processor = ForeignKey(dbName='processor', foreignKey='Processor',
        notNull=True)
    distroarchseries = ForeignKey(dbName='distroarchrelease',
        foreignKey='DistroArchSeries', notNull=True)
    buildstate = EnumCol(dbName='buildstate', notNull=True, schema=BuildStatus)
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

    @property
    def buildqueue_record(self):
        """See `IBuild`"""
        # XXX cprov 20051025
        # Would be nice if we can use fresh sqlobject feature 'singlejoin'
        # instead, see bug # 3424
        return BuildQueue.selectOneBy(build=self)

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
    def is_trusted(self):
        """See `IBuild`"""
        return self.archive.purpose != ArchivePurpose.PPA

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
    def distributionsourcepackagerelease(self):
        """See `IBuild`."""
        from canonical.launchpad.database.distributionsourcepackagerelease \
             import (
            DistributionSourcePackageRelease)

        return DistributionSourcePackageRelease(
            distribution=self.distroarchseries.distroseries.distribution,
            sourcepackagerelease=self.sourcepackagerelease)

    @property
    def binarypackages(self):
        """See `IBuild`."""
        bpklist = BinaryPackageRelease.selectBy(build=self, orderBy=['id'])
        return sorted(bpklist, key=lambda a: a.binarypackagename.name)

    @property
    def distroarchseriesbinarypackages(self):
        """See `IBuild`."""
        # Avoid circular import by importing locally.
        from canonical.launchpad.database.distroarchseriesbinarypackagerelease\
            import (DistroArchSeriesBinaryPackageRelease)
        return [DistroArchSeriesBinaryPackageRelease(
            self.distroarchseries, bp) 
            for bp in self.binarypackages]

    @property
    def can_be_retried(self):
        """See `IBuild`."""
        # check if the build would be properly collected if it was
        # reset. Do not reset denied builds.
        if (self.is_trusted and not
            self.distroseries.canUploadToPocket(self.pocket)):
            return False

        failed_buildstates = [
            BuildStatus.FAILEDTOBUILD,
            BuildStatus.MANUALDEPWAIT,
            BuildStatus.CHROOTWAIT,
            BuildStatus.FAILEDTOUPLOAD,
            ]

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
        assert self.can_be_retried, "Build %s can not be retried" % self.id

        self.buildstate = BuildStatus.NEEDSBUILD
        self.datebuilt = None
        self.buildduration = None
        self.builder = None
        self.buildlog = None
        self.dependencies = None
        self.createBuildQueueEntry()

    def __getitem__(self, name):
        return self.getBinaryPackageRelease(name)

    def getBinaryPackageRelease(self, name):
        """See `IBuild`."""
        for binpkg in self.binarypackages:
            if binpkg.name == name:
                return binpkg
        raise NotFoundError, 'No binary package "%s" in build' % name

    def createBinaryPackageRelease(self, binarypackagename, version,
                                   summary, description,
                                   binpackageformat, component,
                                   section, priority, shlibdeps,
                                   depends, recommends, suggests,
                                   conflicts, replaces, provides,
                                   essential, installedsize,
                                   copyright, licence,
                                   architecturespecific):
        """See `IBuild`."""
        return BinaryPackageRelease(build=self,
                                    binarypackagename=binarypackagename,
                                    version=version,
                                    summary=summary,
                                    description=description,
                                    binpackageformat=binpackageformat,
                                    component=component,
                                    section=section,
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
            }

        # XXX cprov 20061027: temporary extra debug info about the
        # SPR.creator in context, to be used during the service quarantine,
        # notify_owner will be disabled to avoid *spamming* Debian people.
        creator = self.sourcepackagerelease.creator
        extra_headers['X-Creator-Recipient'] = ",".join(
            contactEmailAddresses(creator))

        # Currently there are 7038 SPR published in edgy which the creators
        # have no preferredemail. They are the autosync ones (creator = katie,
        # 3583 packages) and the untouched sources since we have migrated from
        # DAK (the rest). We should not spam Debian maintainers.
        if config.builddmaster.notify_owner:
            recipients = recipients.union(contactEmailAddresses(creator))

        # Modify notification contents according the targeted archive.
        # 'Archive Tag', 'Subject' and 'Source URL' are customized for PPA.
        # We only send build-notifications to 'buildd-admin' celebrity for
        # main archive candidates.
        # For PPA build notifications we include the archive.owner
        # contact_address.
        if self.is_trusted:
            buildd_admins = getUtility(ILaunchpadCelebrities).buildd_admin
            recipients = recipients.union(
                contactEmailAddresses(buildd_admins))
            archive_tag = '%s main archive' % self.distribution.name
            subject = "[Build #%d] %s" % (self.id, self.title)
            source_url = canonical_url(self.distributionsourcepackagerelease)
        else:
            recipients = recipients.union(
                contactEmailAddresses(self.archive.owner))
            # For PPAs we run the risk of having no available contact_address,
            # for instance, when both, SPR.creator and Archive.owner have
            # not enabled it.
            if len(recipients) == 0:
                return
            archive_tag = '%s PPA' % self.archive.owner.name
            subject = "[Build #%d] %s (%s)" % (
                self.id, self.title, archive_tag)
            source_url = 'not available'

        # XXX cprov 20060802: pending security recipients for SECURITY
        # pocket build. We don't build SECURITY yet :(

        # XXX cprov 20060802: find out a way to glue parameters reported
        # with the state in the build worflow, maybe by having an
        # IBuild.statusReport property, which could also be used in the
        # respective page template.
        if self.buildstate in [BuildStatus.NEEDSBUILD, BuildStatus.SUPERSEDED]:
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
            buildlog_url = self.buildlog.http_url
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
            }
        message = template % replacements

        for toaddress in recipients:
            simple_sendmail(
                fromaddress, toaddress, subject, message,
                headers=extra_headers)


class BuildSet:
    implements(IBuildSet)

    def getBuildBySRAndArchtag(self, sourcepackagereleaseID, archtag):
        """See `IBuildSet`"""
        clauseTables = ['DistroArchRelease']
        query = ('Build.sourcepackagerelease = %s '
                 'AND Build.distroarchrelease = DistroArchRelease.id '
                 'AND DistroArchRelease.architecturetag = %s'
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

    def getBuildsForBuilder(self, builder_id, status=None, name=None):
        """See `IBuildSet`."""
        queries = []
        clauseTables = []

        if status:
            queries.append('buildstate=%s' % sqlvalues(status))

        if name:
            queries.append("Build.sourcepackagerelease="
                           "Sourcepackagerelease.id")
            queries.append("Sourcepackagerelease.sourcepackagename="
                           "Sourcepackagename.id")
            queries.append("Sourcepackagename.name LIKE '%%' || %s || '%%'"
                           % quote_like(name))
            clauseTables.append('Sourcepackagerelease')
            clauseTables.append('Sourcepackagename')

        # Ordering according status
        # * SUPERSEDED & All by -datecreated
        # * FULLYBUILT & FAILURES by -datebuilt
        # It should present the builds in a more natural order.
        if status == BuildStatus.SUPERSEDED or status is None:
            orderBy = ["-Build.datecreated"]
        else:
            orderBy = ["-Build.datebuilt"]

        # all orders fallback to -id if the primary order doesn't succeed
        orderBy.append("-id")


        queries.append("builder=%s" % builder_id)

        return Build.select(" AND ".join(queries), clauseTables=clauseTables,
                            orderBy=orderBy)

    def getBuildsForArchive(self, archive, status=None, name=None,
                            pocket=None):
        """See `IBuildSet`."""
        queries = []
        clauseTables = []

        if status:
            queries.append('buildstate=%s' % sqlvalues(status))

        if pocket:
            queries.append('pocket=%s' % sqlvalues(pocket))

        if name:
            queries.append("Build.sourcepackagerelease="
                           "Sourcepackagerelease.id")
            queries.append("Sourcepackagerelease.sourcepackagename="
                           "Sourcepackagename.id")
            queries.append("Sourcepackagename.name LIKE '%%' || %s || '%%'"
                           % quote_like(name))
            clauseTables.append('Sourcepackagerelease')
            clauseTables.append('Sourcepackagename')

        # Ordering according status
        # * SUPERSEDED & All by -datecreated
        # * FULLYBUILT & FAILURES by -datebuilt
        # It should present the builds in a more natural order.
        if status == BuildStatus.SUPERSEDED or status is None:
            orderBy = ["-Build.datecreated"]
        else:
            orderBy = ["-Build.datebuilt"]
        # All orders fallback to -id if the primary order doesn't succeed
        orderBy.append("-id")

        queries.append("archive=%s" % sqlvalues(archive))
        clause = " AND ".join(queries)

        return Build.select(
            clause, clauseTables=clauseTables,orderBy=orderBy)

    def getBuildsByArchIds(self, arch_ids, status=None, name=None,
                           pocket=None):
        """See `IBuildSet`."""
        # If not distroarchseries was found return empty list
        if not arch_ids:
            # XXX cprov 20060908: returning and empty SelectResult to make
            # the callsites happy as bjorn suggested. However it would be
            # much clearer if we have something like SQLBase.empty() for this
            return Build.select("2=1")

        clauseTables = []

        # format clause according single/multiple architecture(s) form
        if len(arch_ids) == 1:
            condition_clauses = [('distroarchrelease=%s'
                                  % sqlvalues(arch_ids[0]))]
        else:
            condition_clauses = [('distroarchrelease IN %s'
                                  % sqlvalues(arch_ids))]

        # XXX cprov 20060925: It would be nice if we could encapsulate
        # the chunk of code below (which deals with the optional paramenters)
        # and share it with ISourcePackage.getBuildRecords()

        # exclude gina-generated and security (dak-made) builds
        # buildstate == FULLYBUILT && datebuilt == null
        condition_clauses.append(
            "NOT (Build.buildstate = %s AND Build.datebuilt is NULL)"
            % sqlvalues(BuildStatus.FULLYBUILT))

        # attempt to given status
        if status is not None:
            condition_clauses.append('buildstate=%s' % sqlvalues(status))

        # restrict to provided pocket
        if pocket:
            condition_clauses.append('pocket=%s' % sqlvalues(pocket))

        # Ordering according status
        # * NEEDSBUILD & BUILDING by -lastscore
        # * SUPERSEDED & All by -datecreated
        # * FULLYBUILT & FAILURES by -datebuilt
        # It should present the builds in a more natural order.
        if status in [BuildStatus.NEEDSBUILD, BuildStatus.BUILDING]:
            orderBy = ["-BuildQueue.lastscore"]
            clauseTables.append('BuildQueue')
            condition_clauses.append('BuildQueue.build = Build.id')
        elif status == BuildStatus.SUPERSEDED or status is None:
            orderBy = ["-Build.datecreated"]
        else:
            orderBy = ["-Build.datebuilt"]

        # Fallback to ordering by -id as a tie-breaker.
        orderBy.append("-id")

        # End of duplication (see XXX cprov 20060925 above).

        if name:
            condition_clauses.append("Build.sourcepackagerelease="
                                     "Sourcepackagerelease.id")
            condition_clauses.append("Sourcepackagerelease.sourcepackagename="
                                     "Sourcepackagename.id")
            condition_clauses.append(
                "Sourcepackagename.name LIKE '%%' || %s || '%%'"
                % quote_like(name))
            clauseTables.append('Sourcepackagerelease')
            clauseTables.append('Sourcepackagename')

        # Only pick builds from the distribution's main archive to
        # exclude PPA builds
        clauseTables.extend(["DistroArchRelease",
                             "Archive",
                             "DistroRelease",
                             "Distribution"])
        condition_clauses.append("""
            Build.distroarchrelease = DistroArchRelease.id AND
            DistroArchRelease.distrorelease = DistroRelease.id AND
            DistroRelease.distribution = Distribution.id AND
            Distribution.id = Archive.distribution AND
            Archive.purpose = %s AND
            Archive.id = Build.archive
            """ % quote(ArchivePurpose.PRIMARY))

        return Build.select(' AND '.join(condition_clauses),
                            clauseTables=clauseTables,
                            orderBy=orderBy)
