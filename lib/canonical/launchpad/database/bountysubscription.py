# Zope
from zope.interface import implements

# SQL imports
from sqlobject import ForeignKey, IntCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import IBountySubscription, \
        IBountySubscriptionSet

from canonical.database.sqlbase import SQLBase
from canonical.lp.dbschema import EnumCol, BountySubscription

class BountySubscription(SQLBase):
    """A relationship between a person and a bounty."""

    implements(IBountySubscription)

    _table='BountySubscription'
    bounty = ForeignKey(dbName='bounty', foreignKey='Bounty', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person',
                notNull=True)
    subscription = EnumCol(notNull=True, schema=BountySubscription)


class BountySubscriptionSet(object):
    """A set for BountySubscription objects."""

    implements(IBountySubscriptionSet)

