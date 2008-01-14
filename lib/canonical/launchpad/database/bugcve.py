# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugCve']

from zope.interface import implements

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

    @property
    def target(self):
        """See IBugLink."""
        return self.cve
