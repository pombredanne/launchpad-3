# Copyright 2006 Canonical Ltd.  All rights reserved.

"""External bugtrackers."""

__metaclass__ = type

import csv
import os.path
import urllib
import urllib2
import xml.parsers.expat
from xml.dom import minidom

from BeautifulSoup import BeautifulSoup, Comment
from zope.interface import implements

from canonical.config import config
from canonical import encoding
from canonical.database.constants import UTC_NOW
from canonical.lp.dbschema import BugTrackerType, BugTaskStatus
from canonical.launchpad.scripts import log, debbugs
from canonical.launchpad.interfaces import (
    IExternalBugtracker, UNKNOWN_REMOTE_STATUS)

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
    else:
        raise UnknownBugTrackerTypeError(bugtrackertype.name,
            bugtracker.name)


class ExternalBugTracker:
    """Base class for an external bug tracker."""

    implements(IExternalBugtracker)

    def urlopen(self, request, data=None):
        return urllib2.urlopen(request, data)

    def initializeRemoteBugDB(self, bug_ids):
        """Do any initialization before each bug watch is updated.

        It's optional to override this method.
        """

    def getRemoteStatus(self, bug_id):
        """Return the remote status for the given bug id.

        Raise BugNotFound if the bug can't be found.
        Raise InvalidBugId if the bug id has an unexpected format.
        """
        raise NotImplementedError(self.getRemoteStatus)

    def _getPage(self, page):
        """GET the specified page on the remote HTTP server."""
        # For some reason, bugs.kde.org doesn't allow the regular urllib
        # user-agent string (Python-urllib/2.x) to access their
        # bugzilla, so we send our own instead.
        request = urllib2.Request("%s/%s" % (self.baseurl, page),
                                  headers={'User-agent': LP_USER_AGENT})
        try:
            url = self.urlopen(request)
        except (urllib2.HTTPError, urllib2.URLError), val:
            raise BugTrackerConnectError(self.baseurl, val)
        page_contents = url.read()
        return page_contents

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
            if not bug_watches_by_remote_bug.has_key(remote_bug):
                bug_watches_by_remote_bug[remote_bug] = []
            bug_watches_by_remote_bug[remote_bug].append(bug_watch)

        bug_ids_to_update = bug_watches_by_remote_bug.keys()
        self.initializeRemoteBugDB(bug_ids_to_update)

        for bug_id, bug_watches in bug_watches_by_remote_bug.items():
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

class Mantis(ExternalBugTracker):
    # Example sites:
    #   http://www.atutor.ca/atutor/mantis/         1.0.7       NOT OK
    #   http://bugs.mantisbt.org/                   1.1.0a4-CVS NOT OK (login.php HTTP 404)
    #   http://bugs.endian.it/                      -           NOT OK (HTTP 404)
    #   http://www.co-ode.org/mantis/               1.0.0rc1    OK  (322 bugs)
    #   http://acme.able.cs.cmu.edu/mantis/         1.0.6       OK  (531 bugs)
    #   http://bugs.netmrg.net/                     1.0.7       NOT OK (login.php infinite HTTP 302 loop)
    #   http://bugs.busybox.net/                    ??? 2006    NOT OK (login.php HTTP 404)
    #   https://bugtrack.alsa-project.org/alsa-bug/ 1.0.6       NOT OK (csv_export.php yields no data)
    #   https://gnunet.org/mantis/                  ??? 2006    OK (787 bugs)

    # These get set in initializeRemoteBugDB()
    headers = None
    bugs = None

    def __init__(self, baseurl):
        self.baseurl = baseurl

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
            raise KeyError(key)

        value_cell = key_node.findNext('td')
        value_node = value_cell.string

        if value_node is None:
            raise KeyError(key)
        return value_node.string.strip()

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
            raise KeyError(key)

        key_cell = key_node.parent
        key_row = key_cell.parent
        key_pos = key_row.findAll('td').index(key_cell)

        value_row = key_row.findNextSibling('tr')
        value_cell = value_row.findAll('td')[key_pos]
        value_node = value_cell.string

        if value_node is None:
            raise KeyError(key)
        return value_node.strip()

    def getRemoteStatus(self, bug_id):
        if not bug_id.isdigit():
            raise InvalidBugId(
                "Mantis (%s) bug number not an integer: %s" % (
                    self.baseurl, bug_id))
        try:
            bug_page = BeautifulSoup(
                self._getPage('view.php?id=%s' % bug_id),
                convertEntities=BeautifulSoup.HTML_ENTITIES)
            status = self._findValueRightOfKey(bug_page, 'Status')
            resolution = self._findValueRightOfKey(bug_page, 'Resolution')
        except KeyError:
            raise BugNotFound(bug_id)

        # Use a colon and a space to join status and resolution because
        # there is a chance that statuses contain spaces, and because
        # it makes display of the data nicer.
        return "%s: %s" % (status, resolution)

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

    def initializeRemoteBugDB(self, bug_ids):
        """Do any initialization before each bug watch is updated.

        If the URL specified for the bugtracker is not valid a
        BugTrackerConnectError will be raised.
        """
        self.bugs = {}
        # Trac offers two ways for us to get bug details from them in CSV
        # format: individually or in groups. For large lists of bug ids we get
        # them as a batch from the remote bug tracker so as to avoid
        # effectively DOSing it.
        if len(bug_ids) > self.batch_query_threshold:
            id_string = '&'.join(['id=%s' % id for id in bug_ids])
            query_url = "%s/%s" % (self.baseurl, self.batch_url % id_string)
            try:
                csv_data = self.urlopen(query_url)
            except (urllib2.HTTPError, urllib2.URLError), val:
                raise BugTrackerConnectError(query_url, val)

            remote_bugs = csv.DictReader(csv_data)
            for remote_bug in remote_bugs:
                # We're only interested in the bug if it's one of the ones in
                # bug_ids, just in case we get all the tickets in the Trac
                # instance back instead of only the ones we want.
                if remote_bug['id'] not in bug_ids:
                    continue

                self.bugs[int(remote_bug['id'])] = remote_bug

        else:
            # When there aren't more than batch_query_threshold bugs to update
            # we make one request per bug id to the remote bug tracker, which
            # (providing it's a reasonably up-to-date Trac instance) will give
            # us a CSV export of the ticket we ask for. If it doesn't, we can
            # safely assume that it either doesn't support this functionality
            # or has this functionality deliberately disabled; either way
            # there is little
            # we can do about it.
            for bug_id in bug_ids:
                # If we can't get the remote bug for any reason a
                # BugTrackerConnectError will be raised at this point.
                # We don't use _getPage at this point for the simple reason
                # that it doesn't return a file-like object, so we can't use
                # the csv module's helpful DictReader on its output.
                bug_id = int(bug_id)
                try:
                    csv_data = self.urlopen(
                        "%s/%s" % (self.baseurl, self.ticket_url % bug_id))
                except (urllib2.HTTPError, urllib2.URLError), val:
                    raise BugTrackerConnectError(self.baseurl, val)

                reader = csv.DictReader(csv_data)
                self.bugs[bug_id] = reader.next()


    def getRemoteStatus(self, bug_id):
        """Return the remote status for the given bug id.

        Raise BugNotFound if the bug can't be found.
        Raise InvalidBugId if the bug id has an unexpected format.
        """
        try:
            bug_id = int(bug_id)
        except ValueError:
            raise InvalidBugId(
                "bug_id must be convertable an integer: %s" + str(bug_id))

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
            return remote_bug['status']

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
