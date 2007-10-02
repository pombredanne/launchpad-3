# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type
__all__ = ['CodeImportJob', 'CodeImportJobSet']

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

    code_import = ForeignKey(dbName='code_import', foreignKey='CodeImport')
    machine = ForeignKey(dbName='machine', foreignKey='CodeImportMachine')
    # ...

class CodeImportJobSet(object):
    """See `ICodeImportJobSet`."""

    implements(ICodeImportJobSet)

    def new(self, code_import):
        pass
