# Zope
from zope.interface import implements

# SQL imports
from sqlobject import ForeignKey, IntCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import IBugSubscription, \
        IBugSubscriptionSet

from canonical.launchpad.database.bugset import BugSetBase

from canonical.database.sqlbase import SQLBase

class BugSubscription(SQLBase):
    """A relationship between a person and a bug."""

    implements(IBugSubscription)

    _table='BugSubscription'
    person = ForeignKey(dbName='person', foreignKey='Person',
                notNull=True)
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    subscription = IntCol(notNull=True)


def BugSubscriptionFactory(context, **kw):
    bug = context.context.bug
    return BugSubscription(bug=bug, **kw)


class BugSubscriptionSet(BugSetBase):
    """A set for BugSubscription objects."""

    implements(IBugSubscriptionSet)
    table = BugSubscription

    def delete(self, id):
        # BugSubscription.delete(id) raises an error in SQLObject
        # why this is I do not know
        conn = BugSubscription._connection
        # I want an exception raised if id can't be converted to an int
        conn.query('DELETE FROM BugSubscription WHERE id=%d' % int(id))
