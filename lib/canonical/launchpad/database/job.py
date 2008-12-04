# Copyright 2008 Canonical Ltd.  All rights reserved.

"""ORM object representing jobs."""

__metaclass__ = type
__all__ = ['InvalidTransition', 'Job']


import datetime

from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
import pytz
from sqlobject import IntCol, StringCol
from storm.references import ReferenceSet
from zope.interface import implements

from canonical.launchpad.interfaces import IJob, JobStatus


UTC = pytz.timezone('UTC')


class InvalidTransition(Exception):

    def __init__(self, current_status, requested_status):
        Exception.__init__(
            self, 'Transition from %s to %s is invalid.' %
            (current_status, requested_status))


class Job(SQLBase):

    implements(IJob)

    scheduled_start = UtcDateTimeCol()

    date_created = UtcDateTimeCol()

    date_started = UtcDateTimeCol()

    date_finished = UtcDateTimeCol()

    lease_expires = UtcDateTimeCol()

    log = StringCol()

    status = EnumCol(enum=JobStatus, notNull=True, default=JobStatus.WAITING)

    attempt_count = IntCol(default=0)

    _valid_transitions = {
        JobStatus.WAITING: (JobStatus.RUNNING,),
        JobStatus.RUNNING: (
            JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.WAITING),
        JobStatus.FAILED: (),
        JobStatus.COMPLETED: (),
    }

    def _set_status(self, status):
        if status not in self._valid_transitions[self.status]:
            raise InvalidTransition(self.status, status)
        self.status = status

    def start(self):
        self._set_status(JobStatus.RUNNING)
        self.date_started = datetime.datetime.now(UTC)
        self.date_finished = None
        self.attempt_count += 1

    def complete(self):
        self._set_status(JobStatus.COMPLETED)
        self.date_finished = datetime.datetime.now(UTC)

    def fail(self):
        self._set_status(JobStatus.FAILED)
        self.date_finished = datetime.datetime.now(UTC)

    def queue(self):
        self._set_status(JobStatus.WAITING)
        self.date_finished = datetime.datetime.now(UTC)
