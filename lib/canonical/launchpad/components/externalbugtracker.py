# Copyright 2006 Canonical Ltd.  All rights reserved.

"""External bugtrackers."""

__metaclass__ = type

import urllib
import urllib2
import xml.parsers.expat
from xml.dom import minidom

from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.lp.dbschema import BugTrackerType, BugTaskStatus
from canonical.launchpad.scripts import log
from canonical.launchpad.interfaces import IExternalBugtracker

# The user agent we send in our requests
LP_USER_AGENT = "Launchpad Bugscraper/0.1 (http://launchpad.net/malone)"


class UnknownBugTrackerTypeError(Exception):
    """ Exception class to catch systems we don't have a class for yet."""

    def __init__(self, bugtrackertypename, bugtrackername):
        self.bugtrackertypename = bugtrackertypename
        self.bugtrackername = bugtrackername

    def __str__(self):
        return self.bugtrackertypename


class BugTrackerConnectError(Exception):
    """Exception class to catch misc errors contacting a bugtracker."""

    def __init__(self, url, error):
        self.url = url
        self.error = str(error)

    def __str__(self):
        return "%s: %s" % (self.url, self.error)


class ExternalSystem(object):
    """
    Generic class for a remote system.  This is a pass-through class
    which loads and calls through to a subclass for each system type
    we know about,
    """

    implements(IExternalBugtracker)

    def __init__(self, bugtracker, version=None):
        self.bugtracker = bugtracker
        self.bugtrackertype = bugtracker.bugtrackertype
        self.remotesystem = None
        if self.bugtrackertype == BugTrackerType.BUGZILLA:
            self.remotesystem = Bugzilla(self.bugtracker.baseurl, version)
        if not self.remotesystem:
            raise UnknownBugTrackerTypeError(self.bugtrackertype.name,
                self.bugtracker.name)
        self.version = self.remotesystem.version

    def malonify_status(self, status):
        return self.remotesystem.malonify_status(status)

    def updateBugWatches(self, bug_watches):
        """Update the given bug watches."""
        return self.remotesystem.updateBugWatches(bug_watches)


