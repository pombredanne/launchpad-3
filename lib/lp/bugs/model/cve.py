# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'Cve',
    'CveSet',
    ]

import operator

from sqlobject import (
    SQLMultipleJoin,
    SQLObjectNotFound,
    StringCol,
    )
from storm.expr import In
from storm.store import Store
from zope.component import getUtility
from zope.interface import implementer

from lp.app.validators.cve import (
    CVEREF_PATTERN,
    valid_cve,
    )
from lp.bugs.interfaces.buglink import IBugLinkTarget
from lp.bugs.interfaces.cve import (
    CveStatus,
    ICve,
    ICveSet,
    )
from lp.bugs.model.bug import Bug
from lp.bugs.model.buglinktarget import BugLinkTargetMixin
from lp.bugs.model.cvereference import CveReference
from lp.services.database import bulk
from lp.services.database.constants import UTC_NOW
from lp.services.database.datetimecol import UtcDateTimeCol
from lp.services.database.enumcol import EnumCol
from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import SQLBase
from lp.services.database.stormexpr import fti_search
from lp.services.xref.interfaces import IXRefSet
from lp.services.xref.model import XRef


@implementer(ICve, IBugLinkTarget)
class Cve(SQLBase, BugLinkTargetMixin):
    """A CVE database record."""

    _table = 'Cve'

    sequence = StringCol(notNull=True, alternateID=True)
    status = EnumCol(dbName='status', schema=CveStatus, notNull=True)
    description = StringCol(notNull=True)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    datemodified = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    references = SQLMultipleJoin(
        'CveReference', joinColumn='cve', orderBy='id')

    @property
    def url(self):
        """See ICve."""
        return ('https://cve.mitre.org/cgi-bin/cvename.cgi?name=%s'
                % self.sequence)

    @property
    def displayname(self):
        return 'CVE-%s' % self.sequence

    @property
    def title(self):
        return 'CVE-%s (%s)' % (self.sequence, self.status.title)

    @property
    def bugs(self):
        bug_ids = [
            int(id) for _, id in getUtility(IXRefSet).findFrom(
                (u'cve', self.sequence), types=[u'bug'])]
        return list(sorted(
            bulk.load(Bug, bug_ids), key=operator.attrgetter('id')))

    # CveReference's
    def createReference(self, source, content, url=None):
        """See ICveReference."""
        return CveReference(cve=self, source=source, content=content,
            url=url)

    def removeReference(self, ref):
        assert ref.cve == self
        CveReference.delete(ref.id)

    def createBugLink(self, bug, props=None):
        """See BugLinkTargetMixin."""
        if props is None:
            props = {}
        # XXX: Should set creator.
        getUtility(IXRefSet).create(
            {(u'cve', self.sequence): {(u'bug', unicode(bug.id)): props}})

    def deleteBugLink(self, bug):
        """See BugLinkTargetMixin."""
        getUtility(IXRefSet).delete(
            {(u'cve', self.sequence): [(u'bug', unicode(bug.id))]})


@implementer(ICveSet)
class CveSet:
    """The full set of ICve's."""
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
        return Cve.select(
            fti_search(Cve, text), distinct=True, orderBy='-datemodified')

    def inText(self, text):
        """See ICveSet."""
        # let's look for matching entries
        cves = set()
        for match in CVEREF_PATTERN.finditer(text):
            # let's get the core CVE data
            sequence = match.group(2)
            # see if there is already a matching CVE ref in the db, and if
            # not, then create it
            cve = self[sequence]
            if cve is None:
                cve = Cve(sequence=sequence, status=CveStatus.DEPRECATED,
                    description="This CVE was automatically created from "
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

    def getBugCvesForBugTasks(self, bugtasks, cve_mapper=None):
        """See ICveSet."""
        bugs = bulk.load_related(Bug, bugtasks, ('bugID', ))
        if len(bugs) == 0:
            return []
        store = Store.of(bugtasks[0])

        xrefs = getUtility(IXRefSet).findFromMany(
            [(u'bug', unicode(bug.id)) for bug in bugs], types=[u'cve'])
        bugcve_ids = set()
        for bug_key in xrefs:
            for cve_key in xrefs[bug_key]:
                bugcve_ids.add((int(bug_key[1]), cve_key[1]))

        bugcve_ids = list(sorted(bugcve_ids))

        cves = store.find(
            Cve, In(Cve.sequence, [seq for _, seq in bugcve_ids]))

        if cve_mapper is None:
            cvemap = dict((cve.sequence, cve) for cve in cves)
        else:
            cvemap = dict((cve.sequence, cve_mapper(cve)) for cve in cves)
        bugmap = dict((bug.id, bug) for bug in bugs)
        return [
            (bugmap[bug_id], cvemap[cve_sequence])
            for bug_id, cve_sequence in bugcve_ids
            ]

    def getBugCveCount(self):
        """See ICveSet."""
        return IStore(XRef).find(
            XRef, XRef.from_type == u'bug', XRef.to_type == u'cve').count()
