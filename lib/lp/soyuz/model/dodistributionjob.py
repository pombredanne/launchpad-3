# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    "DoDistributionJob",
]

from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.launchpad.interfaces.lpstorm import IStore

from lp.services.job.model.job import Job
from lp.soyuz.interfaces.distributionjob import (
    DistributionJobType,
    IDoDistributionJob,
    IDoDistributionJobSource)
from lp.soyuz.model.distributionjob import (
    DistributionJob,
    DistributionJobDerived)
from lp.soyuz.scripts.initialise_distroseries import (
    InitialiseDistroSeries)

class DoDistributionJob(DistributionJobDerived):

    implements(IDoDistributionJob)

    class_job_type = DistributionJobType.DO_INITIALISE
    classProvides(IDoDistributionJobSource)

    @classmethod
    def create(cls, distribution, distroseries):
        """See `IDoDistributionJob`."""
        # If there's already a job, don't create a new one.
        existing_job = IStore(DistributionJob).find(
            DistributionJob,
            DistributionJob.distribution == distribution,
            DistributionJob.distroseries == distroseries,
            DistributionJob.job_type == cls.class_job_type,
            DistributionJob.job == Job.id,
            Job.id.is_in(Job.ready_jobs)
            ).any()

        if existing_job is not None:
            return cls(existing_job)
        else:
            return super(
                DoDistributionJob, cls).create(distribution,
                    distroseries)

    def run(self):
        """See `IRunnableJob`."""
        ids = InitialiseDistroSeries(self.distroseries)
        ids.check()
        ids.initialise()

