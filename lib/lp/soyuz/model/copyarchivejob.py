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
    def create(cls, target_archive):
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
            return super(CopyArchiveJob, cls).create(target_archive)
