# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    "InitialiseDistroSeriesJob",
]

from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.launchpad.interfaces.lpstorm import IStore

from lp.services.job.model.job import Job
from lp.soyuz.interfaces.distributionjob import (
    DistributionJobType,
    IInitialiseDistroSeriesJob,
    IInitialiseDistroSeriesJobSource,
    )
from lp.soyuz.model.distributionjob import (
    DistributionJob,
    DistributionJobDerived,
    )
from lp.soyuz.scripts.initialise_distroseries import (
    InitialiseDistroSeries,
    )

class InitialiseDistroSeriesJob(DistributionJobDerived):

    implements(IInitialiseDistroSeriesJob)

    class_job_type = DistributionJobType.INITIALISE_SERIES
    classProvides(IInitialiseDistroSeriesJobSource)

    @classmethod
    def create(cls, distroseries):
        """See `IInitialiseDistroSeriesJob`."""
        job = DistributionJob(
            distroseries.distribution, distroseries, cls.class_job_type,
            ())
        IStore(DistributionJob).add(job)
        return cls(job)

    def run(self):
        """See `IRunnableJob`."""
        ids = InitialiseDistroSeries(self.distroseries)
        ids.check()
        ids.initialise()

