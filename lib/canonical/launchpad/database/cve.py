# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'Cve',
    'CveSet',
    ]

import re

# Zope
from zope.interface import implements

# SQL imports
from sqlobject import (
    StringCol, SQLRelatedJoin, SQLMultipleJoin, SQLObjectNotFound)

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.interfaces import (
    CveStatus, IBugLinkTarget, ICve, ICveSet)
from canonical.launchpad.validators.cve import valid_cve
from canonical.launchpad.database.buglinktarget import BugLinkTargetMixin
from canonical.launchpad.database.bugcve import BugCve
from canonical.launchpad.database.cvereference import CveReference

cverefpat = re.compile(r'(CVE|CAN)-((19|20)\d{2}\-\d{4})')

class Cve(SQLBase, BugLinkTargetMixin):
    """A CVE database record."""

    implements(ICve, IBugLinkTarget)

    _table = 'Cve'

    sequence = StringCol(notNull=True, alternateID=True)
    status = EnumCol(dbName='status', schema=CveStatus, notNull=True)
    description = StringCol(notNull=True)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    datemodified = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    # joins
    bugs = SQLRelatedJoin('Bug', intermediateTable='BugCve',
        joinColumn='cve', otherColumn='bug', orderBy='id')
    bug_links = SQLMultipleJoin('BugCve', joinColumn='cve', orderBy='id')
    references = SQLMultipleJoin('CveReference', joinColumn='cve', orderBy='id')

    @property
    def url(self):
        """See ICve."""
        return ('http://www.cve.mitre.org/cgi-bin/cvename.cgi?name=%s'
                % self.sequence)

    @property
    def displayname(self):
        return 'CVE-%s' % self.sequence

    @property
    def title(self):
        return 'CVE-%s (%s)' % (self.sequence, self.status.title)

    # CveReference's
    def createReference(self, source, content, url=None):
        """See ICveReference."""
        return CveReference(cve=self, source=source, content=content,
            url=url)

    def removeReference(self, ref):
        assert ref.cve == self
        CveReference.delete(ref.id)

    # Template methods for BugLinkTargetMixin
    buglinkClass = BugCve

    def createBugLink(self, bug):
        """See BugLinkTargetMixin."""
        return BugCve(cve=self, bug=bug)


class CveSet:
    """The full set of ICve's."""

    implements(ICveSet)
    table = Cve

    def __init__(self, bug=None):
        """See ICveSet."""
        self.title = 'The Common Vulnerabilities and Exposures database'

    def __getitem__(self, sequence):
        """See ICveSet."""
        if sequence[:4] in ['CVE-', 'CAN-']:
            sequence = sequence[4:]
        if not valid_cve(sequence):
            return None
        try:
            return Cve.bySequence(sequence)
        except SQLObjectNotFound:
            return None

    def getAll(self):
        """See ICveSet."""
        return Cve.select(orderBy="-datemodified")

    def __iter__(self):
        """See ICveSet."""
        return iter(Cve.select())

    def new(self, sequence, description, status=CveStatus.CANDIDATE):
        """See ICveSet."""
        return Cve(sequence=sequence, status=status,
            description=description)

    def latest(self, quantity=5):
        """See ICveSet."""
        return Cve.select(orderBy='-datecreated', limit=quantity)

    def latest_modified(self, quantity=5):
        """See ICveSet."""
        return Cve.select(orderBy='-datemodified', limit=quantity)

    def search(self, text):
        """See ICveSet."""
        query = "Cve.fti @@ ftq(%s) " % sqlvalues(text)
        return Cve.select(query, distinct=True, orderBy='-datemodified')

    def inText(self, text):
        """See ICveSet."""
        # let's look for matching entries
        cves = set()
        for match in cverefpat.finditer(text):
            # let's get the core CVE data
            cvestate = match.group(1)
            sequence = match.group(2)
            # see if there is already a matching CVE ref in the db, and if
            # not, then create it
            cve = self[sequence]
            if cve is None:
                cve = Cve(sequence=sequence, status=CveStatus.DEPRECATED,
                    description="This CVEwas automatically created from "
                    "a reference found in an email or other text. If you "
                    "are reading this, then this CVE entry is probably "
                    "erroneous, since this text should be replaced by "
                    "the official CVE description automatically.")
            cves.add(cve)

        return sorted(cves, key=lambda a: a.sequence)

    def inMessage(self, message):
        """See ICveSet."""
        cves = set()
        for messagechunk in message:
            if messagechunk.blob is not None:
                # we don't process attachments
                continue
            elif messagechunk.content is not None:
                # look for potential CVE URL's and create them as needed
                cves.update(self.inText(messagechunk.content))
            else:
                raise AssertionError('MessageChunk without content or blob.')
        return sorted(cves, key=lambda a: a.sequence)

    def getBugCvesForBugTasks(self, bugtasks):
        bug_ids = set(task.bug.id for task in bugtasks)
        assert bug_ids, "bugtasks must be non-empty, received %r" % bugtasks
        return BugCve.select("""
            BugCve.bug IN %s""" % sqlvalues(bug_ids),
            prejoins=["cve"],
            orderBy=['bug', 'cve'])

    def getBugCveCount(self):
        """See ICveSet."""
        return BugCve.select().count()

