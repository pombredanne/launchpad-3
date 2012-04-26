# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""ORM object representing jobs."""

__metaclass__ = type
__all__ = [
    'EnumeratedSubclass',
    'InvalidTransition',
    'Job',
    'JobStatus',
    'UniversalJobSource',
    ]


from calendar import timegm
import datetime
import time

from lazr.jobrunner.jobrunner import LeaseHeld

import pytz
from sqlobject import (
    IntCol,
    StringCol,
    )
from storm.expr import (
    And,
    Or,
    Select,
    )
from storm.locals import (
    Int,
    Reference,
    )
from storm.zope.interfaces import IZStorm
import transaction
from zope.component import getUtility
from zope.interface import implements

from lp.services.config import config, dbconfig
from lp.services.database import bulk
from lp.services.database.constants import UTC_NOW
from lp.services.database.datetimecol import UtcDateTimeCol
from lp.services.database.enumcol import EnumCol
from lp.services.database.lpstorm import IStore
from lp.services.database.sqlbase import SQLBase
from lp.services.job.interfaces.job import (
    IJob,
    JobStatus,
    )
from lp.services import scripts


UTC = pytz.timezone('UTC')


class InvalidTransition(Exception):
    """Invalid transition from one job status to another attempted."""

    def __init__(self, current_status, requested_status):
        Exception.__init__(
            self, 'Transition from %s to %s is invalid.' %
            (current_status, requested_status))


class Job(SQLBase):
    """See `IJob`."""

    implements(IJob)

    @property
    def job_id(self):
        return self.id

    scheduled_start = UtcDateTimeCol()

    date_created = UtcDateTimeCol()

    date_started = UtcDateTimeCol()

    date_finished = UtcDateTimeCol()

    lease_expires = UtcDateTimeCol()

    log = StringCol()

    _status = EnumCol(enum=JobStatus, notNull=True, default=JobStatus.WAITING,
                      dbName='status')

    attempt_count = IntCol(default=0)

    max_retries = IntCol(default=0)

    requester_id = Int(name='requester', allow_none=True)
    requester = Reference(requester_id, 'Person.id')

    # Mapping of valid target states from a given state.
    _valid_transitions = {
        JobStatus.WAITING:
            (JobStatus.RUNNING,
             JobStatus.SUSPENDED),
        JobStatus.RUNNING:
            (JobStatus.COMPLETED,
             JobStatus.FAILED,
             JobStatus.SUSPENDED,
             JobStatus.WAITING),
        JobStatus.FAILED: (),
        JobStatus.COMPLETED: (),
        JobStatus.SUSPENDED:
            (JobStatus.WAITING,),
        }

    # Set of all states where the job could eventually complete.
    PENDING_STATUSES = frozenset(
        (JobStatus.WAITING,
         JobStatus.RUNNING,
         JobStatus.SUSPENDED))

    def _set_status(self, status):
        if status not in self._valid_transitions[self._status]:
            raise InvalidTransition(self._status, status)
        self._status = status

    status = property(lambda x: x._status)

    @property
    def is_pending(self):
        """See `IJob`."""
        return self.status in self.PENDING_STATUSES

    @classmethod
    def createMultiple(self, store, num_jobs, requester=None):
        """Create multiple `Job`s at once.

        :param store: `Store` to ceate the jobs in.
        :param num_jobs: Number of `Job`s to create.
        :param request: The `IPerson` requesting the jobs.
        :return: An iterable of `Job.id` values for the new jobs.
        """
        return bulk.create(
                (Job._status, Job.requester),
                [(JobStatus.WAITING, requester) for i in range(num_jobs)],
                get_primary_keys=True)

    def acquireLease(self, duration=300):
        """See `IJob`."""
        if (self.lease_expires is not None
            and self.lease_expires >= datetime.datetime.now(UTC)):
            raise LeaseHeld
        expiry = datetime.datetime.fromtimestamp(time.time() + duration,
            UTC)
        self.lease_expires = expiry

    def getTimeout(self):
        """Return the number of seconds until the job should time out.

        Jobs timeout when their leases expire.  If the lease for this job has
        already expired, return 0.
        """
        expiry = timegm(self.lease_expires.timetuple())
        return max(0, expiry - time.time())

    def start(self, manage_transaction=False):
        """See `IJob`."""
        self._set_status(JobStatus.RUNNING)
        self.date_started = datetime.datetime.now(UTC)
        self.date_finished = None
        self.attempt_count += 1
        if manage_transaction:
            transaction.commit()

    def complete(self, manage_transaction=False):
        """See `IJob`."""
        # Commit the transaction to update the DB time.
        if manage_transaction:
            transaction.commit()
        self._set_status(JobStatus.COMPLETED)
        self.date_finished = datetime.datetime.now(UTC)
        if manage_transaction:
            transaction.commit()

    def fail(self, manage_transaction=False):
        """See `IJob`."""
        if manage_transaction:
            transaction.abort()
        self._set_status(JobStatus.FAILED)
        self.date_finished = datetime.datetime.now(UTC)
        if manage_transaction:
            transaction.commit()

    def queue(self, manage_transaction=False, abort_transaction=False):
        """See `IJob`."""
        if manage_transaction:
            if abort_transaction:
                transaction.abort()
            # Commit the transaction to update the DB time.
            transaction.commit()
        self._set_status(JobStatus.WAITING)
        self.date_finished = datetime.datetime.now(UTC)
        if manage_transaction:
            transaction.commit()

    def suspend(self, manage_transaction=False):
        """See `IJob`."""
        self._set_status(JobStatus.SUSPENDED)
        if manage_transaction:
            transaction.commit()

    def resume(self):
        """See `IJob`."""
        if self.status is not JobStatus.SUSPENDED:
            raise InvalidTransition(self._status, JobStatus.WAITING)
        self._set_status(JobStatus.WAITING)
        self.lease_expires = None


