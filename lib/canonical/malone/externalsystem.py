#!/usr/bin/env python 

import urllib
from xml.dom import minidom
from canonical.launchpad.database import BugSystem, BugSystemType

class UnknownBugSystemTypeError(Exception):
    """
    Exception class to catch systems we don't have a class for yet
    """

    def __init__(self, bugsystemtypename, bugsystemname):
        self.bugsystemtypename = bugsystemtypename
        self.bugsystemname = bugsystemname

    def __str__(self):
        return self.bugsystemtypename

class ExternalSystem(object):
    """
    Generic class for a remote system.  This is a pass-through class
    which loads and calls through to a subclass for each system type
    we know about,
    """

    def __init__(self, bugsystem):
        self.bugsystem = bugsystem
        self.bugsystemtype = bugsystem.bugsystemtype
        self.remotesystem = None
        if self.bugsystemtype.name == 'Bugzilla':
            self.remotesystem = Bugzilla(self.bugsystem.baseurl)
        if not self.remotesystem:
            raise NotImplementedError()

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
    """

    def __init__(self, baseurl):
        if baseurl[-1] == "/":
            baseurl = baseurl[:-1]
        self.baseurl = baseurl
    
    def get_bug_status(self, bug_id):
        """
        Retrieve the bug status from a bug in a remote Bugzilla system

        >>> watch = Bugzilla("http://bugzilla.mozilla.org")
        >>> watch.get_bug_status(11901)
        u'ASSIGNED'
        >>> watch.get_bug_status(251003)
        u'RESOLVED DUPLICATE'
        >>> watch.get_bug_status(12345)
        u'VERIFIED FIXED'
        """

        data = {'ctype'       : 'rdf',
                'form_name'   : 'buglist.cgi',
                'bug_id_type' : 'include',
                'bug_id'      : bug_id,
                }
        # Eventually attach authentication information here if we need it
        #data.update({'Bugzilla_login'    : login,
        #             'Bugzilla_password' : password,
        #             'GoAheadAndLogIn'   : 1})
        getdata = urllib.urlencode(data)
        url = urllib.urlopen("%s/buglist.cgi" % self.baseurl, getdata)
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

        >>> watch = Bugzilla("http://bugzilla.mozilla.org/")
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
