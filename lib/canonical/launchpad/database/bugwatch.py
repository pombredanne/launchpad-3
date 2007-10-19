# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugWatch', 'BugWatchSet']

import re
import urllib
from urlparse import urlunsplit

from zope.event import notify
from zope.interface import implements, providedBy
from zope.component import getUtility

# SQL imports
from sqlobject import ForeignKey, StringCol, SQLObjectNotFound, SQLMultipleJoin

from canonical.lp.dbschema import BugTrackerType, BugTaskImportance

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.event import SQLObjectModifiedEvent

from canonical.launchpad.webapp import urlappend, urlsplit
from canonical.launchpad.webapp.snapshot import Snapshot
from canonical.launchpad.webapp.uri import find_uris_in_text

from canonical.launchpad.interfaces import (
    IBugWatch, IBugWatchSet, IBugTrackerSet, ILaunchpadCelebrities,
    NoBugTrackerFound, NotFoundError, UnrecognizedBugTrackerURL)
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
            BugTrackerType.BUGZILLA:    'show_bug.cgi?id=%s',
            BugTrackerType.TRAC:        'ticket/%s',
            BugTrackerType.DEBBUGS:     'cgi-bin/bugreport.cgi?bug=%s',
            BugTrackerType.ROUNDUP:     'issue%s',
            BugTrackerType.SOURCEFORGE: 'support/tracker.php?aid=%s',
            BugTrackerType.MANTIS:      'view.php?id=%s',
        }
        bt = self.bugtracker.bugtrackertype
        if not url_formats.has_key(bt):
            raise AssertionError('Unknown bug tracker type %s' % bt)
        return urlappend(self.bugtracker.baseurl,
                         url_formats[bt] % self.remotebug)

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
            linked_bugtask.transitionToStatus(
                malone_status,
                getUtility(ILaunchpadCelebrities).bug_watch_updater)
            # We don't yet support updating the following values.
            linked_bugtask.importance = BugTaskImportance.UNKNOWN
            linked_bugtask.transitionToAssignee(None)
            if linked_bugtask.status != old_bugtask.status:
                event = SQLObjectModifiedEvent(
                    linked_bugtask, old_bugtask, ['status'],
                    user=getUtility(ILaunchpadCelebrities).bug_watch_updater)
                notify(event)

    def destroySelf(self):
        """See IBugWatch."""
        assert self.bugtasks.count() == 0, "Can't delete linked bug watches"
        SQLBase.destroySelf(self)


