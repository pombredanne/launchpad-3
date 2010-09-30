# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""ORM object representing jobs."""

__metaclass__ = type
__all__ = ['InvalidTransition', 'Job', 'JobStatus']


from calendar import timegm
import datetime
import time

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
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from lp.services.job.interfaces.job import (
    IJob,
    JobStatus,
    LeaseHeld,
    )


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

    scheduled_start = UtcDateTimeCol()

    date_created = UtcDateTimeCol()

    date_started = UtcDateTimeCol()

    date_finished = UtcDateTimeCol()

    lease_expires = UtcDateTimeCol()

    log = StringCol()

    _status = EnumCol(enum=JobStatus, notNull=True, default=JobStatus.WAITING,
                      dbName='status')

    attempt_count = IntCol(default=0)

    # List of the valid target states from a given state.
    _valid_transitions = {
        JobStatus.WAITING:
            (JobStatus.RUNNING,
             JobStatus.SUSPENDED),
        JobStatus.RUNNING:
            (JobStatus.COMPLETED,
             JobStatus.FAILED,
             JobStatus.WAITING),
        JobStatus.FAILED: (),
        JobStatus.COMPLETED: (),
        JobStatus.SUSPENDED:
            (JobStatus.WAITING,),
    }

    def _set_status(self, status):
        if status not in self._valid_transitions[self._status]:
            raise InvalidTransition(self._status, status)
        self._status = status

    status = property(lambda x: x._status)

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
        return max(0,  expiry - time.time())

    def start(self):
        """See `IJob`."""
        self._set_status(JobStatus.RUNNING)
        self.date_started = datetime.datetime.now(UTC)
        self.date_finished = None
        self.attempt_count += 1

    def complete(self):
        """See `IJob`."""
        self._set_status(JobStatus.COMPLETED)
        self.date_finished = datetime.datetime.now(UTC)

    def fail(self):
        """See `IJob`."""
        self._set_status(JobStatus.FAILED)
        self.date_finished = datetime.datetime.now(UTC)

    def queue(self):
        """See `IJob`."""
        self._set_status(JobStatus.WAITING)
        self.date_finished = datetime.datetime.now(UTC)

    def suspend(self):
        """See `IJob`."""
        self._set_status(JobStatus.SUSPENDED)

    def resume(self):
        """See `IJob`."""
        if self.status is not JobStatus.SUSPENDED:
            raise InvalidTransition(self._status, JobStatus.WAITING)
        self._set_status(JobStatus.WAITING)


Job.ready_jobs = Select(
    Job.id,
    And(
        Job._status == JobStatus.WAITING,
        Or(Job.lease_expires == None, Job.lease_expires < UTC_NOW),
        Or(Job.scheduled_start == None, Job.scheduled_start <= UTC_NOW),
        ))
