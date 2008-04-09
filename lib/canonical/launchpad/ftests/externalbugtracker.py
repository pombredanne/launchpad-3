# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0231

"""Helper classes for testing ExternalSystem."""

__metaclass__ = type

import os
import re
import time
import urlparse
import xmlrpclib

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import commit, ZopelessTransactionManager
from canonical.launchpad.components.externalbugtracker import (
    Bugzilla, BugNotFound, BugTrackerConnectError, ExternalBugTracker,
    DebBugs, Mantis, Trac, Roundup, RequestTracker, SourceForge)
from canonical.launchpad.ftests import login, logout
from canonical.launchpad.interfaces import (
    BugTaskImportance, BugTaskStatus, UNKNOWN_REMOTE_IMPORTANCE,
    UNKNOWN_REMOTE_STATUS)
from canonical.launchpad.database import BugTracker
from canonical.launchpad.interfaces import IBugTrackerSet, IPersonSet
from canonical.launchpad.scripts import checkwatches, debbugs
from canonical.testing.layers import LaunchpadZopelessLayer


def new_bugtracker(bugtracker_type, base_url='http://bugs.some.where'):
    """Create a new bug tracker using the 'launchpad db user.

    Before calling this function, the current transaction should be
    commited, since the current connection to the database will be
    closed. After returning from this function, a new connection using
    the checkwatches db user is created.
    """
    assert ZopelessTransactionManager._installed is not None, (
        "This function can only be used for Zopeless tests.")
    LaunchpadZopelessLayer.switchDbUser('launchpad')
    owner = getUtility(IPersonSet).getByEmail('no-priv@canonical.com')
    bugtracker_set = getUtility(IBugTrackerSet)
    index = 1
    name = '%s-checkwatches' % (bugtracker_type.name.lower(),)
    while bugtracker_set.getByName("%s-%d" % (name, index)) is not None:
        index += 1
    name += '-%d' % index
    bugtracker = BugTracker(
        name=name,
        title='%s *TESTING*' % (bugtracker_type.title,),
        bugtrackertype=bugtracker_type,
        baseurl=base_url,
        summary='-', contactdetails='-',
        owner=owner)
    commit()
    LaunchpadZopelessLayer.switchDbUser(config.checkwatches.dbuser)
    return getUtility(IBugTrackerSet).getByName(name)

def read_test_file(name):
    """Return the contents of the test file named :name:

    Test files are located in lib/canonical/launchpad/ftests/testfiles
    """
    file_path = os.path.join(os.path.dirname(__file__), 'testfiles', name)

    test_file = open(file_path, 'r')
    return test_file.read()


def print_bugwatches(bug_watches, convert_remote_status=None):
    """Print the bug watches for a BugTracker, ordered by remote bug id.

    :bug_watches: A set of BugWatches to print.

    :convert_remote_status: A convertRemoteStatus method from an
        ExternalBugTracker instance, which will convert a bug's remote
        status into a Launchpad BugTaskStatus. See
        `ExternalBugTracker.convertRemoteStatus()`.

    Bug watches will be printed in the form: Remote bug <id>:
    <remote_status>. If convert_remote_status is callable it will be
    used to convert the watches' remote statuses to Launchpad
    BugTaskStatuses and these will be output instead.
    """
    watches = dict((int(bug_watch.remotebug), bug_watch)
        for bug_watch in bug_watches)

    for remote_bug_id in sorted(watches.keys()):
        status = watches[remote_bug_id].remotestatus
        if callable(convert_remote_status):
            status = convert_remote_status(status)

        print 'Remote bug %d: %s' % (remote_bug_id, status)

def convert_python_status(status, resolution):
    """Convert a human readable status and resolution into a Python
    bugtracker status and resolution string.
    """
    status_map = {'open': 1, 'closed': 2, 'pending': 3}
    resolution_map = {
        'None': 'None',
        'accepted': 1,
        'duplicate': 2,
        'fixed': 3,
        'invalid': 4,
        'later': 5,
        'out-of-date': 6,
        'postponed': 7,
        'rejected': 8,
        'remind': 9,
        'wontfix': 10,
        'worksforme': 11
    }

    return "%s:%s" % (status_map[status], resolution_map[resolution])

def set_bugwatch_error_type(bug_watch, error_type):
    """Set the last_error_type field of a bug watch to a given error type."""
    login('test@canonical.com')
    bug_watch.remotestatus = None
    bug_watch.last_error_type = error_type
    bug_watch.updateStatus(UNKNOWN_REMOTE_STATUS, BugTaskStatus.UNKNOWN)
    logout()


