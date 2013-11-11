# Copyright 2009-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'BuildQueue',
    'BuildQueueSet',
    'specific_job_classes',
    ]

from datetime import datetime
from itertools import groupby
from operator import attrgetter

import pytz
from sqlobject import (
    BoolCol,
    ForeignKey,
    IntCol,
    IntervalCol,
    StringCol,
    )
from zope.component import getSiteManager
from zope.interface import implements

from lp.buildmaster.enums import (
    BuildFarmJobType,
    BuildStatus,
    )
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJob
from lp.buildmaster.interfaces.buildqueue import (
    IBuildQueue,
    IBuildQueueSet,
    )
from lp.services.database.bulk import load_related
from lp.services.database.constants import DEFAULT
from lp.services.database.enumcol import EnumCol
from lp.services.database.sqlbase import SQLBase
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.model.job import Job
from lp.services.propertycache import (
    cachedproperty,
    get_property_cache,
    )


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

    def __init__(self, job, job_type=DEFAULT,  estimated_duration=DEFAULT,
                 virtualized=DEFAULT, processor=DEFAULT, lastscore=None):
        super(BuildQueue, self).__init__(job_type=job_type, job=job,
            virtualized=virtualized, processor=processor,
            estimated_duration=estimated_duration, lastscore=lastscore)
        if lastscore is None and self.specific_job is not None:
            self.score()

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

    @cachedproperty
    def specific_job(self):
        """See `IBuildQueue`."""
        specific_class = specific_job_classes()[self.job_type]
        return specific_class.getByJob(self.job)

    def _clear_specific_job_cache(self):
        del get_property_cache(self).specific_job

    @staticmethod
    def preloadSpecificJobData(queues):
        key = attrgetter('job_type')
        for job_type, grouped_queues in groupby(queues, key=key):
            specific_class = specific_job_classes()[job_type]
            queue_subset = list(grouped_queues)
            job_subset = load_related(Job, queue_subset, ['jobID'])
            # We need to preload the build farm jobs early to avoid
            # the call to _set_build_farm_job to look up BuildFarmBuildJobs
            # one by one.
            specific_class.preloadBuildFarmJobs(job_subset)
            specific_jobs = list(specific_class.getByJobs(job_subset))
            if len(specific_jobs) == 0:
                continue
            specific_class.preloadJobsData(specific_jobs)
            specific_jobs_dict = dict(
                (specific_job.job, specific_job)
                    for specific_job in specific_jobs)
            for queue in queue_subset:
                cache = get_property_cache(queue)
                cache.specific_job = specific_jobs_dict[queue.job]

    @property
    def date_started(self):
        """See `IBuildQueue`."""
        return self.job.date_started

    @property
    def current_build_duration(self):
        """See `IBuildQueue`."""
        date_started = self.date_started
        if date_started is None:
            return None
        else:
            return self._now() - date_started

    def destroySelf(self):
        """Remove this record and associated job/specific_job."""
        job = self.job
        specific_job = self.specific_job
        builder = self.builder
        SQLBase.destroySelf(self)
        specific_job.cleanUp()
        job.destroySelf()
        if builder is not None:
            del get_property_cache(builder).currentjob
        self._clear_specific_job_cache()

    def manualScore(self, value):
        """See `IBuildQueue`."""
        self.lastscore = value
        self.manual = True

    def score(self):
        """See `IBuildQueue`."""
        if self.manual:
            return
        # Allow the `IBuildFarmJob` instance with the data/logic specific to
        # the job at hand to calculate the score as appropriate.
        self.lastscore = self.specific_job.score()

    def markAsBuilding(self, builder):
        """See `IBuildQueue`."""
        self.builder = builder
        if self.job.status != JobStatus.RUNNING:
            self.job.start()
        self.specific_job.build.updateStatus(BuildStatus.BUILDING)
        if builder is not None:
            del get_property_cache(builder).currentjob

    def reset(self):
        """See `IBuildQueue`."""
        builder = self.builder
        self.builder = None
        if self.job.status != JobStatus.WAITING:
            self.job.queue()
        self.job.date_started = None
        self.job.date_finished = None
        self.logtail = None
        self.specific_job.build.updateStatus(BuildStatus.NEEDSBUILD)
        if builder is not None:
            del get_property_cache(builder).currentjob

    def cancel(self):
        """See `IBuildQueue`."""
        self.specific_job.build.updateStatus(BuildStatus.CANCELLED)
        self.destroySelf()

    def getEstimatedJobStartTime(self, now=None):
        """See `IBuildQueue`."""
        from lp.buildmaster.queuedepth import estimate_job_start_time
        return estimate_job_start_time(self, now or self._now())

    @staticmethod
    def _now():
        """Return current time (UTC).  Overridable for test purposes."""
        return datetime.now(pytz.utc)


class BuildQueueSet(object):
    """Utility to deal with BuildQueue content class."""
    implements(IBuildQueueSet)

    def get(self, buildqueue_id):
        """See `IBuildQueueSet`."""
        return BuildQueue.get(buildqueue_id)

    def getByBuilder(self, builder):
        """See `IBuildQueueSet`."""
        return BuildQueue.selectOneBy(builder=builder)
