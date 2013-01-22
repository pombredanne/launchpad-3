# Copyright 2009-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'BuildFarmJob',
    'BuildFarmJobDerived',
    'BuildFarmJobMixin',
    'BuildFarmJobOld',
    'BuildFarmJobOldDerived',
    ]

import datetime
import hashlib

from lazr.delegates import delegates
import pytz
from storm.expr import (
    Desc,
    LeftJoin,
    Or,
    )
from storm.locals import (
    Bool,
    DateTime,
    Int,
    Reference,
    Storm,
    )
from storm.store import Store
from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )
from zope.security.proxy import removeSecurityProxy

from lp.buildmaster.enums import (
    BuildFarmJobType,
    BuildStatus,
    )
from lp.buildmaster.interfaces.buildfarmjob import (
    IBuildFarmJob,
    IBuildFarmJobOld,
    IBuildFarmJobSet,
    IBuildFarmJobSource,
    )
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet
from lp.services.database.enumcol import DBEnum
from lp.services.database.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.services.database.lpstorm import (
    IMasterStore,
    IStore,
    )


class BuildFarmJobOldDerived:
    """Setup the delegation and provide some common implementation."""

    implements(IBuildFarmJobOld)

    processor = None
    virtualized = None

    @staticmethod
    def preloadBuildFarmJobs(jobs):
        """Preload the build farm jobs to which the given jobs will delegate.

        """
        pass

    @classmethod
    def getByJob(cls, job):
        """See `IBuildFarmJobOld`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(cls, cls.job == job).one()

    @classmethod
    def getByJobs(cls, jobs):
        """See `IBuildFarmJobOld`.
        """
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        job_ids = [job.id for job in jobs]
        return store.find(
            cls, cls.job_id.is_in(job_ids))

    def score(self):
        """See `IBuildFarmJobOld`."""
        raise NotImplementedError

    def getLogFileName(self):
        """See `IBuildFarmJobOld`."""
        return 'buildlog.txt'

    def getName(self):
        """See `IBuildFarmJobOld`."""
        raise NotImplementedError

    def getTitle(self):
        """See `IBuildFarmJob`."""
        return self.build.title

    def generateSlaveBuildCookie(self):
        """See `IBuildFarmJobOld`."""
        buildqueue = getUtility(IBuildQueueSet).getByJob(self.job)

        if buildqueue.processor is None:
            processor = '*'
        else:
            processor = repr(buildqueue.processor.id)

        contents = ';'.join([
            repr(removeSecurityProxy(self.job).id),
            self.job.date_created.isoformat(),
            repr(buildqueue.id),
            buildqueue.job_type.name,
            processor,
            self.getName(),
            ])

        return hashlib.sha1(contents).hexdigest()

    def cleanUp(self):
        """See `IBuildFarmJob`.

        Classes that derive from BuildFarmJobOld need to clean up
        after themselves correctly.
        """
        Store.of(self).remove(self)

    @staticmethod
    def addCandidateSelectionCriteria(processor, virtualized):
        """See `IBuildFarmJobOld`."""
        return ('')

    @staticmethod
    def postprocessCandidate(job, logger):
        """See `IBuildFarmJobOld`."""
        return True

    def jobStarted(self):
        """See `IBuildFarmJobOld`."""
        # XXX wgrant: builder should be set here.
        self.build.updateStatus(BuildStatus.BUILDING)

    def jobReset(self):
        """See `IBuildFarmJob`."""
        self.build.updateStatus(BuildStatus.NEEDSBUILD)

    def jobAborted(self):
        """See `IBuildFarmJob`."""
        self.build.updateStatus(BuildStatus.NEEDSBUILD)

    def jobCancel(self):
        """See `IBuildFarmJob`."""
        self.build.updateStatus(BuildStatus.CANCELLED)


class BuildFarmJob(Storm):
    """A base implementation for `IBuildFarmJob` classes."""
    __storm_table__ = 'BuildFarmJob'

    implements(IBuildFarmJob)
    classProvides(IBuildFarmJobSource)

    id = Int(primary=True)

    processor_id = Int(name='processor', allow_none=True)
    processor = Reference(processor_id, 'Processor.id')

    virtualized = Bool()

    date_created = DateTime(
        name='date_created', allow_none=False, tzinfo=pytz.UTC)

    date_started = DateTime(
        name='date_started', allow_none=True, tzinfo=pytz.UTC)

    date_finished = DateTime(
        name='date_finished', allow_none=True, tzinfo=pytz.UTC)

    date_first_dispatched = DateTime(
        name='date_first_dispatched', allow_none=True, tzinfo=pytz.UTC)

    builder_id = Int(name='builder', allow_none=True)
    builder = Reference(builder_id, 'Builder.id')

    status = DBEnum(name='status', allow_none=False, enum=BuildStatus)

    log_id = Int(name='log', allow_none=True)
    log = Reference(log_id, 'LibraryFileAlias.id')

    job_type = DBEnum(
        name='job_type', allow_none=False, enum=BuildFarmJobType)

    failure_count = Int(name='failure_count', allow_none=False)

    dependencies = None

    def __init__(self, job_type, status=BuildStatus.NEEDSBUILD,
                 processor=None, virtualized=None, date_created=None):
        super(BuildFarmJob, self).__init__()
        self.job_type, self.status, self.processor, self.virtualized = (
            job_type,
            status,
            processor,
            virtualized,
            )
        if date_created is not None:
            self.date_created = date_created

    @classmethod
    def new(cls, job_type, status=BuildStatus.NEEDSBUILD, processor=None,
            virtualized=None, date_created=None):
        """See `IBuildFarmJobSource`."""
        build_farm_job = BuildFarmJob(
            job_type, status, processor, virtualized, date_created)

        store = IMasterStore(BuildFarmJob)
        store.add(build_farm_job)
        return build_farm_job


class BuildFarmJobMixin:

    @property
    def title(self):
        """See `IBuildFarmJob`."""
        return self.job_type.title

    @property
    def duration(self):
        """See `IBuildFarmJob`."""
        if self.date_started is None or self.date_finished is None:
            return None
        return self.date_finished - self.date_started

    def makeJob(self):
        """See `IBuildFarmJobOld`."""
        raise NotImplementedError

    @property
    def buildqueue_record(self):
        """See `IBuildFarmJob`."""
        return None

    @property
    def is_private(self):
        """See `IBuildFarmJob`.

        This base implementation assumes build farm jobs are public, but
        derived implementations can override as required.
        """
        return False

    @property
    def log_url(self):
        """See `IBuildFarmJob`.

        This base implementation of the property always returns None. Derived
        implementations need to override for their specific context.
        """
        return None

    @property
    def was_built(self):
        """See `IBuild`"""
        return self.status not in [BuildStatus.NEEDSBUILD,
                                   BuildStatus.BUILDING,
                                   BuildStatus.CANCELLED,
                                   BuildStatus.CANCELLING,
                                   BuildStatus.UPLOADING,
                                   BuildStatus.SUPERSEDED]

    def setLog(self, log):
        """See `IBuildFarmJob`."""
        assert self.log is None
        self.log = log

    def updateStatus(self, status, builder=None, slave_status=None,
                     date_started=None, date_finished=None):
        """See `IBuildFarmJob`."""
        self.status = status

        # If there's a builder provided, set it if we don't already have
        # one, or otherwise crash if it's different from the one we
        # expected.
        if builder is not None:
            if self.builder is None:
                self.builder = builder
            else:
                assert self.builder == builder

        # If we're starting to build, set date_started and
        # date_first_dispatched if required.
        if self.date_started is None and status == BuildStatus.BUILDING:
            self.date_started = date_started or datetime.datetime.now(pytz.UTC)
            if self.date_first_dispatched is None:
                self.date_first_dispatched = self.date_started

        # If we're in a final build state (or UPLOADING, which sort of
        # is), set date_finished if date_started is.
        if (self.date_started is not None and self.date_finished is None
            and status not in (
                BuildStatus.NEEDSBUILD, BuildStatus.BUILDING,
                BuildStatus.CANCELLING)):
            # XXX cprov 20060615 bug=120584: Currently buildduration includes
            # the scanner latency, it should really be asking the slave for
            # the duration spent building locally.
            self.date_finished = (
                date_finished or datetime.datetime.now(pytz.UTC))

    def gotFailure(self):
        """See `IBuildFarmJob`."""
        self.failure_count += 1


class BuildFarmJobDerived:
    implements(IBuildFarmJob)
    delegates(IBuildFarmJob, context='build_farm_job')


class BuildFarmJobSet:
    implements(IBuildFarmJobSet)

    def getBuildsForBuilder(self, builder_id, status=None, user=None):
        """See `IBuildFarmJobSet`."""
        # Imported here to avoid circular imports.
        from lp.buildmaster.model.packagebuild import PackageBuild
        from lp.soyuz.model.archive import (
            Archive, get_archive_privacy_filter)

        clauses = [
            BuildFarmJob.builder == builder_id,
            Or(PackageBuild.id == None, get_archive_privacy_filter(user))]
        if status is not None:
            clauses.append(BuildFarmJob.status == status)

        # We need to ensure that we don't include any private builds.
        # Currently only package builds can be private (via their
        # related archive), but not all build farm jobs will have a
        # related package build - hence the left join.
        origin = [
            BuildFarmJob,
            LeftJoin(
                PackageBuild,
                PackageBuild.build_farm_job == BuildFarmJob.id),
            LeftJoin(Archive, Archive.id == PackageBuild.archive_id),
            ]

        return IStore(BuildFarmJob).using(*origin).find(
            BuildFarmJob, *clauses).order_by(
                Desc(BuildFarmJob.date_finished), BuildFarmJob.id)
