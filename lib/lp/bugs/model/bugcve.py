# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugCve']

from sqlobject import ForeignKey
from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from lp.bugs.interfaces.bugcve import IBugCve


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
