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
    'Roundup',
    'SourceForge',
    'UnknownBugTrackerTypeError',
    'UnknownRemoteStatusError',
    'UnparseableBugData',
    'UnparseableBugTrackerVersion',
    'UnsupportedBugTrackerVersion',
    ]

import csv
import email
import re
import socket
import urllib
import urllib2
import urlparse

from BeautifulSoup import BeautifulSoup
from zope.interface import implements

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.launchpad.interfaces import (
    BugTaskImportance, BugTaskStatus, BugWatchErrorType,
    IExternalBugTracker, UNKNOWN_REMOTE_IMPORTANCE)


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


class Roundup(ExternalBugTracker):
    """An ExternalBugTracker descendant for handling Roundup bug trackers."""

    def __init__(self, baseurl):
        """Create a new Roundup instance.

        :bugtracker: The Roundup bugtracker.

        If the bug tracker's baseurl is one which points to
        bugs.python.org, the behaviour of the Roundup bugtracker will be
        different from that which it exhibits to every other Roundup bug
        tracker, since the Python Roundup instance is very specific to
        Python and in fact behaves rather more like SourceForge than
        Roundup.
        """
        super(Roundup, self).__init__(baseurl)

        if self.isPython():
            # The bug export URLs differ only from the base Roundup ones
            # insofar as they need to include the resolution column in
            # order for us to be able to successfully export it.
            self.single_bug_export_url = (
                "issue?@action=export_csv&@columns=title,id,activity,"
                "status,resolution&@sort=id&@group=priority&@filter=id"
                "&@pagesize=50&@startwith=0&id=%i")
            self.batch_bug_export_url = (
                "issue?@action=export_csv&@columns=title,id,activity,"
                "status,resolution&@sort=activity&@group=priority"
                "&@pagesize=50&@startwith=0")
        else:
            # XXX: 2007-08-29 Graham Binns
            #      I really don't like these URLs but Roundup seems to
            #      be very sensitive to changing them. These are the
            #      only ones that I can find that work consistently on
            #      all the roundup instances I can find to test them
            #      against, but I think that refining these should be
            #      looked into at some point.
            self.single_bug_export_url = (
                "issue?@action=export_csv&@columns=title,id,activity,"
                "status&@sort=id&@group=priority&@filter=id"
                "&@pagesize=50&@startwith=0&id=%i")
            self.batch_bug_export_url = (
                "issue?@action=export_csv&@columns=title,id,activity,"
                "status&@sort=activity&@group=priority&@pagesize=50"
                "&@startwith=0")

    @property
    def status_map(self):
        """Return the remote status -> BugTaskStatus mapping for the
        current remote bug tracker.
        """
        if self.isPython():
            # Python bugtracker statuses come in two parts: status and
            # resolution. Both of these are integer values. We can look
            # them up in the form status_map[status][resolution]
            return {
                # Open issues (status=1). We also use this as a fallback
                # for statuses 2 and 3, for which the mappings are
                # different only in a few instances.
                1: {
                    None: BugTaskStatus.NEW,       # No resolution
                    1: BugTaskStatus.CONFIRMED,    # Resolution: accepted
                    2: BugTaskStatus.CONFIRMED,    # Resolution: duplicate
                    3: BugTaskStatus.FIXCOMMITTED, # Resolution: fixed
                    4: BugTaskStatus.INVALID,      # Resolution: invalid
                    5: BugTaskStatus.CONFIRMED,    # Resolution: later
                    6: BugTaskStatus.INVALID,      # Resolution: out-of-date
                    7: BugTaskStatus.CONFIRMED,    # Resolution: postponed
                    8: BugTaskStatus.WONTFIX,      # Resolution: rejected
                    9: BugTaskStatus.CONFIRMED,    # Resolution: remind
                    10: BugTaskStatus.WONTFIX,     # Resolution: wontfix
                    11: BugTaskStatus.INVALID},    # Resolution: works for me

                # Closed issues (status=2)
                2: {
                    None: BugTaskStatus.WONTFIX,   # No resolution
                    1: BugTaskStatus.FIXCOMMITTED, # Resolution: accepted
                    3: BugTaskStatus.FIXRELEASED,  # Resolution: fixed
                    7: BugTaskStatus.WONTFIX},     # Resolution: postponed

                # Pending issues (status=3)
                3: {
                    None: BugTaskStatus.INCOMPLETE,# No resolution
                    7: BugTaskStatus.WONTFIX},     # Resolution: postponed
            }

        else:
            # Our mapping of Roundup => Launchpad statuses.  Roundup
            # statuses are integer-only and highly configurable.
            # Therefore we map the statuses available by default so that
            # they can be overridden by subclassing the Roundup class.
            return {
                1: BugTaskStatus.NEW,          # Roundup status 'unread'
                2: BugTaskStatus.CONFIRMED,    # Roundup status 'deferred'
                3: BugTaskStatus.INCOMPLETE,   # Roundup status 'chatting'
                4: BugTaskStatus.INCOMPLETE,   # Roundup status 'need-eg'
                5: BugTaskStatus.INPROGRESS,   # Roundup status 'in-progress'
                6: BugTaskStatus.INPROGRESS,   # Roundup status 'testing'
                7: BugTaskStatus.FIXCOMMITTED, # Roundup status 'done-cbb'
                8: BugTaskStatus.FIXRELEASED,} # Roundup status 'resolved'

    def isPython(self):
        """Return True if the remote bug tracker is at bugs.python.org.

        Return False otherwise.
        """
        return 'bugs.python.org' in self.baseurl

    def _getBug(self, bug_id):
        """Return the bug with the ID bug_id from the internal bug list.

        :param bug_id: The ID of the remote bug to return.
        :type bug_id: int

        BugNotFound will be raised if the bug does not exist.
        InvalidBugId will be raised if bug_id is not of a valid format.
        """
        try:
            bug_id = int(bug_id)
        except ValueError:
            raise InvalidBugId(
                "bug_id must be convertible an integer: %s." % str(bug_id))

        try:
            return self.bugs[bug_id]
        except KeyError:
            raise BugNotFound(bug_id)

    def getRemoteBug(self, bug_id):
        """See `ExternalBugTracker`."""
        bug_id = int(bug_id)
        query_url = '%s/%s' % (
            self.baseurl, self.single_bug_export_url % bug_id)
        reader = csv.DictReader(self._fetchPage(query_url))
        return (bug_id, reader.next())

    def getRemoteBugBatch(self, bug_ids):
        """See `ExternalBugTracker`"""
        # XXX: 2007-08-28 Graham Binns
        #      At present, Roundup does not support exporting only a
        #      subset of bug ids as a batch (launchpad bug 135317). When
        #      this bug is fixed we need to change this method to only
        #      export the bug ids needed rather than hitting the remote
        #      tracker for a potentially massive number of bugs.
        query_url = '%s/%s' % (self.baseurl, self.batch_bug_export_url)
        remote_bugs = csv.DictReader(self._fetchPage(query_url))
        bugs = {}
        for remote_bug in remote_bugs:
            # We're only interested in the bug if it's one of the ones in
            # bug_ids.
            if remote_bug['id'] not in bug_ids:
                continue

            bugs[int(remote_bug['id'])] = remote_bug

        return bugs

    def getRemoteImportance(self, bug_id):
        """See `ExternalBugTracker`.

        This method is implemented here as a stub to ensure that
        existing functionality is preserved. As a result,
        UNKNOWN_REMOTE_IMPORTANCE will always be returned.
        """
        return UNKNOWN_REMOTE_IMPORTANCE

    def getRemoteStatus(self, bug_id):
        """See `ExternalBugTracker`."""
        remote_bug = self._getBug(bug_id)
        if self.isPython():
            # A remote bug must define a status and a resolution, even
            # if that resolution is 'None', otherwise we can't
            # accurately assign a BugTaskStatus to it.
            try:
                status = remote_bug['status']
                resolution = remote_bug['resolution']
            except KeyError:
                raise UnparseableBugData(
                    "Remote bug %s does not define both a status and a "
                    "resolution." % bug_id)

            # Remote status is stored as a string, so for sanity's sake
            # we return an easily-parseable string.
            return '%s:%s' % (status, resolution)

        else:
            try:
                return remote_bug['status']
            except KeyError:
                raise UnparseableBugData(
                    "Remote bug %s does not define a status.")

    def convertRemoteImportance(self, remote_importance):
        """See `ExternalBugTracker`.

        This method is implemented here as a stub to ensure that
        existing functionality is preserved. As a result,
        BugTaskImportance.UNKNOWN will always be returned.
        """
        return BugTaskImportance.UNKNOWN

    def convertRemoteStatus(self, remote_status):
        """See `IExternalBugTracker`."""
        if self.isPython():
            return self._convertPythonRemoteStatus(remote_status)
        else:
            try:
                return self.status_map[int(remote_status)]
            except (KeyError, ValueError):
                raise UnknownRemoteStatusError()

    def _convertPythonRemoteStatus(self, remote_status):
        """Convert a Python bug status into a BugTaskStatus.

        :remote_status: A bugs.python.org status string in the form
            '<status>:<resolution>', where status is an integer and
            resolution is an integer or None. An AssertionError will be
            raised if these conditions are not met.
        """
        try:
            status, resolution = remote_status.split(':')
        except ValueError:
            raise AssertionError(
                "The remote status must be a string of the form "
                "<status>:<resolution>.")

        try:
            status = int(status)

            # If we can't find the status in our status map we can give
            # up now.
            if not self.status_map.has_key(status):
                raise UnknownRemoteStatusError()
        except ValueError:
            raise AssertionError("The remote status must be an integer.")

        if resolution.isdigit():
            resolution = int(resolution)
        elif resolution == 'None':
            resolution = None
        else:
            raise AssertionError(
                "The resolution must be an integer or 'None'.")

        # We look the status/resolution mapping up first in the status's
        # dict then in the dict for status #1 (open) if we can't find
        # it.
        if self.status_map[status].has_key(resolution):
            return self.status_map[status][resolution]
        elif self.status_map[1].has_key(resolution):
            return self.status_map[1][resolution]
        else:
            raise UnknownRemoteStatusError()


