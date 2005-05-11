# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BugTrackerType', 'BugTracker', 'BugTrackerSet']

from zope.interface import implements

from sqlobject import ForeignKey, StringCol, MultipleJoin

from canonical.launchpad.interfaces import \
        IBugTrackerType, IBugTracker, IBugTrackerSet

from canonical.database.sqlbase import SQLBase


class BugTrackerType(SQLBase):
    """A type of supported remote  bug system. eg Bugzilla."""

    implements(IBugTrackerType)

    _table = 'BugTrackerType'
    name = StringCol(notNull=True)
    title = StringCol(notNull=True)
    description = StringCol(notNull=True)
    homepage = StringCol(notNull=True)
    owner = ForeignKey(foreignKey='Person', dbName='owner', default=None)


class BugTracker(SQLBase):
    """A class to access the BugTracker table of the db. Each BugTracker is a
    distinct instance of that bug tracking tool. For example, each Bugzilla
    deployment is a separate BugTracker. bugzilla.mozilla.org and
    bugzilla.gnome.org are each distinct BugTracker's.
    """
    implements(IBugTracker)
    _table = 'BugTracker'
    bugtrackertype = ForeignKey(dbName='bugtrackertype',
                foreignKey='BugTrackerType', notNull=True)
    name = StringCol(notNull=True, unique=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    baseurl = StringCol(notNull=True)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    contactdetails = StringCol(notNull=False)
    watches = MultipleJoin('BugWatch', joinColumn='bugtracker')

    def watchcount(self):
        return len(list(self.watches))


class BugTrackerSet:
    """Implements IBugTrackerSet for a container or set of BugTracker's,
    either the full set in the db, or a subset.
    """

    implements(IBugTrackerSet)

    table = BugTracker

    def __init__(self):
        self.title = 'Launchpad-registered Bug Trackers'

    def __getitem__(self, name):
        item = self.table.selectOne(self.table.q.name == name)
        if item is None:
            raise KeyError, id
        else:
            return item

    def __iter__(self):
        for row in self.table.select():
            yield row

