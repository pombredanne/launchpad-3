# Copyright 2007 Canonical Ltd.  All rights reserved.

"""External bugtrackers."""

__metaclass__ = type
__all__ = [
    'BugNotFound',
    'BugTrackerConnectError',
    'BugWatchUpdateError',
    'BugWatchUpdateWarning',
    'ExternalBugTracker',
    'InvalidBugId',
    'PrivateRemoteBug',
    'UnknownBugTrackerTypeError',
    'UnknownRemoteStatusError',
    'UnparseableBugData',
    'UnparseableBugTrackerVersion',
    'UnsupportedBugTrackerVersion',
    ]


import urllib
import urllib2

from zope.interface import implements

from canonical.config import config
from canonical.launchpad.interfaces.externalbugtracker import (
    IExternalBugTracker)


# The user agent we send in our requests
LP_USER_AGENT = "Launchpad Bugscraper/0.2 (https://bugs.launchpad.net/)"


#
# Errors.
#


class BugWatchUpdateError(Exception):
    """Base exception for when we fail to update watches for a tracker."""


class UnknownBugTrackerTypeError(BugWatchUpdateError):
    """Exception class to catch systems we don't have a class for yet."""

    def __init__(self, bugtrackertypename, bugtrackername):
        BugWatchUpdateError.__init__(self)
        self.bugtrackertypename = bugtrackertypename
        self.bugtrackername = bugtrackername

    def __str__(self):
        return self.bugtrackertypename


class UnsupportedBugTrackerVersion(BugWatchUpdateError):
    """The bug tracker version is not supported."""


class UnparseableBugTrackerVersion(BugWatchUpdateError):
    """The bug tracker version could not be parsed."""


class UnparseableBugData(BugWatchUpdateError):
    """The bug tracker provided bug data that could not be parsed."""


class BugTrackerConnectError(BugWatchUpdateError):
    """Exception class to catch misc errors contacting a bugtracker."""

    def __init__(self, url, error):
        BugWatchUpdateError.__init__(self)
        self.url = url
        self.error = str(error)

    def __str__(self):
        return "%s: %s" % (self.url, self.error)


#
# Warnings.
#


class BugWatchUpdateWarning(Exception):
    """An exception representing a warning.

    This is a flag exception for the benefit of the OOPS machinery.
    """
    def __init__(self, message, *args):
        # Require a message.
        Exception.__init__(self, message, *args)


class InvalidBugId(BugWatchUpdateWarning):
    """The bug id wasn't in the format the bug tracker expected.

    For example, Bugzilla and debbugs expect the bug id to be an
    integer.
    """


class BugNotFound(BugWatchUpdateWarning):
    """The bug was not found in the external bug tracker."""


class UnknownRemoteStatusError(BugWatchUpdateWarning):
    """Raised when a remote bug's status isn't mapped to a `BugTaskStatus`."""


class PrivateRemoteBug(BugWatchUpdateWarning):
    """Raised when a bug is marked private on the remote bugtracker."""


#
# Everything else.
#

class ExternalBugTracker:
    """Base class for an external bug tracker."""

    implements(IExternalBugTracker)

    batch_size = 100
    batch_query_threshold = config.checkwatches.batch_query_threshold
    comment_template = 'default_remotecomment_template.txt'
    sync_comments = config.checkwatches.sync_comments

    def __init__(self, baseurl):
        self.baseurl = baseurl.rstrip('/')

    def urlopen(self, request, data=None):
        return urllib2.urlopen(request, data)

    def getExternalBugTrackerToUse(self):
        """See `IExternalBugTracker`."""
        return self

    def getCurrentDBTime(self):
        """See `IExternalBugTracker`."""
        # Returning None means that we don't know that the time is,
        # which is a good default.
        return None

    def getModifiedRemoteBugs(self, bug_ids, last_accessed):
        """See `IExternalBugTracker`."""
        # Return all bugs, since we don't know which have been modified.
        return list(bug_ids)

    def initializeRemoteBugDB(self, bug_ids):
        """See `IExternalBugTracker`."""
        self.bugs = {}
        if len(bug_ids) > self.batch_query_threshold:
            self.bugs = self.getRemoteBugBatch(bug_ids)
        else:
            # XXX: 2007-08-24 Graham Binns
            #      It might be better to do this synchronously for the sake of
            #      handling timeouts nicely. For now, though, we do it
            #      sequentially for the sake of easing complexity and making
            #      testing easier.
            for bug_id in bug_ids:
                bug_id, remote_bug = self.getRemoteBug(bug_id)

                if bug_id is not None:
                    self.bugs[bug_id] = remote_bug

    def getRemoteBug(self, bug_id):
        """Retrieve and return a single bug from the remote database.

        The bug is returned as a tuple in the form (id, bug). This ensures
        that bug ids are formatted correctly for the current
        ExternalBugTracker. If no data can be found for bug_id, (None,
        None) will be returned.

        A BugTrackerConnectError will be raised if anything goes wrong.
        """
        raise NotImplementedError(self.getRemoteBug)

    def getRemoteBugBatch(self, bug_ids):
        """Retrieve and return a set of bugs from the remote database.

        A BugTrackerConnectError will be raised if anything goes wrong.
        """
        raise NotImplementedError(self.getRemoteBugBatch)

    def getRemoteImportance(self, bug_id):
        """Return the remote importance for the given bug id.

        Raise BugNotFound if the bug can't be found.
        Raise InvalidBugId if the bug id has an unexpected format.
        Raise UnparseableBugData if the bug data cannot be parsed.
        """
        # This method should be overridden by subclasses, so we raise a
        # NotImplementedError if this version of it gets called for some
        # reason.
        raise NotImplementedError(self.getRemoteImportance)

    def getRemoteStatus(self, bug_id):
        """Return the remote status for the given bug id.

        Raise BugNotFound if the bug can't be found.
        Raise InvalidBugId if the bug id has an unexpected format.
        """
        raise NotImplementedError(self.getRemoteStatus)

    def _fetchPage(self, page):
        """Fetch a page from the remote server.

        A BugTrackerConnectError will be raised if anything goes wrong.
        """
        try:
            return self.urlopen(page)
        except (urllib2.HTTPError, urllib2.URLError), val:
            raise BugTrackerConnectError(self.baseurl, val)

    def _getPage(self, page):
        """GET the specified page on the remote HTTP server."""
        # For some reason, bugs.kde.org doesn't allow the regular urllib
        # user-agent string (Python-urllib/2.x) to access their
        # bugzilla, so we send our own instead.
        request = urllib2.Request("%s/%s" % (self.baseurl, page),
                                  headers={'User-agent': LP_USER_AGENT})
        return self._fetchPage(request).read()

    def _postPage(self, page, form):
        """POST to the specified page.

        :form: is a dict of form variables being POSTed.
        """
        url = "%s/%s" % (self.baseurl, page)
        post_data = urllib.urlencode(form)
        request = urllib2.Request(url, headers={'User-agent': LP_USER_AGENT})
        url = self.urlopen(request, data=post_data)
        page_contents = url.read()
        return page_contents

