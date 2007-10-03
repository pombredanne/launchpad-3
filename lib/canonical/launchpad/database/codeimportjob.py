# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Database classes for the CodeImportJob table."""

__metaclass__ = type
__all__ = ['CodeImportJob', 'CodeImportJobSet']

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    CodeImportJobState, ICodeImportJob, ICodeImportJobSet)

from sqlobject import ForeignKey, IntCol, StringCol

from zope.interface import implements

class CodeImportJob(SQLBase):
    """See `ICodeImportJob`."""

    implements(ICodeImportJob)

    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    code_import = ForeignKey(
        dbName='code_import', foreignKey='CodeImport', notNull=True)

    machine = ForeignKey(
        dbName='machine', foreignKey='CodeImportMachine',
        notNull=False, default=None)

    date_due = UtcDateTimeCol(notNull=True)

    state = EnumCol(
        enum=CodeImportJobState, notNull=True,
        default=CodeImportJobState.PENDING)

    requesting_user = ForeignKey(
        dbName='requesting_user', foreignKey='Person',
        notNull=False, default=None)

    ordering = IntCol(notNull=False)

    heartbeat = UtcDateTimeCol(notNull=False, default=None)

    logtail = StringCol(notNull=False, default=None)

    date_started = UtcDateTimeCol(notNull=False, default=None)

    def assign(self, machine):
        """See `ICodeImportJob`."""

    def request(self, requesting_user):
        """See `ICodeImportJob`."""

    def kill(self, killing_user):
        """See `ICodeImportJob`."""

    def reclaim(self):
        """See `ICodeImportJob`."""

    def start(self):
        """See `ICodeImportJob`."""

    def finish(self, result_status, log_file_alias):
        """See `ICodeImportJob`."""

    def beat(self, logtail):
        """See `ICodeImportJob`."""


class CodeImportJobSet(object):
    """See `ICodeImportJobSet`."""

    implements(ICodeImportJobSet)

    def new(self, code_import, due_date):
        """See `ICodeImportJobSet`."""
        return CodeImportJob(code_import=code_import,
                             due_date=due_date)


    def jobForImport(self, code_import):
        """See `ICodeImportJobSet`."""

    def jobsForMachine(self, machine):
        """See `ICodeImportJobSet`."""
