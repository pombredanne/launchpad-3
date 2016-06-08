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
    ISnapStoreClient,
    UnauthorizedUploadResponse,
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


@implementer(ISnapStoreUploadJob)
@provider(ISnapStoreUploadJobSource)
class SnapStoreUploadJob(SnapBuildJobDerived):
    """A Job that uploads a snap build to the store."""

    class_job_type = SnapBuildJobType.STORE_UPLOAD

    # XXX cjwatson 2016-05-04: identify transient upload failures and retry

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

    def run(self):
        """See `IRunnableJob`."""
        try:
            getUtility(ISnapStoreClient).upload(self.snapbuild)
            self.error_message = None
        except Exception as e:
            # Abort work done so far, but make sure that we commit the error
            # message.
            transaction.abort()
            self.error_message = str(e)
            if isinstance(e, UnauthorizedUploadResponse):
                mailer = SnapBuildMailer.forUnauthorizedUpload(self.snapbuild)
                mailer.sendAll()
            transaction.commit()
            raise
