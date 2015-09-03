# Copyright 2010-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import json
import logging
import StringIO

from lazr.delegates import delegate_to
from storm.expr import And
from storm.locals import (
    Int,
    Reference,
    Unicode,
    )
from zope.component import getUtility
from zope.interface import (
    implementer,
    provider,
    )

from lp.services.config import config
from lp.services.database.enumcol import EnumCol
from lp.services.database.interfaces import IMasterStore
from lp.services.database.stormbase import StormBase
from lp.services.job.model.job import (
    EnumeratedSubclass,
    Job,
    )
from lp.services.job.runner import BaseRunnableJob
from lp.soyuz.enums import (
    ArchiveJobType,
    PackageUploadStatus,
    )
from lp.soyuz.interfaces.archivejob import (
    IArchiveJob,
    IArchiveJobSource,
    IPackageUploadNotificationJob,
    IPackageUploadNotificationJobSource,
    )
from lp.soyuz.interfaces.queue import IPackageUploadSet
from lp.soyuz.model.archive import Archive


@implementer(IArchiveJob)
class ArchiveJob(StormBase):
    """Base class for jobs related to Archives."""

    __storm_table__ = 'ArchiveJob'

    id = Int(primary=True)

    job_id = Int(name='job')
    job = Reference(job_id, Job.id)

    archive_id = Int(name='archive')
    archive = Reference(archive_id, Archive.id)

    job_type = EnumCol(enum=ArchiveJobType, notNull=True)

    _json_data = Unicode('json_data')

    @property
    def metadata(self):
        return json.loads(self._json_data)

    def __init__(self, archive, job_type, metadata):
        """Create an ArchiveJob.

        :param archive: the `IArchive` this job relates to.
        :param job_type: the `ArchiveJobType` of this job.
        :param metadata: the type-specific variables, as a json-compatible
            dict.
        """
        super(ArchiveJob, self).__init__()
        self.job = Job()
        self.archive = archive
        self.job_type = job_type
        self._json_data = unicode(json.dumps(metadata, ensure_ascii=False))


@delegate_to(IArchiveJob)
@provider(IArchiveJobSource)
class ArchiveJobDerived(BaseRunnableJob):
    """Intermediate class for deriving from ArchiveJob."""

    __metaclass__ = EnumeratedSubclass

    def __init__(self, job):
        self.context = job

    @classmethod
    def create(cls, archive, metadata=None):
        """See `IArchiveJob`."""
        if metadata is None:
            metadata = {}
        job = ArchiveJob(archive, cls.class_job_type, metadata)
        derived = cls(job)
        derived.celeryRunOnCommit()
        return derived

    @classmethod
    def iterReady(cls):
        """Iterate through all ready ArchiveJobs."""
        store = IMasterStore(ArchiveJob)
        jobs = store.find(
            ArchiveJob,
            And(ArchiveJob.job_type == cls.class_job_type,
                ArchiveJob.job_id.is_in(Job.ready_jobs)))
        return (cls(job) for job in jobs)

    def getOopsVars(self):
        """See `IRunnableJob`."""
        vars = super(ArchiveJobDerived, self).getOopsVars()
        vars.extend([
            ('archive_id', self.context.archive.id),
            ('archive_job_id', self.context.id),
            ('archive_job_type', self.context.job_type.title),
            ])
        return vars


@implementer(IPackageUploadNotificationJob)
@provider(IPackageUploadNotificationJobSource)
class PackageUploadNotificationJob(ArchiveJobDerived):

    class_job_type = ArchiveJobType.PACKAGE_UPLOAD_NOTIFICATION

    config = config.IPackageUploadNotificationJobSource

    @classmethod
    def create(cls, packageupload, summary_text=None):
        """See `IPackageUploadNotificationJobSource`."""
        metadata = {
            'packageupload_id': packageupload.id,
            'packageupload_status': packageupload.status.title,
            'summary_text': summary_text,
            }
        return super(PackageUploadNotificationJob, cls).create(
            packageupload.archive, metadata)

    def getOopsVars(self):
        """See `ArchiveJobDerived`."""
        vars = super(PackageUploadNotificationJob, self).getOopsVars()
        vars.extend([
            ('packageupload_id', self.metadata['packageupload_id']),
            ('packageupload_status', self.metadata['packageupload_status']),
            ('summary_text', self.metadata['summary_text']),
            ])
        return vars

    @property
    def packageupload(self):
        return getUtility(IPackageUploadSet).get(
            self.metadata['packageupload_id'])

    @property
    def packageupload_status(self):
        return PackageUploadStatus.getTermByToken(
            self.metadata['packageupload_status']).value

    @property
    def summary_text(self):
        return self.metadata['summary_text']

    def run(self):
        """See `IRunnableJob`."""
        packageupload = self.packageupload
        if packageupload.changesfile is None:
            changes_file_object = None
        else:
            changes_file_object = StringIO.StringIO(
                packageupload.changesfile.read())
        logger = logging.getLogger()
        packageupload.notify(
            status=self.packageupload_status, summary_text=self.summary_text,
            changes_file_object=changes_file_object, logger=logger)
