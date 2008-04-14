# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Trac ExternalBugTracker utiltiy."""

__metaclass__ = type
__all__ = ['Trac', 'TracLPPlugin', 'TracXMLRPCTransport']

import csv
from datetime import datetime
import time
import urllib2
import xmlrpclib

import pytz

from canonical.launchpad.components.externalbugtracker import (
    BugNotFound, ExternalBugTracker, InvalidBugId,
    UnknownRemoteStatusError)
from canonical.launchpad.interfaces import (
    BugTaskStatus, BugTaskImportance, UNKNOWN_REMOTE_IMPORTANCE)
from canonical.launchpad.webapp.url import urlappend


class Trac(ExternalBugTracker):
    """An ExternalBugTracker instance for handling Trac bugtrackers."""

    ticket_url = 'ticket/%i?format=csv'
    batch_url = 'query?%s&order=resolution&format=csv'
    batch_query_threshold = 10

    def supportsSingleExports(self, bug_ids):
        """Return True if the Trac instance provides CSV exports for single
        tickets, False otherwise.

        :bug_ids: A list of bug IDs that we can use for discovery purposes.
        """
        valid_ticket = False
        html_ticket_url = '%s/%s' % (
            self.baseurl, self.ticket_url.replace('?format=csv', ''))

        bug_ids = list(bug_ids)
        while not valid_ticket and len(bug_ids) > 0:
            try:
                # We try to retrive the ticket in HTML form, since that will
                # tell us whether or not it is actually a valid ticket
                ticket_id = int(bug_ids.pop())
                html_data = self.urlopen(html_ticket_url % ticket_id)
            except (ValueError, urllib2.HTTPError):
                # If we get an HTTP error we can consider the ticket to be
                # invalid. If we get a ValueError then the ticket_id couldn't
                # be intified and it's of no use to us anyway.
                pass
            else:
                # If we didn't get an error we can try to get the ticket in
                # CSV form. If this fails then we can consider single ticket
                # exports to be unsupported.
                try:
                    csv_data = self.urlopen(
                        "%s/%s" % (self.baseurl, self.ticket_url % ticket_id))
                    return csv_data.headers.subtype == 'csv'
                except (urllib2.HTTPError, urllib2.URLError):
                    return False
        else:
            # If we reach this point then we likely haven't had any valid
            # tickets or something else is wrong. Either way, we can only
            # assume that CSV exports of single tickets aren't supported.
            return False

    def getRemoteBug(self, bug_id):
        """See `ExternalBugTracker`."""
        bug_id = int(bug_id)
        query_url = "%s/%s" % (self.baseurl, self.ticket_url % bug_id)
        reader = csv.DictReader(self._fetchPage(query_url))
        return (bug_id, reader.next())

    def getRemoteBugBatch(self, bug_ids):
        """See `ExternalBugTracker`."""
        id_string = '&'.join(['id=%s' % id for id in bug_ids])
        query_url = "%s/%s" % (self.baseurl, self.batch_url % id_string)
        remote_bugs = csv.DictReader(self._fetchPage(query_url))

        bugs = {}
        for remote_bug in remote_bugs:
            # We're only interested in the bug if it's one of the ones in
            # bug_ids, just in case we get all the tickets in the Trac
            # instance back instead of only the ones we want.
            if remote_bug['id'] not in bug_ids:
                continue

            bugs[int(remote_bug['id'])] = remote_bug

        return bugs

    def initializeRemoteBugDB(self, bug_ids):
        """See `ExternalBugTracker`.

        This method overrides ExternalBugTracker.initializeRemoteBugDB()
        so that the remote Trac instance's support for single ticket
        exports can be taken into account.

        If the URL specified for the bugtracker is not valid a
        BugTrackerConnectError will be raised.
        """
        self.bugs = {}
        # When there are less than batch_query_threshold bugs to update
        # we make one request per bug id to the remote bug tracker,
        # providing it supports CSV exports per-ticket. If the Trac
        # instance doesn't support exports-per-ticket we fail over to
        # using the batch export method for retrieving bug statuses.
        if (len(bug_ids) < self.batch_query_threshold and
            self.supportsSingleExports(bug_ids)):
            for bug_id in bug_ids:
                # If we can't get the remote bug for any reason a
                # BugTrackerConnectError will be raised at this point.
                remote_id, remote_bug = self.getRemoteBug(bug_id)
                self.bugs[remote_id] = remote_bug

        # For large lists of bug ids we retrieve bug statuses as a batch
        # from the remote bug tracker so as to avoid effectively DOSing
        # it.
        else:
            self.bugs = self.getRemoteBugBatch(bug_ids)

    def getRemoteImportance(self, bug_id):
        """See `ExternalBugTracker`.

        This method is implemented here as a stub to ensure that
        existing functionality is preserved. As a result,
        UNKNOWN_REMOTE_IMPORTANCE will always be returned.
        """
        return UNKNOWN_REMOTE_IMPORTANCE

    def getRemoteStatus(self, bug_id):
        """Return the remote status for the given bug id.

        Raise BugNotFound if the bug can't be found.
        Raise InvalidBugId if the bug id has an unexpected format.
        """
        try:
            bug_id = int(bug_id)
        except ValueError:
            raise InvalidBugId(
                "bug_id must be convertable an integer: %s" % str(bug_id))

        try:
            remote_bug = self.bugs[bug_id]
        except KeyError:
            raise BugNotFound(bug_id)

        # If the bug has a valid resolution as well as a status then we return
        # that, since it's more informative than the status field on its own.
        if (remote_bug.has_key('resolution') and
            remote_bug['resolution'] not in ['', '--', None]):
            return remote_bug['resolution']
        else:
            try:
                return remote_bug['status']
            except KeyError:
                # Some Trac instances don't include the bug status in their
                # CSV exports. In those cases we raise a error.
                raise UnknownRemoteStatusError()

    def convertRemoteImportance(self, remote_importance):
        """See `ExternalBugTracker`.

        This method is implemented here as a stub to ensure that
        existing functionality is preserved. As a result,
        BugTaskImportance.UNKNOWN will always be returned.
        """
        return BugTaskImportance.UNKNOWN

    def convertRemoteStatus(self, remote_status):
        """See `IExternalBugTracker`"""
        status_map = {
            'accepted': BugTaskStatus.CONFIRMED,
            'assigned': BugTaskStatus.CONFIRMED,
            # XXX: 2007-08-06 Graham Binns:
            #      We should follow dupes if possible.
            'duplicate': BugTaskStatus.CONFIRMED,
            'fixed': BugTaskStatus.FIXRELEASED,
            'closed': BugTaskStatus.FIXRELEASED,
            'invalid': BugTaskStatus.INVALID,
            'new': BugTaskStatus.NEW,
            'open': BugTaskStatus.NEW,
            'reopened': BugTaskStatus.NEW,
            'wontfix': BugTaskStatus.WONTFIX,
            'worksforme': BugTaskStatus.INVALID,
        }

        try:
            return status_map[remote_status]
        except KeyError:
            raise UnknownRemoteStatusError()


