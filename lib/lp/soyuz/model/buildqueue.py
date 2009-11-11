# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = [
    'BuildQueue',
    'BuildQueueSet'
    ]

from datetime import datetime
import logging
import pytz

from zope.component import getUtility
from zope.interface import implements

from sqlobject import (
    StringCol, ForeignKey, BoolCol, IntCol, SQLObjectNotFound)
from storm.expr import In, LeftJoin
from storm.store import Store

from canonical import encoding
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.webapp.interfaces import NotFoundError
from lp.registry.interfaces.sourcepackage import SourcePackageUrgency
from lp.services.job.interfaces.job import JobStatus
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.build import BuildStatus
from lp.soyuz.interfaces.buildqueue import (
    IBuildQueue, IBuildQueueSet, SoyuzJobType)
from lp.registry.interfaces.pocket import PackagePublishingPocket
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


class BuildQueue(SQLBase):
    implements(IBuildQueue)
    _table = "BuildQueue"
    _defaultOrder = "id"

    job = ForeignKey(dbName='job', foreignKey='Job', notNull=True)
    job_type = IntCol(dbName='job_type', default=1)
    builder = ForeignKey(dbName='builder', foreignKey='Builder', default=None)
    logtail = StringCol(dbName='logtail', default=None)
    lastscore = IntCol(dbName='lastscore', default=0)
    manual = BoolCol(dbName='manual', default=False)

    def _get_build(self):
        """Get the associated `IBuild` instance if this is `PackageBuildJob`.

        :raises AssertionError: if this is not a `PackageBuildJob` or if we
            do not find *exactly* one `IBuild` instance.
        """
        assert self.job_id == SoyuzJobType.PACKAGEBUILDJOB (
            "This job does not build source packages, no build record "
            "available.")
        store = Store.of(self)
        origin = [
            BuildQueue,
            Join(PackageBuildJob, PackageBuildJob.job = BuildQueue.job)]
        result_set = store.using(*origin).find(
            Build, Build.id == PackageBuildJob.build)
        assert result_set.count() == 1, (
            "Wrong number of `IBuild` instances (%s) associated with this job"
            % result_set.count())
        return result_set[0];

    def manualScore(self, value):
        """See `IBuildQueue`."""
        self.lastscore = value
        self.manual = True

    def score(self):
        """See `IBuildQueue`."""
        # Grab any logger instance available.
        logger = logging.getLogger()

        if self.manual:
            logger.debug(
                "%s (%d) MANUALLY RESCORED" % (self.name, self.lastscore))
            return

        # XXX Al-maisan, 2008-05-14 (bug #230330):
        # We keep touching the code here whenever a modification to the
        # scoring parameters/weights is needed. Maybe the latter can be
        # externalized?

        score_pocketname = {
            PackagePublishingPocket.BACKPORTS: 0,
            PackagePublishingPocket.RELEASE: 1500,
            PackagePublishingPocket.PROPOSED: 3000,
            PackagePublishingPocket.UPDATES: 3000,
            PackagePublishingPocket.SECURITY: 4500,
            }

        score_componentname = {
            'multiverse': 0,
            'universe': 250,
            'restricted': 750,
            'main': 1000,
            'partner' : 1250,
            }

        score_urgency = {
            SourcePackageUrgency.LOW: 5,
            SourcePackageUrgency.MEDIUM: 10,
            SourcePackageUrgency.HIGH: 15,
            SourcePackageUrgency.EMERGENCY: 20,
            }

        # Define a table we'll use to calculate the score based on the time
        # in the build queue.  The table is a sorted list of (upper time
        # limit in seconds, score) tuples.
        queue_time_scores = [
            (14400, 100),
            (7200, 50),
            (3600, 20),
            (1800, 15),
            (900, 10),
            (300, 5),
        ]

        private_archive_increment = 10000

        # For build jobs in rebuild archives a score value of -1
        # was chosen because their priority is lower than build retries
        # or language-packs. They should be built only when there is
        # nothing else to build.
        rebuild_archive_score = -10

        build = self._get_build()
        score = 0
        msg = "%s (%d) -> " % (build.title, self.lastscore)

        # Please note: the score for language packs is to be zero because
        # they unduly delay the building of packages in the main component
        # otherwise.
        if build.sourcepackagerelease.section.name == 'translations':
            msg += "LPack => score zero"
        elif build.archive.purpose == ArchivePurpose.COPY:
            score = rebuild_archive_score
            msg += "Rebuild archive => -10"
        else:
            # Calculates the urgency-related part of the score.
            urgency = score_urgency[self.urgency]
            score += urgency
            msg += "U+%d " % urgency

            # Calculates the pocket-related part of the score.
            score_pocket = score_pocketname[build.pocket]
            score += score_pocket
            msg += "P+%d " % score_pocket

            # Calculates the component-related part of the score.
            score_component = score_componentname[
                build.current_component.name]
            score += score_component
            msg += "C+%d " % score_component

            # Calculates the build queue time component of the score.
            right_now = datetime.now(pytz.timezone('UTC'))
            eta = right_now - self.job.date_created
            for limit, dep_score in queue_time_scores:
                if eta.seconds > limit:
                    score += dep_score
                    msg += "T+%d " % dep_score
                    break
            else:
                msg += "T+0 "

            # Private builds get uber score.
            if build.archive.private:
                score += private_archive_increment

            # Lastly, apply the archive score delta.  This is to boost
            # or retard build scores for any build in a particular
            # archive.
            score += build.archive.relative_build_score

        # Store current score value.
        self.lastscore = score

        logger.debug("%s= %d" % (msg, self.lastscore))

    def getLogFileName(self):
        """See `IBuildQueue`."""
        build = self._get_build()
        sourcename = build.sourcepackagerelease.name
        version = build.sourcepackagerelease.version
        # we rely on previous storage of current buildstate
        # in the state handling methods.
        state = build.buildstate.name

        dar = build.distroarchseries
        distroname = dar.distroseries.distribution.name
        distroseriesname = dar.distroseries.name
        archname = dar.architecturetag

        # logfilename format:
        # buildlog_<DISTRIBUTION>_<DISTROSeries>_<ARCHITECTURE>_\
        # <SOURCENAME>_<SOURCEVERSION>_<BUILDSTATE>.txt
        # as:
        # buildlog_ubuntu_dapper_i386_foo_1.0-ubuntu0_FULLYBUILT.txt
        # it fix request from bug # 30617
        return ('buildlog_%s-%s-%s.%s_%s_%s.txt' % (
            distroname, distroseriesname, archname, sourcename, version, state
            ))

    def markAsBuilding(self, builder):
        """See `IBuildQueue`."""
        self.builder = builder
        self.job.date_started = UTC_NOW
        self.job.status = JobStatus.RUNNING
        build = self._get_build()
        build.buildstate = BuildStatus.BUILDING
        # The build started, set the start time if not set already.
        if build.date_first_dispatched is None:
            build.date_first_dispatched = UTC_NOW

    def reset(self):
        """See `IBuildQueue`."""
        self.builder = None
        self.job.date_started = None
        self.job.status = JobStatus.WAITING
        self.logtail = None
        build = self._get_build()
        build.buildstate = BuildStatus.NEEDSBUILD

    def updateBuild_IDLE(self, build_id, build_status, logtail,
                         filemap, dependencies, logger):
        """See `IBuildQueue`."""
        build = self._get_build()
        logger.warn(
            "Builder %s forgot about build %s -- resetting buildqueue record"
            % (self.builder.url, build.title))
        self.reset()

    def updateBuild_BUILDING(self, build_id, build_status,
                             logtail, filemap, dependencies, logger):
        """See `IBuildQueue`."""
        self.logtail = encoding.guess(str(logtail))

    def updateBuild_ABORTING(self, buildid, build_status,
                             logtail, filemap, dependencies, logger):
        """See `IBuildQueue`."""
        self.logtail = "Waiting for slave process to be terminated"

    def updateBuild_ABORTED(self, buildid, build_status,
                            logtail, filemap, dependencies, logger):
        """See `IBuildQueue`."""
        self.builder.cleanSlave()
        self.builder = None
        self.job.date_started = None
        self.job.status = JobStatus.FAILED
        build = self._get_build()
        build.buildstate = BuildStatus.BUILDING


