# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Bugzilla ExternalBugTracker utility."""

__metaclass__ = type
__all__ = [
    'Bugzilla',
    'BugzillaLPPlugin',
    'needs_authentication',
    ]

import pytz
import time
import xml.parsers.expat
import xmlrpclib

from datetime import datetime
from email.Utils import parseaddr
from xml.dom import minidom

from zope.component import getUtility
from zope.interface import implements

from canonical import encoding
from canonical.config import config
from canonical.launchpad.components.externalbugtracker import (
    BugNotFound, BugTrackerConnectError, ExternalBugTracker, InvalidBugId,
    LookupTree, UnknownRemoteStatusError, UnparseableBugData,
    UnparseableBugTrackerVersion)
from canonical.launchpad.components.externalbugtracker.xmlrpc import (
    UrlLib2Transport)
from canonical.launchpad.interfaces import (
    BugTaskStatus, BugTaskImportance, UNKNOWN_REMOTE_IMPORTANCE)
from canonical.launchpad.interfaces.externalbugtracker import (
    ISupportsCommentImport, ISupportsCommentPushing)
from canonical.launchpad.interfaces.message import IMessageSet
from canonical.launchpad.webapp.url import urlappend


class Bugzilla(ExternalBugTracker):
    """An ExternalBugTrack for dealing with remote Bugzilla systems."""

    batch_query_threshold = 0 # Always use the batch method.

    def __init__(self, baseurl, version=None):
        super(Bugzilla, self).__init__(baseurl)
        self.version = self._parseVersion(version)
        self.is_issuezilla = False
        self.remote_bug_status = {}

        # The XML-RPC endpoint used by getExternalBugTrackerToUse()
        self.xmlrpc_endpoint = urlappend(self.baseurl, 'xmlrpc.cgi')
        self.xmlrpc_transport = None

    @property
    def xmlrpc_proxy(self):
        """Return an `xmlrpclib.ServerProxy` to self.xmlrpc_endpoint."""
        return xmlrpclib.ServerProxy(
            self.xmlrpc_endpoint, transport=self.xmlrpc_transport)

    def getExternalBugTrackerToUse(self):
        """Return the correct `Bugzilla` subclass for the current bugtracker.

        See `IExternalBugTracker`.
        """
        try:
            # We try calling Launchpad.plugin_version() on the remote
            # server because it's the most lightweight method there is.
            plugin = BugzillaLPPlugin(self.baseurl)
            plugin.xmlrpc_proxy.Launchpad.plugin_version()
        except xmlrpclib.Fault, fault:
            if fault.faultCode == 'Client':
                return self
            else:
                raise
        except xmlrpclib.ProtocolError, error:
            if error.errcode == 404:
                return self
            else:
                raise
        else:
            return BugzillaLPPlugin(self.baseurl)

    def _parseDOMString(self, contents):
        """Return a minidom instance representing the XML contents supplied"""
        # Some Bugzilla sites will return pages with content that has
        # broken encoding. It's unfortunate but we need to guess the
        # encoding that page is in, and then encode() it into the utf-8
        # that minidom requires.
        contents = encoding.guess(contents).encode("utf-8")
        return minidom.parseString(contents)

    def _probe_version(self):
        """Retrieve and return a remote bugzilla version.

        If the version cannot be parsed from the remote server
        `UnparseableBugTrackerVersion` will be raised. If the remote
        server cannot be reached `BugTrackerConnectError` will be
        raised.
        """
        version_xml = self._getPage('xml.cgi?id=1')
        try:
            document = self._parseDOMString(version_xml)
        except xml.parsers.expat.ExpatError, e:
            raise BugTrackerConnectError(self.baseurl,
                "Failed to parse output when probing for version: %s" % e)
        bugzilla = document.getElementsByTagName("bugzilla")
        if not bugzilla:
            # Welcome to Disneyland. The Issuezilla tracker replaces
            # "bugzilla" with "issuezilla".
            bugzilla = document.getElementsByTagName("issuezilla")
            if bugzilla:
                self.is_issuezilla = True
            else:
                raise UnparseableBugTrackerVersion(
                    'Failed to parse version from xml.cgi for %s: could '
                    'not find top-level bugzilla element'
                    % self.baseurl)
        version = bugzilla[0].getAttribute("version")
        return self._parseVersion(version)

    def _parseVersion(self, version):
        """Return a Bugzilla version parsed into a tuple.

        A typical tuple will be in the form (major_version,
        minor_version), so the version string '2.15' would be returned
        as (2, 15).

        If the passed version is None, None will be returned.
        If the version cannot be parsed `UnparseableBugTrackerVersion`
        will be raised.
        """
        if version is None:
            return None

        try:
            # Get rid of trailing -rh, -debian, etc.
            version = version.split("-")[0]
            # Ignore plusses in the version.
            version = version.replace("+", "")
            # We need to convert the version to a tuple of integers if
            # we are to compare it correctly.
            version = tuple(int(x) for x in version.split("."))
        except ValueError:
            raise UnparseableBugTrackerVersion(
                'Failed to parse version %r for %s' %
                (version, self.baseurl))

        return version

    def convertRemoteImportance(self, remote_importance):
        """See `ExternalBugTracker`.

        This method is implemented here as a stub to ensure that
        existing functionality is preserved. As a result,
        BugTaskImportance.UNKNOWN will always be returned.
        """
        return BugTaskImportance.UNKNOWN

    _status_lookup_titles = 'Bugzilla status', 'Bugzilla resolution'
    _status_lookup = LookupTree(
        ('ASSIGNED', 'ON_DEV', 'FAILS_QA', 'STARTED',
         BugTaskStatus.INPROGRESS),
        ('NEEDINFO', 'NEEDINFO_REPORTER', 'WAITING', 'SUSPENDED',
         BugTaskStatus.INCOMPLETE),
        ('PENDINGUPLOAD', 'MODIFIED', 'RELEASE_PENDING', 'ON_QA',
         BugTaskStatus.FIXCOMMITTED),
        ('REJECTED', BugTaskStatus.INVALID),
        ('RESOLVED', 'VERIFIED', 'CLOSED',
            LookupTree(
                ('CODE_FIX', 'CURRENTRELEASE', 'ERRATA', 'NEXTRELEASE',
                 'PATCH_ALREADY_AVAILABLE', 'FIXED', 'RAWHIDE',
                 BugTaskStatus.FIXRELEASED),
                ('WONTFIX', BugTaskStatus.WONTFIX),
                (BugTaskStatus.INVALID,))),
        ('REOPENED', 'NEW', 'UPSTREAM', 'DEFERRED', BugTaskStatus.CONFIRMED),
        ('UNCONFIRMED', BugTaskStatus.NEW),
        )

    def convertRemoteStatus(self, remote_status):
        """See `IExternalBugTracker`.

        Bugzilla status consist of two parts separated by space, where
        the last part is the resolution. The resolution is optional.
        """
        try:
            return self._status_lookup.find(*remote_status.split())
        except KeyError:
            raise UnknownRemoteStatusError(remote_status)

    def initializeRemoteBugDB(self, bug_ids):
        """See `ExternalBugTracker`.

        This method is overriden so that Bugzilla version issues can be
        accounted for.
        """
        if self.version is None:
            self.version = self._probe_version()

        super(Bugzilla, self).initializeRemoteBugDB(bug_ids)

    def getRemoteBug(self, bug_id):
        """See `ExternalBugTracker`."""
        return (bug_id, self.getRemoteBugBatch([bug_id]))

    def getRemoteBugBatch(self, bug_ids):
        """See `ExternalBugTracker`."""
        # XXX: GavinPanella 2007-10-25 bug=153532: The modification of
        # self.remote_bug_status later on is a side-effect that should
        # really not be in this method, but for the fact that
        # getRemoteStatus needs it at other times. Perhaps
        # getRemoteBug and getRemoteBugBatch could return RemoteBug
        # objects which have status properties that would replace
        # getRemoteStatus.
        if self.is_issuezilla:
            buglist_page = 'xml.cgi'
            data = {'download_type' : 'browser',
                    'output_configured' : 'true',
                    'include_attachments' : 'false',
                    'include_dtd' : 'true',
                    'id'      : ','.join(bug_ids),
                    }
            bug_tag = 'issue'
            id_tag = 'issue_id'
            status_tag = 'issue_status'
            resolution_tag = 'resolution'
        elif self.version < (2, 16):
            buglist_page = 'xml.cgi'
            data = {'id': ','.join(bug_ids)}
            bug_tag = 'bug'
            id_tag = 'bug_id'
            status_tag = 'bug_status'
            resolution_tag = 'resolution'
        else:
            buglist_page = 'buglist.cgi'
            data = {'form_name'   : 'buglist.cgi',
                    'bug_id_type' : 'include',
                    'bug_id'      : ','.join(bug_ids),
                    }
            if self.version < (2, 17, 1):
                data.update({'format' : 'rdf'})
            else:
                data.update({'ctype'  : 'rdf'})
            bug_tag = 'bz:bug'
            id_tag = 'bz:id'
            status_tag = 'bz:bug_status'
            resolution_tag = 'bz:resolution'

        buglist_xml = self._postPage(buglist_page, data)
        try:
            document = self._parseDOMString(buglist_xml)
        except xml.parsers.expat.ExpatError, e:
            raise UnparseableBugData('Failed to parse XML description for '
                '%s bugs %s: %s' % (self.baseurl, bug_ids, e))

        bug_nodes = document.getElementsByTagName(bug_tag)
        for bug_node in bug_nodes:
            # We use manual iteration to pick up id_tags instead of
            # getElementsByTagName because the latter does a recursive
            # search, and in some documents we've found the id_tag to
            # appear under other elements (such as "has_duplicates") in
            # the document hierarchy.
            bug_id_nodes = [node for node in bug_node.childNodes if
                            node.nodeName == id_tag]
            if not bug_id_nodes:
                # Something in the output is really weird; this will
                # show up as a bug not found, but we can catch that
                # later in the error logs.
                continue
            bug_id_node = bug_id_nodes[0]
            assert len(bug_id_node.childNodes) == 1, (
                "id node should contain a non-empty text string.")
            bug_id = str(bug_id_node.childNodes[0].data)
            # This assertion comes in late so we can at least tell what
            # bug caused this crash.
            assert len(bug_id_nodes) == 1, ("Should be only one id node, "
                "but %s had %s." % (bug_id, len(bug_id_nodes)))

            status_nodes = bug_node.getElementsByTagName(status_tag)
            if not status_nodes:
                # Older versions of bugzilla used bz:status; this was
                # later changed to bz:bug_status. For robustness, and
                # because there is practically no risk of reading wrong
                # data here, just try the older format as well.
                status_nodes = bug_node.getElementsByTagName("bz:status")
            assert len(status_nodes) == 1, ("Couldn't find a status "
                                            "node for bug %s." % bug_id)
            bug_status_node = status_nodes[0]
            assert len(bug_status_node.childNodes) == 1, (
                "status node for bug %s should contain a non-empty "
                "text string." % bug_id)
            status = bug_status_node.childNodes[0].data

            resolution_nodes = bug_node.getElementsByTagName(resolution_tag)
            assert len(resolution_nodes) <= 1, (
                "Should be only one resolution node for bug %s." % bug_id)
            if resolution_nodes:
                assert len(resolution_nodes[0].childNodes) <= 1, (
                    "Resolution for bug %s should just contain "
                    "a string." % bug_id)
                if resolution_nodes[0].childNodes:
                    resolution = resolution_nodes[0].childNodes[0].data
                    status += ' %s' % resolution
            self.remote_bug_status[bug_id] = status

    def getRemoteImportance(self, bug_id):
        """See `ExternalBugTracker`.

        This method is implemented here as a stub to ensure that
        existing functionality is preserved. As a result,
        UNKNOWN_REMOTE_IMPORTANCE will always be returned.
        """
        return UNKNOWN_REMOTE_IMPORTANCE

    def getRemoteStatus(self, bug_id):
        """See ExternalBugTracker."""
        if not bug_id.isdigit():
            raise InvalidBugId(
                "Bugzilla (%s) bug number not an integer: %s" % (
                    self.baseurl, bug_id))
        try:
            return self.remote_bug_status[bug_id]
        except KeyError:
            raise BugNotFound(bug_id)


