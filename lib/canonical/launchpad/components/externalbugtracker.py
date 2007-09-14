# Copyright 2006 Canonical Ltd.  All rights reserved.

"""External bugtrackers."""

__metaclass__ = type

import cgi
import csv
import os.path
import urllib
import urllib2
import urlparse
import ClientCookie
import xml.parsers.expat
from xml.dom import minidom

from BeautifulSoup import BeautifulSoup, Comment, SoupStrainer
from zope.interface import implements

from canonical.config import config
from canonical import encoding
from canonical.database.constants import UTC_NOW
from canonical.lp.dbschema import BugTrackerType
from canonical.launchpad.scripts import log, debbugs
from canonical.launchpad.interfaces import (
    BugTaskStatus, IExternalBugtracker, UNKNOWN_REMOTE_STATUS)

# The user agent we send in our requests
LP_USER_AGENT = "Launchpad Bugscraper/0.2 (http://bugs.launchpad.net/)"


#
# Exceptions caught in scripts/checkwatches.py
#
class BugWatchUpdateError(Exception):
    """Base exception for when we fail to update watches for a tracker."""


class UnknownBugTrackerTypeError(BugWatchUpdateError):
    """Exception class to catch systems we don't have a class for yet."""

    def __init__(self, bugtrackertypename, bugtrackername):
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
        self.url = url
        self.error = str(error)

    def __str__(self):
        return "%s: %s" % (self.url, self.error)

#
# Exceptions caught locally
#
class InvalidBugId(Exception):
    """The bug id wasn't in the format the bug tracker expected.

    For example, Bugzilla and debbugs expect the bug id to be an
    integer.
    """


class BugNotFound(Exception):
    """The bug was not found in the external bug tracker."""


#
# Helper function
#
def get_external_bugtracker(bugtracker, version=None):
    """Return an ExternalBugTracker for bugtracker."""
    bugtrackertype = bugtracker.bugtrackertype
    if bugtrackertype == BugTrackerType.BUGZILLA:
        return Bugzilla(bugtracker.baseurl, version)
    elif bugtrackertype == BugTrackerType.DEBBUGS:
        return DebBugs()
    elif bugtrackertype == BugTrackerType.MANTIS:
        return Mantis(bugtracker.baseurl)
    elif bugtrackertype == BugTrackerType.TRAC:
        return Trac(bugtracker.baseurl)
    elif bugtrackertype == BugTrackerType.ROUNDUP:
        return Roundup(bugtracker.baseurl)
    else:
        raise UnknownBugTrackerTypeError(bugtrackertype.name,
            bugtracker.name)


class ExternalBugTracker:
    """Base class for an external bug tracker."""

    implements(IExternalBugtracker)
    batch_query_threshold = config.checkwatches.batch_query_threshold

    def urlopen(self, request, data=None):
        return urllib2.urlopen(request, data)

    def initializeRemoteBugDB(self, bug_ids):
        """Do any initialization before each bug watch is updated.

        It's optional to override this method.
        """
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
                self.bugs[bug_id] = remote_bug

    def getRemoteBug(self, bug_id):
        """Retrieve and return a single bug from the remote database.

        The bug is returned as a tuple in the form (id, bug). This ensures
        that bug ids are formatted correctly for the current
        ExternalBugTracker.

        A BugTrackerConnectError will be raised if anything goes wrong.
        """
        raise NotImplementedError(self.getRemoteBug)

    def getRemoteBugBatch(self, bug_ids):
        """Retrieve and return a set of bugs from the remote database.

        A BugTrackerConnectError will be raised if anything goes wrong.
        """
        raise NotImplementedError(self.getRemoteBugBatch)

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

    def updateBugWatches(self, bug_watches):
        """Update the given bug watches."""
        # Save the url for later, since we might need it to report an
        # error after a transaction has been aborted.
        bug_tracker_url = self.baseurl
        bug_watches_by_remote_bug = {}

        for bug_watch in bug_watches:
            remote_bug = bug_watch.remotebug
            # There can be multiple bug watches pointing to the same
            # remote bug; because of that, we need to store lists of bug
            # watches related to the remote bug, and later update the
            # status of each one of them.
            if remote_bug not in bug_watches_by_remote_bug:
                bug_watches_by_remote_bug[remote_bug] = []
            bug_watches_by_remote_bug[remote_bug].append(bug_watch)

        # Do things in a fixed order, mainly to help with testing.
        bug_ids_to_update = sorted(bug_watches_by_remote_bug)
        self.initializeRemoteBugDB(bug_ids_to_update)

        # Again, fixed order here to help with testing.
        for bug_id, bug_watches in sorted(bug_watches_by_remote_bug.items()):
            local_ids = ", ".join(str(watch.bug.id) for watch in bug_watches)
            try:
                try:
                    new_remote_status = self.getRemoteStatus(bug_id)
                except InvalidBugId, error:
                    log.warn("Invalid bug %r on %s (local bugs: %s)" %
                             (bug_id, self.baseurl, local_ids))
                    new_remote_status = UNKNOWN_REMOTE_STATUS
                except BugNotFound:
                    log.warn("Didn't find bug %r on %s (local bugs: %s)" %
                             (bug_id, self.baseurl, local_ids))
                    new_remote_status = UNKNOWN_REMOTE_STATUS
                new_malone_status = self.convertRemoteStatus(new_remote_status)

                for bug_watch in bug_watches:
                    bug_watch.lastchecked = UTC_NOW
                    bug_watch.updateStatus(new_remote_status, new_malone_status)

            except (KeyboardInterrupt, SystemExit):
                # We should never catch KeyboardInterrupt or SystemExit.
                raise
            except:
                # If something unexpected goes wrong, we shouldn't break the
                # updating of the other bugs.
                log.error("Failure updating bug %r on %s (local bugs: %s)" %
                            (bug_id, bug_tracker_url, local_ids),
                          exc_info=True)