class BuildQueueSet(object):
    """Utility to deal with BuildQueue content class."""
    implements(IBuildQueueSet)

    def __init__(self):
        self.title = "The Launchpad build queue"

    def __iter__(self):
        """See `IBuildQueueSet`."""
        return iter(BuildQueue.select())

    def __getitem__(self, job_id):
        """See `IBuildQueueSet`."""
        try:
            return BuildQueue.get(job_id)
        except SQLObjectNotFound:
            raise NotFoundError(job_id)

    def get(self, job_id):
        """See `IBuildQueueSet`."""
        return BuildQueue.get(job_id)

    def count(self):
        """See `IBuildQueueSet`."""
        return BuildQueue.select().count()

    def getByBuilder(self, builder):
        """See `IBuildQueueSet`."""
        return BuildQueue.selectOneBy(builder=builder)

    def getActiveBuildJobs(self):
        """See `IBuildQueueSet`."""
        return BuildQueue.select('buildstart is not null')

    def calculateCandidates(self, archseries):
        """See `IBuildQueueSet`."""
        if not archseries:
            raise AssertionError("Given 'archseries' cannot be None/empty.")

        arch_ids = [d.id for d in archseries]

        query = """
           Build.distroarchseries IN %s AND
           Build.buildstate = %s AND
           BuildQueue.job_type = %s AND
           BuildQueue.job = PackageBuildJob.job AND
           PackageBuildJob.build = build.id AND
           BuildQueue.builder IS NULL
        """ % sqlvalues(
            arch_ids, BuildStatus.NEEDSBUILD, SoyuzJobType.PACKAGEBUILDJOB)

        candidates = BuildQueue.select(
            query, clauseTables=['Build'], orderBy=['-BuildQueue.lastscore'])

        return candidates

    def getForBuilds(self, build_ids):
        """See `IBuildQueueSet`."""
        # Avoid circular import problem.
        from lp.soyuz.model.builder import Builder

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

        origin = (
            PackageBuildJob,
            Join(BuildQueue, BuildQueue.job == PackageBuildJob.job),
            LeftJoin(
                Builder,
                BuildQueue.builderID == Builder.id),
            )
        result_set = store.using(*origin).find(
            (BuildQueue, Builder),
            In(PackageBuildJob.buildID, build_ids))

        return result_set
