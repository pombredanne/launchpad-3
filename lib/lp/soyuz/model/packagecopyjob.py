# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    "PackageCopyJob",
]

from functools import partial

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
from lp.registry.interfaces.sourcepackagename import ISourcePackageNameSet
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.soyuz.interfaces.distributionjob import (
    DistributionJobType,
    IPackageCopyJob,
    IPackageCopyJobSource,
    )
from lp.soyuz.model.distributionjob import (
    DistributionJob,
    DistributionJobDerived,
    )
from lp.soyuz.scripts.packagecopier import do_copy


class PackageCopyJob(DistributionJobDerived):
    """Job that copies a package between archives."""

    implements(IPackageCopyJob)

    class_job_type = DistributionJobType.COPY_PACKAGE
    classProvides(IPackageCopyJobSource)

    @classmethod
    def create(cls, source_packages, source_archive,
               target_archive, target_distroseries, target_pocket,
               include_binaries=False):
        """See `IPackageCopyJobSource`."""
        metadata = {
            'source_packages': source_packages,
            'source_archive_id': source_archive.id,
            'target_archive_id': target_archive.id,
            'target_pocket': target_pocket.value,
            'include_binaries': include_binaries,
            }
        job = DistributionJob(
            target_distroseries.distribution, target_distroseries,
            cls.class_job_type, metadata)
        IMasterStore(DistributionJob).add(job)
        return cls(job)

    @classmethod
    def getActiveJobs(cls, archive):
        """See `IPackageCopyJobSource`."""
        # TODO: JRV 20101104. This iterates manually over all active
        # PackageCopyJobs. This should usually be a short enough list,
        # but if it really becomes an issue target_archive should
        # be moved into a separate database field.
        jobs = IStore(DistributionJob).find(
            DistributionJob,
            DistributionJob.job_type == cls.class_job_type,
            DistributionJob.distribution == archive.distribution)
        jobs = [cls(job) for job in jobs]
        return (job for job in jobs if job.target_archive == archive)

    @property
    def source_packages(self):
        return [
            (name, version) for (name, version) in
            self.metadata['source_packages']]

    # TODO Add source_archive_id and target_archive_id properties.

    @property
    def source_archive(self):
        return getUtility(IArchiveSet).get(self.metadata['source_archive_id'])

    @property
    def target_archive(self):
        return getUtility(IArchiveSet).get(self.metadata['target_archive_id'])

    # TODO Add target_distroseries property which just returns
    # self.distroseries.

    @property
    def target_pocket(self):
        return PackagePublishingPocket.items[self.metadata['target_pocket']]

    @property
    def include_binaries(self):
        return self.metadata['include_binaries']

    def run(self):
        """See `IRunnableJob`."""
        # if target_archive.is_ppa:
        #     if self.target_pocket != PackagePublishingPocket.RELEASE:
        #         raise CannotCopy(
        #             "Destination pocket must be 'release' for a PPA.")

        get_published_sources = partial(
            self.source_archive.getPublishedSources, exact_match=True)

        source_packages = frozenset(
            get_published_sources(
                name=source_name, version=source_version).first()
            for source_name, source_version in self.source_packages)

        # Check that all packages were found.
        if None in source_packages:
            # Look up each name until one of them is not found, at which point
            # ISourcePackageNameSet will raise a useful error.
            for source_name, source_version in self.source_packages:
                getUtility(ISourcePackageNameSet)[source_name]

        do_copy(
            sources=source_packages, archive=self.target_archive,
            series=self.distroseries, pocket=self.target_pocket,
            include_binaries=self.include_binaries)
