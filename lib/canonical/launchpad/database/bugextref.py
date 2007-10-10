# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugExternalRef', 'BugExternalRefSet']

from zope.interface import implements

from sqlobject import ForeignKey, StringCol

from canonical.launchpad.interfaces import IBugExternalRef, IBugExternalRefSet
from canonical.database.sqlbase import SQLBase
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.database.bugset import BugSetBase


class BugExternalRef(SQLBase):
    """An external reference for a bug, not supported remote bug systems."""

    implements(IBugExternalRef)

    _table = 'BugExternalRef'
    bug = ForeignKey(foreignKey='Bug', dbName='bug', notNull=True)
    url = StringCol(notNull=True)
    title = StringCol(notNull=True)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=True)


class BugExternalRefSet(BugSetBase):
    """A set for BugExternalRef."""

    implements(IBugExternalRefSet)
    table = BugExternalRef

    def __init__(self, bug=None):
        super(BugExternalRefSet, self).__init__(bug)
        self.title = 'Web References'
        if bug:
            self.title += ' for Malone Bug #' + str(bug)

    def createBugExternalRef(self, bug, url, title, owner):
        """See canonical.launchpad.interfaces.IBugExternalRefSet."""
        return BugExternalRef(
            bug = bug, url = url, title = title, owner = owner)

    def search(self):
        return BugExternalRef.select()
