# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BranchSubscription']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IBranchSubscription


class BranchSubscription(SQLBase):
    """A relationship between a person and a branch."""

    implements(IBranchSubscription)

    _table = 'BranchSubscription'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    branch = ForeignKey(dbName='branch', foreignKey='Branch', notNull=True)
