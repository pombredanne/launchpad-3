from datetime import datetime

# Zope
from zope.interface import implements

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import IBugWatch, \
        IBugWatchSet
from canonical.launchpad.database.bug import BugSetBase
from canonical.database.sqlbase import SQLBase
from canonical.database.constants import nowUTC


class BugWatch(SQLBase):
    implements(IBugWatch)
    _table = 'BugWatch'
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    bugtracker = ForeignKey(dbName='bugtracker',
                foreignKey='BugTracker', notNull=True)
    remotebug = StringCol(notNull=True)
    remotestatus = StringCol(notNull=False, default=None)
    lastchanged = DateTimeCol(notNull=False, default=None)
    lastchecked = DateTimeCol(notNull=False, default=None)
    datecreated = DateTimeCol(notNull=True, default=nowUTC)
    owner = ForeignKey(dbName='owner', foreignKey='Person',
                notNull=True)

class BugWatchSet(BugSetBase):
    """A set for BugWatch"""

    implements(IBugWatchSet)
    table = BugWatch

def BugWatchFactory(context, **kw):
    bug = context.context.bug
    now = datetime.utcnow()
    return BugWatch(
        bug=bug, owner=context.request.principal.id, datecreated=now,
        lastchanged=now, lastchecked=now, **kw)
