# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugActivity', 'BugActivitySet']

import re

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

    # The regular expression we use for matching bug task changes.
    bugtask_change_re = re.compile(
        '(?P<target>[a-z0-9][a-z0-9\+\.\-]+( \([A-Za-z0-9\s]+\))?): '
        '(?P<attribute>assignee|importance|milestone|status)')

    @property
    def target(self):
        """Return the target of this BugActivityItem.

        `target` is determined based on the `whatchanged` string.

        :return: The target name of the item if `whatchanged` is of the
        form <target_name>: <attribute>. Otherwise, return None.
        """
        match = self.bugtask_change_re.match(self.whatchanged)
        if match is None:
            return None
        else:
            return match.groupdict()['target']

    @property
    def attribute(self):
        """Return the attribute changed in this BugActivityItem.

        `attribute` is determined based on the `whatchanged` string.

        :return: The attribute name of the item if `whatchanged` is of
            the form <target_name>: <attribute>. Otherwise, return the
            original `whatchanged` string.
        """
        match = self.bugtask_change_re.match(self.whatchanged)
        if match is None:
            return self.whatchanged
        else:
            return match.groupdict()['attribute']


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
