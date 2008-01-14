# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugActivity', 'BugActivitySet']

from zope.interface import implements

from sqlobject import ForeignKey, IntCol, StringCol

from canonical.launchpad.interfaces import IBugActivity, IBugActivitySet

from canonical.database.sqlbase import SQLBase
from canonical.database.datetimecol import UtcDateTimeCol

class BugActivity(SQLBase):
    """Bug activity log entry."""

    implements(IBugActivity)

    _table = 'BugActivity'
    bug = ForeignKey(foreignKey='BugActivity', dbName='bug', notNull=True)
    datechanged = UtcDateTimeCol(notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    whatchanged = StringCol(notNull=True)
    oldvalue = StringCol(default=None)
    newvalue = StringCol(default=None)
    message = StringCol(default=None)


class BugActivitySet:
    """See IBugActivitySet."""

    implements(IBugActivitySet)

    def new(self, bug, datechanged, person, whatchanged,
            oldvalue=None, newvalue=None, message=None):
        """See IBugActivitySet."""
        return BugActivity(
            bug=bug, datechanged=datechanged, person=person,
            whatchanged=whatchanged, oldvalue=oldvalue, newvalue=newvalue,
            message=message)
