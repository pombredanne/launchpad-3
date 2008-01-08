# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BountySubscription', 'BountySubscriptionSet']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad.interfaces import \
    IBountySubscription, IBountySubscriptionSet

from canonical.database.sqlbase import SQLBase


class BountySubscription(SQLBase):
    """A subscription by a person to a bounty."""

    implements(IBountySubscription)

    _table='BountySubscription'

    bounty = ForeignKey(dbName='bounty', foreignKey='Bounty', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)


class BountySubscriptionSet:
    """A set for BountySubscription objects."""

    implements(IBountySubscriptionSet)

