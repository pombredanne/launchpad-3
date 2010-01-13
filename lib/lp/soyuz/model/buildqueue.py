# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = [
    'BuildQueue',
    'BuildQueueSet',
    'specific_job_classes'
    ]

import logging

from zope.component import getSiteManager, getUtility

from zope.interface import implements

from sqlobject import (
    StringCol, ForeignKey, BoolCol, IntCol, IntervalCol, SQLObjectNotFound)
from storm.expr import In, Join, LeftJoin
from storm.store import Store

from canonical import encoding
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.webapp.interfaces import NotFoundError
from lp.buildmaster.interfaces.buildfarmjob import (
    BuildFarmJobType, IBuildFarmJob)
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.model.job import Job
from lp.soyuz.interfaces.build import BuildStatus, IBuildSet
from lp.soyuz.interfaces.buildqueue import IBuildQueue, IBuildQueueSet
from lp.soyuz.model.buildpackagejob import BuildPackageJob
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


def specific_job_classes():
    """Job classes that may run on the build farm."""
    job_classes = dict()
    # Get all components that implement the `IBuildFarmJob` interface.
    components = getSiteManager()
    implementations = sorted(components.getUtilitiesFor(IBuildFarmJob))
    # The above yields a collection of 2-tuples where the first element
    # is the name of the `BuildFarmJobType` enum and the second element
    # is the implementing class respectively.
    for job_enum_name, job_class in implementations:
        job_enum = getattr(BuildFarmJobType, job_enum_name)
        job_classes[job_enum] = job_class

    return job_classes


