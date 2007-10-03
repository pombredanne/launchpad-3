# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Database classes for the CodeImportResult table."""

__metaclass__ = type
__all__ = ['CodeImportResult', 'CodeImportResultSet']

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    CodeImportResultStatus, ICodeImportResult, ICodeImportResultSet)

from sqlobject import ForeignKey, IntCol, StringCol

from zope.interface import implements

class CodeImportResult(SQLBase):
    """See `ICodeImportResult`."""

    implements(ICodeImportResult)

    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    code_import = ForeignKey(
        dbName='code_import', foreignKey='CodeImport', notNull=True)

    machine = ForeignKey(
        dbName='machine', foreignKey='CodeImportMachine', notNull=True)

    requesting_user = ForeignKey(
        dbName='requesting_user', foreignKey='Person', notNull=False)

    log_excerpt = StringCol(notNull=False)

    log_file = ForeignKey(
        dbName='log_file', foreignKey='LibraryFileAlias', notNull=False)

    status = EnumCol(
        enum=CodeImportResultStatus, notNull=True)

    date_started = UtcDateTimeCol(notNull=True)

    @property
    def date_finished(self):
        """See `ICodeImportResult`."""
        return self.date_created


class CodeImportResultSet(object):
    """See `ICodeImportResultSet`."""

    implements(ICodeImportResultSet)
