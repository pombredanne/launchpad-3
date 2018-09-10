# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snap package jobs."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'SnapJob',
    'SnapJobType',
    'SnapRequestBuildsJob',
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
from storm.store import EmptyResultSet
import transaction
from zope.component import getUtility
from zope.interface import (
    implementer,
    provider,
    )

from lp.app.errors import NotFoundError
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
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
from lp.services.mail.sendmail import format_address_for_person
from lp.services.propertycache import cachedproperty
from lp.services.scripts import log
from lp.snappy.interfaces.snap import (
    CannotFetchSnapcraftYaml,
    CannotParseSnapcraftYaml,
    )
from lp.snappy.interfaces.snapjob import (
    ISnapJob,
    ISnapRequestBuildsJob,
    ISnapRequestBuildsJobSource,
    )
from lp.snappy.model.snapbuild import SnapBuild
from lp.soyuz.model.archive import Archive


class SnapJobType(DBEnumeratedType):
    """Values that `ISnapJob.job_type` can take."""

    REQUEST_BUILDS = DBItem(0, """
        Request builds

        This job requests builds of a snap package.
        """)


@implementer(ISnapJob)
class SnapJob(StormBase):
    """See `ISnapJob`."""

    __storm_table__ = 'SnapJob'

    job_id = Int(name='job', primary=True, allow_none=False)
    job = Reference(job_id, 'Job.id')

    snap_id = Int(name='snap', allow_none=False)
    snap = Reference(snap_id, 'Snap.id')

    job_type = EnumCol(enum=SnapJobType, notNull=True)

    metadata = JSON('json_data', allow_none=False)

    def __init__(self, snap, job_type, metadata, **job_args):
        """Constructor.

        Extra keyword arguments are used to construct the underlying Job
        object.

        :param snap: The `ISnap` this job relates to.
        :param job_type: The `SnapJobType` of this job.
        :param metadata: The type-specific variables, as a JSON-compatible
            dict.
        """
        super(SnapJob, self).__init__()
        self.job = Job(**job_args)
        self.snap = snap
        self.job_type = job_type
        self.metadata = metadata

    def makeDerived(self):
        return SnapJobDerived.makeSubclass(self)


@delegate_to(ISnapJob)
class SnapJobDerived(BaseRunnableJob):

    __metaclass__ = EnumeratedSubclass

    def __init__(self, snap_job):
        self.context = snap_job

    def __repr__(self):
        """An informative representation of the job."""
        return "<%s for ~%s/+snap/%s>" % (
            self.__class__.__name__, self.snap.owner.name, self.snap.name)

    @classmethod
    def get(cls, job_id):
        """Get a job by id.

        :return: The `SnapJob` with the specified id, as the current
            `SnapJobDerived` subclass.
        :raises: `NotFoundError` if there is no job with the specified id,
            or its `job_type` does not match the desired subclass.
        """
        snap_job = IStore(SnapJob).get(SnapJob, job_id)
        if snap_job.job_type != cls.class_job_type:
            raise NotFoundError(
                "No object found with id %d and type %s" %
                (job_id, cls.class_job_type.title))
        return cls(snap_job)

    @classmethod
    def iterReady(cls):
        """See `IJobSource`."""
        jobs = IMasterStore(SnapJob).find(
            SnapJob,
            SnapJob.job_type == cls.class_job_type,
            SnapJob.job == Job.id,
            Job.id.is_in(Job.ready_jobs))
        return (cls(job) for job in jobs)

    def getOopsVars(self):
        """See `IRunnableJob`."""
        oops_vars = super(SnapJobDerived, self).getOopsVars()
        oops_vars.extend([
            ("job_id", self.context.job.id),
            ("job_type", self.context.job_type.title),
            ("snap_owner_name", self.context.snap.owner.name),
            ("snap_name", self.context.snap.name),
            ])
        return oops_vars


