# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = [
    'BuildQueue',
    'BuildQueueSet'
    ]

import logging

from zope.component import getUtility
from zope.interface import implements

from sqlobject import (
    StringCol, ForeignKey, BoolCol, IntCol, SQLObjectNotFound)
from storm.expr import In, Join, LeftJoin

from canonical import encoding
from canonical.database.constants import UTC_NOW
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.webapp.interfaces import NotFoundError
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.model.job import Job
from lp.soyuz.interfaces.build import BuildStatus, IBuildSet
from lp.soyuz.interfaces.buildqueue import IBuildQueue, IBuildQueueSet
from lp.soyuz.interfaces.soyuzjob import SoyuzJobType
from lp.soyuz.model.buildpackagejob import BuildPackageJob
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


class BuildQueue(SQLBase):
    implements(IBuildQueue)
    _table = "BuildQueue"
    _defaultOrder = "id"

    job = ForeignKey(dbName='job', foreignKey='Job', notNull=True)
    job_type = EnumCol(
        enum=SoyuzJobType, notNull=True, default=SoyuzJobType.PACKAGEBUILD,
        dbName='job_type')
    builder = ForeignKey(dbName='builder', foreignKey='Builder', default=None)
    logtail = StringCol(dbName='logtail', default=None)
    lastscore = IntCol(dbName='lastscore', default=0)
    manual = BoolCol(dbName='manual', default=False)

    def _get_specific_job(self):
        """Object with data and behaviour specific to the job type at hand."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        result_set = store.find(
            BuildPackageJob, BuildPackageJob.job == self.job)
        return result_set[0]

    def manualScore(self, value):
        """See `IBuildQueue`."""
        self.lastscore = value
        self.manual = True

    def score(self):
        """See `IBuildQueue`."""
        # Grab any logger instance available.
        logger = logging.getLogger()
        name = self._get_specific_job().getName()

        if self.manual:
            logger.debug(
                "%s (%d) MANUALLY RESCORED" % (name, self.lastscore))
            return

        # Allow the `ISoyuzJob` instance with the data/logic specific to the
        # job at hand to calculate the score as appropriate.
        the_job = self._get_specific_job()
        self.lastscore = the_job.score()

    def getLogFileName(self):
        """See `IBuildQueue`."""
        # Allow the `ISoyuzJob` instance with the data/logic specific to the
        # job at hand to calculate the log file name as appropriate.
        the_job = self._get_specific_job()
        return the_job.getLogFileName()

    def markAsBuilding(self, builder):
        """See `IBuildQueue`."""
        self.builder = builder
        self.job.start()
        build = getUtility(IBuildSet).getByQueueEntry(self)
        build.buildstate = BuildStatus.BUILDING
        # The build started, set the start time if not set already.
        if build.date_first_dispatched is None:
            build.date_first_dispatched = UTC_NOW

    def reset(self):
        """See `IBuildQueue`."""
        self.builder = None
        if self.job.status != JobStatus.WAITING:
            self.job.queue()
        self.job.date_started = None
        self.job.date_finished = None
        self.logtail = None
        build = getUtility(IBuildSet).getByQueueEntry(self)
        build.buildstate = BuildStatus.NEEDSBUILD

    def updateBuild_IDLE(self, build_id, build_status, logtail,
                         filemap, dependencies, logger):
        """See `IBuildQueue`."""
        build = getUtility(IBuildSet).getByQueueEntry(self)
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
        self.job.fail()
        self.job.date_started = None
        self.job.date_finished = None
        build = getUtility(IBuildSet).getByQueueEntry(self)
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
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        result_set = store.find(
            BuildQueue,
            BuildQueue.job == Job.id,
            Job.date_started is not None)
        return result_set

    def calculateCandidates(self, archseries):
        """See `IBuildQueueSet`."""
        if not archseries:
            raise AssertionError("Given 'archseries' cannot be None/empty.")

        arch_ids = [d.id for d in archseries]

        query = """
           Build.distroarchseries IN %s AND
           Build.buildstate = %s AND
           BuildQueue.job_type = %s AND
           BuildQueue.job = BuildPackageJob.job AND
           BuildPackageJob.build = build.id AND
           BuildQueue.builder IS NULL
        """ % sqlvalues(
            arch_ids, BuildStatus.NEEDSBUILD, SoyuzJobType.PACKAGEBUILD)

        candidates = BuildQueue.select(
            query, clauseTables=['Build', 'BuildPackageJob'],
            orderBy=['-BuildQueue.lastscore'])

        return candidates

    def getForBuilds(self, build_ids):
        """See `IBuildQueueSet`."""
        # Avoid circular import problem.
        from lp.soyuz.model.build import Build
        from lp.soyuz.model.builder import Builder

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

        origin = (
            BuildPackageJob,
            Join(BuildQueue, BuildPackageJob.job == BuildQueue.jobID),
            Join(Build, BuildPackageJob.build == Build.id),
            LeftJoin(
                Builder,
                BuildQueue.builderID == Builder.id),
            )
        result_set = store.using(*origin).find(
            (BuildQueue, Builder, BuildPackageJob),
            In(Build.id, build_ids))

        return result_set