#
# Bugzilla
#

class Bugzilla(ExternalBugTracker):
    """A class that deals with communications with a remote Bugzilla system."""

    implements(IExternalBugtracker)

    def __init__(self, baseurl, version=None):
        if baseurl.endswith("/"):
            baseurl = baseurl[:-1]
        self.baseurl = baseurl
        self.version = version
        self.is_issuezilla = False

    def _parseDOMString(self, contents):
        """Return a minidom instance representing the XML contents supplied"""
        # Some Bugzilla sites will return pages with content that has
        # broken encoding. It's unfortunate but we need to guess the
        # encoding that page is in, and then encode() it into the utf-8
        # that minidom requires.
        contents = encoding.guess(contents).encode("utf-8")
        return minidom.parseString(contents)

    def _probe_version(self):
        version_xml = self._getPage('xml.cgi?id=1')
        try:
            document = self._parseDOMString(version_xml)
        except xml.parsers.expat.ExpatError, e:
            raise BugTrackerConnectError(self.baseurl, "Failed to parse output "
                                         "when probing for version: %s" % e)
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
        return version

    def convertRemoteStatus(self, remote_status):
        """See IExternalBugtracker.

        Bugzilla status consist of two parts separated by space, where
        the last part is the resolution. The resolution is optional.
        """
        if not remote_status or remote_status == UNKNOWN_REMOTE_STATUS:
            return BugTaskStatus.UNKNOWN
        if ' ' in remote_status:
            remote_status, resolution = remote_status.split(' ', 1)
        else:
            resolution = ''

        if remote_status in ['ASSIGNED', 'ON_DEV', 'FAILS_QA', 'STARTED']:
            # FAILS_QA, ON_DEV: bugzilla.redhat.com
            # STARTED: OOO Issuezilla
           malone_status = BugTaskStatus.INPROGRESS
        elif remote_status in ['NEEDINFO', 'NEEDINFO_REPORTER',
                               'WAITING', 'SUSPENDED']:
            # NEEDINFO_REPORTER: bugzilla.redhat.com
            # SUSPENDED, WAITING: http://gcc.gnu.org/bugzilla
            #   though SUSPENDED applies to something pending discussion
            #   in a larger/separate context.
            malone_status = BugTaskStatus.INCOMPLETE
        elif remote_status in ['PENDINGUPLOAD', 'MODIFIED', 'RELEASE_PENDING', 'ON_QA']:
            # RELEASE_PENDING, MODIFIED, ON_QA: bugzilla.redhat.com
            malone_status = BugTaskStatus.FIXCOMMITTED
        elif remote_status in ['REJECTED']:
            # REJECTED: bugzilla.kernel.org
            malone_status = BugTaskStatus.INVALID
        elif remote_status in ['RESOLVED', 'VERIFIED', 'CLOSED']:
            # depends on the resolution:
            if resolution in ['CODE_FIX', 'CURRENTRELEASE', 'ERRATA',
                              'FIXED', 'NEXTRELEASE',
                              'PATCH_ALREADY_AVAILABLE', 'RAWHIDE']:

                # The following resolutions come from bugzilla.redhat.com.
                # All of them map to Malone's FIXRELEASED status:
                #     CODE_FIX, CURRENTRELEASE, ERRATA, NEXTRELEASE,
                #     PATCH_ALREADY_AVAILABLE, RAWHIDE
                malone_status = BugTaskStatus.FIXRELEASED
            elif resolution == 'WONTFIX':
                # VERIFIED WONTFIX maps directly to WONTFIX
                malone_status = BugTaskStatus.WONTFIX
            else:
                #XXX: Bjorn Tillenius 2005-02-03 Bug=31745:
                #     Which are the valid resolutions? We should fail
                #     if we don't know of the resolution.
                malone_status = BugTaskStatus.INVALID
        elif remote_status in ['REOPENED', 'NEW', 'UPSTREAM', 'DEFERRED']:
            # DEFERRED: bugzilla.redhat.com
            malone_status = BugTaskStatus.CONFIRMED
        elif remote_status in ['UNCONFIRMED']:
            malone_status = BugTaskStatus.NEW
        else:
            log.warning(
                "Unknown Bugzilla status '%s' at %s" % (
                    remote_status, self.baseurl))
            malone_status = BugTaskStatus.UNKNOWN

        return malone_status

    def initializeRemoteBugDB(self, bug_ids):
        """See ExternalBugTracker."""
        if self.version is None:
            self.version = self._probe_version()

        try:
            # Get rid of trailing -rh, -debian, etc.
            version = self.version.split("-")[0]
            # Ignore plusses in the version.
            version = version.replace("+", "")
            # We need to convert the version to a tuple of integers if
            # we are to compare it correctly.
            version = tuple(int(x) for x in version.split("."))
        except ValueError:
            raise UnparseableBugTrackerVersion(
                'Failed to parse version %r for %s' % (self.version, self.baseurl))

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
        elif version < (2, 16):
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
            if version < (2, 17, 1):
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

        self.remote_bug_status = {}
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
            assert len(bug_id_nodes) == 1, \
                "Should be only one id node, but %s had %s." % (bug_id, len(bug_id_nodes))

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

