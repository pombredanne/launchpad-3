# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""RT ExternalBugTracker Utility."""

__metaclass__ = type
__all__ = ['RequestTracker']

import email
import re

import requests
from requests.cookies import RequestsCookieJar

from lp.bugs.externalbugtracker import (
    BugNotFound,
    BugTrackerConnectError,
    ExternalBugTracker,
    InvalidBugId,
    LookupTree,
    UnknownRemoteStatusError,
    )
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    )
from lp.bugs.interfaces.externalbugtracker import UNKNOWN_REMOTE_IMPORTANCE
from lp.services.config import config
from lp.services.webapp.url import urlparse


class RequestTracker(ExternalBugTracker):
    """`ExternalBugTracker` subclass for handling RT imports."""

    ticket_url = 'REST/1.0/ticket/%s/show'
    batch_url = 'REST/1.0/search/ticket/'
    batch_query_threshold = 1

    def __init__(self, baseurl, cookie_jar=None):
        super(RequestTracker, self).__init__(baseurl)

        if cookie_jar is None:
            cookie_jar = RequestsCookieJar()
        self._cookie_jar = cookie_jar
        self._logged_in = False

    @property
    def credentials(self):
        """Return the authentication credentials needed to log in.

        If there are specific credentials for the current RT instance,
        these will be returned. Otherwise the RT default guest
        credentials (username and password of 'guest') will be returned.
        """
        credentials_config = config['checkwatches.credentials']
        hostname = urlparse(self.baseurl)[1]
        try:
            username = credentials_config['%s.username' % hostname]
            password = credentials_config['%s.password' % hostname]
            return {'user': username, 'pass': password}
        except KeyError:
            return {'user': 'guest', 'pass': 'guest'}

    def makeRequest(self, method, url, **kwargs):
        """See `ExternalBugTracker`."""
        if not self._logged_in:
            # To log in to an RT instance we must pass a username and
            # password to its login form, as a user would from the web.
            try:
                super(RequestTracker, self).makeRequest(
                    'GET', '%s/' % self.baseurl,
                    params=self.credentials, cookies=self._cookie_jar)
            except requests.RequestException as e:
                raise BugTrackerConnectError('%s/' % self.baseurl,
                    "Unable to authenticate with remote RT service: "
                    "Could not submit login form: %s" % e)
            self._logged_in = True
        return super(RequestTracker, self).makeRequest(
            method, url, cookies=self._cookie_jar, **kwargs)

    def getRemoteBug(self, bug_id):
        """See `ExternalBugTracker`."""
        ticket_url = self.ticket_url % str(bug_id)
        query_url = '%s/%s' % (self.baseurl, ticket_url)
        try:
            bug_data = self.makeRequest('GET', query_url).text
        except requests.HTTPError as error:
            raise BugTrackerConnectError(ticket_url, error)

        # We use the first line of the response to ensure that we've
        # made a successful request.
        bug_firstline, bug_rest = re.split(r'\r?\n', bug_data, maxsplit=1)
        firstline = bug_firstline.strip().split(' ')
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
        bug = email.message_from_string(bug_rest.strip())
        if bug.get('id') is None:
            return None, None
        else:
            bug_id = bug['id'].replace('ticket/', '')
            return int(bug_id), bug

    def getRemoteBugBatch(self, bug_ids):
        """See `ExternalBugTracker`."""
        # We need to ensure that all the IDs are strings first.
        id_list = [str(id) for id in bug_ids]
        query = "id = " + " OR id = ".join(id_list)

        query_url = '%s/%s' % (self.baseurl, self.batch_url)
        request_params = {'query': query, 'format': 'l'}
        try:
            bug_data = self.makeRequest(
                'GET', query_url, params=request_params,
                headers={'Referer': self.baseurl}).text
        except requests.HTTPError as error:
            raise BugTrackerConnectError(query_url, error)

        # We use the first line of the response to ensure that we've
        # made a successful request.
        bug_firstline, bug_rest = re.split(r'\r?\n', bug_data, maxsplit=1)
        firstline = bug_firstline.strip().split(' ')
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
        tickets = bug_rest.split("--\n")
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
        return UNKNOWN_REMOTE_IMPORTANCE

    def convertRemoteImportance(self, remote_importance):
        """See `IExternalBugTracker`."""
        return BugTaskImportance.UNKNOWN

    _status_lookup_titles = 'RT status',
    _status_lookup = LookupTree(
        ('new', BugTaskStatus.NEW),
        ('open', BugTaskStatus.CONFIRMED),
        ('stalled', BugTaskStatus.CONFIRMED),
        ('rejected', BugTaskStatus.INVALID),
        ('resolved', BugTaskStatus.FIXRELEASED),
        )

    def convertRemoteStatus(self, remote_status):
        """Convert an RT status into a Launchpad BugTaskStatus."""
        try:
            return self._status_lookup.find(remote_status.lower())
        except KeyError:
            raise UnknownRemoteStatusError(remote_status)

    def getRemoteProduct(self, remote_bug):
        """Return the remote product for a remote bug.

        See `IExternalBugTracker`.
        """
        if remote_bug not in self.bugs:
            raise BugNotFound(remote_bug)

        return self.bugs[remote_bug].get('queue', None)
