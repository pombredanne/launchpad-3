# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'BuildFarmJob',
    'BuildFarmJobDerived',
    ]


from lazr.delegates import delegates

import hashlib
import pytz

from storm.locals import Bool, DateTime, Int, Reference, Storm

from zope.component import getUtility
from zope.interface import classProvides, implements
from zope.security.proxy import removeSecurityProxy

from canonical.database.enumcol import DBEnum
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IStoreSelector, MAIN_STORE)

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.interfaces.buildfarmjob import (
    BuildFarmJobType, IBuildFarmJob, IBuildFarmJobDerived,
    IBuildFarmJobSource)
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet


class BuildFarmJob(Storm):
    """A base implementation for `IBuildFarmJob` classes."""

    __storm_table__ = 'BuildFarmJob'

    implements(IBuildFarmJob)
    classProvides(IBuildFarmJobSource)

    id = Int(primary=True)

    processor_id = Int(name='processor', allow_none=True)
    processor = Reference(processor_id, 'Processor.id')

    virtualived = Bool()

    date_created = DateTime(
        name='date_created', allow_none=False, tzinfo=pytz.UTC)

    date_started = DateTime(
        name='date_started', allow_none=True, tzinfo=pytz.UTC)

    date_finished = DateTime(
        name='date_finished', allow_none=False, tzinfo=pytz.UTC)

    builder_id = Int(name='builder', allow_none=True)
    builder = Reference(builder_id, 'Builder.id')

    status = DBEnum(name='status', allow_none=False, enum=BuildStatus)

    log_id = Int(name='log', allow_none=True)
    log = Reference(log_id, 'LibraryFileAlias.id')

    job_type = DBEnum(
        name='job_type', allow_none=False, enum=BuildFarmJobType)

    @classmethod
    def new(cls, job_type, status=None, processor=None,
            virtualized=None):
        """See `IBuildFarmJobSource`."""
        build_farm_job = BuildFarmJob()
        build_farm_job.job_type = job_type

        if status is None:
            status = BuildStatus.PENDING
        build_farm_job.status = status

        build_farm_job.processor = processor
        build_farm_job.virtualized = virtualized

        store = IMasterStore(BuildFarmJob)
        store.add(build_farm_job)
        return build_farm_job

    def score(self):
        """See `IBuildFarmJob`."""
        raise NotImplementedError

    def getLogFileName(self):
        """See `IBuildFarmJob`."""
        return 'buildlog.txt'

    def getName(self):
        """See `IBuildFarmJob`."""
        raise NotImplementedError

    def getTitle(self):
        """See `IBuildFarmJob`."""
        raise NotImplementedError

    def jobStarted(self):
        """See `IBuildFarmJob`."""
        pass

    def jobReset(self):
        """See `IBuildFarmJob`."""
        pass

    def jobAborted(self):
        """See `IBuildFarmJob`."""
        pass

    @property
    def processor(self):
        """See `IBuildFarmJob`."""
        return None

    @property
    def virtualized(self):
        """See `IBuildFarmJob`."""
        return None

    @staticmethod
    def addCandidateSelectionCriteria(processor, virtualized):
        """See `IBuildFarmJob`."""
        return ('')

    @staticmethod
    def postprocessCandidate(job, logger):
        """See `IBuildFarmJob`."""
        return True


class BuildFarmJobDerived:
    """See `IBuildFarmJobDerived`."""
    implements(IBuildFarmJobDerived)
    delegates(IBuildFarmJob, context='_build_farm_job')

    def __init__(self, *args, **kwargs):
        """Ensure the instance to which we delegate is set on creation."""
        self._set_build_farm_job()
        super(BuildFarmJobDerived, self).__init__(*args, **kwargs)

    def __storm_loaded__(self):
        """Set the attribute for our IBuildFarmJob delegation.

        This is needed here as __init__() is not called when a storm object
        is loaded from the database.
        """
        self._set_build_farm_job()

    def _set_build_farm_job(self):
        """Set the build farm job to which we will delegate.

        Sub-classes can override as required.
        """
        self._build_farm_job = BuildFarmJob()

    @classmethod
    def getByJob(cls, job):
        """See `IBuildFarmJobDerived`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(cls, cls.job == job).one()

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
