#!/usr/bin/env python 

import urllib
import urllib2
from xml.dom import minidom

from canonical.lp.dbschema import BugTrackerType
from canonical.launchpad.scripts import log

# The user agent we send in our requests
LP_USER_AGENT = "Launchpad Bugscraper/0.1 (http://launchpad.net/malone)"


class UnknownBugTrackerTypeError(Exception):
    """
    Exception class to catch systems we don't have a class for yet
    """

    def __init__(self, bugtrackertypename, bugtrackername):
        self.bugtrackertypename = bugtrackertypename
        self.bugtrackername = bugtrackername

    def __str__(self):
        return self.bugtrackertypename


class BugTrackerConnectError(Exception):
    """
    Exception class to catch misc errors contacting a bugtracker
    """

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

    def get_bug_status(self, bug_id):
        return self.remotesystem.get_bug_status(bug_id)

    def malonify_status(self, status):
        return self.remotesystem.malonify_status(status)


class Bugzilla(ExternalSystem):
    """
    A class that deals with communications with a remote Bugzilla system

    >>> watch = Bugzilla("http://bugzilla.mozilla.org")
    >>> watch.baseurl
    'http://bugzilla.mozilla.org'
    >>> watch = Bugzilla("http://bugzilla.mozilla.org/")
    >>> watch.baseurl
    'http://bugzilla.mozilla.org'
    >>> watch = Bugzilla("https://bugzilla.mozilla.org/")
    >>> watch.baseurl
    'https://bugzilla.mozilla.org'
    >>> watch = Bugzilla("http://bugs.kde.org/")
    >>> watch.version
    u'2.16.10'
    """

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

    def _probe_version(self):
        # For some reason, bugs.kde.org doesn't allow the regular urllib
        # user-agent string (Python-urllib/2.x) to access their
        # bugzilla, so we send our own instead.
        request = urllib2.Request("%s/xml.cgi?id=1" % self.baseurl,
                                  headers={'User-agent': LP_USER_AGENT})
        try:
            url = urllib2.urlopen(request)
        except (urllib2.HTTPError, urllib2.URLError), val:
            raise BugTrackerConnectError(self.baseurl, val)
        ret = url.read()
        document = minidom.parseString(ret)
        bugzilla = document.getElementsByTagName("bugzilla")
        if not bugzilla:
            return None
        version = bugzilla[0].getAttribute("version")
        return version

    def get_bug_status(self, bug_id):
        """
        Retrieve the bug status from a bug in a remote Bugzilla system.
        Returns None if it cannot be determined.

        >>> watch = Bugzilla("https://bugzilla.mozilla.org")
        >>> watch.get_bug_status(11901)
        u'RESOLVED FIXED'
        >>> watch.get_bug_status(251003)
        u'RESOLVED DUPLICATE'
        >>> watch.get_bug_status(12345)
        u'VERIFIED FIXED'
        """

        data = {'form_name'   : 'buglist.cgi',
                'bug_id_type' : 'include',
                'bug_id'      : bug_id,
                }
        if self.version < '2.17.1':
            data.update({'format' : 'rdf'})
            status_tag = "bz:status"
        else:
            data.update({'ctype'  : 'rdf'})
            status_tag = "bz:bug_status"
        # Eventually attach authentication information here if we need it
        #data.update({'Bugzilla_login'    : login,
        #             'Bugzilla_password' : password,
        #             'GoAheadAndLogIn'   : 1})
        getdata = urllib.urlencode(data)
        url = urllib2.urlopen("%s/buglist.cgi?%s" % (self.baseurl, getdata))
        ret = url.read()
        document = minidom.parseString(ret)
        result = None
        if len(document.getElementsByTagName("bz:id")) > 0:
            try:
                status_node = document.getElementsByTagName(status_tag)[0]
            except IndexError:
                log.warn('No status found for %s bug %s' 
                         (self.baseurl, bug_id))
                return None
            result = status_node.childNodes[0].data
            try:
                resolution_node = document.getElementsByTagName(
                        "bz:resolution")[0]
            except IndexError:
                log.warn('No resolution found for %s bug %s',
                         (self.baseurl, bug_id))
                return None
            if len(resolution_node.childNodes) > 0:
                result = "%s %s" % (result, resolution_node.childNodes[0].data)
        return result

    def malonify_status(self, status):
        """
        translate statuses from this system to the equivalent Malone status

        >>> watch = Bugzilla("https://bugzilla.mozilla.org/")
        >>> watch.malonify_status('RESOLVED FIXED')
        'closed'
        >>> watch.malonify_status('ASSIGNED')
        'open'
        >>> watch.malonify_status('UNCONFIRMED')
        'new'
        >>> watch.malonify_status('NEW')
        'new'
        >>> watch.malonify_status('VERIFIED WONTFIX')
        'closed'
        >>> watch.malonify_status('CLOSED INVALID')
        'closed'

        """
        resolution = ""
        if " " in status:
            separated = status.split(" ")
            status = separated[0]
            resolution = separated[1]
        if status in ('UNCONFIRMED','NEW'):
            return 'new'
        elif status in ('ASSIGNED','REOPENED'):
            return 'open'
        elif status in ('RESOLVED','VERIFIED','CLOSED'):
            return 'closed'
        else:
            raise NotImplementedError("Unsupported status %s at %s" 
                                      % (status, self.baseurl))


def _test():
    import doctest, externalsystem
    return doctest.testmod(externalsystem)


if __name__ == "__main__":
    _test()