class EnumeratedSubclass(type):
    """Metaclass for when subclasses are assigned enums."""

    def __init__(cls, name, bases, dict_):
        if getattr(cls, '_subclass', None) is None:
            cls._subclass = {}
        job_type = dict_.get('class_job_type')
        if job_type is not None:
            value = cls._subclass.setdefault(job_type, cls)
            assert value is cls, (
                '%s already registered to %s.' % (
                    job_type.name, value.__name__))
        # Perform any additional set-up requested by class.
        cls._register_subclass(cls)

    @staticmethod
    def _register_subclass(cls):
        pass

    def makeSubclass(cls, job):
        return cls._subclass[job.job_type](job)


Job.ready_jobs = Select(
    Job.id,
    And(
        Job._status == JobStatus.WAITING,
        Or(Job.lease_expires == None, Job.lease_expires < UTC_NOW),
        Or(Job.scheduled_start == None, Job.scheduled_start <= UTC_NOW),
        ))


class UniversalJobSource:
    """Returns the RunnableJob associated with a Job.id.

    Only BranchJobs are supported at present.
    """

    memory_limit = 2 * (1024 ** 3)

    needs_init = True

    @staticmethod
    def _getDerived(job_id, base_class):
        store = IStore(base_class)
        base_job = store.find(base_class, base_class.job == job_id).one()
        if base_job is None:
            return None, None, None
        return base_job.makeDerived(), base_job.__class__, store

    @classmethod
    def getUserAndBaseJob(cls, job_id):
        """Return the derived branch job associated with the job id."""
        # Avoid circular imports.
        from lp.bugs.model.apportjob import ApportJob
        from lp.code.model.branchjob import (
            BranchJob,
            )
        from lp.code.model.branchmergeproposaljob import (
            BranchMergeProposalJob,
            )
        from lp.registry.model.persontransferjob import PersonTransferJob
        from lp.answers.model.questionjob import QuestionJob
        from lp.soyuz.model.distributionjob import DistributionJob
        from lp.soyuz.model.packagecopyjob import PackageCopyJob
        from lp.translations.model.pofilestatsjob import POFileStatsJob
        from lp.translations.model.translationsharingjob import (
            TranslationSharingJob,
        )
        dbconfig.override(
            dbuser=config.launchpad.dbuser, isolation_level='read_committed')

        for baseclass in [
            ApportJob, BranchJob, BranchMergeProposalJob, DistributionJob,
            PackageCopyJob, PersonTransferJob, POFileStatsJob, QuestionJob,
            TranslationSharingJob,
            ]:
            derived, base_class, store = cls._getDerived(job_id, baseclass)
            if derived is not None:
                cls.clearStore(store)
                return derived.config.dbuser, base_class
        raise ValueError('No Job with job=%s.' % job_id)

    @staticmethod
    def clearStore(store):
        transaction.abort()
        getUtility(IZStorm).remove(store)
        store.close()

    @classmethod
    def get(cls, job_id):
        transaction.abort()
        if cls.needs_init:
            scripts.execute_zcml_for_scripts(use_web_security=False)
            cls.needs_init = False
        cls.clearStore(IStore(Job))
        dbuser, base_class = cls.getUserAndBaseJob(job_id)
        dbconfig.override(dbuser=dbuser, isolation_level='read_committed')
        return cls._getDerived(job_id, base_class)[0]
