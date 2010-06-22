from zope.interface import classProvides, implements

from lp.soyuz.interfaces.archivejob import (
    ArchiveJobType, ICopyArchiveJob, ICopyArchiveJobSource)
from lp.soyuz.model.archivejob import ArchiveJobDerived


class CopyArchiveJob(ArchiveJobDerived):

    implements(ICopyArchiveJob)

    class_job_type = ArchiveJobType.COPY_ARCHIVE
    classProvides(ICopyArchiveJobSource)

    @classmethod
    def create(cls, archive):
        """See `ICopyArchiveJobSource`."""
        return super(CopyArchiveJob, cls).create(archive)
