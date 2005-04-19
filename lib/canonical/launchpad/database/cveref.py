from datetime import datetime

# Zope
from zope.interface import implements

# SQL imports
from sqlobject import ForeignKey, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import ICVERef, ICVERefSet

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.database.bugset import BugSetBase



class CVERef(SQLBase):
    """A CVE reference for a bug."""

    implements(ICVERef)

    _table = 'CVERef'
    bug = ForeignKey(foreignKey='Bug', dbName='bug', notNull=True)
    cveref = StringCol(notNull=True)
    title = StringCol(notNull=True)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=True)

    def url(self):
        """Return the URL for this CVE reference.
        """

        return 'http://www.cve.mitre.org/cgi-bin/cvename.cgi?name=%s' % (
                                                                  self.cveref)


class CVERefSet(BugSetBase):
    """A set of ICVERef's."""

    implements(ICVERefSet)
    table = CVERef

    def __init__(self, bug=None):
        super(CVERefSet, self).__init__(bug)
        self.title = 'CVE References'
        if bug:
            self.title += ' for Malone Bug #' + str(bug)

    def createCVERef(self, bug, cveref, title, owner):
        """See canonical.launchpad.interfaces.ICVERefSet."""
        return CVERef(
            bug = bug, cveref = cveref, title = title, owner = owner)

def CVERefFactory(context, **kw):
    bug = context.context.bug
    return CVERef(
        bug=bug,
        owner=context.request.principal.id,
        **kw)