#
# Debbugs
#

debbugsstatusmap = {'open':      BugTaskStatus.NEW,
                    'forwarded': BugTaskStatus.CONFIRMED,
                    'done':      BugTaskStatus.FIXRELEASED}

class DebBugs(ExternalBugTracker):
    """A class that deals with communications with a debbugs db."""

    implements(IExternalBugtracker)

    # We don't support different versions of debbugs.
    version = None
    debbugs_pl = os.path.join(
        os.path.dirname(debbugs.__file__), 'debbugs-log.pl')

    def __init__(self, db_location=None):
        if db_location is None:
            self.db_location = config.malone.debbugs_db_location
        else:
            self.db_location = db_location

        if not os.path.exists(os.path.join(self.db_location, 'db-h')):
            log.error("There's no debbugs db at %s" % self.db_location)
            self.debbugs_db = None
            return

        # The debbugs database is split in two parts: a current
        # database, which is kept under the 'db-h' directory, and the
        # archived database, which is kept under 'archive'. The archived
        # database is used as a fallback, as you can see in getRemoteStatus
        self.debbugs_db = debbugs.Database(self.db_location, self.debbugs_pl)
        if os.path.exists(os.path.join(self.db_location, 'archive')):
            self.debbugs_db_archive = debbugs.Database(self.db_location,
                                                       self.debbugs_pl,
                                                       subdir="archive")

    def initializeRemoteBugDB(self, bug_ids):
        """See `ExternalBugTracker`.

        This method is overridden (and left empty) here to avoid breakage when
        the continuous bug-watch checking spec is implemented.
        """

    @property
    def baseurl(self):
        return self.db_location

    def convertRemoteStatus(self, remote_status):
        """Convert a debbugs status to a Malone status.

        A debbugs status consists of either two or three parts,
        separated with space; the status and severity, followed by
        optional tags. The tags are also separated with a space
        character.
        """
        if not remote_status or remote_status == UNKNOWN_REMOTE_STATUS:
            return BugTaskStatus.UNKNOWN
        parts = remote_status.split(' ')
        if len(parts) < 2:
            log.error('Malformed debbugs status: %r' % remote_status)
            return BugTaskStatus.UNKNOWN
        status = parts[0]
        severity = parts[1]
        tags = parts[2:]

        # For the moment we convert only the status, not the severity.
        try:
            malone_status = debbugsstatusmap[status]
        except KeyError:
            log.warn('Unknown debbugs status "%s"' % status)
            malone_status = BugTaskStatus.UNKNOWN
        if status == 'open':
            confirmed_tags = [
                'help', 'confirmed', 'upstream', 'fixed-upstream']
            fix_committed_tags = ['pending', 'fixed', 'fixed-in-experimental']
            if 'moreinfo' in tags:
                malone_status = BugTaskStatus.INCOMPLETE
            for confirmed_tag in confirmed_tags:
                if confirmed_tag in tags:
                    malone_status = BugTaskStatus.CONFIRMED
                    break
            for fix_committed_tag in fix_committed_tags:
                if fix_committed_tag in tags:
                    malone_status = BugTaskStatus.FIXCOMMITTED
                    break
            if 'wontfix' in tags:
                malone_status = BugTaskStatus.WONTFIX

        return malone_status

    def _findBug(self, bug_id):
        if self.debbugs_db is None:
            raise BugNotFound(bug_id)
        if not bug_id.isdigit():
            raise InvalidBugId(
                "Debbugs bug number not an integer: %s" % bug_id)
        try:
            debian_bug = self.debbugs_db[int(bug_id)]
        except KeyError:
            # If we couldn't find it in the main database, there's
            # always the archive.
            try:
                debian_bug = self.debbugs_db_archive[int(bug_id)]
            except KeyError:
                raise BugNotFound(bug_id)

        return debian_bug

    def getRemoteStatus(self, bug_id):
        """See ExternalBugTracker."""
        debian_bug = self._findBug(bug_id)
        if not debian_bug.severity:
            # 'normal' is the default severity in debbugs.
            severity = 'normal'
        else:
            severity = debian_bug.severity
        new_remote_status = ' '.join(
            [debian_bug.status, severity] + debian_bug.tags)
        return new_remote_status

