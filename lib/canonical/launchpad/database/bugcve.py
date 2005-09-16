# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BugCve']

from zope.interface import implements
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from sqlobject import ForeignKey

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import IBugCve


class BugCve(SQLBase):
    """A table linking bugs and CVE entries."""

    implements(IBugCve)

    _table = 'BugCve'

    # db field names
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    cve = ForeignKey(dbName='cve', foreignKey='Cve', notNull=True)

