# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugActivity', 'BugActivitySet']

from zope.interface import implements

from sqlobject import ForeignKey, StringCol
from storm.store import Store

from canonical.launchpad.interfaces import IBugActivity, IBugActivitySet

from canonical.database.sqlbase import SQLBase
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.validators.person import validate_public_person

class BugActivity(SQLBase):
    """Bug activity log entry."""

    implements(IBugActivity)

    _table = 'BugActivity'
    bug = ForeignKey(foreignKey='Bug', dbName='bug', notNull=True)
    datechanged = UtcDateTimeCol(notNull=True)
    person = ForeignKey(
        dbName='person', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
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
        activity = BugActivity(
            bug=bug, datechanged=datechanged, person=person,
            whatchanged=whatchanged, oldvalue=oldvalue, newvalue=newvalue,
            message=message)
        Store.of(activity).flush()
        return activity
