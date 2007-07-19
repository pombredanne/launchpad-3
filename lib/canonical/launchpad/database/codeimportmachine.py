# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Database classes including and related to CodeImportMachine."""

__metaclass__ = type

__all__ = [
    'CodeImportMachine',
    'CodeImportMachineSet',
    ]

from sqlobject import BoolCol, StringCol

from zope.interface import implements

from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    ICodeImportMachine, ICodeImportMachineSet)


class CodeImportMachine(SQLBase):
    """See `ICodeImportMachine`."""

    implements(ICodeImportMachine)

    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    hostname = StringCol(default=None)
    online = BoolCol(default=False)


class CodeImportMachineSet(object):
    """See `ICodeImportMachineSet`."""

    implements(ICodeImportMachineSet)

    def getAll(self):
        """See `ICodeImportMachineSet`."""
        return CodeImportMachine.select()

    def getByHostname(self, hostname):
        """See `ICodeImportMachineSet`."""
        return CodeImportMachine.selectOneBy(hostname=hostname)
