# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BugWatch', 'BugWatchSet']

import re
import cgi
import urllib
from urlparse import urlunsplit

from zope.event import notify
from zope.interface import implements, providedBy
from zope.component import getUtility

# SQL imports
from sqlobject import ForeignKey, StringCol, SQLObjectNotFound, SQLMultipleJoin

from canonical.lp.dbschema import BugTrackerType, BugTaskImportance

from canonical.database.sqlbase import SQLBase, flush_database_updates
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.event import SQLObjectModifiedEvent

from canonical.launchpad.webapp import urlappend, urlsplit
from canonical.launchpad.webapp.snapshot import Snapshot

from canonical.launchpad.interfaces import (
    IBugWatch, IBugWatchSet, IBugTrackerSet, NoBugTrackerFound, NotFoundError)
from canonical.launchpad.database.bugset import BugSetBase


class BugWatch(SQLBase):
    """See canonical.launchpad.interfaces.IBugWatch."""
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
    bugtasks = SQLMultipleJoin('BugTask', joinColumn='bugwatch',
        orderBy=['-datecreated'])

    @property
    def title(self):
        """See canonical.launchpad.interfaces.IBugWatch."""
        return "%s #%s" % (self.bugtracker.title, self.remotebug)

    @property
    def url(self):
        """See canonical.launchpad.interfaces.IBugWatch."""
        url_formats = {
            BugTrackerType.BUGZILLA: 'show_bug.cgi?id=%s',
            BugTrackerType.TRAC:     'ticket/%s',
            BugTrackerType.DEBBUGS:  'cgi-bin/bugreport.cgi?bug=%s',
            BugTrackerType.ROUNDUP:  'issue%s'
        }
        bt = self.bugtracker.bugtrackertype
        if bt == BugTrackerType.SOURCEFORGE:
            return self._sf_url()
        elif not url_formats.has_key(bt):
            raise AssertionError('Unknown bug tracker type %s' % bt)
        return urlappend(self.bugtracker.baseurl,
                         url_formats[bt] % self.remotebug)

    def _sf_url(self):
        # XXX: validate that the bugtracker URL has atid and group_id in
        # it.
        #
        # Sourceforce has a pretty nasty URL model, with two codes that
        # specify what project are looking at. This code disassembles
        # it, sets the bug number and then reassembles it again.
        # http://sourceforge.net/tracker/?atid=737291
        #                                &group_id=136955
        #                                &func=detail
        #                                &aid=1337833
        method, base, path, query, frag = urlsplit(self.bugtracker.baseurl)
        params = cgi.parse_qs(query)
        params['func'] = "detail"
        params['aid'] = self.remotebug
        query = urllib.urlencode(params, doseq=True)
        return urlunsplit((method, base, path, query, frag))

    @property
    def needscheck(self):
        """See canonical.launchpad.interfaces.IBugWatch."""
        return True

    def updateStatus(self, remote_status, malone_status):
        """See IBugWatch."""
        if self.remotestatus != remote_status:
            self.remotestatus = remote_status
            self.lastchanged = UTC_NOW
            # Sync the object in order to convert the UTC_NOW sql
            # constant to a datetime value.
            self.sync()
        for linked_bugtask in self.bugtasks:
            old_bugtask = Snapshot(
                linked_bugtask, providing=providedBy(linked_bugtask))
            linked_bugtask.transitionToStatus(malone_status)
            # We don't yet support updating the following values.
            linked_bugtask.importance = BugTaskImportance.UNKNOWN
            linked_bugtask.transitionToAssignee(None)
            if linked_bugtask.status != old_bugtask.status:
                event = SQLObjectModifiedEvent(
                    linked_bugtask, old_bugtask, ['status'])
                notify(event)


class BugWatchSet(BugSetBase):
    """A set for BugWatch"""

    implements(IBugWatchSet)
    table = BugWatch

    def __init__(self, bug=None):
        BugSetBase.__init__(self, bug)
        self.title = 'A set of bug watches'
        self.bugtracker_references = {
            BugTrackerType.BUGZILLA: re.compile(
                r'(https?://.+/)show_bug.cgi.+id=(\d+).*'),
            BugTrackerType.ROUNDUP: re.compile(r'(https?://.+/)issue(\d+).*'),
            BugTrackerType.TRAC: re.compile(r'(https?://.+/)ticket/(\d+)'),
            }

    def get(self, watch_id):
        """See canonical.launchpad.interfaces.IBugWatchSet."""
        try:
            return BugWatch.get(watch_id)
        except SQLObjectNotFound:
            raise NotFoundError, watch_id

    def search(self):
        return BugWatch.select()

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
        watches = set([])
        for trackertype, pattern in self.bugtracker_references.items():
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

    def createBugWatch(self, bug, owner, bugtracker, remotebug):
        """See canonical.launchpad.interfaces.IBugWatchSet."""
        return BugWatch(
            bug=bug, owner=owner, datecreated=UTC_NOW, lastchanged=UTC_NOW, 
            bugtracker=bugtracker, remotebug=remotebug)

    def getBugTrackerAndBug(self, url):
        """See IBugWatchSet."""
        for trackertype, pattern in self.bugtracker_references.items():
            match = pattern.match(url)
            if not match:
                continue

            bugtrackerset = getUtility(IBugTrackerSet)
            baseurl = match.group(1)
            remotebug = match.group(2)
            # Check whether we have a registered bug tracker already.
            bugtracker = bugtrackerset.queryByBaseURL(baseurl)
            if bugtracker is None and baseurl.endswith('/'):
                bugtracker = bugtrackerset.queryByBaseURL(baseurl[:-1])

            if bugtracker is not None:
                return bugtracker, remotebug
            else:
                raise NoBugTrackerFound(baseurl, remotebug, trackertype)
        return None, None