#
# Mantis
#

class MantisLoginHandler(ClientCookie.HTTPRedirectHandler):
    """Handler for ClientCookie.build_opener to automatically log-in
    to Mantis anonymously if needed.

    The ALSA bug tracker is the only tested Mantis installation that
    actually needs this. For ALSA bugs, the dance is like so:

      1. We request bug 3301 ('jack sensing problem'):
           https://bugtrack.alsa-project.org/alsa-bug/view.php?id=3301

      2. Mantis redirects us to:
           .../alsa-bug/login_page.php?return=%2Falsa-bug%2Fview.php%3Fid%3D3301

      3. We notice this, rewrite the query, and skip to login.php:
           .../alsa-bug/login.php?return=%2Falsa-bug%2Fview.php%3Fid%3D3301&username=guest&password=guest

      4. Mantis accepts our credentials then redirects us to the bug
         view page via a cookie test page (login_cookie_test.php)
    """

    def redirect_request(self, newurl, req, fp, code, msg, headers):
        # XXX: The argument order here is different from that in
        # urllib2.HTTPRedirectHandler. ClientCookie is meant to mimic
        # urllib2 (and does subclass it), so this is probably a
        # bug. -- Gavin Panella, 2007-08-27

        scheme, host, path, params, query, fragment = (
            urlparse.urlparse(newurl))

        # If we can, skip the login page and submit credentials
        # directly. The query should contain a 'return' parameter
        # which, if our credentials are accepted, means we'll be
        # redirected back from whence we came. In other words, we'll
        # end up back at the bug page we first requested.
        login_page = '/login_page.php'
        if path.endswith(login_page):
            path = path[:-len(login_page)] + '/login.php'
            query = cgi.parse_qs(query, True)
            query['username'] = query['password'] = ['guest']
            if 'return' not in query:
                log.warn("Mantis redirected us to the login page "
                    "but did not set a return path.")
            query = urllib.urlencode(query, True)
            newurl = urlparse.urlunparse(
                (scheme, host, path, params, query, fragment))

        # XXX: Previous versions of the Mantis external bug tracker
        # fetched login_anon.php in addition to the login.php method
        # above, but none of the Mantis installations tested actually
        # needed this. For example, the ALSA bugtracker actually
        # issues an error "Your account may be disabled" when
        # accessing this page. For now it's better to *not* try this
        # page because we may end up annoying admins with spurious
        # login attempts. -- Gavin Panella, 2007-08-28.

        return ClientCookie.HTTPRedirectHandler.redirect_request(
            self, newurl, req, fp, code, msg, headers)


