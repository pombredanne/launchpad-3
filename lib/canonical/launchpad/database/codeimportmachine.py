# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Database classes including and related to CodeImportMachine."""

__metaclass__ = type

__all__ = [
    'CodeImportMachine',
    'CodeImportMachineSet',
    ]

from sqlobject import StringCol

from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    ICodeImportMachine, ICodeImportMachineSet, CodeImportMachineState,
    ICodeImportEventSet)


class CodeImportMachine(SQLBase):
    """See `ICodeImportMachine`."""

    implements(ICodeImportMachine)

    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)

    hostname = StringCol(default=None)
    state = EnumCol(enum=CodeImportMachineState, notNull=True,
        default=CodeImportMachineState.OFFLINE)
    heartbeat = UtcDateTimeCol(notNull=False)

    def setOnline(self):
        """See `ICodeImportMachine`."""
        assert self.state == CodeImportMachineState.OFFLINE, (
            "State of machine %s was %s." % (self.hostname, self.state.name))
        self.state = CodeImportMachineState.ONLINE
        getUtility(ICodeImportEventSet).newOnline(self)

    def setOffline(self, reason):
        """See `ICodeImportMachine`."""
        assert self.state in (CodeImportMachineState.ONLINE,
                              CodeImportMachineState.QUIESCING), (
            "State of machine %s was %s." % (self.hostname, self.state.name))
        self.state = CodeImportMachineState.OFFLINE
        getUtility(ICodeImportEventSet).newOffline(self, reason)

    def setQuiescing(self, user, message):
        """See `ICodeImportMachine`."""
        assert self.state == CodeImportMachineState.ONLINE, (
            "State of machine %s was %s." % (self.hostname, self.state.name))
        self.state = CodeImportMachineState.QUIESCING
        getUtility(ICodeImportEventSet).newQuiesce(self, user, message)


class CodeImportMachineSet(object):
    """See `ICodeImportMachineSet`."""

    implements(ICodeImportMachineSet)

    def getAll(self):
        """See `ICodeImportMachineSet`."""
        return CodeImportMachine.select()

    def getByHostname(self, hostname):
        """See `ICodeImportMachineSet`."""
        return CodeImportMachine.selectOneBy(hostname=hostname)
