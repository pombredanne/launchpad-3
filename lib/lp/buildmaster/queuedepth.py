# Copyright 2009-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'estimate_job_start_time',
    ]

from collections import defaultdict
from datetime import (
    datetime,
    timedelta,
    )

from pytz import utc
from storm.expr import Count

from lp.buildmaster.enums import BuildQueueStatus
from lp.buildmaster.model.builder import (
    Builder,
    BuilderProcessor,
    )
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import sqlvalues


def get_builder_data():
    """How many working builders are there, how are they configured?"""
    # XXX: This is broken with multi-Processor buildds, as it only
    # considers competition from the same processor.
    per_arch_totals = list(IStore(Builder).find(
        (BuilderProcessor.processor_id, Builder.virtualized,
         Count(Builder.id)),
        BuilderProcessor.builder_id == Builder.id,
        Builder._builderok == True, Builder.manual == False).group_by(
            BuilderProcessor.processor_id, Builder.virtualized))
    per_virt_totals = list(IStore(Builder).find(
        (Builder.virtualized, Count(Builder.id)),
        Builder._builderok == True, Builder.manual == False).group_by(
            Builder.virtualized))

    builder_stats = defaultdict(int)
    for virtualized, count in per_virt_totals:
        builder_stats[(None, virtualized)] = count
    for processor, virtualized, count in per_arch_totals:
        builder_stats[(processor, virtualized)] = count
    return builder_stats


def get_free_builders_count(processor, virtualized):
    """How many builders capable of running jobs for the given processor
    and virtualization combination are idle/free at present?"""
    query = """
        SELECT COUNT(id) FROM builder
        WHERE
            builderok = TRUE AND manual = FALSE
            AND id NOT IN (
                SELECT builder FROM BuildQueue WHERE builder IS NOT NULL)
            AND virtualized = %s
        """ % sqlvalues(virtualized)
    if processor is not None:
        query += """
            AND id IN (
                SELECT builder FROM BuilderProcessor WHERE processor = %s)
        """ % sqlvalues(processor)
    result_set = IStore(BuildQueue).execute(query)
    free_builders = result_set.get_one()[0]
    return free_builders


def get_head_job_platform(bq):
    """Find the processor and virtualization setting for the head job.

    Among the jobs that compete with the job of interest (JOI) for
    builders and are queued ahead of it the head job is the one in pole
    position i.e. the one to be dispatched to a builder next.

    :return: A (processor, virtualized) tuple which is the head job's
    platform or None if the JOI is the head job.
    """
    my_platform = (getattr(bq.processor, 'id', None), bq.virtualized)
    query = """
        SELECT
            processor,
            virtualized
        FROM BuildQueue
        WHERE
        """
    query += get_pending_jobs_clauses(bq)
    query += """
        ORDER BY lastscore DESC, id LIMIT 1
        """
    result = IStore(BuildQueue).execute(query).get_one()
    return (my_platform if result is None else result)


