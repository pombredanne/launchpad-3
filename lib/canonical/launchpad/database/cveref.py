# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['CVERef', 'CVERefSet', 'CVERefFactory']

import re
from datetime import datetime

# Zope
from zope.interface import implements

# SQL imports
from sqlobject import ForeignKey, StringCol

from canonical.launchpad.interfaces import ICVERef, ICVERefSet

from canonical.lp.dbschema import EnumCol, CVEState

from canonical.database.sqlbase import SQLBase, flush_database_updates
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.database.bugset import BugSetBase

cverefpat = re.compile(r'(CVE|CAN)-((19|20)\d{2}\-\d{4})')

class CVERef(SQLBase):
    """A CVE reference for a bug."""

    implements(ICVERef)

    _table = 'CVERef'
    bug = ForeignKey(foreignKey='Bug', dbName='bug', notNull=True)
    cveref = StringCol(notNull=True)
    cvestate = EnumCol(dbName='cvestate', schema=CVEState, notNull=True)
    title = StringCol(notNull=True)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=True)

    @property
    def url(self):
        """See ICVERef."""
        return ('http://www.cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-%s'
                % self.cveref)

    @property
    def displayname(self):
        return 'CVE-%s' % self.cveref


class CVERefSet(BugSetBase):
    """A set of ICVERef's."""

    implements(ICVERefSet)
    table = CVERef

    def __init__(self, bug=None):
        """See ICVERefSet."""
        BugSetBase.__init__(self, bug)
        self.title = 'CVE References'
        if bug:
            self.title += ' for Malone Bug #' + str(bug)

    def __iter__(self):
        """See ICVERefSet."""
        return iter(CVERef.select())

    def createCVERef(self, bug, cveref, cvestate, title, owner):
        """See ICVERefSet."""
        return CVERef(bug=bug, cveref=cveref, cvestate=cvestate,
            title=title, owner=owner)

    def fromText(self, text, bug, title, owner):
        """See ICVERefSet."""
        # let's look for matching entries
        matches = cverefpat.findall(text)
        if len(matches) == 0:
            return []
        newcverefs = []
        for match in matches:
            # let's get the core CVE data
            cvestate = match[0]
            cvenum = match[1]
            # see if there is already a matching CVE ref on this bug
            cveref = None
            for ref in bug.cverefs:
                if ref.cveref == cvenum:
                    cveref = ref
                    break
            if cveref is None:
                cveref = CVERef(bug=bug, cveref=cvenum,
                    cvestate=CVEState.CANDIDATE, owner=owner,
                    title=title)
                newcverefs.append(cveref)
                flush_database_updates()
        return sorted(newcverefs, key=lambda a: a.cveref)

    def fromMessage(self, message, bug):
        """See ICVERefSet."""
        cverefs = set()
        for messagechunk in message:
            if messagechunk.blob is not None:
                # we don't process attachments
                continue
            elif messagechunk.content is not None:
                # look for potential BugWatch URL's and create the trackers
                # and watches as needed
                cverefs = cverefs.union(self.fromText(messagechunk.content,
                    bug, message.title, message.owner))
            else:
                raise AssertionError('MessageChunk without content or blob.')
        return sorted(cverefs, key=lambda a: a.cveref)


def CVERefFactory(context, **kw):
    bug = context.context.bug
    return CVERef(bug=bug, owner=context.request.principal.id, **kw)