class Bugzilla(ExternalSystem):
    """A class that deals with communications with a remote Bugzilla system."""

    def __init__(self, baseurl, version=None):
        if baseurl[-1] == "/":
            baseurl = baseurl[:-1]
        self.baseurl = baseurl
        if version != None:
            self.version = version
        else:
            self.version = self._probe_version()
        if not self.version or self.version < '2.16':
            raise NotImplementedError("Unsupported version %r for %s" 
                                      % (self.version, baseurl))
    def _getPage(self, page):
        """GET the specified page on the remote HTTP server."""
        # For some reason, bugs.kde.org doesn't allow the regular urllib
        # user-agent string (Python-urllib/2.x) to access their
        # bugzilla, so we send our own instead.
        request = urllib2.Request("%s/%s" % (self.baseurl, page),
                                  headers={'User-agent': LP_USER_AGENT})
        try:
            url = urllib2.urlopen(request)
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
        url = urllib2.urlopen(request, data=post_data)
        page_contents = url.read()
        return page_contents

    def _probe_version(self):
        version_xml = self._getPage('xml.cgi?id=1')
        try:
            document = minidom.parseString(version_xml)
        except xml.parsers.expat.ExpatError, e:
            raise BugTrackerConnectError(self.baseurl, "Failed to parse output "
                                         "when probing for version: %s" % e)
        bugzilla = document.getElementsByTagName("bugzilla")
        if not bugzilla:
            return None
        version = bugzilla[0].getAttribute("version")
        return version

    def malonify_status(self, status):
        """Translate a status from this system to the equivalent Malone status.

        Bugzilla status consist of two parts separated by space, where
        the last part is the resolution. The resolution is optional.
        """
        if ' ' in status:
            status, resolution = status.split(' ')
        else:
            resolution = ''

        if status == 'ASSIGNED':
           malone_status = BugTaskStatus.CONFIRMED
        elif status == 'NEEDINFO':
            malone_status = BugTaskStatus.NEEDSINFO
        elif status == 'PENDINGUPLOAD':
            malone_status = BugTaskStatus.FIXCOMMITTED
        elif status in ['RESOLVED', 'VERIFIED', 'CLOSED']:
            # depends on the resolution:
            if resolution == 'FIXED':
                malone_status = BugTaskStatus.FIXRELEASED
            else:
                #XXX: Which are the valid resolutions? We should fail
                #     if we don't know of the resolution. Bug 31745.
                #     -- Bjorn Tillenius, 2005-02-03
                malone_status = BugTaskStatus.REJECTED
        elif status in ['UNCONFIRMED', 'REOPENED', 'NEW', 'UPSTREAM']:
            malone_status = BugTaskStatus.UNCONFIRMED
        else:
            if status != 'UNKNOWN':
                log.warning(
                    "Unknown Bugzilla status '%s' at %s" % (
                        status, self.baseurl))
            return 'Unknown'

        return malone_status.title

    def updateBugWatches(self, bug_watches):
        """Update the given bug watches."""
        bug_watches_by_remote_bug = {}
        for bug_watch in bug_watches:
            bug_watches_by_remote_bug[bug_watch.remotebug] = bug_watch
        bug_ids_to_update = set(bug_watches_by_remote_bug.keys())

        data = {'form_name'   : 'buglist.cgi',
                'bug_id_type' : 'include',
                'bug_id'      : ','.join(bug_ids_to_update),
                }
        if self.version < '2.17.1':
            data.update({'format' : 'rdf'})
            status_tag = "bz:status"
        else:
            data.update({'ctype'  : 'rdf'})
            status_tag = "bz:bug_status"
        buglist_xml = self._postPage('buglist.cgi', data)
        try:
            document = minidom.parseString(buglist_xml)
        except xml.parsers.expat.ExpatError, e:
            log.error('Failed to parse XML description for %s bugs %s: %s' %
                      (self.baseurl, bug_ids, e))
            return None
        result = None
        bug_nodes = document.getElementsByTagName('bz:bug')
        found_bug_ids = set()
        for bug_node in bug_nodes:
            bug_id_nodes = bug_node.getElementsByTagName("bz:id")
            assert len(bug_id_nodes) == 1, "Should be only one id node."
            bug_id_node = bug_id_nodes[0]
            assert len(bug_id_node.childNodes) == 1, (
                "id node should contain a non-empty text string.")
            bug_id = str(bug_id_node.childNodes[0].data)
            found_bug_ids.add(bug_id)

            status_nodes = bug_node.getElementsByTagName(status_tag)
            assert len(status_nodes) == 1, "Should be only one status node."
            bug_status_node = status_nodes[0]
            assert len(bug_status_node.childNodes) == 1, (
                "status node should contain a non-empty text string.")
            status = bug_status_node.childNodes[0].data

            resolution_nodes = bug_node.getElementsByTagName('bz:resolution')
            assert len(resolution_nodes) <= 1, (
                "Only one resolution node is allowed.")
            if resolution_nodes:
                assert len(resolution_nodes[0].childNodes) <= 1, (
                    "Resolution should contain a, possible empty, string.")
                if resolution_nodes[0].childNodes:
                    resolution = resolution_nodes[0].childNodes[0].data
                    status += ' %s' % resolution

            bug_watch = bug_watches_by_remote_bug[bug_id]
            if bug_watch.remotestatus != status:
                log.debug('Updating status for remote bug #%s' % bug_id)
                bug_watch.remotestatus = status
                bug_watch.lastchanged = UTC_NOW

            bug_watch.lastchecked = UTC_NOW

        not_found_bugs = bug_ids_to_update.difference(found_bug_ids)
        for not_found_id in not_found_bugs:
            log.warn(
                "Didn't find bug #%s on %s." % (not_found_id, self.baseurl))
            bug_watch = bug_watches_by_remote_bug[not_found_id]
            bug_watch.remotestatus = 'UNKNOWN'
            bug_watch.lastchanged = UTC_NOW
            bug_watch.lastchecked = UTC_NOW

        return result