class BuildQueue(SQLBase):
    implements(IBuildQueue)
    _table = "BuildQueue"
    _defaultOrder = "id"

    job = ForeignKey(dbName='job', foreignKey='Job', notNull=True)
    job_type = EnumCol(
        enum=BuildFarmJobType, notNull=True,
        default=BuildFarmJobType.PACKAGEBUILD, dbName='job_type')
    builder = ForeignKey(dbName='builder', foreignKey='Builder', default=None)
    logtail = StringCol(dbName='logtail', default=None)
    lastscore = IntCol(dbName='lastscore', default=0)
    manual = BoolCol(dbName='manual', default=False)
    estimated_duration = IntervalCol()
    processor = ForeignKey(
        dbName='processor', foreignKey='Processor', notNull=True)
    virtualized = BoolCol(dbName='virtualized')

    @property
    def required_build_behavior(self):
        """See `IBuildQueue`."""
        return IBuildFarmJobBehavior(self.specific_job)

    @property
    def specific_job(self):
        """See `IBuildQueue`."""
        specific_class = specific_job_classes()[self.job_type]
        store = Store.of(self)
        result_set = store.find(
            specific_class, specific_class.job == self.job)
        return result_set.one()

    @property
    def date_started(self):
        """See `IBuildQueue`."""
        return self.job.date_started

    def destroySelf(self):
        """Remove this record and associated job/specific_job."""
        job = self.job
        specific_job = self.specific_job
        SQLBase.destroySelf(self)
        Store.of(specific_job).remove(specific_job)
        job.destroySelf()

    def manualScore(self, value):
        """See `IBuildQueue`."""
        self.lastscore = value
        self.manual = True

    def score(self):
        """See `IBuildQueue`."""
        # Grab any logger instance available.
        logger = logging.getLogger()
        name = self.specific_job.getName()

        if self.manual:
            logger.debug(
                "%s (%d) MANUALLY RESCORED" % (name, self.lastscore))
            return

        # Allow the `IBuildFarmJob` instance with the data/logic specific to
        # the job at hand to calculate the score as appropriate.
        self.lastscore = self.specific_job.score()

    def getLogFileName(self):
        """See `IBuildQueue`."""
        # Allow the `IBuildFarmJob` instance with the data/logic specific to
        # the job at hand to calculate the log file name as appropriate.
        return self.specific_job.getLogFileName()

    def markAsBuilding(self, builder):
        """See `IBuildQueue`."""
        self.builder = builder
        if self.job.status != JobStatus.RUNNING:
            self.job.start()
        self.specific_job.jobStarted()

    def reset(self):
        """See `IBuildQueue`."""
        self.builder = None
        if self.job.status != JobStatus.WAITING:
            self.job.queue()
        self.job.date_started = None
        self.job.date_finished = None
        self.logtail = None
        self.specific_job.jobReset()

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
        if self.job.status != JobStatus.RUNNING:
            self.job.start()
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
        if self.job.status != JobStatus.FAILED:
            self.job.fail()
        self.job.date_started = None
        self.job.date_finished = None
        self.specific_job.jobAborted()

    def setDateStarted(self, timestamp):
        """See `IBuildQueue`."""
        self.job.date_started = timestamp

    def _getBuilderData(self):
        """How many working builders are there, how are they configured?"""
        # Please note: this method will send only one request to the database.

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        my_processor = self.specific_job.processor
        my_virtualized = self.specific_job.virtualized

        # We need to know the total number of builders as well as the
        # number of builders that can run the job of interest (JOI).
        # If the JOI is processor independent these builder counts will
        # have the same value.
        builder_data = """
            SELECT processor, virtualized, COUNT(id) FROM builder
            WHERE builderok = TRUE AND manual = FALSE
            GROUP BY processor, virtualized;
        """
        results = store.execute(builder_data).get_all()

        builder_stats = dict()
        builders_in_total = builders_for_job = 0
        for processor, virtualized, count in results:
            if my_processor is not None:
                if (my_processor.id == processor and
                    my_virtualized == virtualized):
                    # The job on hand can only run on builders with a
                    # particular processor/virtualization combination and
                    # this is how many of these we have.
                    builders_for_job = count
            builders_in_total += count
            builder_stats[(processor, virtualized)] = count
        if my_processor is None:
            # The job of interest (JOI) is processor independent.
            builders_for_job = builders_in_total

        return (builders_in_total, builders_for_job, builder_stats)

    def _freeBuildersCount(self, processor, virtualized):
        """How many builders capable of running jobs for the given processor
        and virtualization combination are idle/free at present?"""
        query = """
            SELECT COUNT(id) FROM builder
            WHERE
                builderok = TRUE AND manual = FALSE
                AND id NOT IN (
                    SELECT builder FROM BuildQueue WHERE builder IS NOT NULL)
            """
        if processor is not None:
            query += """
                AND processor = %s AND virtualized = %s
            """ % sqlvalues(processor, virtualized)
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        result_set = store.execute(query)
        free_builders = result_set.get_one()[0]
        return free_builders

    def _estimateTimeToNextBuilder(
        self, head_job_processor, head_job_virtualized):
        """Estimate time until next builder becomes available.
        
        For the purpose of estimating the dispatch time of the job of interest
        (JOI) we need to know how long it will take until the job at the head
        of JOI's queue is dispatched.

        There are two cases to consider here: the head job is

            - processor dependent: only builders with the matching
              processor/virtualization combination should be considered.
            - *not* processor dependent: all builders should be considered.

        :param head_job_processor: The processor required by the job at the
            head of the queue.
        :param head_job_virtualized: The virtualization setting required by
            the job at the head of the queue.
        :return: The estimated number of seconds untils a builder capable of
            running the head job becomes available or None if no such builder
            exists.
        """
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

        # First check whether we have free builders.
        free_builders = self._freeBuildersCount(
            head_job_processor, head_job_virtualized)

        if free_builders > 0:
            # We have free builders for the given processor/virtualization
            # combination -> zero delay
            return 0

        extra_clauses = ''
        if head_job_processor is not None:
            # Only look at builders with specific processor types.
            extra_clauses += """
                AND Builder.processor = %s
                AND Builder.virtualized = %s
                """ % sqlvalues(head_job_processor, head_job_virtualized)

        params = sqlvalues(JobStatus.RUNNING) + (extra_clauses,)

        delay_query = """
            SELECT MIN(
              CASE WHEN 
                EXTRACT(EPOCH FROM
                  (BuildQueue.estimated_duration -
                   (((now() AT TIME ZONE 'UTC') - Job.date_started))))  >= 0
              THEN
                EXTRACT(EPOCH FROM
                  (BuildQueue.estimated_duration -
                   (((now() AT TIME ZONE 'UTC') - Job.date_started))))
              ELSE
                -- Assume that jobs that have overdrawn their estimated
                -- duration time budget will complete within 2 minutes.
                -- This is a wild guess but has worked well so far.
                --
                -- Please note that this is entirely innocuous i.e. if our
                -- guess is off nothing bad will happen but our estimate will
                -- not be as good as it could be.
                120
              END)
            FROM
                BuildQueue, Job, Builder
            WHERE
                BuildQueue.job = Job.id
                AND BuildQueue.builder = Builder.id
                AND Builder.manual = False
                AND Builder.builderok = True
                AND Job.status = %s
                %s
            """ % params

        result_set = store.execute(delay_query)
        head_job_delay = result_set.get_one()[0]
        if head_job_delay is None:
            return None
        else:
            return int(head_job_delay)


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
            Job.date_started != None)
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
            arch_ids, BuildStatus.NEEDSBUILD, BuildFarmJobType.PACKAGEBUILD)

        candidates = BuildQueue.select(
            query, clauseTables=['Build', 'BuildPackageJob'],
            orderBy=['-BuildQueue.lastscore'])

        return candidates

    def getForBuilds(self, build_ids):
        """See `IBuildQueueSet`."""
        # Avoid circular import problem.
        from lp.soyuz.model.build import Build
        from lp.buildmaster.model.builder import Builder

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