class Mantis(ExternalBugTracker):
    # Example sites (tested 2007-08-2X):            Version      Scrape  CSV Export
    #   http://www.atutor.ca/atutor/mantis/         1.0.7        NOT OK  NOT OK (no anon access)
    #   http://bugs.mantisbt.org/                   1.1.0a4-CVS  OK      OK
    #   http://bugs.endian.it/                      -            OK      OK
    #   http://www.co-ode.org/mantis/               1.0.0rc1     OK      OK
    #   http://acme.able.cs.cmu.edu/mantis/         1.0.6        OK      OK
    #   http://bugs.netmrg.net/                     1.0.7        OK      OK
    #   http://bugs.busybox.net/                    ??? 2006     OK      NOT OK (empty)
    #   https://bugtrack.alsa-project.org/alsa-bug/ 1.0.6        OK      NOT OK (empty)
    #   https://gnunet.org/mantis/                  ??? 2006     OK      OK
    #   http://www.futureware.biz/mantisdemo/       1.1.0rc1-CVS OK      OK

    # Custom opener that automatically sends anonymous credentials to
    # Mantis if (and only if) needed.
    _opener = ClientCookie.build_opener(MantisLoginHandler)

    def __init__(self, baseurl, use_csv_export=False):
        self.baseurl = baseurl.rstrip('/')

        # Use the CSV export method to get bug statuses. This is
        # disabled by default because there have been problems with
        # some Mantis installations sending empty exports.
        self.use_csv_export = use_csv_export
        if self.use_csv_export:
            # Bugs maps an integer bug ID to a dictionary with bug
            # data that we snarf from the CSV. We use an integer bug
            # ID because the bug ID for mantis comes prefixed with a
            # bunch of zeroes and it could get hard to match if we
            # really wanted to format it exactly the same (and also
            # because of the way we split lines below in
            # initializeRemoteBugDB().
            self.bugs = {}

    def urlopen(self, request, data=None):
        # We use ClientCookie to make following cookies transparent.
        # This is required for certain bugtrackers that require
        # cookies that actually do anything (as is the case with
        # Mantis). It's basically a drop-in replacement for
        # urllib2.urlopen() that tracks cookies. We also have a
        # customised ClientCookie opener to handle transparent
        # authentication.
        return self._opener.open(request, data)

    def initializeRemoteBugDB(self, bug_ids):
        if self.use_csv_export:
            self._fetchCSVExport(bug_ids)

    def _fetchCSVExport(self, bug_ids):
        # It's unfortunate that Mantis offers no way of limiting its CSV
        # export to a set of bugs; we end up having to pull the CSV for
        # the entire bugtracker at once (and some of them actually blow
        # up in the process!); this is why we ignore the bug_ids
        # argument here.

        if not bug_ids:
            # Well, not completely: if we have no ids to refresh from
            # this Mantis instance, don't even start the process and
            # save us some time and bandwidth.
            return

        # Next step is getting our query filter cookie set up; we need
        # to do this weird submit in order to get the closed bugs
        # included in the results; the default Mantis filter excludes
        # them. It's unlikely that all these parameters are actually
        # necessary, but it's easy to prepare the complete set from a
        # view_all_bugs.php form dump so let's keep it complete.
        data = {
           'type': '1',
           'page_number': '1',
           'view_type': 'simple',
           'reporter_id[]': '0',
           'user_monitor[]': '0',
           'handler_id[]': '0',
           'show_category[]': '0',
           'show_severity[]': '0',
           'show_resolution[]': '0',
           'show_profile[]': '0',
           'show_status[]': '0',
           # Some of the more modern Mantis trackers use
           # a value of 'hide_status[]': '-2' here but it appears that
           # [none] works. Oops, older Mantis uses 'none' here. Gross!
           'hide_status[]': '[none]',
           'show_build[]': '0',
           'show_version[]': '0',
           'fixed_in_version[]': '0',
           'show_priority[]': '0',
           'per_page': '50',
           'view_state': '0',
           'sticky_issues': 'on',
           'highlight_changed': '6',
           'relationship_type': '-1',
           'relationship_bug': '0',
           # Hack around the fact that the sorting parameter has
           # changed over time.
           'sort': 'last_updated',
           'sort_0': 'last_updated',
           'dir': 'DESC',
           'dir_0': 'DESC',
           'search': '',
           'filter': 'Apply Filter',
        }
        self.page = self._postPage("view_all_set.php?f=3", data)

        # Finally grab the full CSV export, which uses the
        # MANTIS_VIEW_ALL_COOKIE set in the previous step to specify
        # what's being viewed.
        csv_data = self._getPage("csv_export.php")
        # We store CSV in the instance just to make debugging easier.
        self.csv_data = csv_data

        # You may find this zero in "\r\n0" funny. Well I don't. This is
        # to work around the fact that Mantis' CSV export doesn't cope
        # with the fact that the bug summary can contain embedded "\r\n"
        # characters! I don't see a better way to handle this short of
        # not using the CSV module and forcing all lines to have the
        # same number as fields as the header.
        # XXX: kiko 2007-07-05: Report Mantis bug.
        # XXX: allenap 2007-09-06: Reported in LP as bug #137780.
        csv_data = csv_data.strip().split("\r\n0")

        if not csv_data:
            raise UnparseableBugData("Empty CSV for %s" % self.baseurl)

        # Clean out stray, unquoted newlines inside csv_data to avoid
        # the CSV module blowing up.
        csv_data = [s.replace("\r", "") for s in csv_data]
        csv_data = [s.replace("\n", "") for s in csv_data]

        # The first line of the CSV file is the header. We need to read
        # it because different Mantis instances have different header
        # ordering and even different columns in the export.
        self.headers = [h.lower() for h in csv_data.pop(0).split(",")]
        if len(self.headers) < 2:
            raise UnparseableBugData("CSV header mangled: %r" % self.headers)

        if not csv_data:
            # A file with a header and no bugs is also useless.
            raise UnparseableBugData("CSV for %s contained no bugs!"
                                     % self.baseurl)

        try:
            # Using the CSV reader is pretty much essential since the
            # data that comes back can include title text which can in
            # turn contain field separators -- you don't want to handle
            # the unquoting yourself.
            for bug_line in csv.reader(csv_data):
                self._processCSVBugLine(bug_line)
        except csv.Error, e:
            log.warn("Exception parsing CSV file: %s" % e)

    def _processCSVBugLine(self, bug_line):
        """Processes a single line of the CSV.

        Adds the bug it represents to self.bugs.
        """
        required_fields = ['id', 'status', 'resolution']
        bug = {}
        for header in self.headers:
            try:
                data = bug_line.pop(0)
            except IndexError:
                log.warn("Line %r incomplete" % bug_line)
                return
            bug[header] = data
        for field in required_fields:
            if field not in bug:
                log.warn("Bug %s lacked field %r" % (bug['id'], field))
                return
            try:
                # See __init__ for an explanation of why we use integer
                # IDs in the internal data structure.
                bug_id = int(bug['id'])
            except ValueError:
                log.warn("Bug with invalid ID: %r" % bug['id'])
                return

        self.bugs[bug_id] = bug

    def _checkForApplicationError(self, page_soup):
        """If Mantis does not find the bug it still returns a 200 OK
        response, so we need to look into the page to figure it out.

        If there is no error, None is returned.

        If there is an error, a 2-tuple of (code, message) is
        returned, both unicode strings.
        """
        app_error = page_soup.find(
            text=lambda node: (node.startswith('APPLICATION ERROR ')
                               and node.parent['class'] == 'form-title'
                               and not isinstance(node, Comment)))
        if app_error:
            app_error_code = ''.join(c for c in app_error if c.isdigit())
            app_error_message = app_error.findNext('p')
            if app_error_message is not None:
                app_error_message = app_error_message.string
            return app_error_code, app_error_message

        return None

    def _findValueRightOfKey(self, page_soup, key):
        """Scrape a value from a Mantis bug view page where the value
        is displayed to the right of the key.

        The Mantis bug view page uses HTML tables for both layout and
        representing tabular data, often within the same table. This
        method assumes that the key and value are on the same row,
        adjacent to one another, with the key preceeding the value:

        ...
        <td>Key</td>
        <td>Value</td>
        ...

        This method does not compensate for colspan or rowspan.
        """
        key_node = page_soup.find(
            text=lambda node: (node.strip() == key
                               and not isinstance(node, Comment)))
        if key_node is None:
            raise UnparseableBugData(
                "Key %r not found." % (key,))

        value_cell = key_node.findNext('td')
        if value_cell is None:
            raise UnparseableBugData(
                "Value cell for key %r not found." % (key,))

        value_node = value_cell.string
        if value_node is None:
            raise UnparseableBugData(
                "Value for key %r not found." % (key,))

        return value_node.strip()

    def _findValueBelowKey(self, page_soup, key):
        """Scrape a value from a Mantis bug view page where the value
        is displayed directly below the key.

        The Mantis bug view page uses HTML tables for both layout and
        representing tabular data, often within the same table. This
        method assumes that the key and value are within the same
        column on adjacent rows, with the key preceeding the value:

        ...
        <tr>...<td>Key</td>...</tr>
        <tr>...<td>Value</td>...</tr>
        ...

        This method does not compensate for colspan or rowspan.
        """
        key_node = page_soup.find(
            text=lambda node: (node.strip() == key
                               and not isinstance(node, Comment)))
        if key_node is None:
            raise UnparseableBugData(
                "Key %r not found." % (key,))

        key_cell = key_node.parent
        if key_cell is None:
            raise UnparseableBugData(
                "Cell for key %r not found." % (key,))

        key_row = key_cell.parent
        if key_row is None:
            raise UnparseableBugData(
                "Row for key %r not found." % (key,))

        try:
            key_pos = key_row.findAll('td').index(key_cell)
        except ValueError:
            raise UnparseableBugData(
                "Key cell in row for key %r not found." % (key,))

        value_row = key_row.findNextSibling('tr')
        if value_row is None:
            raise UnparseableBugData(
                "Value row for key %r not found." % (key,))

        value_cell = value_row.findAll('td')[key_pos]
        if value_cell is None:
            raise UnparseableBugData(
                "Value cell for key %r not found." % (key,))

        value_node = value_cell.string
        if value_node is None:
            raise UnparseableBugData(
                "Value for key %r not found." % (key,))

        return value_node.strip()

    def getRemoteStatus(self, bug_id):
        if not bug_id.isdigit():
            raise InvalidBugId(
                "Mantis (%s) bug number not an integer: %s" % (
                    self.baseurl, bug_id))

        if self.use_csv_export:
            status, resolution = self._getStatusFromCSV(bug_id)
        else:
            status, resolution = self._getStatusFromScrape(bug_id)

        # Use a colon and a space to join status and resolution because
        # there is a chance that statuses contain spaces, and because
        # it makes display of the data nicer.
        return "%s: %s" % (status, resolution)

    def _getStatusFromCSV(self, bug_id):
        try:
            bug = self.bugs[int(bug_id)]
        except KeyError:
            raise BugNotFound(bug_id)
        else:
            return bug['status'], bug['resolution']

    def _getStatusFromScrape(self, bug_id):
        # Only parse tables to save time and memory. If we didn't have
        # to check for application errors in the page (using
        # _checkForApplicationError) then we could be much more
        # specific than this.
        bug_page = BeautifulSoup(
            self._getPage('view.php?id=%s' % bug_id),
            convertEntities=BeautifulSoup.HTML_ENTITIES,
            parseOnlyThese=SoupStrainer('table'))

        app_error = self._checkForApplicationError(bug_page)
        if app_error:
            app_error_code, app_error_message = app_error
            # 1100 is ERROR_BUG_NOT_FOUND in Mantis (see
            # mantisbt/core/constant_inc.php) so we raise
            # BugNotFound.
            if app_error_code == '1100':
                raise BugNotFound(bug_id)
            else:
                raise BugWatchUpdateError(
                    "Mantis APPLICATION ERROR #%s: %s" % (
                    app_error_code, app_error_message))

        status = self._findValueRightOfKey(bug_page, 'Status')
        resolution = self._findValueRightOfKey(bug_page, 'Resolution')

        return status, resolution

    def convertRemoteStatus(self, status_and_resolution):
        if (not status_and_resolution or
            status_and_resolution == UNKNOWN_REMOTE_STATUS):
            return BugTaskStatus.UNKNOWN

        remote_status, remote_resolution = status_and_resolution.split(": ", 1)

        if remote_status == 'assigned':
            return BugTaskStatus.INPROGRESS
        if remote_status == 'feedback':
            return BugTaskStatus.INCOMPLETE
        if remote_status in ['new']:
            return BugTaskStatus.NEW
        if remote_status in ['confirmed', 'acknowledged']:
            return BugTaskStatus.CONFIRMED
        if remote_status in ['resolved', 'closed']:
            if remote_resolution == 'fixed':
                return BugTaskStatus.FIXRELEASED
            if remote_resolution == 'reopened':
                return BugTaskStatus.NEW
            if remote_resolution in ["unable to reproduce", "not fixable",
                                     'suspended']:
                return BugTaskStatus.INVALID
            if remote_resolution == "won't fix":
                return BugTaskStatus.WONTFIX
            if remote_resolution == 'duplicate':
                # XXX: kiko 2007-07-05: Follow duplicates
                return BugTaskStatus.INVALID
            if remote_resolution in ['open', 'no change required']:
                # XXX: kiko 2007-07-05: Pretty inconsistently used
                return BugTaskStatus.FIXRELEASED

        log.warn("Unknown status/resolution %s/%s" %
                 (remote_status, remote_resolution))
        return BugTaskStatus.UNKNOWN