class OOPSHook:
    def install(self):
        self.reset()
        self.original_report_oops = checkwatches.report_oops
        checkwatches.report_oops = self.reportOOPS

    def uninstall(self):
        checkwatches.report_oops = self.original_report_oops
        del self.original_report_oops

    def reportOOPS(self, message=None, properties=None, info=None):
        self.oops_info = self.original_report_oops(
            message=message, properties=properties, info=info)
        return self.oops_info

    def reset(self):
        if hasattr(self, 'oops_info'):
            del self.oops_info

    @property
    def formatted_oops_info(self):
        properties_string = '\n'.join(
            '%s=%r' % (name, value) for name, value
            in sorted(self.oops_info._data))
        return '%s\n%s' % (self.oops_info.oopsid, properties_string)

oops_hook = OOPSHook()


class TestExternalBugTracker(ExternalBugTracker):
    """A test version of `ExternalBugTracker`.

    Implements all the methods required of an `IExternalBugTracker`
    implementation, though it doesn't actually do anything.
    """

    def __init__(self, baseurl='http://example.com/'):
        super(TestExternalBugTracker, self).__init__(baseurl)

    def convertRemoteStatus(self, remote_status):
        """Always return UNKNOWN_REMOTE_STATUS.

        This method exists to satisfy the implementation requirements of
        `IExternalBugTracker`.
        """
        return BugTaskStatus.UNKNOWN

    def getRemoteImportance(self, bug_id):
        """Stub implementation."""
        return UNKNOWN_REMOTE_IMPORTANCE

    def convertRemoteImportance(self, remote_importance):
        """Stub implementation."""
        return BugTaskImportance.UNKNOWN

    def getRemoteStatus(self, bug_id):
        """Stub implementation."""
        return UNKNOWN_REMOTE_STATUS


class TestBrokenExternalBugTracker(TestExternalBugTracker):
    """A test version of ExternalBugTracker, designed to break."""

    initialize_remote_bugdb_error = None
    get_remote_status_error = None

    def initializeRemoteBugDB(self, bug_ids):
        """Raise the error specified in initialize_remote_bugdb_error.

        If initialize_remote_bugdb_error is None, None will be returned.
        See `ExternalBugTracker`.
        """
        if self.initialize_remote_bugdb_error:
            # We have to special case BugTrackerConnectError as it takes
            # two non-optional arguments.
            if self.initialize_remote_bugdb_error is BugTrackerConnectError:
                raise self.initialize_remote_bugdb_error(
                    "http://example.com", "Testing")
            else:
                raise self.initialize_remote_bugdb_error("Testing")

    def getRemoteStatus(self, bug_id):
        """Raise the error specified in get_remote_status_error.

        If get_remote_status_error is None, None will be returned.
        See `ExternalBugTracker`.
        """
        if self.get_remote_status_error:
            raise self.get_remote_status_error("Testing")


