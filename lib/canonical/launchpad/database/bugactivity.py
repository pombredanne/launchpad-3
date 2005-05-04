# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BugActivity']

from zope.interface import implements

from sqlobject import ForeignKey, IntCol, StringCol

from canonical.launchpad.interfaces import IBugActivity

from canonical.database.sqlbase import SQLBase
from canonical.database.datetimecol import UtcDateTimeCol

class BugActivity(SQLBase):
    """Bug activity log entry."""

    implements(IBugActivity)

    _table = 'BugActivity'
    bug = ForeignKey(foreignKey='BugActivity', dbName='bug', notNull=True)
    datechanged = UtcDateTimeCol(notNull=True)
    person = IntCol(notNull=True)
    whatchanged = StringCol(notNull=True)
    oldvalue = StringCol(default=None)
    newvalue = StringCol(default=None)
    message = StringCol(default=None)

