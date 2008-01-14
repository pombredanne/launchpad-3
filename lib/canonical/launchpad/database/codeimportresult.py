# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Database classes for the CodeImportResult table."""

__metaclass__ = type
__all__ = ['CodeImportResult', 'CodeImportResultSet']

from sqlobject import ForeignKey, StringCol

from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    CodeImportResultStatus, ICodeImportResult, ICodeImportResultSet)

class CodeImportResult(SQLBase):
    """See `ICodeImportResult`."""

    implements(ICodeImportResult)

    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    code_import = ForeignKey(
        dbName='code_import', foreignKey='CodeImport', notNull=True)

    machine = ForeignKey(
        dbName='machine', foreignKey='CodeImportMachine', notNull=True)

    requesting_user = ForeignKey(
        dbName='requesting_user', foreignKey='Person', default=None)

    log_excerpt = StringCol(default=None)

    log_file = ForeignKey(
        dbName='log_file', foreignKey='LibraryFileAlias', default=None)

    status = EnumCol(
        enum=CodeImportResultStatus, notNull=True)

    # XXX MichaelHudson, 2007-10-11
    # We should rename date_started to date_job_started in the database.
    # See bug #151583.
    date_job_started = UtcDateTimeCol(dbName='date_started', notNull=True)

    @property
    def date_job_finished(self):
        """See `ICodeImportResult`."""
        return self.date_created


class CodeImportResultSet(object):
    """See `ICodeImportResultSet`."""

    implements(ICodeImportResultSet)