class Trac(ExternalBugTracker):
    """An ExternalBugTracker instance for handling Trac bugtrackers."""

    ticket_url = 'ticket/%i?format=csv'
    batch_url = 'query?%s&order=resolution&format=csv'
    batch_query_threshold = 10

    def __init__(self, baseurl):
        # Trac can be really finicky about slashes in URLs, so we strip any
        # trailing slashes to ensure we don't incur its wrath in the form of
        # a 404.
        self.baseurl = baseurl.rstrip('/')

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
        # When there are less than batch_query_threshold bugs to update we
        # make one request per bug id to the remote bug tracker, providing it
        # supports CSV exports per-ticket. If the Trac instance doesn't support
        # exports-per-ticket we fail over to using the batch export method for
        # retrieving bug statuses.
        if (len(bug_ids) < self.batch_query_threshold and
            self.supportsSingleExports(bug_ids)):
            for bug_id in bug_ids:
                # If we can't get the remote bug for any reason a
                # BugTrackerConnectError will be raised at this point.
                remote_id, remote_bug = self.getRemoteBug(bug_id)
                self.bugs[remote_id] = remote_bug

        # For large lists of bug ids we retrieve bug statuses as a batch from
        # the remote bug tracker so as to avoid effectively DOSing it.
        else:
            self.bugs = self.getRemoteBugBatch(bug_ids)

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
                # CSV exports. In those cases we raise a warning.
                log.warn("Trac ticket %i defines no status" % bug_id)
                return UNKNOWN_REMOTE_STATUS

    def convertRemoteStatus(self, remote_status):
        """See IExternalBugTracker"""
        status_map = {
            'assigned': BugTaskStatus.CONFIRMED,
            # XXX: 2007-08-06 Graham Binns:
            #      We should follow dupes if possible.
            'duplicate': BugTaskStatus.CONFIRMED,
            'fixed': BugTaskStatus.FIXRELEASED,
            'invalid': BugTaskStatus.INVALID,
            'new': BugTaskStatus.NEW,
            'open': BugTaskStatus.NEW,
            'reopened': BugTaskStatus.NEW,
            'wontfix': BugTaskStatus.WONTFIX,
            'worksforme': BugTaskStatus.INVALID,
            UNKNOWN_REMOTE_STATUS: BugTaskStatus.UNKNOWN,
        }

        try:
            return status_map[remote_status]
        except KeyError:
            log.warn("Unknown status '%s'" % remote_status)
            return BugTaskStatus.UNKNOWN

