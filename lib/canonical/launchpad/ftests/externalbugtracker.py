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

    def __init__(self, baseurl, version=None):
        Bugzilla.__init__(self, baseurl, version=version)

        # A dict containing all bugs in the form of
        # $bug_id: ($status, $resolution)
        self.bugzilla_bugs = {
            3224: ('RESOLVED', 'FIXED'),
            328430: ('UNCONFIRMED', ''),
        }

    def _getPage(self, page):
        """GET a page.

        Only handles xml.cgi?id=1 so far.
        """
        if self.trace_calls:
            print "CALLED _getPage()"
        if page == 'xml.cgi?id=1':
            data = read_test_file('gnome_bugzilla_version.xml')
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
        if page == 'buglist.cgi':
            buglist_xml = read_test_file('gnome_buglist.xml')
            bug_ids = str(form['bug_id']).split(',')
            bug_li_items = []
            status_tag = None
            for bug_id in bug_ids:
                # Alternate status tag name to ensure we match both tag
                # formats; see comment in Bugzilla._initializeRemoteBugDB
                # for details.
                if status_tag:
                    status_tag = "status"
                else:
                    status_tag = "bug_status"
                bug_id = int(bug_id)
                if bug_id not in self.bugzilla_bugs:
                    #Unknown bugs aren't included in the resulting xml.
                    continue
                bug_status, bug_resolution = self.bugzilla_bugs[int(bug_id)]
                bug_item = read_test_file('gnome_bug_li_item.xml') % {
                    'status_tag': status_tag, 'bug_id': bug_id,
                    'status': bug_status, 'resolution': bug_resolution,
                    # Add some utf8 to test bug 61129
                    'non_ascii_utf8': '\xc3\xa9'
                    }
                bug_li_items.append(bug_item)
            return buglist_xml % {
                'bug_li_items': '\n'.join(bug_li_items),
                'page': page}
        else:
            raise AssertionError('Unknown page: %s' % page)

