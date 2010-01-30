# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = [
    'BuildQueue',
    'BuildQueueSet',
    'specific_job_classes',
    ]

from collections import defaultdict
import logging

from zope.component import getSiteManager, getUtility

from zope.interface import implements

from sqlobject import (
    StringCol, ForeignKey, BoolCol, IntCol, IntervalCol, SQLObjectNotFound)
from storm.expr import In, Join, LeftJoin
from storm.store import Store

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.webapp.interfaces import NotFoundError
from lp.buildmaster.interfaces.buildfarmjob import (
    BuildFarmJobType, IBuildFarmJob)
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.model.job import Job
from lp.soyuz.interfaces.build import BuildStatus
from lp.soyuz.interfaces.buildqueue import IBuildQueue, IBuildQueueSet
from lp.soyuz.model.buildpackagejob import BuildPackageJob
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


def normalize_virtualization(virtualized):
    """Jobs with NULL virtualization settings should be treated the
       same way as virtualized jobs."""
    return virtualized is None or virtualized


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
    processor = ForeignKey(dbName='processor', foreignKey='Processor')
    virtualized = BoolCol(dbName='virtualized')

    @property
    def required_build_behavior(self):
        """See `IBuildQueue`."""
        return IBuildFarmJobBehavior(self.specific_job)

    @property
    def specific_job(self):
        """See `IBuildQueue`."""
        specific_class = specific_job_classes()[self.job_type]
        return specific_class.getByJob(self.job)

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
        builders_in_total = builders_for_job = 0
        virtualized_total = 0
        native_total = 0

        builder_stats = dict()
        for processor, virtualized, count in results:
            builders_in_total += count
            if virtualized:
                virtualized_total += count
            else:
                native_total += count
            if my_processor is not None:
                if (my_processor.id == processor and
                    my_virtualized == virtualized):
                    # The job on hand can only run on builders with a
                    # particular processor/virtualization combination and
                    # this is how many of these we have.
                    builders_for_job = count
            builder_stats[(processor, virtualized)] = count
        if my_processor is None:
            # The job of interest (JOI) is processor independent.
            builders_for_job = builders_in_total

        builder_stats[(None, None)] = builders_in_total
        builder_stats[(None, True)] = virtualized_total
        builder_stats[(None, False)] = native_total

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

    def _estimateTimeToNextBuilder(self):
        """Estimate time until next builder becomes available.

        For the purpose of estimating the dispatch time of the job of interest
        (JOI) we need to know how long it will take until the job at the head
        of JOI's queue is dispatched.

        There are two cases to consider here: the head job is

            - processor dependent: only builders with the matching
              processor/virtualization combination should be considered.
            - *not* processor dependent: all builders with the matching
              virtualization setting should be considered.

        :return: The estimated number of seconds untils a builder capable of
            running the head job becomes available or None if no such builder
            exists.
        """
        head_job_platform = self._getHeadJobPlatform()
        if head_job_platform is None:
            # The job of interest (JOI) is the head job.
            return 0

        head_job_processor, head_job_virtualized = head_job_platform

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

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        result_set = store.execute(delay_query)
        head_job_delay = result_set.get_one()[0]
        if head_job_delay is None:
            return None
        else:
            return int(head_job_delay)

    def _getPendingJobsClauses(self):
        """WHERE clauses for pending job queries, used for dipatch time
        estimation."""
        virtualized = normalize_virtualization(self.virtualized)
        clauses = """
                BuildQueue.job = Job.id
                AND Job.status = %s
                AND (
                    -- The score must be either above my score or the
                    -- job must be older than me in cases where the
                    -- score is equal.
                    BuildQueue.lastscore > %s OR
                    (BuildQueue.lastscore = %s AND Job.id < %s))
                AND (
                    -- The virtualized values either match or the job
                    -- does not care about virtualization and the job
                    -- of interest (JOI) is to be run on a virtual builder
                    -- (we want to prevent the execution of untrusted code
                    -- on native builders).
                    buildqueue.virtualized = %s OR
                    (buildqueue.virtualized IS NULL AND %s = TRUE))
        """ % sqlvalues(
            JobStatus.WAITING, self.lastscore, self.lastscore, self.job,
            virtualized, virtualized)
        processor_clause = """
                AND (
                    -- The processor values either match or the candidate
                    -- job is processor-independent.
                    buildqueue.processor = %s OR
                    buildqueue.processor IS NULL)
        """ % sqlvalues(self.processor)
        # We don't care about processors if the estimation is for a
        # processor-independent job.
        if self.processor is not None:
            clauses += processor_clause
        return clauses

    def _getHeadJobPlatform(self):
        """Find the processor and virtualization setting for the head job.

        Among the jobs that compete with the job of interest (JOI) for
        builders and are queued ahead of it the head job is the one in pole
        position i.e. the one to be dispatched to a builder next.

        :return: A (processor, virtualized) tuple which is the head job's
        platform or None if the JOI is the head job.
        """
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        my_platform = (
            getattr(self.processor, 'id', None),
            normalize_virtualization(self.virtualized))
        query = """
            SELECT
                processor,
                virtualized
            FROM
                BuildQueue, Job
            WHERE
            """
        query += self._getPendingJobsClauses()
        query += """
            ORDER BY lastscore DESC, job LIMIT 1
            """
        head_job_platform = store.execute(query).get_all()
        if len(head_job_platform) == 1:
            head_job_platform = head_job_platform.pop()
        else:
            head_job_platform = None
        return head_job_platform

    def _estimateJobDelay(self, builder_stats):
        """Sum of estimated durations for *pending* jobs ahead in queue.

        For the purpose of estimating the dispatch time of the job of
        interest (JOI) we need to know the delay caused by all the pending
        jobs that are ahead of the JOI in the queue and that compete with it
        for builders.

        :param builder_stats: A dictionary with builder counts where the
            key is a (processor, virtualized) combination (aka "platform") and
            the value is the number of builders that can take on jobs
            requiring that combination.
        :return: An integer value holding the sum of delays (in seconds)
            caused by the jobs that are ahead of and competing with the JOI.
        """
        def jobs_compete_for_builders(a, b):
            """True if the two jobs compete for builders."""
            a_processor, a_virtualized = a
            b_processor, b_virtualized = b
            if a_processor is None or b_processor is None:
                # If either of the jobs is platform-independent then the two
                # jobs compete for the same builders if the virtualization
                # settings match.
                if a_virtualized == b_virtualized:
                    return True
            else:
                # Neither job is platform-independent, match processor and
                # virtualization settings.
                return a == b

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        my_platform = (
            getattr(self.processor, 'id', None),
            normalize_virtualization(self.virtualized))
        query = """
            SELECT
                BuildQueue.processor,
                BuildQueue.virtualized,
                COUNT(BuildQueue.job),
                CAST(EXTRACT(
                    EPOCH FROM
                        SUM(BuildQueue.estimated_duration)) AS INTEGER)
            FROM
                BuildQueue, Job
            WHERE
            """
        query += self._getPendingJobsClauses()
        query += """
            GROUP BY BuildQueue.processor, BuildQueue.virtualized
            """

        delays_by_platform = store.execute(query).get_all()

        # This will be used to capture per-platform delay totals.
        delays = defaultdict(int)
        # This will be used to capture per-platform job counts.
        job_counts = defaultdict(int)

        # Apply weights to the estimated duration of the jobs as follows:
        #   - if a job is tied to a processor TP then divide the estimated
        #     duration of that job by the number of builders that target TP
        #     since only these can build the job.
        #   - if the job is processor-independent then divide its estimated
        #     duration by the total number of builders with the same
        #     virtualization setting because any one of them may run it.
        for processor, virtualized, job_count, delay in delays_by_platform:
            virtualized = normalize_virtualization(virtualized)
            platform = (processor, virtualized)
            builder_count = builder_stats.get(platform, 0)
            if builder_count == 0:
                # There is no builder that can run this job, ignore it
                # for the purpose of dispatch time estimation.
                continue

            if jobs_compete_for_builders(my_platform, platform):
                # The jobs that target the platform at hand compete with
                # the JOI for builders, add their delays.
                delays[platform] += delay
                job_counts[platform] += job_count

        sum_of_delays = 0
        # Now weight/average the delays based on a jobs/builders comparison.
        for platform, duration in delays.iteritems():
            jobs = job_counts[platform]
            builders = builder_stats[platform]
            # If there are less jobs than builders that can take them on,
            # the delays should be averaged/divided by the number of jobs.
            denominator = (jobs if jobs < builders else builders)
            if denominator > 1:
                duration = int(duration/float(denominator))

            sum_of_delays += duration

        return sum_of_delays

    def getEstimatedJobStartTime(self):
        """See `IBuildQueue`.

        The estimated dispatch time for the build farm job at hand is
        calculated from the following ingredients:
            * the start time for the head job (job at the
              head of the respective build queue)
            * the estimated build durations of all jobs that
              precede the job of interest (JOI) in the build queue
              (weighted by the number of machines in the respective
              build pool)
        """
        # This method may only be invoked for pending jobs.
        if self.job.status != JobStatus.WAITING:
            raise AssertionError(
                "The start time is only estimated for pending jobs.")

        # A None value indicates that the estimated dispatch time is not
        # available.
        result = None

        (builders_in_total, builders_for_job,
         builder_stats) = self._getBuilderData()
        if builders_for_job == 0:
            # No builders that can run the job at hand
            #   -> no dispatch time estimation available.
            return result

        # Get the sum of the estimated run times for *pending* jobs that are
        # ahead of us in the queue.
        sum_of_delays = self._estimateJobDelay(builder_stats)

        # Get the minimum time duration until the next builder becomes
        # available.
        min_wait_time = self._estimateTimeToNextBuilder()

        start_time = min_wait_time + sum_of_delays

        result = (
            datetime.datetime.utcnow() +
            datetime.timedelta(seconds=start_time))

        return result


class BuildQueueSet(object):
    """Utility to deal with BuildQueue content class."""
    implements(IBuildQueueSet)

    def __init__(self):
        self.title = "The Launchpad build queue"

    def __iter__(self):
        """See `IBuildQueueSet`."""
        return iter(BuildQueue.select())

    def __getitem__(self, buildqueue_id):
        """See `IBuildQueueSet`."""
        try:
            return BuildQueue.get(buildqueue_id)
        except SQLObjectNotFound:
            raise NotFoundError(buildqueue_id)

    def get(self, buildqueue_id):
        """See `IBuildQueueSet`."""
        return BuildQueue.get(buildqueue_id)

    def getByJob(self, job):
        """See `IBuildQueueSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(BuildQueue, BuildQueue.job == job).one()

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
            # status is a property. Let's use _status.
            Job._status == JobStatus.RUNNING,
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
