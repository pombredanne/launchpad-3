from datetime import datetime

# Zope
from zope.interface import implements

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import IBugWatch, \
        IBugWatchContainer
from canonical.launchpad.database.bug import BugContainerBase
from canonical.database.sqlbase import SQLBase

class BugWatch(SQLBase):
    implements(IBugWatch)
    _table = 'BugWatch'
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    bugtracker = ForeignKey(dbName='bugtracker',
                foreignKey='BugTracker', notNull=True)
    remotebug = StringCol(notNull=True)
    # TODO: Default should be NULL, but column is NOT NULL
    remotestatus = StringCol(notNull=True, default='')
    lastchanged = DateTimeCol(notNull=True)
    lastchecked = DateTimeCol(notNull=True)
    datecreated = DateTimeCol(notNull=True)
    owner = ForeignKey(dbName='owner', foreignKey='Person',
                notNull=True)

class BugWatchContainer(BugContainerBase):
    """A container for BugWatch"""

    implements(IBugWatchContainer)
    table = BugWatch

def BugWatchFactory(context, **kw):
    bug = context.context.bug
    now = datetime.utcnow()
    return BugWatch(
        bug=bug, owner=context.request.principal.id, datecreated=now,
        lastchanged=now, lastchecked=now, **kw)
