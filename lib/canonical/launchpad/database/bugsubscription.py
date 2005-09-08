# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BugSubscription']

from zope.interface import implements
from zope.component import getUtility

from sqlobject import ForeignKey

from canonical.lp.dbschema import EnumCol
from canonical.launchpad.interfaces import IBugSubscription, ILaunchBag
from canonical.launchpad.database.bugset import BugSetBase
from canonical.database.sqlbase import SQLBase


class BugSubscription(SQLBase):
    """A relationship between a person and a bug."""

    implements(IBugSubscription)

    _table='BugSubscription'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)