def needs_authentication(func):
    """Decorator for automatically authenticating if needed.

    If an `xmlrpclib.Fault` with error code 410 is raised by the
    function, we'll try to authenticate and call the function again.
    """
    def decorator(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except xmlrpclib.Fault, fault:
            # Catch authentication errors only.
            if fault.faultCode != 410:
                raise
            self._authenticate()
            return func(self, *args, **kwargs)
    return decorator


class BugzillaLPPlugin(Bugzilla):
    """An `ExternalBugTracker` to handle Bugzillas using the LP Plugin."""

    implements(ISupportsCommentImport, ISupportsCommentPushing)

    def __init__(self, baseurl, xmlrpc_transport=None,
                 internal_xmlrpc_transport=None):
        super(BugzillaLPPlugin, self).__init__(baseurl)

        self.internal_xmlrpc_transport = internal_xmlrpc_transport
        if xmlrpc_transport is None:
            self.xmlrpc_transport = UrlLib2Transport(self.xmlrpc_endpoint)
        else:
            self.xmlrpc_transport = xmlrpc_transport

    def _authenticate(self):
        """Authenticate with the remote Bugzilla instance.

        Authentication works by means of using a LoginToken of type
        BUGTRACKER. We send the token text to the remote server as a
        parameter to Launchpad.login(), which verifies it using the
        standard launchpad.net/token/$token/+bugtracker-handshake URL.

        If the token is valid, Bugzilla will send us a user ID as a
        return value for the call to Launchpad.login() and will set two
        cookies in the response header, Bugzilla_login and
        Bugzilla_logincookie, which we can then use to re-authenticate
        ourselves for each subsequent method call.
        """
        internal_xmlrpc_server = xmlrpclib.ServerProxy(
            config.checkwatches.xmlrpc_url,
            transport=self.internal_xmlrpc_transport)

        token_text = internal_xmlrpc_server.newBugTrackerToken()

        user_id = self.xmlrpc_proxy.Launchpad.login({'token': token_text})

        auth_cookies = self._extractAuthCookie(
            self.xmlrpc_transport.last_response_headers['Set-Cookie'])
        for cookie in auth_cookies.split(';'):
            self.xmlrpc_transport.setCookie(cookie.strip())

    def _extractAuthCookie(self, cookie_header):
        """Extract the Bugzilla authentication cookies from the header."""
        cookies = []
        for cookie_header_part in cookie_header.split(','):
            cookie = cookie_header_part.split(';')[0]
            cookie = cookie.strip()

            if cookie.startswith('Bugzilla_login'):
                cookies.append(cookie)

        return '; '.join(cookies)

    def initializeRemoteBugDB(self, bug_ids):
        """See `IExternalBugTracker`."""
        self.bugs = {}
        self.bug_aliases = {}

        # First, grab the bugs from the remote server.
        request_args = {
            'ids': bug_ids,
            'permissive': True,
            }
        response_dict = self.xmlrpc_proxy.Bug.get_bugs(request_args)
        remote_bugs = response_dict['bugs']

        # Now copy them into the local bugs dict.
        for remote_bug in remote_bugs:
            self.bugs[remote_bug['id']] = remote_bug

            # The bug_aliases dict is a mapping between aliases and bug
            # IDs. We use the aliases dict to look up the correct ID for
            # a bug. This allows us to reference a bug by either ID or
            # alias.
            if remote_bug['alias'] and remote_bug['alias'] in bug_ids:
                self.bug_aliases[remote_bug['alias']] = remote_bug['id']

    def getCurrentDBTime(self):
        """See `IExternalBugTracker`."""
        time_dict = self.xmlrpc_proxy.Launchpad.time()

        # Return the UTC time sent by the server so that we don't have
        # to care about timezones.
        server_timetuple = time.strptime(
            str(time_dict['utc_time']), '%Y%m%dT%H:%M:%S')

        server_utc_time = datetime(*server_timetuple[:6])
        return server_utc_time.replace(tzinfo=pytz.timezone('UTC'))

    def _getActualBugId(self, bug_id):
        """Return the actual bug id for an alias or id."""
        # See if bug_id is actually an alias.
        actual_bug_id = self.bug_aliases.get(bug_id)

        # bug_id isn't an alias, so try turning it into an int and
        # looking the bug up by ID.
        if actual_bug_id is not None:
            return actual_bug_id
        else:
            try:
                return int(bug_id)
            except ValueError:
                # If bug_id can't be int()'d then it's likely an alias
                # that doesn't exist, so raise BugNotFound.
                raise BugNotFound(bug_id)

    def getRemoteStatus(self, bug_id):
        """See `IExternalBugTracker`."""
        actual_bug_id = self._getActualBugId(bug_id)

        try:
            status = self.bugs[actual_bug_id]['status']
            resolution = self.bugs[actual_bug_id]['resolution']

            if resolution != '' and resolution is not None:
                return "%s %s" % (status, resolution)
            else:
                return status

        except KeyError:
            raise BugNotFound(bug_id)

    def getCommentIds(self, bug_watch):
        """See `ISupportsCommentImport`."""
        actual_bug_id = self._getActualBugId(bug_watch.remotebug)

        # Check that the bug exists, first.
        if actual_bug_id not in self.bugs:
            raise BugNotFound(bug_watch.remotebug)

        # Get only the remote comment IDs and store them in the
        # 'comments' field of the bug.
        request_params = {
            'bug_ids': [actual_bug_id],
            'include': ['id'],
            }
        bug_comments_dict = self.xmlrpc_proxy.Bug.comments(request_params)

        bug_comments = bug_comments_dict['bugs'][actual_bug_id]
        return [comment['id'] for comment in bug_comments]

    def fetchComments(self, bug_watch, comment_ids):
        """See `ISupportsCommentImport`."""
        actual_bug_id = self._getActualBugId(bug_watch.remotebug)

        # Fetch the comments we want.
        request_params = {
            'bug_ids': [actual_bug_id],
            'ids': comment_ids,
            }
        bug_comments_dict = self.xmlrpc_proxy.Bug.comments(request_params)
        comment_list = bug_comments_dict['bugs'][actual_bug_id]

        # Transfer the comment list into a dict.
        bug_comments = dict(
            (comment['id'], comment) for comment in comment_list)

        self.bugs[actual_bug_id]['comments'] = bug_comments

    def getPosterForComment(self, bug_watch, comment_id):
        """See `ISupportsCommentImport`."""
        actual_bug_id = self._getActualBugId(bug_watch.remotebug)

        comment = self.bugs[actual_bug_id]['comments'][comment_id]
        display_name, email = parseaddr(comment['author'])

        # If the name is empty then we return None so that
        # IPersonSet.ensurePerson() can actually do something with it.
        if not display_name:
            display_name = None

        return (display_name, email)

    def getMessageForComment(self, bug_watch, comment_id, poster):
        """See `ISupportsCommentImport`."""
        actual_bug_id = self._getActualBugId(bug_watch.remotebug)
        comment = self.bugs[actual_bug_id]['comments'][comment_id]

        # Turn the time in the comment, which is an XML-RPC datetime
        # into something more useful to us.
        comment_timestamp = time.mktime(
            time.strptime(str(comment['time']), '%Y%m%dT%H:%M:%S'))
        comment_datetime = datetime.fromtimestamp(comment_timestamp)
        comment_datetime = comment_datetime.replace(
            tzinfo=pytz.timezone('UTC'))

        message = getUtility(IMessageSet).fromText(
            owner=poster, subject='', content=comment['text'],
            datecreated=comment_datetime)

        return message

    @needs_authentication
    def addRemoteComment(self, remote_bug, comment_body, rfc822msgid):
        """Add a comment to the remote bugtracker.

        See `ISupportsCommentPushing`.
        """
        actual_bug_id = self._getActualBugId(remote_bug)

        request_params = {
            'id': actual_bug_id,
            'comment': comment_body,
            }
        return_dict = self.xmlrpc_proxy.Bug.add_comment(request_params)

        return return_dict['comment_id']