class TracLPPlugin(ExternalBugTracker):
    """A Trac instance having the LP plugin installed."""

    def __init__(self, baseurl, xmlrpc_transport=None):
        super(TracLPPlugin, self).__init__(baseurl)

        if xmlrpc_transport is None:
            xmlrpc_transport = TracXMLRPCTransport()
        self.xmlrpc_transport = xmlrpc_transport

    def _generateAuthenticationToken(self):
        """Create an authentication token an return it."""
        from zope.component import getUtility
        from canonical.launchpad.interfaces import (
            ILoginTokenSet, LoginTokenType)
        login_token = getUtility(ILoginTokenSet).new(
            None, None, 'externalbugtrackers@launchpad.net',
            LoginTokenType.BUGTRACKER)
        return login_token.token

    def _authenticate(self):
        """Authenticate with the Trac instance."""
        token_text = self._generateAuthenticationToken()
        base_auth_url = urlappend(self.baseurl, 'launchpad-auth')
        auth_url = urlappend(base_auth_url, token_text)
        response = self.urlopen(auth_url)
        auth_cookie = response.headers['Set-Cookie']
        self.xmlrpc_transport.auth_cookie = auth_cookie

    def getCurrentDBTime(self):
        """See `IExternalBugTracker`."""
        endpoint = urlappend(self.baseurl, 'xmlrpc')
        server = xmlrpclib.ServerProxy(
            endpoint, transport=self.xmlrpc_transport)
        time_zone, local_time, utc_time = server.launchpad.time_snapshot()
        # Return the UTC time, so we don't have to care about the time
        # zone for now.
        trac_time = datetime.fromtimestamp(utc_time)
        return trac_time.replace(tzinfo=pytz.timezone('UTC'))

    def getModifiedRemoteBugs(self, remote_bug_ids, last_checked):
        """See `IExternalBugTracker`."""
        endpoint = urlappend(self.baseurl, 'xmlrpc')
        server = xmlrpclib.ServerProxy(
            endpoint, transport=self.xmlrpc_transport)

        # Convert last_checked into an integer timestamp (which is what
        # the Trac LP plugin expects).
        last_checked_timestamp = int(
            time.mktime(last_checked.timetuple()))

        # We retrieve only the IDs of the modified bugs from the server.
        criteria = {
            'modified_since': last_checked_timestamp,
            'bugs': remote_bug_ids,}
        time_snapshot, modified_bugs = server.launchpad.bug_info(
            level=0, criteria=criteria)

        return [bug['id'] for bug in modified_bugs]


class TracXMLRPCTransport(xmlrpclib.Transport):

    auth_cookie = None

    def send_host(self, connection, host):
        xmlrpclib.Transport.send_host(self, connection, host)
        if self.auth_cookie is not None:
            connection.putheader('Cookie', self.auth_cookie)
