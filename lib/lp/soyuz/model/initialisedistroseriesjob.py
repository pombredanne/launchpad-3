# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    "InitialiseDistroSeriesJob",
]

from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.launchpad.interfaces.lpstorm import IMasterStore

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
    def create(cls, distroseries, arches=(), packagesets=()):
        """See `IInitialiseDistroSeriesJob`."""
        metadata = {'arches': arches, 'packagesets': packagesets}
        job = DistributionJob(
            distroseries.distribution, distroseries, cls.class_job_type,
            metadata)
        IMasterStore(DistributionJob).add(job)
        return cls(job)

    @property
    def arches(self):
        return tuple(self.metadata['arches'])

    @property
    def packagesets(self):
        return tuple(self.metadata['packagesets'])

    def run(self):
        """See `IRunnableJob`."""
        # XXX self.packagesets is missing
        ids = InitialiseDistroSeries(self.distroseries, self.arches)
        ids.check()
        ids.initialise()