class TestBugzilla(Bugzilla):
    """Bugzilla ExternalSystem for use in tests.

    It overrides _getPage and _postPage, so that access to a real Bugzilla
    instance isn't needed.
    """
    # We set the batch_query_threshold to zero so that only
    # getRemoteBugBatch() is used to retrieve bugs, since getRemoteBug()
    # calls getRemoteBugBatch() anyway.
    batch_query_threshold = 0
    trace_calls = False

    version_file = 'gnome_bugzilla_version.xml'
    buglist_file = 'gnome_buglist.xml'
    bug_item_file = 'gnome_bug_li_item.xml'

    buglist_page = 'buglist.cgi'
    bug_id_form_element = 'bug_id'

    def __init__(self, baseurl, version=None):
        Bugzilla.__init__(self, baseurl, version=version)
        self.bugzilla_bugs = self._getBugsToTest()

    def _getBugsToTest(self):
        """Return a dict with bugs in the form bug_id: (status, resolution)"""
        return {3224: ('RESOLVED', 'FIXED'),
                328430: ('UNCONFIRMED', '')}

    def _readBugItemFile(self):
        """Reads in the file for an individual bug item.

        This method exists really only to allow us to check that the
        file is being used. So what?
        """
        return read_test_file(self.bug_item_file)

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
                bug_item = self._readBugItemFile() % {
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


class TestWeirdBugzilla(TestBugzilla):
    """Test support for a few corner cases in Bugzilla.

        - UTF8 data in the files being parsed.
        - bz:status instead of bz:bug_status
    """
    bug_item_file = 'weird_non_ascii_bug_li_item.xml'

    def _getBugsToTest(self):
        return {2000: ('ASSIGNED', ''),
                123543: ('RESOLVED', 'FIXED')}


class TestBrokenBugzilla(TestBugzilla):
    """Test parsing of a Bugzilla which returns broken XML."""
    bug_item_file = 'broken_bug_li_item.xml'

    def _getBugsToTest(self):
        return {42: ('ASSIGNED', ''),
                2000: ('RESOLVED', 'FIXED')}


class TestIssuezilla(TestBugzilla):
    """Test support for Issuezilla, with slightly modified XML."""
    version_file = 'issuezilla_version.xml'
    buglist_file = 'issuezilla_buglist.xml'
    bug_item_file = 'issuezilla_item.xml'

    buglist_page = 'xml.cgi'
    bug_id_form_element = 'id'

    def _getBugsToTest(self):
        return {2000: ('RESOLVED', 'FIXED'),
                123543: ('ASSIGNED', '')}


class TestOldBugzilla(TestBugzilla):
    """Test support for older Bugzilla versions."""
    version_file = 'ximian_bugzilla_version.xml'
    buglist_file = 'ximian_buglist.xml'
    bug_item_file = 'ximian_bug_item.xml'

    buglist_page = 'xml.cgi'
    bug_id_form_element = 'id'

    def _getBugsToTest(self):
        return {42: ('RESOLVED', 'FIXED'),
                123543: ('ASSIGNED', '')}


class TestMantis(Mantis):
    """Mantis ExternalSystem for use in tests.

    It overrides _getPage and _postPage, so that access to a real
    Mantis instance isn't needed.
    """

    trace_calls = False

    def _getPage(self, page):
        if self.trace_calls:
            print "CALLED _getPage(%r)" % (page,)
        if page == "csv_export.php":
            return read_test_file('mantis_example_bug_export.csv')
        elif page.startswith('view.php?id='):
            bug_id = page.split('id=')[-1]
            return read_test_file('mantis--demo--bug-%s.html' % bug_id)
        else:
            return ''

    def _postPage(self, page, form):
        if self.trace_calls:
            print "CALLED _postPage(%r, ...)" % (page,)
        return ''

    def cleanCache(self):
        """Clean the csv_data cache."""
        # Remove the self._csv_data_cached_value if it exists.
        try:
            del self._csv_data_cached_value
        except AttributeError:
            pass


class TestTrac(Trac):
    """Trac ExternalBugTracker for testing purposes.

    It overrides urlopen, so that access to a real Trac instance isn't needed,
    and supportsSingleExports so that the tests don't fail due to the lack of
    a network connection. Also, it overrides the default batch_query_threshold
    for the sake of making test data sane.
    """

    # We remove the batch_size limit for the purposes of the tests so
    # that we can test batching and not batching correctly.
    batch_size = None
    batch_query_threshold = 10
    supports_single_exports = True
    trace_calls = False

    def supportsSingleExports(self, bug_ids):
        """See `Trac`."""
        return self.supports_single_exports

    def urlopen(self, url):
        file_path = os.path.join(os.path.dirname(__file__), 'testfiles')

        if self.trace_calls:
            print "CALLED urlopen(%r)" % (url,)

        return open(file_path + '/' + 'trac_example_ticket_export.csv', 'r')


class TestTracXMLRPCTransport:
    """An XML-RPC transport to be used when testing Trac."""

    seconds_since_epoch = None
    local_timezone = 'UTC'
    utc_offset = 0


    def request(self, host, handler, request, verbose=None):
        """Call the corresponding XML-RPC method.

        The method name and arguments are extracted from `request`. The
        method on this class with the same name as the XML-RPC method is
        called, with the extracted arguments passed on to it.
        """
        args, method_name = xmlrpclib.loads(request)
        prefix = 'launchpad.'
        assert method_name.startswith(prefix), (
            'All methods should be in the launchpad namespace')

        method_name = method_name[len(prefix):]
        method = getattr(self, method_name)
        return method(*args)

    def bugtracker_version(self):
        """Return the bug tracker version information."""
        return ['0.11.0', '1.0', False]

    def time_snapshot(self):
        """Return the current time."""
        if self.seconds_since_epoch is None:
            local_time = int(time.time())
        else:
            local_time = self.seconds_since_epoch
        utc_time = local_time - self.utc_offset
        return [self.local_timezone, local_time, utc_time]


class TestRoundup(Roundup):
    """Roundup ExternalBugTracker for testing purposes.

    It overrides urlopen, so that access to a real Roundup instance isn't
    needed.
    """

    # We remove the batch_size limit for the purposes of the tests so
    # that we can test batching and not batching correctly.
    batch_size = None
    trace_calls = False

    def urlopen(self, url):
        if self.trace_calls:
            print "CALLED urlopen(%r)" % (url,)

        file_path = os.path.join(os.path.dirname(__file__), 'testfiles')

        if self.isPython():
            return open(
                file_path + '/' + 'python_example_ticket_export.csv', 'r')
        else:
            return open(
                file_path + '/' + 'roundup_example_ticket_export.csv', 'r')


class TestRequestTracker(RequestTracker):
    """A Test-oriented `RequestTracker` implementation.

    Overrides _getPage() and _postPage() so that access to an RT
    instance is not needed.
    """
    trace_calls = False
    simulate_bad_response = False

    def urlopen(self, page, data=None):
        file_path = os.path.join(os.path.dirname(__file__), 'testfiles')
        path = urlparse.urlparse(page)[2].lstrip('/')
        if self.trace_calls:
            print "CALLED urlopen(%r)" % path

        if self.simulate_bad_response:
            return open(file_path + '/' + 'rt-sample-bug-bad.txt')

        if path == self.batch_url:
            return open(file_path + '/' + 'rt-sample-bug-batch.txt')
        else:
            # We extract the ticket ID from the url and use that to find
            # the test file we want.
            page_re = re.compile('REST/1.0/ticket/([0-9]+)/show')
            bug_id = page_re.match(path).groups()[0]

            return open(file_path + '/' + 'rt-sample-bug-%s.txt' % bug_id)


class TestSourceForge(SourceForge):
    """Test-oriented SourceForge ExternalBugTracker.

    Overrides _getPage() so that access to SourceForge itself is not
    required.
    """

    trace_calls = False

    def _getPage(self, page):
        if self.trace_calls:
            print "CALLED _getPage(%r)" % (page,)

        page_re = re.compile('support/tracker.php\?aid=([0-9]+)')
        bug_id = page_re.match(page).groups()[0]

        file_path = os.path.join(
            os.path.dirname(__file__), 'testfiles',
            'sourceforge-sample-bug-%s.html' % bug_id)
        return open(file_path, 'r')


class TestDebianBug(debbugs.Bug):
    """A debbugs bug that doesn't require the debbugs db."""

    def __init__(self, reporter_email='foo@example.com', package='evolution',
                 summary='Test Summary', description='Test description.',
                 status='open', severity=None, tags=None, id=None):
        if tags is None:
            tags = []
        self.originator = reporter_email
        self.package = package
        self.subject = summary
        self.description = description
        self.status = status
        self.severity = severity
        self.tags = tags
        self.id = id
        self._emails = []

    def __getattr__(self, name):
        # We redefine this method here to as to avoid some of the
        # behaviour of debbugs.Bug from raising spurious errors during
        # testing.
        return getattr(self, name, None)


class TestDebBugsDB:
    """A debbugs db object that doesn't require access to the debbugs db."""

    def __init__(self):
        self._data_path = os.path.join(os.path.dirname(__file__),
            'testfiles')
        self._data_file = 'debbugs-1-comment.txt'
        self.fail_on_load_log = False

    @property
    def data_file(self):
        return os.path.join(self._data_path, self._data_file)

    def load_log(self, bug):
        """Load the comments for a particular debian bug."""
        if self.fail_on_load_log:
            raise debbugs.LogParseFailed(
                'debbugs-log.pl exited with code 512')

        comment_data = open(self.data_file).read()
        bug._emails = []
        bug.comments = [comment.strip() for comment in
            comment_data.split('--\n')]


class TestDebBugs(DebBugs):
    """A Test-oriented Debbugs ExternalBugTracker.

    It allows you to pass in bugs to be used, instead of relying on an
    existing debbugs db.
    """
    import_comments = False

    def __init__(self, baseurl, bugs):
        super(TestDebBugs, self).__init__(baseurl)
        self.bugs = bugs
        self.debbugs_db = TestDebBugsDB()

    def _findBug(self, bug_id):
        if bug_id not in self.bugs:
            raise BugNotFound(bug_id)

        bug = self.bugs[bug_id]
        self.debbugs_db.load_log(bug)
        return bug

