# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = [
    'ScriptActivity',
    'ScriptActivitySet',
    ]

import socket

from sqlobject import StringCol
from zope.interface import implements

from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from lp.services.scripts.interfaces.scriptactivity import (
    IScriptActivity,
    IScriptActivitySet,
    )


class ScriptActivity(SQLBase):

    implements(IScriptActivity)

    name = StringCol(notNull=True)
    hostname = StringCol(notNull=True)
    date_started = UtcDateTimeCol(notNull=True)
    date_completed = UtcDateTimeCol(notNull=True)


class ScriptActivitySet:

    implements(IScriptActivitySet)

    def recordSuccess(self, name, date_started, date_completed,
                      hostname=None):
        """See IScriptActivitySet"""
        if hostname is None:
            hostname = socket.gethostname()
        return ScriptActivity(
            name=name, hostname=hostname, date_started=date_started,
            date_completed=date_completed)

    def getLastActivity(self, name):
        """See IScriptActivitySet"""
        return ScriptActivity.selectFirstBy(
            name=name, orderBy='-date_started')
