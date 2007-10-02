# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type
__all__ = ['CodeImportResult', 'CodeImportResultSet']

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

    code_import = ForeignKey(dbName='code_import', foreignKey='CodeImport')
    machine = ForeignKey(dbName='machine', foreignKey='CodeImportMachine')
    date_due = UtcDateTimeCol()
    requesting_user = ForeignKey(dbName='requesting_user', foreignKey='Person')
    ordering = IntCol()
    heartbeat = UtcDateTimeCol()
    logtail = StringCol()
    date_started = UtcDateTimeCol()

class CodeImportResultSet(object):
    """See `ICodeImportResultSet`."""

    implements(ICodeImportResultSet)
