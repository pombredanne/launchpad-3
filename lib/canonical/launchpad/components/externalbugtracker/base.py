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
    'RequestTracker',
    'UnknownBugTrackerTypeError',
    'UnknownRemoteStatusError',
    'UnparseableBugData',
    'UnparseableBugTrackerVersion',
    'UnsupportedBugTrackerVersion',
    ]

import email
import socket
import urllib
import urllib2
import urlparse

from zope.interface import implements

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.launchpad.interfaces import (
    BugTaskStatus, BugWatchErrorType, IExternalBugTracker,
    UNKNOWN_REMOTE_IMPORTANCE)


# The user agent we send in our requests
LP_USER_AGENT = "Launchpad Bugscraper/0.2 (https://bugs.launchpad.net/)"


#
# Exceptions caught in scripts/checkwatches.py
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
# Exceptions caught locally
#


class BugWatchUpdateWarning(Exception):
    """An exception representing a warning.

    This is a flag exception for the benefit of the OOPS machinery.
    """


class InvalidBugId(BugWatchUpdateWarning):
    """The bug id wasn't in the format the bug tracker expected.

    For example, Bugzilla and debbugs expect the bug id to be an
    integer.
    """


class BugNotFound(BugWatchUpdateWarning):
    """The bug was not found in the external bug tracker."""


class UnknownRemoteStatusError(BugWatchUpdateWarning):
    """Raised when a remote bug's status isn't mapped to a `BugTaskStatus`."""


_exception_to_bugwatcherrortype = [
   (BugTrackerConnectError, BugWatchErrorType.CONNECTION_ERROR),
   (UnparseableBugData, BugWatchErrorType.UNPARSABLE_BUG),
   (UnparseableBugTrackerVersion, BugWatchErrorType.UNPARSABLE_BUG_TRACKER),
   (UnsupportedBugTrackerVersion, BugWatchErrorType.UNSUPPORTED_BUG_TRACKER),
   (UnknownBugTrackerTypeError, BugWatchErrorType.UNSUPPORTED_BUG_TRACKER),
   (socket.timeout, BugWatchErrorType.TIMEOUT)]

def get_bugwatcherrortype_for_error(error):
    """Return the correct `BugWatchErrorType` for a given error."""
    for exc_type, bugwatcherrortype in _exception_to_bugwatcherrortype:
        if isinstance(error, exc_type):
            return bugwatcherrortype
    else:
        return BugWatchErrorType.UNKNOWN


class ExternalBugTracker:
    """Base class for an external bug tracker."""

    implements(IExternalBugTracker)
    batch_size = None
    batch_query_threshold = config.checkwatches.batch_query_threshold
    import_comments = config.checkwatches.import_comments

    def __init__(self, baseurl):
        self.baseurl = baseurl.rstrip('/')

    def urlopen(self, request, data=None):
        return urllib2.urlopen(request, data)

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


