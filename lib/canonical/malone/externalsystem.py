#!/usr/bin/env python 

import urllib
import urllib2
from xml.dom import minidom
from canonical.launchpad.database.bugtracker import BugTracker, BugTrackerType

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
        if self.bugtrackertype.name == 'bugzilla':
            self.remotesystem = Bugzilla(self.bugtracker.baseurl,version)
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

    >>> watch = Bugzilla("https://bugzilla.mozilla.org")
    >>> watch.baseurl
    'https://bugzilla.mozilla.org'
    >>> watch = Bugzilla("https://bugzilla.mozilla.org/")
    >>> watch.baseurl
    'https://bugzilla.mozilla.org'
    """

    def __init__(self, baseurl, version=None):
        if baseurl[-1] == "/":
            baseurl = baseurl[:-1]
        self.baseurl = baseurl
        if version != None:
            self.version = version
        else:
            self.version = self._probe_version()
        if self.version < '2.16':
            raise NotImplementedError()

    def _probe_version(self):
        #print "probing version of %s" % self.baseurl
        try:
            url = urllib2.urlopen("%s/xml.cgi?id=1" % self.baseurl)
        except (urllib2.HTTPError, urllib2.URLError), val:
            raise BugTrackerConnectError(self.baseurl, val)
        ret = url.read()
        document = minidom.parseString(ret)
        bugzilla = document.getElementsByTagName("bugzilla")
        version = bugzilla[0].getAttribute("version")
        return version
    
    def get_bug_status(self, bug_id):
        """
        Retrieve the bug status from a bug in a remote Bugzilla system

        >>> watch = Bugzilla("https://bugzilla.mozilla.org")
        >>> watch.get_bug_status(11901)
        u'ASSIGNED'
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
        else:
            data.update({'ctype'  : 'rdf'})
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
            status_node = document.getElementsByTagName("bz:bug_status")[0]
            result = status_node.childNodes[0].data
            resolution_node = document.getElementsByTagName("bz:resolution")[0]
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
            raise NotImplementedError()

def _test():
    import doctest, externalsystem
    return doctest.testmod(externalsystem)

if __name__ == "__main__":
    _test()

# DO NOT EDIT BELOW THIS LINE
# arch-tag: 1c567a56-be63-4bda-a488-07028951bd9e
