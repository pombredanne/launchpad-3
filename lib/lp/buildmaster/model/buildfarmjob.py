# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'BuildFarmJob',
    'BuildFarmJobDerived',
    'BuildFarmJobOld',
    'BuildFarmJobOldDerived',
    ]


from lazr.delegates import delegates

import hashlib
import pytz

from storm.locals import Bool, DateTime, Int, Reference, Storm

from zope.component import getUtility
from zope.interface import classProvides, implements
from zope.security.proxy import removeSecurityProxy

from canonical.database.constants import UTC_NOW
from canonical.database.enumcol import DBEnum
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IStoreSelector, MAIN_STORE)

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.interfaces.buildfarmjob import (
    BuildFarmJobType, IBuildFarmJob, IBuildFarmJobDerived,
    IBuildFarmJobOld, IBuildFarmJobSource)
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet


class BuildFarmJobOld:
    """See `IBuildFarmJobOld`."""
    implements(IBuildFarmJobOld)
    processor = None
    virtualized = None

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
        """See `IBuildFarmJobOld`."""
        raise NotImplementedError

    def makeJob(self):
        """See `IBuildFarmJobOld`."""
        raise NotImplementedError

    def jobStarted(self):
        """See `IBuildFarmJobOld`."""
        pass

    def jobReset(self):
        """See `IBuildFarmJobOld`."""
        pass

    def jobAborted(self):
        """See `IBuildFarmJobOld`."""
        pass


class BuildFarmJobOldDerived:
    delegates(IBuildFarmJobOld, context='build_farm_job')

    def __init__(self, *args, **kwargs):
        """Ensure the instance to which we delegate is set on creation."""
        self._set_build_farm_job()
        super(BuildFarmJobOldDerived, self).__init__(*args, **kwargs)

    def __storm_loaded__(self):
        """Set the attribute for our IBuildFarmJob delegation.

        This is needed here as __init__() is not called when a storm object
        is loaded from the database.
        """
        self._set_build_farm_job()

    def _set_build_farm_job(self):
        """Set the build farm job to which we will delegate.

        This is just a hook that can be used
        """
        raise NotImplementedError

    @classmethod
    def getByJob(cls, job):
        """See `IBuildFarmJobDerived`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(cls, cls.job == job).one()

    @staticmethod
    def addCandidateSelectionCriteria(processor, virtualized):
        """See `IBuildFarmJobDerived`."""
        return ('')

    @staticmethod
    def postprocessCandidate(job, logger):
        """See `IBuildFarmJobDerived`."""
        return True

    def generateSlaveBuildCookie(self):
        """See `IBuildFarmJobDerived`."""
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


class BuildFarmJob(BuildFarmJobOld, Storm):
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

    def __init__(self, job_type, status=BuildStatus.NEEDSBUILD,
                 processor=None, virtualized=None):
        self.job_type, self.status, self.process, self.virtualized = (
            job_type,
            status,
            processor,
            virtualized,
            )

    @classmethod
    def new(cls, job_type, status=BuildStatus.NEEDSBUILD, processor=None,
            virtualized=None):
        """See `IBuildFarmJobSource`."""
        build_farm_job = BuildFarmJob(
            job_type, status, processor, virtualized)

        store = IMasterStore(BuildFarmJob)
        store.add(build_farm_job)
        return build_farm_job

    @property
    def title(self):
        """See `IBuildFarmJob`."""
        return self.job_type.title

    def makeJob(self):
        """See `IBuildFarmJob`."""
        raise NotImplementedError

    def jobStarted(self):
        """See `IBuildFarmJob`."""
        self.status = BuildStatus.BUILDING
        # The build started, set the start time if not set already.
        self.date_started = UTC_NOW
        if self.date_first_dispatched is None:
            self.date_first_dispatched = UTC_NOW

    def jobReset(self):
        """See `IBuildFarmJob`."""
        self.status = BuildStatus.NEEDSBUILD
        self.date_started = None

    # The implementation of aborting a job is the same as resetting
    # a job.
    jobAborted = jobReset

    @staticmethod
    def addCandidateSelectionCriteria(processor, virtualized):
        """See `IBuildFarmJob`."""
        return ('')

    @staticmethod
    def postprocessCandidate(job, logger):
        """See `IBuildFarmJob`."""
        return True

    @property
    def buildqueue_record(self):
        """See `IBuildFarmJob`."""
        # Need to update the db schema for buildpackagejob before
        # this can be implemented here.
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


class BuildFarmJobDerived:
    """See `IBuildFarmJobDerived`."""
    implements(IBuildFarmJobDerived)
    delegates(IBuildFarmJob, context='build_farm_job')