class RequestTracker(ExternalBugTracker):
    """`ExternalBugTracker` subclass for handling RT imports."""

    ticket_url = 'REST/1.0/ticket/%s/show'
    batch_url = 'REST/1.0/search/ticket/'
    batch_query_threshold = 1

    @property
    def credentials(self):
        """Return the authentication credentials needed to log in.

        If there are specific credentials for the current RT instance,
        these will be returned. Otherwise the RT default guest
        credentials (username and password of 'guest') will be returned.
        """
        credentials_map = {
            'rt.cpan.org': {'user': 'launchpad@launchpad.net',
                            'pass': 'th4t3'}}

        hostname = urlparse(self.baseurl)[1]
        try:
            return credentials_map[hostname]
        except KeyError:
            return {'user': 'guest', 'pass': 'guest'}

    def _logIn(self, opener):
        """Attempt to log in to the remote RT service.

        :param opener: An instance of urllib2.OpenerDirector
            to be used to connect to the remote server.

        If HTTPError or URLErrors are encountered at any point in this
        process, they will be raised to be caught at the callsite.

        This method is separate from the _opener property so as to allow
        us to test the _opener property without having to connect to a
        remote server.
        """
        # To log in to an RT instance we must pass a username and
        # password to its login form, as a user would from the web.
        opener.open('%s/' % self.baseurl, urllib.urlencode(
            self.credentials))

    @cachedproperty
    def _opener(self):
        """Return a urllib2.OpenerDirector for the remote RT instance.

        An attempt will be made to log in to the remote instance before
        the opener is returned. If logging in is not successful a
        BugTrackerConnectError will be raised
        """
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())

        # Attempt to log in to the remote system. Raise an error if we
        # can't.
        try:
            self._logIn(opener)
        except (urllib2.HTTPError, urllib2.URLError), error:
            raise BugTrackerConnectError('%s/' % self.baseurl,
                "Unable to authenticate with remote RT service: "
                "Could not submit login form: " +
                error.message)

        return opener

    def urlopen(self, request, data=None):
        """Return a handle to a remote resource.

        This method overrides that of `ExternalBugTracker` so that the
        custom URL opener for RequestTracker instances can be used.
        """
        # We create our own opener so as to handle the RT authentication
        # cookies that need to be passed around.
        return self._opener.open(request, data)

    def getRemoteBug(self, bug_id):
        """See `ExternalBugTracker`."""
        ticket_url = self.ticket_url % str(bug_id)
        query_url = '%s/%s' % (self.baseurl, ticket_url)
        try:
            bug_data = self.urlopen(query_url)
        except urllib2.HTTPError, error:
            raise BugTrackerConnectError(ticket_url, error.message)

        # We use the first line of the response to ensure that we've
        # made a successful request.
        firstline = bug_data.readline().strip().split(' ')
        if firstline[1] != '200':
            # If anything goes wrong we raise a BugTrackerConnectError.
            # We included in the error message the status code and error
            # message returned by the server.
            raise BugTrackerConnectError(
                query_url,
                "Unable to retrieve bug %s. The remote server returned the "
                "following error: %s." %
                (str(bug_id), " ".join(firstline[1:])))

        # RT's REST interface returns tickets in RFC822 format, so we
        # can use the email module to parse them.
        bug = email.message_from_string(bug_data.read().strip())
        if bug.get('id') is None:
            return None, None
        else:
            bug_id = bug['id'].replace('ticket/', '')
            return int(bug_id), bug

    def getRemoteBugBatch(self, bug_ids):
        """See `ExternalBugTracker`."""
        # We need to ensure that all the IDs are strings first.
        id_list = [str(id) for id in bug_ids]
        query = "id = " + "OR id = ".join(id_list)

        query_url = '%s/%s' % (self.baseurl, self.batch_url)
        request_params = {'query': query, 'format': 'l'}
        try:
            bug_data = self.urlopen(query_url, urllib.urlencode(
                request_params))
        except urllib2.HTTPError, error:
            raise BugTrackerConnectError(query_url, error.message)

        # We use the first line of the response to ensure that we've
        # made a successful request.
        firstline = bug_data.readline().strip().split(' ')
        if firstline[1] != '200':
            # If anything goes wrong we raise a BugTrackerConnectError.
            # We included in the error message the status code and error
            # message returned by the server.
            bug_id_string = ", ".join([str(bug_id) for bug_id in bug_ids])
            raise BugTrackerConnectError(
                query_url,
                "Unable to retrieve bugs %s. The remote server returned the "
                "following error:  %s." %
                (bug_id_string, " ".join(firstline[1:])))

        # Tickets returned in RT multiline format are separated by lines
        # containing only --\n.
        tickets = bug_data.read().split("--\n")
        bugs = {}
        for ticket in tickets:
            ticket = ticket.strip()

            # RT's REST interface returns tickets in RFC822 format, so we
            # can use the email module to parse them.
            bug = email.message_from_string(ticket)

            # We only bother adding the bug to the bugs dict if we
            # actually have some data worth adding.
            if bug.get('id') is not None:
                bug_id = bug['id'].replace('ticket/', '')
                bugs[int(bug_id)] = bug

        return bugs

    def getRemoteStatus(self, bug_id):
        """Return the remote status of a given bug.

        See `ExternalBugTracker`.
        """
        try:
            bug_id = int(bug_id)
        except ValueError:
            raise InvalidBugId(
                "RequestTracker bug ids must be integers (was passed %r)"
                % bug_id)

        if bug_id not in self.bugs:
            raise BugNotFound(bug_id)

        return self.bugs[bug_id]['status']

    def getRemoteImportance(self, bug_id):
        """See `IExternalBugTracker`."""
        pass

    def convertRemoteImportance(self, remote_importance):
        """See `IExternalBugTracker`."""
        return UNKNOWN_REMOTE_IMPORTANCE

    def convertRemoteStatus(self, remote_status):
        """Convert an RT status into a Launchpad BugTaskStatus."""
        status_map = {
            'new': BugTaskStatus.NEW,
            'open': BugTaskStatus.CONFIRMED,
            'stalled': BugTaskStatus.CONFIRMED,
            'rejected': BugTaskStatus.INVALID,
            'resolved': BugTaskStatus.FIXRELEASED,}

        try:
            remote_status = remote_status.lower()
            return status_map[remote_status]
        except KeyError:
            raise UnknownRemoteStatusError()

