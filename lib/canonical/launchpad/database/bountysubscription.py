# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BountySubscription', 'BountySubscriptionSet']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad.interfaces import \
    IBountySubscription, IBountySubscriptionSet

from canonical.database.sqlbase import SQLBase
from canonical.lp.dbschema import EnumCol, BountySubscription


class BountySubscription(SQLBase):
    """A relationship between a person and a bounty."""

    implements(IBountySubscription)

    _table='BountySubscription'
    bounty = ForeignKey(dbName='bounty', foreignKey='Bounty', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    subscription = EnumCol(notNull=True, schema=BountySubscription)


class BountySubscriptionSet:
    """A set for BountySubscription objects."""

    implements(IBountySubscriptionSet)