@implementer(ISnapRequestBuildsJob)
@provider(ISnapRequestBuildsJobSource)
class SnapRequestBuildsJob(SnapJobDerived):
    """A Job that processes a request for builds of a snap package."""

    class_job_type = SnapJobType.REQUEST_BUILDS

    user_error_types = (CannotParseSnapcraftYaml, NotFoundError)
    retry_error_types = (CannotFetchSnapcraftYaml,)

    max_retries = 5

    config = config.ISnapRequestBuildsJobSource

    @classmethod
    def create(cls, snap, requester, archive, pocket, channels):
        """See `ISnapRequestBuildsJobSource`."""
        metadata = {
            "requester": requester.id,
            "archive": archive.id,
            "pocket": pocket.value,
            "channels": channels,
            }
        snap_job = SnapJob(snap, cls.class_job_type, metadata)
        job = cls(snap_job)
        job.celeryRunOnCommit()
        return job

    @classmethod
    def getBySnapAndID(cls, snap, job_id):
        """See `ISnapRequestBuildsJobSource`."""
        snap_job = IStore(SnapJob).find(
            SnapJob,
            SnapJob.job_id == job_id,
            SnapJob.snap == snap,
            SnapJob.job_type == cls.class_job_type).one()
        if snap_job is None:
            raise NotFoundError(
                "No REQUEST_BUILDS job with ID %d found for %r" %
                (job_id, snap))
        return cls(snap_job)

    def getOperationDescription(self):
        return "requesting builds of %s" % self.snap.name

    def getErrorRecipients(self):
        if self.requester is None or self.requester.preferredemail is None:
            return []
        return [format_address_for_person(self.requester)]

    @cachedproperty
    def requester(self):
        """See `ISnapRequestBuildsJob`."""
        requester_id = self.metadata["requester"]
        return getUtility(IPersonSet).get(requester_id)

    @cachedproperty
    def archive(self):
        """See `ISnapRequestBuildsJob`."""
        archive_id = self.metadata["archive"]
        return IStore(Archive).find(Archive, Archive.id == archive_id).one()

    @property
    def pocket(self):
        """See `ISnapRequestBuildsJob`."""
        name = self.metadata["pocket"]
        return PackagePublishingPocket.items[name]

    @property
    def channels(self):
        """See `ISnapRequestBuildsJob`."""
        return self.metadata["channels"]

    @property
    def date_created(self):
        """See `ISnapRequestBuildsJob`."""
        return self.context.job.date_created

    @property
    def date_finished(self):
        """See `ISnapRequestBuildsJob`."""
        return self.context.job.date_finished

    @property
    def error_message(self):
        """See `ISnapRequestBuildsJob`."""
        return self.metadata.get("error_message")

    @error_message.setter
    def error_message(self, message):
        """See `ISnapRequestBuildsJob`."""
        self.metadata["error_message"] = message

    @property
    def build_request(self):
        """See `ISnapRequestBuildsJob`."""
        return self.snap.getBuildRequest(self.job.id)

    @property
    def builds(self):
        """See `ISnapRequestBuildsJob`."""
        build_ids = self.metadata.get("builds")
        if build_ids is None:
            return EmptyResultSet()
        else:
            return IStore(SnapBuild).find(
                SnapBuild, SnapBuild.id.is_in(build_ids))

    @builds.setter
    def builds(self, builds):
        """See `ISnapRequestBuildsJob`."""
        self.metadata["builds"] = [build.id for build in builds]

    def run(self):
        """See `IRunnableJob`."""
        requester = self.requester
        if requester is None:
            log.info(
                "Skipping %r because the requester has been deleted." % self)
            return
        archive = self.archive
        if archive is None:
            log.info(
                "Skipping %r because the archive has been deleted." % self)
            return
        try:
            self.builds = self.snap.requestBuildsFromJob(
                requester, archive, self.pocket, channels=self.channels,
                build_request=self.build_request, logger=log)
            self.error_message = None
        except self.retry_error_types:
            raise
        except Exception as e:
            self.error_message = str(e)
            # The normal job infrastructure will abort the transaction, but
            # we want to commit instead: the only database changes we make
            # are to this job's metadata and should be preserved.
            transaction.commit()
            raise