class BugWatchSet(BugSetBase):
    """A set for BugWatch"""

    implements(IBugWatchSet)
    table = BugWatch

    def __init__(self, bug=None):
        BugSetBase.__init__(self, bug)
        self.title = 'A set of bug watches'
        self.bugtracker_parse_functions = {
            BugTrackerType.BUGZILLA: self.parseBugzillaURL,
            BugTrackerType.DEBBUGS:  self.parseDebbugsURL,
            BugTrackerType.ROUNDUP: self.parseRoundupURL,
            BugTrackerType.SOURCEFORGE: self.parseSourceForgeURL,
            BugTrackerType.TRAC: self.parseTracURL,
            BugTrackerType.MANTIS: self.parseMantisURL,
        }

    def get(self, watch_id):
        """See canonical.launchpad.interfaces.IBugWatchSet."""
        try:
            return BugWatch.get(watch_id)
        except SQLObjectNotFound:
            raise NotFoundError, watch_id

    def search(self):
        return BugWatch.select()

    def fromText(self, text, bug, owner):
        """See IBugTrackerSet.fromText."""
        newwatches = []
        # Let's find all the URLs and see if they are bug references.
        matches = list(find_uris_in_text(text))
        if len(matches) == 0:
            return []

        for url in matches:
            try:
                bugtracker, remotebug = self.extractBugTrackerAndBug(str(url))
            except NoBugTrackerFound, error:
                bugtracker = getUtility(IBugTrackerSet).ensureBugTracker(
                    error.base_url, owner, error.bugtracker_type)
                remotebug = error.remote_bug
            except UnrecognizedBugTrackerURL:
                # It doesn't look like a bug URL, so simply ignore it.
                continue

            if bug.getBugWatch(bugtracker, remotebug) is None:
                # This bug doesn't have such a bug watch, let's create
                # one.
                bugwatch = BugWatch(
                    bugtracker=bugtracker, bug=bug, remotebug=remotebug,
                    owner=owner)
                newwatches.append(bugwatch)

        return newwatches

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

    def parseBugzillaURL(self, scheme, host, path, query):
        """Extract the Bugzilla base URL and bug ID."""
        bug_page = 'show_bug.cgi'
        if not path.endswith(bug_page):
            return None
        if query.get('id'):
            # This is a Bugzilla URL.
            remote_bug = query['id']
        elif query.get('issue'):
            # This is a Issuezilla URL.
            remote_bug = query['issue']
        else:
            return None
        base_path = path[:-len(bug_page)]
        base_url = urlunsplit((scheme, host, base_path, '', ''))
        return base_url, remote_bug

    def parseMantisURL(self, scheme, host, path, query):
        """Extract the Mantis base URL and bug ID."""
        bug_page = 'view.php'
        if not path.endswith(bug_page):
            return None
        if query.get('id'):
            remote_bug = query['id']
        else:
            return None
        base_path = path[:-len(bug_page)]
        base_url = urlunsplit((scheme, host, base_path, '', ''))
        return base_url, remote_bug

    def parseDebbugsURL(self, scheme, host, path, query):
        """Extract the Debbugs base URL and bug ID."""
        bug_page = 'cgi-bin/bugreport.cgi'
        remote_bug = None

        if path.endswith(bug_page):
            remote_bug = query.get('bug')
            base_path = path[:-len(bug_page)]
        elif host == "bugs.debian.org":
            # Oy, what a hack. debian's tracker allows you to access
            # bugs by saying http://bugs.debian.org/400848, so support
            # that shorthand. The reason we need to do this special
            # check here is because otherwise /any/ URL that ends with
            # "/number" will appear to match a debbugs URL.
            remote_bug = path.split("/")[-1]
            base_path = ''
        else:
            return None

        if remote_bug is None or not remote_bug.isdigit():
            return None

        base_url = urlunsplit((scheme, host, base_path, '', ''))
        return base_url, remote_bug

    def parseRoundupURL(self, scheme, host, path, query):
        """Extract the RoundUp base URL and bug ID."""
        match = re.match(r'(.*/)issue(\d+)', path)
        if not match:
            return None
        base_path = match.group(1)
        remote_bug = match.group(2)

        base_url = urlunsplit((scheme, host, base_path, '', ''))
        return base_url, remote_bug

    def parseTracURL(self, scheme, host, path, query):
        """Extract the Trac base URL and bug ID."""
        match = re.match(r'(.*/)ticket/(\d+)', path)
        if not match:
            return None
        base_path = match.group(1)
        remote_bug = match.group(2)

        base_url = urlunsplit((scheme, host, base_path, '', ''))
        return base_url, remote_bug

    def parseSourceForgeURL(self, scheme, host, path, query):
        """Extract the SourceForge base URL and bug ID.

        Only the path is considered. If it looks like a SF URL, we
        return the global SF instance. This makes it possible for people
        to use alternative host names, like sf.net.
        """
        if (not path.startswith('/support/tracker.php') and
            not path.startswith('/tracker/index.php')):
            return None
        if not query.get('aid'):
            return None

        remote_bug = query['aid']
        # There's only one global SF instance registered in Launchpad.
        sf_tracker = getUtility(ILaunchpadCelebrities).sourceforge_tracker

        return sf_tracker.baseurl, remote_bug

    def extractBugTrackerAndBug(self, url):
        """See IBugWatchSet."""
        for trackertype, parse_func in self.bugtracker_parse_functions.items():
            scheme, host, path, query_string, frag = urlsplit(url)
            query = {}
            for query_part in query_string.split('&'):
                key, value = urllib.splitvalue(query_part)
                query[key] = value

            bugtracker_data = parse_func(scheme, host, path, query)
            if not bugtracker_data:
                continue
            base_url, remote_bug = bugtracker_data
            bugtrackerset = getUtility(IBugTrackerSet)
            # Check whether we have a registered bug tracker already.
            bugtracker = bugtrackerset.queryByBaseURL(base_url)

            if bugtracker is not None:
                return bugtracker, remote_bug
            else:
                raise NoBugTrackerFound(base_url, remote_bug, trackertype)

        raise UnrecognizedBugTrackerURL(url)
