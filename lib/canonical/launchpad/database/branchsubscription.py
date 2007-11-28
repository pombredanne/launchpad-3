# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BranchSubscription']

from zope.interface import implements

from sqlobject import ForeignKey, IntCol

from canonical.database.constants import DEFAULT
from canonical.database.sqlbase import SQLBase
from canonical.database.enumcol import EnumCol

from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, BranchSubscriptionDiffSize,
    IBranchSubscription)


class BranchSubscription(SQLBase):
    """A relationship between a person and a branch."""

    implements(IBranchSubscription)

    _table = 'BranchSubscription'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    branch = ForeignKey(dbName='branch', foreignKey='Branch', notNull=True)
    notification_level = EnumCol(enum=BranchSubscriptionNotificationLevel,
                                 notNull=True, default=DEFAULT)
    max_diff_lines = EnumCol(enum=BranchSubscriptionDiffSize,
                             notNull=True)
