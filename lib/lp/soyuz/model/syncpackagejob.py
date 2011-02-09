# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    "SyncPackageJob",
]

from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )

from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    IStore,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.soyuz.interfaces.distributionjob import (
    DistributionJobType,
    ISyncPackageJob,
    ISyncPackageJobSource,
    )
from lp.soyuz.model.distributionjob import (
    DistributionJob,
    DistributionJobDerived,
    )


class SyncPackageJob(DistributionJobDerived):
    """Job that copies a package between archives."""

    implements(ISyncPackageJob)

    class_job_type = DistributionJobType.SYNC_PACKAGE
    classProvides(ISyncPackageJobSource)

    @classmethod
    def create(cls, source_archive, target_archive, distroseries,
        pocket, source_package_name, source_package_version,
        include_binaries):
        """See `ISyncPackageJobSource`."""
        metadata = {
            'source_archive_id': source_archive.id,
            'target_archive_id': target_archive.id,
            'pocket': pocket.value,
            'source_package_name': source_package_name,
            'source_package_version': source_package_version,
            'include_binaries': include_binaries,
            }
        job = DistributionJob(
            distroseries.distribution, distroseries, cls.class_job_type,
            metadata)
        IMasterStore(DistributionJob).add(job)
        return cls(job)

    @classmethod
    def getActiveJobs(cls, archive):
        """See `ISyncPackageJobSource`."""
        # TODO: JRV 20101104. This iterates manually over all active
        # SyncPackageJobs. This should usually be a short enough list,
        # but if it really becomes an issue target_archive should
        # be moved into a separate database field.
        jobs = IStore(DistributionJob).find(
            DistributionJob,
            DistributionJob.job_type == cls.class_job_type,
            DistributionJob.distribution == archive.distribution)
        jobs = [cls(job) for job in jobs]
        return (job for job in jobs if job.target_archive == archive)

    @property
    def source_archive(self):
        return getUtility(IArchiveSet).get(self.metadata['source_archive_id'])

    @property
    def target_archive(self):
        return getUtility(IArchiveSet).get(self.metadata['target_archive_id'])

    @property
    def pocket(self):
        return PackagePublishingPocket.items[self.metadata['pocket']]

    @property
    def include_binaries(self):
        return self.metadata['include_binaries']

    @property
    def source_package_name(self):
        return self.metadata['source_package_name']

    @property
    def source_package_version(self):
        return self.metadata['source_package_version']

    def run(self):
        """See `IRunnableJob`."""
        self.target_archive.syncSource(
            self.source_package_name, self.source_package_version,
            self.source_archive, to_pocket=str(self.pocket),
            to_series=self.distroseries.name,
            include_binaries=self.include_binaries)