class SourceForge(ExternalBugTracker):
    """An ExternalBugTracker for SourceForge bugs."""

    # We only allow ourselves to update one SourceForge bug at a time to
    # avoid getting clobbered by SourceForge's rate limiting code.
    export_url = 'support/tracker.php?aid=%s'
    batch_size = 1

    def initializeRemoteBugDB(self, bug_ids):
        """See `ExternalBugTracker`.

        We override this method because SourceForge does not provide a
        nice way for us to export bug statuses en masse. Instead, we
        resort to screen-scraping on a per-bug basis. Therefore the
        usual choice of batch vs. single export does not apply here and
        we only perform single exports.
        """
        self.bugs = {}

        for bug_id in bug_ids:
            query_url = self.export_url % bug_id
            page_data = self._getPage(query_url)

            soup = BeautifulSoup(page_data)
            status_tag = soup.find(text=re.compile('Status:'))

            # If we can't find a status line in the output from
            # SourceForge there's little point in continuing.
            if not status_tag:
                raise UnparseableBugData(
                    'Remote bug %s does not define a status.' % bug_id)

            # We can extract the status by finding the grandparent tag.
            # Happily, BeautifulSoup will turn the contents of this tag
            # into a newline-delimited list from which we can then
            # extract the requisite data.
            status_row = status_tag.findParent().findParent()
            status = status_row.contents[-1]
            status = status.strip()

            # We need to do the same for Resolution, though if we can't
            # find it it's not critical.
            resolution_tag = soup.find(text=re.compile('Resolution:'))
            if resolution_tag:
                resolution_row = resolution_tag.findParent().findParent()
                resolution = resolution_row.contents[-1]
                resolution = resolution.strip()
            else:
                resolution = None

            self.bugs[int(bug_id)] = {
                'id': int(bug_id),
                'status': status,
                'resolution': resolution}

    def getRemoteImportance(self, bug_id):
        """See `ExternalBugTracker`.

        This method is implemented here as a stub to ensure that
        existing functionality is preserved. As a result,
        UNKNOWN_REMOTE_IMPORTANCE will always be returned.
        """
        return UNKNOWN_REMOTE_IMPORTANCE

    def getRemoteStatus(self, bug_id):
        """See `ExternalBugTracker`."""
        try:
            bug_id = int(bug_id)
        except ValueError:
            raise InvalidBugId(
                "bug_id must be convertible to an integer: %s" % str(bug_id))

        try:
            remote_bug = self.bugs[bug_id]
        except KeyError:
            raise BugNotFound(bug_id)

        try:
            return '%(status)s:%(resolution)s' % remote_bug
        except KeyError:
            raise UnparseableBugData(
                "Remote bug %i does not define a status." % bug_id)

    def convertRemoteImportance(self, remote_importance):
        """See `ExternalBugTracker`.

        This method is implemented here as a stub to ensure that
        existing functionality is preserved. As a result,
        BugTaskImportance.UNKNOWN will always be returned.
        """
        return BugTaskImportance.UNKNOWN

    def convertRemoteStatus(self, remote_status):
        """See `IExternalBugTracker`."""
        # SourceForge statuses come in two parts: status and
        # resolution. Both of these are strings. We can look
        # them up in the form status_map[status][resolution]
        status_map = {
            # We use the open status as a fallback when we can't find an
            # exact mapping for the other statuses.
            'Open' : {
                None: BugTaskStatus.NEW,
                'Accepted': BugTaskStatus.CONFIRMED,
                'Duplicate': BugTaskStatus.CONFIRMED,
                'Fixed': BugTaskStatus.FIXCOMMITTED,
                'Invalid': BugTaskStatus.INVALID,
                'Later': BugTaskStatus.CONFIRMED,
                'Out of Date': BugTaskStatus.INVALID,
                'Postponed': BugTaskStatus.CONFIRMED,
                'Rejected': BugTaskStatus.WONTFIX,
                'Remind': BugTaskStatus.CONFIRMED,

                # Some custom SourceForge trackers misspell this, so we
                # deal with the syntactically incorrect version, too.
                "Won't Fix": BugTaskStatus.WONTFIX,
                'Wont Fix': BugTaskStatus.WONTFIX,
                'Works For Me': BugTaskStatus.INVALID,
            },

            'Closed': {
                None: BugTaskStatus.FIXRELEASED,
                'Accepted': BugTaskStatus.FIXCOMMITTED,
                'Fixed': BugTaskStatus.FIXRELEASED,
                'Postponed': BugTaskStatus.WONTFIX,
            },

            'Pending': {
                None: BugTaskStatus.INCOMPLETE,
                'Postponed': BugTaskStatus.WONTFIX,
            },
        }

        # We have to deal with situations where we can't get a
        # resolution to go with the status, so we define both even if we
        # can't get both from SourceForge.
        if ':' in remote_status:
            status, resolution = remote_status.split(':')

            if resolution == 'None':
                resolution = None
        else:
            status = remote_status
            resolution = None

        if status not in status_map:
            raise UnknownRemoteStatusError()

        local_status = status_map[status].get(
            resolution, status_map['Open'].get(resolution))
        if local_status is None:
            raise UnknownRemoteStatusError()
        else:
            return local_status


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

