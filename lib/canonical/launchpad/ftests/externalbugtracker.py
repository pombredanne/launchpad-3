# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Helper classes for testing ExternalSystem."""

__metaclass__ = type

import os

from canonical.launchpad.components.externalbugtracker import Bugzilla


def read_test_file(name):
    """Return the contents of the test file named :name:

    Test files are located in lib/canonical/launchpad/ftests/testfiles
    """
    file_path = os.path.join(os.path.dirname(__file__), 'testfiles', name)

    test_file = open(file_path, 'r')
    return test_file.read()


class TestBugzilla(Bugzilla):
    """Bugzilla ExternalSystem for use in tests.

    It overrides _getPage and _postPage, so that access to a real Bugzilla
    instance isn't needed.
    """

    trace_calls = False

    version_file = 'gnome_bugzilla_version.xml'
    buglist_file = 'gnome_buglist.xml'
    bug_item_file = 'gnome_bug_li_item.xml'

    buglist_page = 'buglist.cgi'
    bug_id_form_element = 'bug_id'

    def __init__(self, baseurl, version=None):
        """Return a dict with bugs in the form bug_id: (status, resolution)"""
        Bugzilla.__init__(self, baseurl, version=version)
        self.bugzilla_bugs = {3224: ('RESOLVED', 'FIXED'),
                              328430: ('UNCONFIRMED', '')}

    def _getPage(self, page):
        """GET a page.

        Only handles xml.cgi?id=1 so far.
        """
        if self.trace_calls:
            print "CALLED _getPage()"
        if page == 'xml.cgi?id=1':
            data = read_test_file(self.version_file)
            # Add some latin1 to test bug 61129
            return data % dict(non_ascii_latin1="\xe9")
        else:
            raise AssertionError('Unknown page: %s' % page)

    def _postPage(self, page, form):
        """POST to the specified page.

        :form: is a dict of form variables being POSTed.

        Only handles buglist.cgi so far.
        """
        if self.trace_calls:
            print "CALLED _postPage()"
        if page == self.buglist_page:
            buglist_xml = read_test_file(self.buglist_file)
            bug_ids = str(form[self.bug_id_form_element]).split(',')
            bug_li_items = []
            status_tag = None
            for bug_id in bug_ids:
                bug_id = int(bug_id)
                if bug_id not in self.bugzilla_bugs:
                    #Unknown bugs aren't included in the resulting xml.
                    continue
                bug_status, bug_resolution = self.bugzilla_bugs[int(bug_id)]
                bug_item = read_test_file(self.bug_item_file) % {
                    'bug_id': bug_id,
                    'status': bug_status,
                    'resolution': bug_resolution,
                    }
                bug_li_items.append(bug_item)
            return buglist_xml % {
                'bug_li_items': '\n'.join(bug_li_items),
                'page': page
            }
        else:
            raise AssertionError('Unknown page: %s' % page)

class TestIssuezilla(TestBugzilla):
    version_file = 'issuezilla_version.xml'
    buglist_file = 'issuezilla_buglist.xml'
    bug_item_file = 'issuezilla_item.xml'

    buglist_page = 'xml.cgi'
    bug_id_form_element = 'id'

    def __init__(self, baseurl, version=None):
        """Return a dict with bugs in the form bug_id: (status, resolution)"""
        Bugzilla.__init__(self, baseurl, version=version)
        self.bugzilla_bugs = {2000: ('RESOLVED', 'FIXED'),
                              123543: ('ASSIGNED', '')}


class TestOldBugzilla(TestBugzilla):
    version_file = 'ximian_bugzilla_version.xml'
    buglist_file = 'ximian_buglist.xml'
    bug_item_file = 'ximian_bug_item.xml'

    buglist_page = 'xml.cgi'
    bug_id_form_element = 'id'

    def __init__(self, baseurl, version=None):
        """Return a dict with bugs in the form bug_id: (status, resolution)"""
        Bugzilla.__init__(self, baseurl, version=version)
        self.bugzilla_bugs = {42: ('RESOLVED', 'FIXED'),
                              123543: ('ASSIGNED', '')}

# XXX: still missing tests
# Add some utf8 to test bug 61129
#   'non_ascii_utf8': '\xc3\xa9'
#'status_tag': 
#   Alternate status tag name to ensure we match both tag
#   formats; see comment in Bugzilla._initializeRemoteBugDB
#   for details.
#   if status_tag:
#       status_tag = "status"
#   else:
#       status_tag = "bug_status"
# UnparseableBugData


