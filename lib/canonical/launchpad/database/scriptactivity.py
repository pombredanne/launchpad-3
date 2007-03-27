# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from datetime import datetime
import pytz
import socket

from sqlobject import StringCol
from zope.interfaces import implements

from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IScriptActivity, IScriptActivitySet


class ScriptActivity(SQLBase):

    implements(IScriptActivity)

    name = StringCol(notNull=True)
    hostname = StringCol(notNull=True)
    date_started = UtcDateTimeCol(notNull=True)
    date_completed = UtcDateTimeCol(notNull=True)
    status = IntCol(notNull=True)


class ScriptActivitySet:

    implements(IScriptActivitySet)

    def recordSuccess(self, name, date_started, date_completed):
        """See IScriptActivitySet"""
        return ScriptActivity(name=name, hostname=socket.gethostname(),
                              date_started=date_started,
                              date_completed=date_completed, status=0)
