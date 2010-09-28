# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugActivity', 'BugActivitySet']

from sqlobject import (
    ForeignKey,
    StringCol,
    )
from storm.store import Store
from zope.interface import implements

from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from lp.bugs.interfaces.bugactivity import (
    IBugActivity,
    IBugActivitySet,
    )
from lp.registry.interfaces.person import validate_person


class BugActivity(SQLBase):
    """Bug activity log entry."""

    implements(IBugActivity)

    _table = 'BugActivity'
    bug = ForeignKey(foreignKey='Bug', dbName='bug', notNull=True)
    datechanged = UtcDateTimeCol(notNull=True)
    person = ForeignKey(
        dbName='person', foreignKey='Person',
        storm_validator=validate_person,
        notNull=True)
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
