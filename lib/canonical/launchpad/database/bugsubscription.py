# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.interface import implements
from zope.component import getUtility

from sqlobject import ForeignKey
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.lp.dbschema import EnumCol
from canonical.lp import dbschema
from canonical.launchpad.interfaces import IBugSubscription, \
        IBugSubscriptionSet, ILaunchBag

from canonical.launchpad.database.bugset import BugSetBase

from canonical.database.sqlbase import SQLBase

class BugSubscription(SQLBase):
    """A relationship between a person and a bug."""

    implements(IBugSubscription)

    _table='BugSubscription'
    person = ForeignKey(dbName='person', foreignKey='Person',
                notNull=True)
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    subscription = EnumCol(
        dbName='subscription', notNull=True, schema=dbschema.BugSubscription)


def BugSubscriptionFactory(context, **kw):
    return BugSubscription(bug = getUtility(ILaunchBag).bug.id, **kw)


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
