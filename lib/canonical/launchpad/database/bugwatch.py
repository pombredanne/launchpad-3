# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BugWatch', 'BugWatchSet', 'BugWatchFactory']

import re

from zope.interface import implements
from zope.exceptions import NotFoundError
from zope.component import getUtility

# SQL imports
from sqlobject import ForeignKey, StringCol, SQLObjectNotFound, MultipleJoin

from canonical.lp.dbschema import BugTrackerType

from canonical.database.sqlbase import SQLBase, flush_database_updates
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.interfaces import (IBugWatch, IBugWatchSet,
    IBugTrackerSet)
from canonical.launchpad.database.bugset import BugSetBase

bugzillaref = re.compile(r'(https?://.+/)show_bug.cgi.+id=(\d+).*')
roundupref = re.compile(r'(https?://.+/)issue(\d+).*')

class BugWatch(SQLBase):
    """A watch, which links a Malone bug to a bug in a foreign bugtracker"""
    implements(IBugWatch)
    _table = 'BugWatch'
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    bugtracker = ForeignKey(dbName='bugtracker',
                foreignKey='BugTracker', notNull=True)
    remotebug = StringCol(notNull=True)
    remotestatus = StringCol(notNull=False, default=None)
    lastchanged = UtcDateTimeCol(notNull=False, default=None)
    lastchecked = UtcDateTimeCol(notNull=False, default=None)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)

    # useful joins
    bugtasks = MultipleJoin('BugTask', joinColumn='bugwatch',
        orderBy=['-datecreated'])

    @property
    def title(self):
        """See canonical.launchpad.interfaces.IBugWatch."""
        return "%s #%s" % (self.bugtracker.title, self.remotebug)

    @property
    def url(self):
        """See canonical.launchpad.interfaces.IBugWatch."""
        url_formats = {
            # XXX 20050712 kiko: slash-suffixing the bugtracker baseurl
            # protects us from the bugtracker baseurl not ending in
            # slashes -- should we instead ensure when it is entered?
            # Filed bug 1434.
            BugTrackerType.BUGZILLA: '%s/show_bug.cgi?id=%s',
            BugTrackerType.DEBBUGS:  '%s/cgi-bin/bugreport.cgi?bug=%s',
            BugTrackerType.ROUNDUP:  '%s/issue%s'
        }
        bt = self.bugtracker.bugtrackertype
        if not url_formats.has_key(bt):
            raise AssertionError('Unknown bug tracker type %s' % bt)
        return url_formats[bt] % (self.bugtracker.baseurl, self.remotebug)

    @property
    def needscheck(self):
        """See canonical.launchpad.interfaces.IBugWatch."""
        return True

class BugWatchSet(BugSetBase):
    """A set for BugWatch"""

    implements(IBugWatchSet)
    table = BugWatch

    def __init__(self, bug=None):
        BugSetBase.__init__(self, bug)
        self.title = 'A Set of Bug Watches'

    def get(self, watch_id):
        """See canonical.launchpad.interfaces.IBugWatchSet."""
        try:
            return BugWatch.get(watch_id)
        except SQLObjectNotFound:
            raise NotFoundError, watch_id

    def _find_watches(self, pattern, trackertype, text, bug, owner):
        """Find the watches in a piece of text, based on a given pattern and
        tracker type."""
        newwatches = []
        # let's look for matching entries
        matches = pattern.findall(text)
        if len(matches) == 0:
            return []
        for match in matches:
            # let's see if we already know about this bugtracker
            bugtrackerset = getUtility(IBugTrackerSet)
            baseurl = match[0]
            remotebug = match[1]
            # make sure we have a bugtracker
            bugtracker = bugtrackerset.ensureBugTracker(baseurl, owner,
                trackertype)
            # see if there is a bugwatch for this remote bug on this bug
            bugwatch = None
            for watch in bug.watches:
                if (watch.bugtracker == bugtracker and
                    watch.remotebug == remotebug):
                    bugwatch = watch
                    break
            if bugwatch is None:
                bugwatch = BugWatch(bugtracker=bugtracker, bug=bug,
                    remotebug=remotebug, owner=owner)
                newwatches.append(bugwatch)
                if len(newwatches) > 0:
                    flush_database_updates()
        return newwatches

    def fromText(self, text, bug, owner):
        """See IBugTrackerSet.fromText."""
        # XXX sabdfl this should also look for sourceforge
        watches = set([])
        for pattern, trackertype in [
            (bugzillaref, BugTrackerType.BUGZILLA),
            (roundupref, BugTrackerType.ROUNDUP),]:
            watches = watches.union(self._find_watches(pattern,
                trackertype, text, bug, owner))
        return sorted(watches, key=lambda a: (a.bugtracker.name,
            a.remotebug))

    def fromMessage(self, message, bug):
        """See IBugWatchSet."""
        watches = set()
        for messagechunk in message:
            if messagechunk.blob is not None:
                # we don't process attachments
                continue
            elif messagechunk.content is not None:
                # look for potential BugWatch URL's and create the trackers
                # and watches as needed
                watches = watches.union(self.fromText(messagechunk.content,
                    bug, message.owner))
            else:
                raise AssertionError('MessageChunk without content or blob.')
        return sorted(watches, key=lambda a: a.remotebug)


def BugWatchFactory(context, **kw):
    bug = context.context.bug
    return BugWatch(
        bug=bug, owner=context.request.principal.id, datecreated=UTC_NOW,
        lastchanged=UTC_NOW, lastchecked=UTC_NOW, **kw)

