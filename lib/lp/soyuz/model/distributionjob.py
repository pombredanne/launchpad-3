# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    "DistributionJob",
    "DistributionJobDerived",
]

import simplejson

from storm.locals import And, Int, Reference, Unicode

from zope.interface import implements

from canonical.database.enumcol import EnumCol
from canonical.launchpad.interfaces.lpstorm import IStore

from lazr.delegates import delegates

from lp.app.errors import NotFoundError
from lp.registry.model.distribution import Distribution
from lp.registry.model.distroseries import DistroSeries
from lp.soyuz.interfaces.distributionjob import (
    DistributionJobType,
    IDistributionJob,
    )
from lp.services.job.model.job import Job
from lp.services.job.runner import BaseRunnableJob
from lp.services.database.stormbase import StormBase


class DistributionJob(StormBase):
    """Base class for jobs related to Distributions."""

    implements(IDistributionJob)

    __storm_table__ = 'DistributionJob'

    id = Int(primary=True)

    job_id = Int(name='job')
    job = Reference(job_id, Job.id)

    distribution_id = Int(name='distribution')
    distribution = Reference(distribution_id, Distribution.id)

    distroseries_id = Int(name='distroseries')
    distroseries = Reference(distroseries_id, DistroSeries.id)

    job_type = EnumCol(enum=DistributionJobType, notNull=True)

    _json_data = Unicode('json_data')

    def __init__(self, distribution, distroseries, job_type, metadata):
        super(DistributionJob, self).__init__()
        self.job = Job()
        self.distribution = distribution
        self.distroseries = distroseries
        self.job_type = job_type
        self._json_data = self.serializeMetadata(metadata)

    @classmethod
    def serializeMetadata(cls, metadata_dict):
        """Serialize a dict of metadata into a unicode string."""
        return simplejson.dumps(metadata_dict).decode('utf-8')

    @property
    def metadata(self):
        return simplejson.loads(self._json_data)


class DistributionJobDerived(BaseRunnableJob):
    """Abstract class for deriving from DistributionJob."""
    delegates(IDistributionJob)

    def __init__(self, job):
        self.context = job

    @classmethod
    def get(cls, job_id):
        """Get a job by id.

        :return: the DistributionJob with the specified id, as
                 the current DistributionJobDerived subclass.
        :raises: NotFoundError if there is no job with the specified id,
                 or its job_type does not match the desired subclass.
        """
        job = DistributionJob.get(job_id)
        if job.job_type != cls.class_job_type:
            raise NotFoundError(
                'No object found with id %d and type %s' % (job_id,
                cls.class_job_type.title))
        return cls(job)

    @classmethod
    def iterReady(cls):
        """Iterate through all ready DistributionJobs."""
        jobs = IStore(DistributionJob).find(
            DistributionJob,
            And(DistributionJob.job_type == cls.class_job_type,
                DistributionJob.job == Job.id,
                Job.id.is_in(Job.ready_jobs)))
        return (cls(job) for job in jobs)

    def getOopsVars(self):
        """See `IRunnableJob`."""
        vars = BaseRunnableJob.getOopsVars(self)
        vars.extend([
            ('distribution_id', self.context.distribution.id),
            ('distroseries_id', self.context.distroseries.id),
            ('distribution_job_id', self.context.id),
            ('distribution_job_type', self.context.job_type.title),
            ])
        return vars
