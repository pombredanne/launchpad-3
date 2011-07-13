# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    "InitializeDistroSeriesJob",
]

from zope.interface import (
    classProvides,
    implements,
    )

from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    IStore,
    )
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.model.job import Job
from lp.soyuz.interfaces.distributionjob import (
    DistributionJobType,
    IInitializeDistroSeriesJob,
    IInitializeDistroSeriesJobSource,
    InitializationCompleted,
    InitializationPending,
    )
from lp.soyuz.model.distributionjob import (
    DistributionJob,
    DistributionJobDerived,
    )
from lp.soyuz.scripts.initialize_distroseries import InitializeDistroSeries


class InitializeDistroSeriesJob(DistributionJobDerived):

    implements(IInitializeDistroSeriesJob)

    class_job_type = DistributionJobType.INITIALIZE_SERIES
    classProvides(IInitializeDistroSeriesJobSource)

    @classmethod
    def create(cls, child, parents, arches=(), packagesets=(),
               rebuild=False, overlays=(), overlay_pockets=(),
               overlay_components=()):
        """See `IInitializeDistroSeriesJob`."""
        store = IMasterStore(DistributionJob)
        # Only one InitializeDistroSeriesJob can be present at a time.
        distribution_job = store.find(
            DistributionJob, DistributionJob.job_id == Job.id,
            DistributionJob.job_type == cls.class_job_type,
            DistributionJob.distroseries_id == child.id).one()
        if distribution_job is not None:
            if distribution_job.job.status == JobStatus.FAILED:
                # Delete the failed job to allow initialization of the series
                # to be rescheduled.
                store.remove(distribution_job)
                store.remove(distribution_job.job)
            elif distribution_job.job.status == JobStatus.COMPLETED:
                raise InitializationCompleted(cls(distribution_job))
            else:
                raise InitializationPending(cls(distribution_job))
        # Schedule the initialization.
        metadata = {
            'parents': parents,
            'arches': arches,
            'packagesets': packagesets,
            'rebuild': rebuild,
            'overlays': overlays,
            'overlay_pockets': overlay_pockets,
            'overlay_components': overlay_components,
            }
        distribution_job = DistributionJob(
            child.distribution, child, cls.class_job_type, metadata)
        store.add(distribution_job)
        return cls(distribution_job)

    @classmethod
    def get(cls, distroseries):
        """See `IInitializeDistroSeriesJob`."""
        distribution_job = IStore(DistributionJob).find(
            DistributionJob, DistributionJob.job_id == Job.id,
            DistributionJob.job_type == cls.class_job_type,
            DistributionJob.distroseries_id == distroseries.id).one()
        return None if distribution_job is None else cls(distribution_job)

    @property
    def parents(self):
        return tuple(self.metadata['parents'])

    @property
    def overlays(self):
        if self.metadata['overlays'] is None:
            return ()
        else:
            return tuple(self.metadata['overlays'])

    @property
    def overlay_pockets(self):
        if self.metadata['overlay_pockets'] is None:
            return ()
        else:
            return tuple(self.metadata['overlay_pockets'])

    @property
    def overlay_components(self):
        if self.metadata['overlay_components'] is None:
            return ()
        else:
            return tuple(self.metadata['overlay_components'])

    @property
    def arches(self):
        if self.metadata['arches'] is None:
            return ()
        else:
            return tuple(self.metadata['arches'])

    @property
    def packagesets(self):
        if self.metadata['packagesets'] is None:
            return ()
        else:
            return tuple(self.metadata['packagesets'])

    @property
    def rebuild(self):
        return self.metadata['rebuild']

    def run(self):
        """See `IRunnableJob`."""
        ids = InitializeDistroSeries(
            self.distroseries, self.parents, self.arches,
            self.packagesets, self.rebuild, self.overlays,
            self.overlay_pockets, self.overlay_components)
        ids.check()
        ids.initialize()

    def getOopsVars(self):
        """See `IRunnableJob`."""
        vars = super(InitializeDistroSeriesJob, self).getOopsVars()
        vars.append(('parent_distroseries_ids', self.metadata.get("parents")))
        return vars
