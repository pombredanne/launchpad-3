# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snap build jobs."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'SnapBuildJob',
    'SnapBuildJobType',
    'SnapStoreUploadJob',
    ]

from datetime import timedelta

from lazr.delegates import delegate_to
from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )
from storm.locals import (
    Int,
    JSON,
    Reference,
    )
import transaction
from zope.component import getUtility
from zope.interface import (
    implementer,
    provider,
    )

from lp.app.errors import NotFoundError
from lp.services.config import config
from lp.services.database.enumcol import EnumCol
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.services.database.stormbase import StormBase
from lp.services.job.model.job import (
    EnumeratedSubclass,
    Job,
    )
from lp.services.job.runner import BaseRunnableJob
from lp.snappy.interfaces.snapbuildjob import (
    ISnapBuildJob,
    ISnapStoreUploadJob,
    ISnapStoreUploadJobSource,
    )
from lp.snappy.interfaces.snapstoreclient import (
    BadReleaseResponse,
    BadScanStatusResponse,
    BadUploadResponse,
    ISnapStoreClient,
    ReleaseFailedResponse,
    ScanFailedResponse,
    UnauthorizedUploadResponse,
    UploadNotScannedYetResponse,
    )
from lp.snappy.mail.snapbuild import SnapBuildMailer


class SnapBuildJobType(DBEnumeratedType):
    """Values that `ISnapBuildJob.job_type` can take."""

    STORE_UPLOAD = DBItem(0, """
        Store upload

        This job uploads a snap build to the store.
        """)


@implementer(ISnapBuildJob)
class SnapBuildJob(StormBase):
    """See `ISnapBuildJob`."""

    __storm_table__ = 'SnapBuildJob'

    job_id = Int(name='job', primary=True, allow_none=False)
    job = Reference(job_id, 'Job.id')

    snapbuild_id = Int(name='snapbuild', allow_none=False)
    snapbuild = Reference(snapbuild_id, 'SnapBuild.id')

    job_type = EnumCol(enum=SnapBuildJobType, notNull=True)

    metadata = JSON('json_data', allow_none=False)

    def __init__(self, snapbuild, job_type, metadata, **job_args):
        """Constructor.

        Extra keyword arguments are used to construct the underlying Job
        object.

        :param snapbuild: The `ISnapBuild` this job relates to.
        :param job_type: The `SnapBuildJobType` of this job.
        :param metadata: The type-specific variables, as a JSON-compatible
            dict.
        """
        super(SnapBuildJob, self).__init__()
        self.job = Job(**job_args)
        self.snapbuild = snapbuild
        self.job_type = job_type
        self.metadata = metadata

    def makeDerived(self):
        return SnapBuildJobDerived.makeSubclass(self)


@delegate_to(ISnapBuildJob)
class SnapBuildJobDerived(BaseRunnableJob):

    __metaclass__ = EnumeratedSubclass

    def __init__(self, snap_build_job):
        self.context = snap_build_job

    def __repr__(self):
        """An informative representation of the job."""
        return "<%s for %s>" % (self.__class__.__name__, self.snapbuild.title)

    @classmethod
    def get(cls, job_id):
        """Get a job by id.

        :return: The `SnapBuildJob` with the specified id, as the current
            `SnapBuildJobDerived` subclass.
        :raises: `NotFoundError` if there is no job with the specified id,
            or its `job_type` does not match the desired subclass.
        """
        snap_build_job = IStore(SnapBuildJob).get(SnapBuildJob, job_id)
        if snap_build_job.job_type != cls.class_job_type:
            raise NotFoundError(
                "No object found with id %d and type %s" %
                (job_id, cls.class_job_type.title))
        return cls(snap_build_job)

    @classmethod
    def iterReady(cls):
        """See `IJobSource`."""
        jobs = IMasterStore(SnapBuildJob).find(
            SnapBuildJob,
            SnapBuildJob.job_type == cls.class_job_type,
            SnapBuildJob.job == Job.id,
            Job.id.is_in(Job.ready_jobs))
        return (cls(job) for job in jobs)

    def getOopsVars(self):
        """See `IRunnableJob`."""
        oops_vars = super(SnapBuildJobDerived, self).getOopsVars()
        oops_vars.extend([
            ('job_id', self.context.job.id),
            ('job_type', self.context.job_type.title),
            ('snapbuild_id', self.context.snapbuild.id),
            ('snap_owner_name', self.context.snapbuild.snap.owner.name),
            ('snap_name', self.context.snapbuild.snap.name),
            ])
        return oops_vars