def estimate_time_to_next_builder(bq, now=None):
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
        running the head job becomes available.
    """
    head_job_platform = get_head_job_platform(bq)

    # Return a zero delay if we still have free builders available for the
    # given platform/virtualization combination.
    free_builders = get_free_builders_count(*head_job_platform)
    if free_builders > 0:
        return 0

    head_job_processor, head_job_virtualized = head_job_platform

    now = now or datetime.now(utc)
    delay_query = """
        SELECT MIN(
            CASE WHEN
            EXTRACT(EPOCH FROM
                (BuildQueue.estimated_duration -
                (((%s AT TIME ZONE 'UTC') - BuildQueue.date_started))))  >= 0
            THEN
            EXTRACT(EPOCH FROM
                (BuildQueue.estimated_duration -
                (((%s AT TIME ZONE 'UTC') - BuildQueue.date_started))))
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
            BuildQueue, Builder
        WHERE
            BuildQueue.builder = Builder.id
            AND Builder.manual = False
            AND Builder.builderok = True
            AND BuildQueue.status = %s
            AND Builder.virtualized = %s
        """ % sqlvalues(
            now, now, BuildQueueStatus.RUNNING, head_job_virtualized)

    if head_job_processor is not None:
        # Only look at builders with specific processor types.
        delay_query += """
            AND Builder.id IN (
                SELECT builder FROM BuilderProcessor WHERE processor = %s)
            """ % sqlvalues(head_job_processor)

    result_set = IStore(BuildQueue).execute(delay_query)
    head_job_delay = result_set.get_one()[0]
    return (0 if head_job_delay is None else int(head_job_delay))


def get_pending_jobs_clauses(bq):
    """WHERE clauses for pending job queries, used for dipatch time
    estimation."""
    clauses = """
        BuildQueue.status = %s
        AND (
            -- The score must be either above my score or the
            -- job must be older than me in cases where the
            -- score is equal.
            BuildQueue.lastscore > %s OR
            (BuildQueue.lastscore = %s AND BuildQueue.id < %s))
        AND buildqueue.virtualized = %s
        """ % sqlvalues(
            BuildQueueStatus.WAITING, bq.lastscore, bq.lastscore, bq,
            bq.virtualized)
    processor_clause = """
        AND (
            -- The processor values either match or the candidate
            -- job is processor-independent.
            buildqueue.processor = %s OR
            buildqueue.processor IS NULL)
        """ % sqlvalues(bq.processor)
    # We don't care about processors if the estimation is for a
    # processor-independent job.
    if bq.processor is not None:
        clauses += processor_clause
    return clauses


def estimate_job_delay(bq, builder_stats):
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
    # XXX: This is broken with multi-Processor buildds, as it only
    # considers competition from the same processor.
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

    my_platform = (getattr(bq.processor, 'id', None), bq.virtualized)
    query = """
        SELECT
            BuildQueue.processor,
            BuildQueue.virtualized,
            COUNT(BuildQueue.id),
            CAST(EXTRACT(
                EPOCH FROM
                    SUM(BuildQueue.estimated_duration)) AS INTEGER)
        FROM BuildQueue
        WHERE
        """
    query += get_pending_jobs_clauses(bq)
    query += """
        GROUP BY BuildQueue.processor, BuildQueue.virtualized
        """

    delays_by_platform = IStore(BuildQueue).execute(query).get_all()

    # This will be used to capture per-platform delay totals.
    delays = defaultdict(int)
    # This will be used to capture per-platform job counts.
    job_counts = defaultdict(int)

    # Divide the estimated duration of the jobs as follows:
    #   - if a job is tied to a processor TP then divide the estimated
    #     duration of that job by the number of builders that target TP
    #     since only these can build the job.
    #   - if the job is processor-independent then divide its estimated
    #     duration by the total number of builders with the same
    #     virtualization setting because any one of them may run it.
    for processor, virtualized, job_count, delay in delays_by_platform:
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
    # Now devide the delays based on a jobs/builders comparison.
    for platform, duration in delays.iteritems():
        jobs = job_counts[platform]
        builders = builder_stats[platform]
        # If there are less jobs than builders that can take them on,
        # the delays should be averaged/divided by the number of jobs.
        denominator = (jobs if jobs < builders else builders)
        if denominator > 1:
            duration = int(duration / float(denominator))

        sum_of_delays += duration

    return sum_of_delays


def estimate_job_start_time(bq, now=None):
    """Estimate the start time of the given `IBuildQueue`.

    The estimated dispatch time for the build farm job at hand is
    calculated from the following ingredients:
        * the start time for the head job (job at the
            head of the respective build queue)
        * the estimated build durations of all jobs that
            precede the job of interest (JOI) in the build queue
            (divided by the number of machines in the respective
            build pool)
    """
    # This method may only be invoked for pending jobs.
    if bq.status != BuildQueueStatus.WAITING:
        raise AssertionError(
            "The start time is only estimated for pending jobs.")

    # XXX: This is broken with multi-Processor buildds, as it only
    # considers competition from the same processor.

    builder_stats = get_builder_data()
    platform = (getattr(bq.processor, 'id', None), bq.virtualized)
    if builder_stats[platform] == 0:
        # No builders that can run the job at hand
        #   -> no dispatch time estimation available.
        return None

    # Get the sum of the estimated run times for *pending* jobs that are
    # ahead of us in the queue.
    sum_of_delays = estimate_job_delay(bq, builder_stats)

    # Get the minimum time duration until the next builder becomes
    # available.
    min_wait_time = estimate_time_to_next_builder(bq, now=now)

    # A job will not get dispatched in less than 5 seconds no matter what.
    start_time = max(5, min_wait_time + sum_of_delays)
    result = (now or datetime.now(utc)) + timedelta(seconds=start_time)
    return result
