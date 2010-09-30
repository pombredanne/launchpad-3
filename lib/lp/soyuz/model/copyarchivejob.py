# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = object

from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )

from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.registry.interfaces.distroseries import IDistroSeriesSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.job.model.job import Job
from lp.soyuz.adapters.packagelocation import PackageLocation
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.soyuz.enums import ArchiveJobType
from lp.soyuz.interfaces.archivejob import (
    ICopyArchiveJob,
    ICopyArchiveJobSource,
    )
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.packagecloner import IPackageCloner
from lp.soyuz.interfaces.packageset import IPackagesetSet
from lp.soyuz.interfaces.processor import IProcessorFamilySet
from lp.soyuz.model.archivejob import (
    ArchiveJob,
    ArchiveJobDerived,
    )


class CopyArchiveJob(ArchiveJobDerived):

    implements(ICopyArchiveJob)

    class_job_type = ArchiveJobType.COPY_ARCHIVE
    classProvides(ICopyArchiveJobSource)

    @classmethod
    def create(cls, target_archive, source_archive,
               source_series, source_pocket, target_series, target_pocket,
               target_component=None, proc_families=None, packagesets=None,
               merge=False):
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
            raise ValueError(
                "CopyArchiveJob already in progress for %s" % target_archive)
        else:
            if proc_families is None:
                proc_families = []
            if len(proc_families) > 0 and merge:
                raise ValueError("Can't specify the architectures for merge.")
            proc_family_names = [p.name for p in proc_families]
            if packagesets is None:
                packagesets = []
            packageset_names = [p.name for p in packagesets]
            target_component_id = None
            if target_component is not None:
                target_component_id = target_component.id
            metadata = {
                'source_archive_id': source_archive.id,
                'source_distroseries_id': source_series.id,
                'source_pocket_value': source_pocket.value,
                'target_distroseries_id': target_series.id,
                'target_pocket_value': target_pocket.value,
                'target_component_id': target_component_id,
                'proc_family_names': proc_family_names,
                'packageset_names': packageset_names,
                'merge': merge,
            }
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
            ('merge', self.metadata['merge']),
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
        packageset_names = self.metadata['packageset_names']
        packagesets = [getUtility(IPackagesetSet).getByName(name)
                        for name in packageset_names]
        source_location = PackageLocation(
            source_archive, source_distribution, source_distroseries,
            source_pocket, packagesets=packagesets)
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
        if target_component_id is not None:
            target_location.component = getUtility(IComponentSet).get(
                target_component_id)
        return target_location

    def run(self):
        """See `IRunnableJob`."""
        source_location = self.getSourceLocation()
        target_location = self.getTargetLocation()
        proc_family_names = self.metadata['proc_family_names']
        proc_family_set = getUtility(IProcessorFamilySet)
        proc_families = [proc_family_set.getByName(p)
                         for p in proc_family_names]
        package_cloner = getUtility(IPackageCloner)
        if self.metadata['merge']:
            package_cloner.mergeCopy(source_location, target_location)
        else:
            package_cloner.clonePackages(
                source_location, target_location, proc_families=proc_families)