class Roundup(ExternalBugTracker):
    """An ExternalBugTracker descendant for handling Roundup bug trackers."""

    # Our mapping of Roundup => Launchpad statuses.  Roundup statuses
    # are integer-only and highly configurable. Therefore we map the
    # statuses available by default so that they can be overridden by
    # subclassing the Roundup class.
    status_map = {
        1: BugTaskStatus.NEW,          # Roundup status 'unread'
        2: BugTaskStatus.CONFIRMED,    # Roundup status 'deferred'
        3: BugTaskStatus.INCOMPLETE,   # Roundup status 'chatting'
        4: BugTaskStatus.INCOMPLETE,   # Roundup status 'need-eg'
        5: BugTaskStatus.INPROGRESS,   # Roundup status 'in-progress'
        6: BugTaskStatus.INPROGRESS,   # Roundup status 'testing'
        7: BugTaskStatus.FIXCOMMITTED, # Roundup status 'done-cbb'
        8: BugTaskStatus.FIXRELEASED,  # Roundup status 'resolved'
        UNKNOWN_REMOTE_STATUS: BugTaskStatus.UNKNOWN
    }

    # XXX: 2007-08-29 Graham Binns
    #      I really don't like these URLs but Roundup seems to be very
    #      sensitive to changing them. These are the only ones that I
    #      can find that work consistently on all the roundup instances
    #      I can find to test them against, but I think that refining
    #      these should be looked into at some point.
    single_bug_export_url = (
        "issue?@action=export_csv&@columns=title,id,activity,status"
        "&@sort=id&@group=priority&@filter=id&@pagesize=50"
        "&@startwith=0&id=%i")
    batch_bug_export_url = (
        "issue?@action=export_csv&@columns=title,id,activity,status"
        "&@sort=activity&@group=priority&@pagesize=50&@startwith=0")

    def __init__(self, baseurl):
        # We strip any trailing slashes to ensure that we don't end up
        # requesting a URL that Roundup can't handle.
        self.baseurl = baseurl.rstrip('/')

    def convertRemoteStatus(self, remote_status):
        """See `IExternalBugTracker`."""
        if remote_status == UNKNOWN_REMOTE_STATUS:
            return self.status_map[remote_status]

        try:
            return self.status_map[int(remote_status)]
        except (KeyError, ValueError):
            log.warn("Unknown status '%s'" % remote_status)
            return BugTaskStatus.UNKNOWN

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

    def getRemoteStatus(self, bug_id):
        """See `ExternalBugTracker`."""
        try:
            bug_id = int(bug_id)
        except ValueError:
            raise InvalidBugId(
                "bug_id must be convertable an integer: %s" % str(bug_id))

        try:
            remote_bug = self.bugs[bug_id]
        except KeyError:
            raise BugNotFound(bug_id)
        else:
            try:
                return remote_bug['status']
            except KeyError:
                raise UnparseableBugData(
                    "Remote bug %s does not define a status.")
