from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IStoreSelector, MAIN_STORE)

from lp.services.job.model.job import Job
from lp.soyuz.interfaces.archivejob import (
    ArchiveJobType, ICopyArchiveJob, ICopyArchiveJobSource)
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
