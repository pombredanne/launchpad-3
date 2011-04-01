# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job class to request generation or update of `DistroSeriesDifference`s."""

__metaclass__ = type
__all__ = [
    'DistroSeriesDifferenceJob',
    ]

from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )

from canonical.launchpad.interfaces.lpstorm import IMasterStore
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifferenceSource,
    )
from lp.registry.model.distroseriesdifference import DistroSeriesDifference
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.services.features import getFeatureFlag
from lp.services.job.model.job import Job
from lp.soyuz.interfaces.distributionjob import (
    DistributionJobType,
    IDistroSeriesDifferenceJob,
    IDistroSeriesDifferenceJobSource,
    )
from lp.soyuz.model.distributionjob import (
    DistributionJob,
    DistributionJobDerived,
    )


FEATURE_FLAG_ENABLE_MODULE = u"soyuz.derived_series_jobs.enabled"


def make_metadata(sourcepackagename):
    """Return JSON metadata for a job on `sourcepackagename`."""
    return {'sourcepackagename': sourcepackagename.id}


def create_job(distroseries, sourcepackagename):
    """Create a `DistroSeriesDifferenceJob` for a given source package.

    :param distroseries: A `DistroSeries` that is assumed to be derived
        from another one.
    :param sourcepackagename: The `SourcePackageName` whose publication
        history has changed.
    """
    job = DistributionJob(
        distribution=distroseries.distribution, distroseries=distroseries,
        job_type=DistributionJobType.DISTROSERIESDIFFERENCE,
        metadata=make_metadata(sourcepackagename))
    IMasterStore(DistributionJob).add(job)
    return DistroSeriesDifferenceJob(job)


def find_waiting_jobs(distroseries, sourcepackagename):
    """Look for pending `DistroSeriesDifference` jobs on a package."""
    # Look for identical pending jobs.  This compares directly on
    # the metadata string.  It's fragile, but this is only an
    # optimization.  It's not actually disastrous to create
    # redundant jobs occasionally.
    json_metadata = DistributionJob.serializeMetadata(
        make_metadata(sourcepackagename))

    # Use master store because we don't like outdated information
    # here.
    store = IMasterStore(DistributionJob)

    return store.find(
        DistributionJob,
        DistributionJob.job_type ==
            DistributionJobType.DISTROSERIESDIFFERENCE,
        DistributionJob.distroseries == distroseries,
        DistributionJob._json_data == json_metadata,
        DistributionJob.job_id.is_in(Job.ready_jobs))


def may_require_job(distroseries, sourcepackagename):
    """Might publishing this package require a new job?

    Use this to determine whether to create a new
    `DistroSeriesDifferenceJob`.  The answer may possibly be
    conservatively wrong: the check is really only to save the job
    runner some unnecessary work, but we don't expect a bit of
    unnecessary work to be a big problem.
    """
    if distroseries is None:
        return False
    parent_series = distroseries.parent_series
    if parent_series is None:
        return False
    if parent_series.distribution == distroseries.distribution:
        # Differences within a distribution are not tracked.
        return False
    return find_waiting_jobs(distroseries, sourcepackagename).is_empty()


class DistroSeriesDifferenceJob(DistributionJobDerived):
    """A `Job` type for creating/updating `DistroSeriesDifference`s."""

    implements(IDistroSeriesDifferenceJob)
    classProvides(IDistroSeriesDifferenceJobSource)

    class_job_type = DistributionJobType.DISTROSERIESDIFFERENCE

    @classmethod
    def createForPackagePublication(cls, distroseries, sourcepackagename):
        """See `IDistroSeriesDifferenceJobSource`."""
        if not getFeatureFlag(FEATURE_FLAG_ENABLE_MODULE):
            return
        jobs = []
        children = list(distroseries.getDerivedSeries())
        for relative in children + [distroseries]:
            if may_require_job(relative, sourcepackagename):
                jobs.append(create_job(relative, sourcepackagename))
        return jobs

    @property
    def sourcepackagename(self):
        return SourcePackageName.get(self.metadata['sourcepackagename'])

    def run(self):
        """See `IRunnableJob`."""
        store = IMasterStore(DistroSeriesDifference)
        ds_diff = store.find(
            DistroSeriesDifference, 
            DistroSeriesDifference.derived_series == self.distroseries,
            DistroSeriesDifference.source_package_name == 
            self.sourcepackagename).one()
        if ds_diff is None:
            ds_diff = getUtility(IDistroSeriesDifferenceSource).new(
                self.distroseries, self.sourcepackagename)
        else:
            ds_diff.update()