class ManualReview(Exception):
    pass


@implementer(ISnapStoreUploadJob)
@provider(ISnapStoreUploadJobSource)
class SnapStoreUploadJob(SnapBuildJobDerived):
    """A Job that uploads a snap build to the store."""

    class_job_type = SnapBuildJobType.STORE_UPLOAD

    user_error_types = (
        UnauthorizedUploadResponse,
        ScanFailedResponse,
        ManualReview,
        ReleaseFailedResponse,
        )

    # XXX cjwatson 2016-05-04: identify transient upload failures and retry
    retry_error_types = (UploadNotScannedYetResponse,)
    retry_delay = timedelta(minutes=1)
    max_retries = 20

    config = config.ISnapStoreUploadJobSource

    @classmethod
    def create(cls, snapbuild):
        """See `ISnapStoreUploadJobSource`."""
        snap_build_job = SnapBuildJob(snapbuild, cls.class_job_type, {})
        job = cls(snap_build_job)
        job.celeryRunOnCommit()
        return job

    @property
    def error_message(self):
        """See `ISnapStoreUploadJob`."""
        return self.metadata.get("error_message")

    @error_message.setter
    def error_message(self, message):
        """See `ISnapStoreUploadJob`."""
        self.metadata["error_message"] = message

    @property
    def store_url(self):
        """See `ISnapStoreUploadJob`."""
        return self.metadata.get("store_url")

    @store_url.setter
    def store_url(self, url):
        """See `ISnapStoreUploadJob`."""
        self.metadata["store_url"] = url

    def run(self):
        """See `IRunnableJob`."""
        client = getUtility(ISnapStoreClient)
        try:
            if "status_url" not in self.metadata:
                self.metadata["status_url"] = client.upload(self.snapbuild)
            if self.store_url is None:
                self.store_url, self.metadata["store_revision"] = (
                    client.checkStatus(self.metadata["status_url"]))
            if self.snapbuild.snap.store_channels:
                if self.metadata["store_revision"] is None:
                    raise ManualReview(
                        "Package held for manual review on the store; "
                        "cannot release it automatically.")
                client.release(self.snapbuild, self.metadata["store_revision"])
            self.error_message = None
        except self.retry_error_types:
            raise
        except Exception as e:
            self.error_message = str(e)
            if isinstance(e, UnauthorizedUploadResponse):
                mailer = SnapBuildMailer.forUnauthorizedUpload(self.snapbuild)
                mailer.sendAll()
            elif isinstance(e, BadUploadResponse):
                mailer = SnapBuildMailer.forUploadFailure(self.snapbuild)
                mailer.sendAll()
            elif isinstance(e, (BadScanStatusResponse, ScanFailedResponse)):
                mailer = SnapBuildMailer.forUploadScanFailure(self.snapbuild)
                mailer.sendAll()
            elif isinstance(e, ManualReview):
                mailer = SnapBuildMailer.forManualReview(self.snapbuild)
                mailer.sendAll()
            elif isinstance(e, (BadReleaseResponse, ReleaseFailedResponse)):
                mailer = SnapBuildMailer.forReleaseFailure(self.snapbuild)
                mailer.sendAll()
            # The normal job infrastructure will abort the transaction, but
            # we want to commit instead: the only database changes we make
            # are to this job's metadata and should be preserved.
            transaction.commit()
            raise
