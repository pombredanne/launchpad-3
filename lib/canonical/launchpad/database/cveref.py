
from datetime import datetime

# Zope
from zope.interface import implements

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import IBug
from canonical.launchpad.interfaces import IBugExternalRef
from canonical.launchpad.interfaces import *

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.database.bugset import BugSetBase



class CVERef(SQLBase):
    """A CVE reference for a bug."""

    implements(ICVERef)

    _table = 'CVERef'
    bug = ForeignKey(foreignKey='Bug', dbName='bug', notNull=True)
    cveref = StringCol(notNull=True)
    title = StringCol(notNull=True)
    datecreated = DateTimeCol(notNull=True, default=datetime.utcnow())
    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=True)

    def url(self):
        """Return the URL for this CVE reference.
        """

        return 'http://www.cve.mitre.org/cgi-bin/cvename.cgi?name=%s' % (
                                                                  self.data)


class CVERefSet(BugSetBase):
    """A set of CVERef."""

    implements(ICVERefSet)
    table = CVERef


def CVERefFactory(context, **kw):
    bug = context.context.bug
    return CVERef(
        bug=bug,
        owner=context.request.principal.id,
        **kw)


