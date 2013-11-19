# Copyright 2009-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'BuildQueue',
    'BuildQueueSet',
    'specific_job_classes',
    'specific_build_farm_job_sources',
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
from storm.properties import (
    DateTime,
    Int,
    )
from storm.references import Reference
from storm.store import Store
from zope.component import (
    getSiteManager,
    getUtility,
    )
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from lp.buildmaster.enums import (
    BuildFarmJobType,
    BuildQueueStatus,
    BuildStatus,
    )
from lp.buildmaster.interfaces.buildfarmjob import (
    IBuildFarmJob,
    ISpecificBuildFarmJobSource,
    )
from lp.buildmaster.interfaces.buildqueue import (
    IBuildQueue,
    IBuildQueueSet,
    )
from lp.services.database.bulk import load_related
from lp.services.database.constants import (
    DEFAULT,
    UTC_NOW,
    )
from lp.services.database.enumcol import EnumCol
from lp.services.database.sqlbase import SQLBase
from lp.services.job.interfaces.job import JobStatus
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


def specific_build_farm_job_sources():
    """Sources for specific jobs that may run on the build farm."""
    job_sources = dict()
    # Get all components that implement the `ISpecificBuildFarmJobSource`
    # interface.
    components = getSiteManager()
    implementations = sorted(
        components.getUtilitiesFor(ISpecificBuildFarmJobSource))
    # The above yields a collection of 2-tuples where the first element
    # is the name of the `BuildFarmJobType` enum and the second element
    # is the implementing class respectively.
    for job_enum_name, job_source in implementations:
        if not job_enum_name:
            continue
        job_enum = getattr(BuildFarmJobType, job_enum_name)
        job_sources[job_enum] = job_source

    return job_sources


class BuildQueue(SQLBase):
    implements(IBuildQueue)
    _table = "BuildQueue"
    _defaultOrder = "id"

    def __init__(self, build_farm_job, job, job_type=DEFAULT,
                 estimated_duration=DEFAULT, virtualized=DEFAULT,
                 processor=DEFAULT, lastscore=None):
        super(BuildQueue, self).__init__(_build_farm_job=build_farm_job,
            job_type=job_type, job=job, virtualized=virtualized,
            processor=processor, estimated_duration=estimated_duration,
            lastscore=lastscore)
        if lastscore is None and self.specific_build is not None:
            self.score()

    _build_farm_job_id = Int(name='build_farm_job')
    _build_farm_job = Reference(_build_farm_job_id, 'BuildFarmJob.id')
    status = EnumCol(enum=BuildQueueStatus, default=BuildQueueStatus.WAITING)
    date_started = DateTime(tzinfo=pytz.UTC)

    job = ForeignKey(dbName='job', foreignKey='Job')
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
    def specific_build(self):
        """See `IBuildQueue`."""
        bfj = self._build_farm_job
        specific_source = specific_build_farm_job_sources()[bfj.job_type]
        return specific_source.getByBuildFarmJob(bfj)

    def _clear_specific_build_cache(self):
        del get_property_cache(self).specific_build

    @cachedproperty
    def specific_old_job(self):
        """See `IBuildQueue`."""
        if self.job is None:
            return None
        specific_class = specific_job_classes()[self.job_type]
        return specific_class.getByJob(self.job)

    def _clear_specific_old_job_cache(self):
        del get_property_cache(self).specific_old_job

    @staticmethod
    def preloadSpecificBuild(queues):
        from lp.buildmaster.model.buildfarmjob import BuildFarmJob
        load_related(BuildFarmJob, queues, ['_build_farm_job_id'])
        bfj_to_bq = dict(
            (removeSecurityProxy(bq)._build_farm_job, bq)
            for bq in queues)
        key = attrgetter('job_type')
        for job_type, grouped_queues in groupby(queues, key=key):
            source = getUtility(ISpecificBuildFarmJobSource, job_type.name)
            builds = source.getByBuildFarmJobs(
                [bq._build_farm_job for bq in grouped_queues])
            for build in builds:
                bq = bfj_to_bq[build.build_farm_job]
                get_property_cache(bq).specific_build = build

    @property
    def current_build_duration(self):
        """See `IBuildQueue`."""
        date_started = self.date_started
        if date_started is None:
            return None
        else:
            return self._now() - date_started

    def destroySelf(self):
        """Remove this record and associated job/specific_old_job."""
        job = self.job
        specific_old_job = self.specific_old_job
        builder = self.builder
        Store.of(self).remove(self)
        if specific_old_job is not None:
            specific_old_job.cleanUp()
        Store.of(self).flush()
        if job is not None:
            job.destroySelf()
        if builder is not None:
            del get_property_cache(builder).currentjob
        self._clear_specific_old_job_cache()
        self._clear_specific_build_cache()

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
        self.lastscore = self.specific_build.calculateScore()

    def markAsBuilding(self, builder):
        """See `IBuildQueue`."""
        self.builder = builder
        if self.job is not None and self.job.status != JobStatus.RUNNING:
            self.job.start()
        self.status = BuildQueueStatus.RUNNING
        self.date_started = UTC_NOW
        self.specific_build.updateStatus(BuildStatus.BUILDING)
        if builder is not None:
            del get_property_cache(builder).currentjob

    def suspend(self):
        """See `IBuildQueue`."""
        if self.status != BuildQueueStatus.WAITING:
            raise AssertionError("Only waiting jobs can be suspended.")
        if self.job is not None:
            self.job.suspend()
        self.status = BuildQueueStatus.SUSPENDED

    def resume(self):
        """See `IBuildQueue`."""
        if self.status != BuildQueueStatus.SUSPENDED:
            raise AssertionError("Only suspended jobs can be resumed.")
        if self.job is not None:
            self.job.resume()
        self.status = BuildQueueStatus.WAITING

    def reset(self):
        """See `IBuildQueue`."""
        builder = self.builder
        self.builder = None
        if self.job is not None and self.job.status != JobStatus.WAITING:
            self.job.queue()
        self.status = BuildQueueStatus.WAITING
        self.date_started = None
        if self.job is not None:
            self.job.date_started = None
            self.job.date_finished = None
        self.logtail = None
        self.specific_build.updateStatus(BuildStatus.NEEDSBUILD)
        if builder is not None:
            del get_property_cache(builder).currentjob

    def cancel(self):
        """See `IBuildQueue`."""
        self.specific_build.updateStatus(BuildStatus.CANCELLED)
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
