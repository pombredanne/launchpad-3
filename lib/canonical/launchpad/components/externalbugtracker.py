# Copyright 2006 Canonical Ltd.  All rights reserved.

"""External bugtrackers."""

__metaclass__ = type

import csv
import os.path
import urllib
import urllib2
import ClientCookie
import xml.parsers.expat
from xml.dom import minidom

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
        # Bugs maps an integer bug ID to a dictionary with bug data that
        # we snarf from the CSV. We use an integer bug ID because the
        # bug ID for mantis comes prefixed with a bunch of zeroes and it
        # could get hard to match if we really wanted to format it
        # exactly the same (and also because of the way we split lines
        # below in initializeRemoteBugDB().
        self.bugs = {}

    def urlopen(self, request, data=None):
        # We use ClientCookie to make following cookies transparent.
        # This is required for certain bugtrackers that require cookies
        # that actually do anything (as is the case with Mantis). It's
        # basically a drop-in replacement for urllib.urlopen() that
        # tracks cookies.
        return ClientCookie.urlopen(request, data)

    def initializeRemoteBugDB(self, bug_ids):
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

        # We hit the login page first to authenticate; some sites
        # require us to do this silly authenticatiion; others just let
        # us in with no authentication step. I suspect some sites will
        # reject our authentication here and the rest of the process
        # will blow up. This sets MANTIS_STRING_COOKIE, btw.
        self._getPage("login.php?username=guest&password=guest")
        # Older versions of Mantis have a special anonymous login page;
        # why not give that a try too? ;-)
        self._getPage("login_anon.php")

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
        csv_data = csv_data.strip().split("\r\n0")

        if not csv_data:
            raise UnparseableBugData("Empty CSV for %s" % self.baseurl)

        # Clean out stray, unqouted newlines inside csv_data to avoid
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
                self._processBugLine(bug_line)
        except csv.Error, e:
            log.warn("Exception parsing CSV file: %s" % e)

    def _processBugLine(self, bug_line):
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

    def getRemoteStatus(self, bug_id):
        if not bug_id.isdigit():
            raise InvalidBugId(
                "Mantis (%s) bug number not an integer: %s" % (
                    self.baseurl, bug_id))
        try:
            bug = self.bugs[int(bug_id)]
        except KeyError:
            raise BugNotFound(bug_id)

        # Use a colon and a space to join status and resolution because
        # there is a chance that statuses contain spaces, and because
        # it makes display of the data nicer.
        return "%s: %s" % (bug['status'], bug['resolution'])

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

