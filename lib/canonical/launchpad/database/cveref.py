# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['CVERef', 'CVERefSet', 'CVERefFactory']

from datetime import datetime

# Zope
from zope.interface import implements

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, StringCol

from canonical.launchpad.interfaces import ICVERef, ICVERefSet

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
        """Return the URL for this CVE reference."""
        return ('http://www.cve.mitre.org/cgi-bin/cvename.cgi?name=%s'
                % self.cveref)


class CVERefSet(BugSetBase):
    """A set of ICVERef's."""

    implements(ICVERefSet)
    table = CVERef

    def __init__(self, bug=None):
        BugSetBase.__init__(self, bug)
        self.title = 'CVE References'
        if bug:
            self.title += ' for Malone Bug #' + str(bug)

    def createCVERef(self, bug, cveref, title, owner):
        """See canonical.launchpad.interfaces.ICVERefSet."""
        return CVERef(bug=bug, cveref=cveref, title=title, owner=owner)

def CVERefFactory(context, **kw):
    bug = context.context.bug
    return CVERef(bug=bug, owner=context.request.principal.id, **kw)

