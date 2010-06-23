from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IStoreSelector, MAIN_STORE)

from lp.registry.interfaces.distroseries import IDistroSeriesSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.job.model.job import Job
from lp.soyuz.adapters.packagelocation import PackageLocation
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.soyuz.interfaces.archivejob import (
    ArchiveJobType, ICopyArchiveJob, ICopyArchiveJobSource)
from lp.soyuz.interfaces.packagecloner import IPackageCloner
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.model.archivejob import ArchiveJob, ArchiveJobDerived


class CopyArchiveJob(ArchiveJobDerived):

    implements(ICopyArchiveJob)

    class_job_type = ArchiveJobType.COPY_ARCHIVE
    classProvides(ICopyArchiveJobSource)

    @classmethod
    def create(cls, target_archive, source_archive_id,
               source_series_id, source_pocket_value, target_series_id,
               target_pocket_value, target_component_id, source_user_id=None):
        """See `ICopyArchiveJobSource`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        job_for_archive = store.find(
            ArchiveJob,
            ArchiveJob.archive == target_archive,
            ArchiveJob.job_type == cls.class_job_type,
            ArchiveJob.job == Job.id,
            Job.id.is_in(Job.ready_jobs)
            ).any()

        if job_for_archive is not None:
            return cls(job_for_archive)
        else:
            metadata = {
                'source_archive_id': source_archive_id,
                'source_distroseries_id': source_series_id,
                'source_pocket_value': source_pocket_value,
                'target_distroseries_id': target_series_id,
                'target_pocket_value': target_pocket_value,
                'target_component_id': target_component_id,
            }
            if source_user_id is not None:
                metadata['source_user_id'] = source_user_id
            return super(CopyArchiveJob, cls).create(target_archive, metadata)

    def getOopsVars(self):
        """See `ArchiveJobDerived`."""
        vars = ArchiveJobDerived.getOopsVars(self)
        vars.extend([
            ('source_archive_id', self.metadata['source_archive_id']),
            ('source_distroseries_id',
                self.metadata['source_distroseries_id']),
            ('target_distroseries_id',
                self.metadata['target_distroseries_id']),
            ('source_pocket_value', self.metadata['source_pocket_value']),
            ('target_pocket_value', self.metadata['target_pocket_value']),
            ('target_component_id', self.metadata['target_component_id']),
            ])
        if 'source_user_id' in self.metadata:
           vars.extend([
                ('source_user_id', self.metadata['source_user_id']),
                ])
        return vars

    def getSourceLocation(self):
        """Get the PackageLocation for the source."""
        # TODO: handle things going bye-bye before we get here.
        source_archive_id = self.metadata['source_archive_id']
        source_archive = getUtility(IArchiveSet).get(source_archive_id)
        source_distroseries_id = self.metadata['source_distroseries_id']
        source_distroseries = getUtility(IDistroSeriesSet).get(
            source_distroseries_id)
        source_distribution = source_distroseries.distribution
        source_pocket_value = self.metadata['source_pocket_value']
        source_pocket = PackagePublishingPocket.items[source_pocket_value]
        source_location = PackageLocation(
            source_archive, source_distribution, source_distroseries,
            source_pocket)
        return source_location

    def getTargetLocation(self):
        """Get the PackageLocation for the target."""
        # TODO: handle things going bye-bye before we get here.
        target_distroseries_id = self.metadata['target_distroseries_id']
        target_distroseries = getUtility(IDistroSeriesSet).get(
            target_distroseries_id)
        target_distribution = target_distroseries.distribution
        target_pocket_value = self.metadata['target_pocket_value']
        target_pocket = PackagePublishingPocket.items[target_pocket_value]
        target_location = PackageLocation(
            self.archive, target_distribution, target_distroseries,
            target_pocket)
        target_component_id = self.metadata['target_component_id']
        target_component = getUtility(IComponentSet).get(
            target_component_id)
        return target_location

    def run(self):
        """See `IRunnableJob`."""
        source_location = self.getSourceLocation()
        target_location = self.getTargetLocation()
        package_cloner = getUtility(IPackageCloner)
        package_cloner.clonePackages(source_location, target_location)
