
# Zope
from zope.interface import implements
# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces.bug import IBug
from canonical.launchpad.interfaces import *

from canonical.database.sqlbase import SQLBase


class BugExternalRef(SQLBase):
    """An external reference for a bug, not supported remote bug systems."""

    implements(IBugExternalRef)

    _table = 'BugExternalRef'
    bug = ForeignKey(foreignKey='Bug', dbName='bug', notNull=True)
    bugreftype = IntCol(notNull=True)
    data = StringCol(notNull=True)
    description = StringCol(notNull=True)
    datecreated = DateTimeCol(notNull=True)
    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=True)

    def url(self):
        """Return the URL for this external reference.

        1: If a CVE number link to the CVE site
        2: If a URL link to that URL
        """

        if self.bugreftype == 1:
             return 'http://www.cve.mitre.org/cgi-bin/cvename.cgi?name=%s' % (
                                                                    self.data)
        else:
            return self.data


