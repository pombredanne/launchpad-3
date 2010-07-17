# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0401,C0301,F0401


from __future__ import with_statement


__metaclass__ = type
__all__ = [
    'ANONYMOUS',
    'build_yui_unittest_suite',
    'BrowserTestCase',
    'capture_events',
    'celebrity_logged_in',
    'FakeTime',
    'get_lsb_information',
    'is_logged_in',
    'launchpadlib_for',
    'launchpadlib_credentials_for',
    'login',
    'login_as',
    'login_celebrity',
    'login_person',
    'login_team',
    'logout',
    'map_branch_contents',
    'normalize_whitespace',
    'oauth_access_token_for',
    'person_logged_in',
    'record_statements',
    'run_with_login',
    'run_with_storm_debug',
    'run_script',
    'TestCase',
    'TestCaseWithFactory',
    'test_tales',
    'time_counter',
    'unlink_source_packages',
    'validate_mock_class',
    'WindmillTestCase',
    'with_celebrity_logged_in',
    'ws_object',
    'YUIUnitTestCase',
    'ZopeTestInSubProcess',
    ]

from contextlib import contextmanager
from datetime import datetime, timedelta
from inspect import getargspec, getmembers, getmro, isclass, ismethod
import os
from pprint import pformat
import re
import shutil
import subprocess
import subunit
import sys
import tempfile
import time
import unittest

from bzrlib.bzrdir import BzrDir, format_registry
from bzrlib.transport import get_transport

import pytz
from storm.expr import Variable
from storm.store import Store
from storm.tracer import install_tracer, remove_tracer_type

import testtools
import transaction

from windmill.authoring import WindmillTestClient

from zope.component import adapter, getUtility
import zope.event
from zope.interface.verify import verifyClass, verifyObject
from zope.security.proxy import (
    isinstance as zope_isinstance, removeSecurityProxy)
from zope.testing.testrunner.runner import TestResult as ZopeTestResult

from canonical.launchpad.webapp import canonical_url, errorlog
from canonical.launchpad.webapp.servers import WebServiceTestRequest
from canonical.config import config
from canonical.launchpad.webapp.errorlog import ErrorReportEvent
from canonical.launchpad.webapp.interaction import ANONYMOUS
from canonical.launchpad.windmill.testing import constants
from lp.codehosting.vfs import branch_id_to_path, get_rw_server
from lp.registry.interfaces.packaging import IPackagingUtil
# Import the login helper functions here as it is a much better
# place to import them from in tests.
from lp.testing._login import (
    celebrity_logged_in,
    is_logged_in,
    login,
    login_as,
    login_celebrity,
    login_person,
    login_team,
    logout,
    person_logged_in,
    run_with_login,
    with_celebrity_logged_in,
    )
# canonical.launchpad.ftests expects test_tales to be imported from here.
# XXX: JonathanLange 2010-01-01: Why?!
from lp.testing._tales import test_tales
from lp.testing._webservice import (
    launchpadlib_credentials_for, launchpadlib_for, oauth_access_token_for)
from lp.testing.fixture import ZopeEventHandlerFixture

# zope.exception demands more of frame objects than twisted.python.failure
# provides in its fake frames.  This is enough to make it work with them
# as of 2009-09-16.  See https://bugs.edge.launchpad.net/bugs/425113.
from twisted.python.failure import _Frame
_Frame.f_locals = property(lambda self: {})


class FakeTime:
    """Provides a controllable implementation of time.time().

    You can either advance the time manually using advance() or have it done
    automatically using next_now(). The amount of seconds to advance the
    time by is set during initialization but can also be changed for single
    calls of advance() or next_now().

    >>> faketime = FakeTime(1000)
    >>> print faketime.now()
    1000
    >>> print faketime.now()
    1000
    >>> faketime.advance(10)
    >>> print faketime.now()
    1010
    >>> print faketime.next_now()
    1011
    >>> print faketime.next_now(100)
    1111
    >>> faketime = FakeTime(1000, 5)
    >>> print faketime.next_now()
    1005
    >>> print faketime.next_now()
    1010
    """

    def __init__(self, start=None, advance=1):
        """Set up the instance.

        :param start: The value that will initially be returned by `now()`.
            If None, the current time will be used.
        :param advance: The value in secounds to advance the clock by by
            default.
        """
        if start is not None:
            self._now = start
        else:
            self._now = time.time()
        self._advance = advance

    def advance(self, amount=None):
        """Advance the value that will be returned by `now()`.

        :param amount: The amount of seconds to advance the value by.
            If None, the configured default value will be used.
        """
        if amount is None:
            self._now += self._advance
        else:
            self._now += amount

    def now(self):
        """Use this bound method instead of time.time in tests."""
        return self._now

    def next_now(self, amount=None):
        """Read the current time and advance it.

        Calls advance() and returns the current value of now().
        :param amount: The amount of seconds to advance the value by.
            If None, the configured default value will be used.
        """
        self.advance(amount)
        return self.now()


class StormStatementRecorder:
    """A storm tracer to count queries."""

    def __init__(self):
        self.statements = []

    def connection_raw_execute(self, ignored, raw_cursor, statement, params):
        """Increment the counter.  We don't care about the args."""

        raw_params = []
        for param in params:
            if isinstance(param, Variable):
                raw_params.append(param.get())
            else:
                raw_params.append(param)
        raw_params = tuple(raw_params)
        self.statements.append("%r, %r" % (statement, raw_params))


def record_statements(function, *args, **kwargs):
    """Run the function and record the sql statements that are executed.

    :return: a tuple containing the return value of the function,
        and a list of sql statements.
    """
    recorder = StormStatementRecorder()
    try:
        install_tracer(recorder)
        ret = function(*args, **kwargs)
    finally:
        remove_tracer_type(StormStatementRecorder)
    return (ret, recorder.statements)


def run_with_storm_debug(function, *args, **kwargs):
    """A helper function to run a function with storm debug tracing on."""
    from storm.tracer import debug
    debug(True)
    try:
        return function(*args, **kwargs)
    finally:
        debug(False)


class TestCase(testtools.TestCase):
    """Provide Launchpad-specific test facilities."""
    def becomeDbUser(self, dbuser):
        """Commit, then log into the database as `dbuser`.
        
        For this to work, the test must run in a layer.
        
        Try to test every code path at least once under a realistic db
        user, or you'll hit privilege violations later on.
        """
        assert self.layer, "becomeDbUser requires a layer."
        transaction.commit()
        self.layer.switchDbUser(dbuser)

    def installFixture(self, fixture):
        """Install 'fixture', an object that has a `setUp` and `tearDown`.

        `installFixture` will run 'fixture.setUp' and schedule
        'fixture.tearDown' to be run during the test's tear down (using
        `addCleanup`).

        :param fixture: Any object that has a `setUp` and `tearDown` method.
        """
        fixture.setUp()
        self.addCleanup(fixture.tearDown)

    def __str__(self):
        """The string representation of a test is its id.

        The most descriptive way of writing down a test is to write down its
        id. It is usually the fully-qualified Python name, which is pretty
        handy.
        """
        return self.id()

    def useContext(self, context):
        """Use the supplied context in this test.

        The context will be cleaned via addCleanup.
        """
        retval = context.__enter__()
        self.addCleanup(context.__exit__, None, None, None)
        return retval

    def makeTemporaryDirectory(self):
        """Create a temporary directory, and return its path."""
        return self.useContext(temp_dir())

    def assertProvides(self, obj, interface):
        """Assert 'obj' correctly provides 'interface'."""
        self.assertTrue(
            interface.providedBy(obj),
            "%r does not provide %r." % (obj, interface))
        self.assertTrue(
            verifyObject(interface, obj),
            "%r claims to provide %r but does not do so correctly."
            % (obj, interface))

    def assertClassImplements(self, cls, interface):
        """Assert 'cls' may correctly implement 'interface'."""
        self.assertTrue(
            verifyClass(interface, cls),
            "%r does not correctly implement %r." % (cls, interface))

    def assertNotifies(self, event_type, callable_obj, *args, **kwargs):
        """Assert that a callable performs a given notification.

        :param event_type: The type of event that notification is expected
            for.
        :param callable_obj: The callable to call.
        :param *args: The arguments to pass to the callable.
        :param **kwargs: The keyword arguments to pass to the callable.
        :return: (result, event), where result was the return value of the
            callable, and event is the event emitted by the callable.
        """
        result, events = capture_events(callable_obj, *args, **kwargs)
        if len(events) == 0:
            raise AssertionError('No notification was performed.')
        elif len(events) > 1:
            raise AssertionError('Too many (%d) notifications performed.'
                % len(events))
        elif not isinstance(events[0], event_type):
            raise AssertionError('Wrong event type: %r (expected %r).' %
                (events[0], event_type))
        return result, events[0]

    def assertNoNotification(self, callable_obj, *args, **kwargs):
        """Assert that no notifications are generated by the callable.

        :param callable_obj: The callable to call.
        :param *args: The arguments to pass to the callable.
        :param **kwargs: The keyword arguments to pass to the callable.
        """
        result, events = capture_events(callable_obj, *args, **kwargs)
        if len(events) == 1:
            raise AssertionError('An event was generated: %r.' % events[0])
        elif len(events) > 1:
            raise AssertionError('Events were generated: %s.' %
                                 ', '.join([repr(event) for event in events]))
        return result

    def assertNoNewOops(self, old_oops):
        """Assert that no oops has been recorded since old_oops."""
        oops = errorlog.globalErrorUtility.getLastOopsReport()
        if old_oops is None:
            self.assertIs(None, oops)
        else:
            self.assertEqual(oops.id, old_oops.id)

    def assertSqlAttributeEqualsDate(self, sql_object, attribute_name, date):
        """Fail unless the value of the attribute is equal to the date.

        Use this method to test that date value that may be UTC_NOW is equal
        to another date value. Trickery is required because SQLBuilder truth
        semantics cause UTC_NOW to appear equal to all dates.

        :param sql_object: a security-proxied SQLObject instance.
        :param attribute_name: the name of a database column in the table
            associated to this object.
        :param date: `datetime.datetime` object or `UTC_NOW`.
        """
        # XXX: Aaron Bentley 2008-04-14: Probably does not belong here, but
        # better location not clear. Used primarily for testing ORM objects,
        # which ought to use factory.
        sql_object = removeSecurityProxy(sql_object)
        sql_class = type(sql_object)
        store = Store.of(sql_object)
        found_object = store.find(
            sql_class, **({'id': sql_object.id, attribute_name: date})).one()
        if found_object is None:
            self.fail(
                "Expected %s to be %s, but it was %s."
                % (attribute_name, date, getattr(sql_object, attribute_name)))

    def assertEqual(self, a, b, message=''):
        """Assert that 'a' equals 'b'."""
        if a == b:
            return
        if message:
            message += '\n'
        self.fail("%snot equal:\na = %s\nb = %s\n"
                  % (message, pformat(a), pformat(b)))

    def assertIsInstance(self, instance, assert_class):
        """Assert that an instance is an instance of assert_class.

        instance and assert_class have the same semantics as the parameters
        to isinstance.
        """
        self.assertTrue(zope_isinstance(instance, assert_class),
            '%r is not an instance of %r' % (instance, assert_class))

    def assertIsNot(self, expected, observed, msg=None):
        """Assert that `expected` is not the same object as `observed`."""
        if msg is None:
            msg = "%r is %r" % (expected, observed)
        self.assertTrue(expected is not observed, msg)

    def assertContentEqual(self, iter1, iter2):
        """Assert that 'iter1' has the same content as 'iter2'."""
        list1 = sorted(iter1)
        list2 = sorted(iter2)
        self.assertEqual(
            list1, list2, '%s != %s' % (pformat(list1), pformat(list2)))

    def assertRaisesWithContent(self, exception, exception_content,
                                func, *args):
        """Check if the given exception is raised with given content.

        If the exception isn't raised or the exception_content doesn't
        match what was raised an AssertionError is raised.
        """
        err = self.assertRaises(exception, func, *args)
        self.assertEqual(exception_content, str(err))

    def assertBetween(self, lower_bound, variable, upper_bound):
        """Assert that 'variable' is strictly between two boundaries."""
        self.assertTrue(
            lower_bound < variable < upper_bound,
            "%r < %r < %r" % (lower_bound, variable, upper_bound))

    def pushConfig(self, section, **kwargs):
        """Push some key-value pairs into a section of the config.

        The config values will be restored during test tearDown.
        """
        name = self.factory.getUniqueString()
        body = '\n'.join(["%s: %s" % (k, v) for k, v in kwargs.iteritems()])
        config.push(name, "\n[%s]\n%s\n" % (section, body))
        self.addCleanup(config.pop, name)

    def setUp(self):
        testtools.TestCase.setUp(self)
        from lp.testing.factory import ObjectFactory
        self.factory = ObjectFactory()
        # Record the oopses generated during the test run.
        self.oopses = []
        self.installFixture(ZopeEventHandlerFixture(self._recordOops))

    @adapter(ErrorReportEvent)
    def _recordOops(self, event):
        """Add the oops to the testcase's list."""
        self.oopses.append(event.object)

    def assertStatementCount(self, expected_count, function, *args, **kwargs):
        """Assert that the expected number of SQL statements occurred.

        :return: Returns the result of calling the function.
        """
        ret, statements = record_statements(function, *args, **kwargs)
        if len(statements) != expected_count:
            self.fail(
                "Expected %d statements, got %d:\n%s"
                % (expected_count, len(statements), "\n".join(statements)))
        return ret

    def useTempDir(self):
        """Use a temporary directory for this test."""
        tempdir = self.makeTemporaryDirectory()
        cwd = os.getcwd()
        os.chdir(tempdir)
        self.addCleanup(os.chdir, cwd)
        return tempdir

    def _unfoldEmailHeader(self, header):
        """Unfold a multiline e-mail header."""
        header = ''.join(header.splitlines())
        return header.replace('\t', ' ')

    def assertEmailHeadersEqual(self, expected, observed):
        """Assert that two e-mail headers are equal.

        The headers are unfolded before being compared.
        """
        return self.assertEqual(
            self._unfoldEmailHeader(expected),
            self._unfoldEmailHeader(observed))


class TestCaseWithFactory(TestCase):

    def setUp(self, user=ANONYMOUS):
        TestCase.setUp(self)
        login(user)
        self.addCleanup(logout)
        from lp.testing.factory import LaunchpadObjectFactory
        self.factory = LaunchpadObjectFactory()
        self.direct_database_server = False
        self._use_bzr_branch_called = False

    def getUserBrowser(self, url=None, user=None, password='test'):
        """Return a Browser logged in as a fresh user, maybe opened at `url`.

        :param user: The user to open a browser for.
        :param password: The password to use.  (This cannot be determined
            because it's stored as a hash.)
        """
        # Do the import here to avoid issues with import cycles.
        from canonical.launchpad.testing.pages import setupBrowser
        login(ANONYMOUS)
        if user is None:
            user = self.factory.makePerson(password=password)
        naked_user = removeSecurityProxy(user)
        email = naked_user.preferredemail.email
        logout()
        browser = setupBrowser(
            auth="Basic %s:%s" % (str(email), password))
        if url is not None:
            browser.open(url)
        return browser

    def createBranchAtURL(self, branch_url, format=None):
        """Create a branch at the supplied URL.

        The branch will be scheduled for deletion when the test terminates.
        :param branch_url: The URL to create the branch at.
        :param format: The format of branch to create.
        """
        if format is not None and isinstance(format, basestring):
            format = format_registry.get(format)()
        return BzrDir.create_branch_convenience(
            branch_url, format=format)

    def create_branch_and_tree(self, tree_location=None, product=None,
                               db_branch=None, format=None,
                               **kwargs):
        """Create a database branch, bzr branch and bzr checkout.

        :param tree_location: The path on disk to create the tree at.
        :param product: The product to associate with the branch.
        :param db_branch: If supplied, the database branch to use.
        :param format: Override the default bzrdir format to create.
        :return: a `Branch` and a workingtree.
        """
        if db_branch is None:
            if product is None:
                db_branch = self.factory.makeAnyBranch(**kwargs)
            else:
                db_branch = self.factory.makeProductBranch(product, **kwargs)
        branch_url = 'lp-internal:///' + db_branch.unique_name
        if not self.direct_database_server:
            transaction.commit()
        bzr_branch = self.createBranchAtURL(branch_url, format=format)
        if tree_location is None:
            tree_location = tempfile.mkdtemp()
            self.addCleanup(lambda: shutil.rmtree(tree_location))
        return db_branch, bzr_branch.create_checkout(
            tree_location, lightweight=True)

    def createBzrBranch(self, db_branch, parent=None):
        """Create a bzr branch for a database branch.

        :param db_branch: The database branch to create the branch for.
        :param parent: If supplied, the bzr branch to use as a parent.
        """
        bzr_branch = self.createBranchAtURL(db_branch.getInternalBzrUrl())
        if parent:
            bzr_branch.pull(parent)
            removeSecurityProxy(db_branch).last_scanned_id = bzr_branch.last_revision()
        return bzr_branch

    @staticmethod
    def getBranchPath(branch, base):
        """Return the path of the branch in the mirrored area.

        This always uses the configured mirrored area, ignoring whatever
        server might be providing lp-mirrored: urls.
        """
        # XXX gary 2009-5-28 bug 381325
        # This is a work-around for some failures on PQM, arguably caused by
        # relying on test set-up that is happening in the Makefile rather than
        # the actual test set-up.
        get_transport(base).create_prefix()
        return os.path.join(base, branch_id_to_path(branch.id))

    def useTempBzrHome(self):
        # XXX: Extract the temporary environment blatting into a generic
        # helper function.
        self.useTempDir()
        # Avoid leaking local user configuration into tests.
        old_bzr_home = os.environ.get('BZR_HOME')
        def restore_bzr_home():
            if old_bzr_home is None:
                del os.environ['BZR_HOME']
            else:
                os.environ['BZR_HOME'] = old_bzr_home
        os.environ['BZR_HOME'] = os.getcwd()
        self.addCleanup(restore_bzr_home)

    def useBzrBranches(self, direct_database=False):
        """Prepare for using bzr branches.

        This sets up support for lp-internal URLs, changes to a temp
        directory, and overrides the bzr home directory.

        :param direct_database: If true, translate branch locations by
            directly querying the database, not the internal XML-RPC server.
            If the test is in an AppServerLayer, you probably want to pass
            direct_database=False and if not you probably want to pass
            direct_database=True.
        """
        if self._use_bzr_branch_called:
            if direct_database != self.direct_database_server:
                raise AssertionError(
                    "useBzrBranches called with inconsistent values for "
                    "direct_database")
            return
        self._use_bzr_branch_called = True
        self.useTempBzrHome()
        self.direct_database_server = direct_database
        server = get_rw_server(direct_database=direct_database)
        server.start_server()
        self.addCleanup(server.destroy)


class BrowserTestCase(TestCaseWithFactory):
    """A TestCase class for browser tests.

    This testcase provides an API similar to page tests, and can be used for
    cases when one wants a unit test and not a frakking pagetest.
    """
    def setUp(self):
        """Provide useful defaults."""
        super(BrowserTestCase, self).setUp()
        self.user = self.factory.makePerson(password='test')

    def assertTextMatchesExpressionIgnoreWhitespace(self,
                                                    regular_expression_txt,
                                                    text):
        def normalise_whitespace(text):
            return ' '.join(text.split())
        pattern = re.compile(
            normalise_whitespace(regular_expression_txt), re.S)
        self.assertIsNot(
            None, pattern.search(normalise_whitespace(text)), text)

    def getViewBrowser(self, context, view_name=None):
        login(ANONYMOUS)
        url = canonical_url(context, view_name=view_name)
        return self.getUserBrowser(url, self.user)

    def getMainText(self, context, view_name=None):
        """Return the main text of a context's page."""
        from canonical.launchpad.testing.pages import (
            extract_text, find_main_content)
        browser = self.getViewBrowser(context, view_name)
        return extract_text(find_main_content(browser.contents))


class WindmillTestCase(TestCaseWithFactory):
    """A TestCase class for Windmill tests.

    It provides a WindmillTestClient (self.client) with Launchpad's front
    page loaded.
    """

    suite_name = ''

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.client = WindmillTestClient(self.suite_name)
        # Load the front page to make sure we don't get fooled by stale pages
        # left by the previous test. (For some reason, when you create a new
        # WindmillTestClient you get a new session and everything, but if you
        # do anything before you open() something you'd be operating on the
        # page that was last accessed by the previous test, which is the cause
        # of things like https://launchpad.net/bugs/515494)
        self.client.open(url=u'http://launchpad.dev:8085')


class YUIUnitTestCase(WindmillTestCase):

    layer = None
    suite_name = ''

    _yui_results = None
    _view_name = u'http://launchpad.dev:8085/+yui-unittest/'

    def initialize(self, test_path):
        self.test_path = test_path
        self.yui_runner_url = self._view_name + test_path

    def setUp(self):
        super(YUIUnitTestCase, self).setUp()
        client = self.client
        client.open(url=self.yui_runner_url)
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        client.waits.forElement(id='complete')
        response = client.commands.getPageText()
        self._yui_results = {}
        # Maybe testing.pages should move to lp to avoid circular imports.
        from canonical.launchpad.testing.pages import find_tags_by_class
        entries = find_tags_by_class(
            response['result'], 'yui-console-entry-TestRunner')
        for entry in entries:
            category = entry.find(
                attrs={'class': 'yui-console-entry-cat'})
            if category is None:
                continue
            result = category.string
            if result not in ('pass', 'fail'):
                continue
            message = entry.pre.string
            test_name, ignore = message.split(':', 1)
            self._yui_results[test_name] = dict(
                result=result, message=message)

    def runTest(self):
        if self._yui_results is None or len(self._yui_results) == 0:
            self.fail("Test harness or js failed.")
        for test_name in self._yui_results:
            result = self._yui_results[test_name]
            self.assertTrue('pass' == result['result'],
                    'Failure in %s.%s: %s' % (
                        self.test_path, test_name, result['message']))


def build_yui_unittest_suite(app_testing_path, yui_test_class):
    suite = unittest.TestSuite()
    testing_path = os.path.join(config.root, 'lib', app_testing_path)
    unit_test_names = [
        file_name for file_name in os.listdir(testing_path)
        if file_name.startswith('test_') and file_name.endswith('.html')]
    for unit_test_name in unit_test_names:
        test_path = os.path.join(app_testing_path, unit_test_name)
        test_case = yui_test_class()
        test_case.initialize(test_path)
        suite.addTest(test_case)
    return suite


class ZopeTestInSubProcess:
    """Run tests in a sub-process, respecting Zope idiosyncrasies.

    Use this as a mixin with an interesting `TestCase` to isolate
    tests with side-effects. Each and every test *method* in the test
    case is run in a new, forked, sub-process. This will slow down
    your tests, so use it sparingly. However, when you need to, for
    example, start the Twisted reactor (which cannot currently be
    safely stopped and restarted in process) it is invaluable.

    This is basically a reimplementation of subunit's
    `IsolatedTestCase` or `IsolatedTestSuite`, but adjusted to work
    with Zope. In particular, Zope's TestResult object is responsible
    for calling testSetUp() and testTearDown() on the selected layer.
    """

    def run(self, result):
        # The result must be an instance of Zope's TestResult because
        # we construct a super() of it later on. Other result classes
        # could be supported with a more general approach, but it's
        # unlikely that any one approach is going to work for every
        # class. It's better to fail early and draw attention here.
        assert isinstance(result, ZopeTestResult), (
            "result must be a Zope result object, not %r." % (result,))
        pread, pwrite = os.pipe()
        pid = os.fork()
        if pid == 0:
            # Child.
            os.close(pread)
            fdwrite = os.fdopen(pwrite, 'w', 1)
            # Send results to both the Zope result object (so that
            # layer setup and teardown are done properly, etc.) and to
            # the subunit stream client so that the parent process can
            # obtain the result.
            result = testtools.MultiTestResult(
                result, subunit.TestProtocolClient(fdwrite))
            super(ZopeTestInSubProcess, self).run(result)
            fdwrite.flush()
            sys.stdout.flush()
            sys.stderr.flush()
            # Exit hard to avoid running onexit handlers and to avoid
            # anything that could suppress SystemExit; this exit must
            # not be prevented.
            os._exit(0)
        else:
            # Parent.
            os.close(pwrite)
            fdread = os.fdopen(pread, 'rU')
            # Skip all the Zope-specific result stuff by using a
            # super() of the result. This is because the Zope result
            # object calls testSetUp() and testTearDown() on the
            # layer, and handles post-mortem debugging. These things
            # do not make sense in the parent process. More
            # immediately, it also means that the results are not
            # reported twice; they are reported on stdout by the child
            # process, so they need to be suppressed here.
            result = super(ZopeTestResult, result)
            # Accept the result from the child process.
            protocol = subunit.TestProtocolServer(result)
            protocol.readFrom(fdread)
            fdread.close()
            os.waitpid(pid, 0)


def capture_events(callable_obj, *args, **kwargs):
    """Capture the events emitted by a callable.

    :param callable_obj: The callable to call.
    :param *args: The arguments to pass to the callable.
    :param **kwargs: The keyword arguments to pass to the callable.
    :return: (result, events), where result was the return value of the
        callable, and events are the events emitted by the callable.
    """
    events = []
    def on_notify(event):
        events.append(event)
    old_subscribers = zope.event.subscribers[:]
    try:
        zope.event.subscribers[:] = [on_notify]
        result = callable_obj(*args, **kwargs)
        return result, events
    finally:
        zope.event.subscribers[:] = old_subscribers


# XXX: This doesn't seem like a generically-useful testing function. Perhaps
# it should go in a sub-module or something? -- jml
def get_lsb_information():
    """Returns a dictionary with the LSB host information.

    Code stolen form /usr/bin/lsb-release
    """
    distinfo = {}
    if os.path.exists('/etc/lsb-release'):
        for line in open('/etc/lsb-release'):
            line = line.strip()
            if not line:
                continue
            # Skip invalid lines
            if not '=' in line:
                continue
            var, arg = line.split('=', 1)
            if var.startswith('DISTRIB_'):
                var = var[8:]
                if arg.startswith('"') and arg.endswith('"'):
                    arg = arg[1:-1]
                distinfo[var] = arg

    return distinfo


def time_counter(origin=None, delta=timedelta(seconds=5)):
    """A generator for yielding datetime values.

    Each time the generator yields a value, the origin is incremented
    by the delta.

    >>> now = time_counter(datetime(2007, 12, 1), timedelta(days=1))
    >>> now.next()
    datetime.datetime(2007, 12, 1, 0, 0)
    >>> now.next()
    datetime.datetime(2007, 12, 2, 0, 0)
    >>> now.next()
    datetime.datetime(2007, 12, 3, 0, 0)
    """
    if origin is None:
        origin = datetime.now(pytz.UTC)
    now = origin
    while True:
        yield now
        now += delta


def run_script(cmd_line):
    """Run the given command line as a subprocess.

    Return a 3-tuple containing stdout, stderr and the process' return code.

    The environment given to the subprocess is the same as the one in the
    parent process except for the PYTHONPATH, which is removed so that the
    script, passed as the `cmd_line` parameter, will fail if it doesn't set it
    up properly.
    """
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    process = subprocess.Popen(
        cmd_line, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=env)
    (out, err) = process.communicate()
    return out, err, process.returncode


def normalize_whitespace(string):
    """Replace all sequences of whitespace with a single space."""
    # In Python 2.4, splitting and joining a string to normalize
    # whitespace is roughly 6 times faster than using an uncompiled
    # regex (for the expression \s+), and 4 times faster than a
    # compiled regex.
    return " ".join(string.split())


# XXX: This doesn't seem to be a generically useful testing function. Perhaps
# it should go into a sub-module? -- jml
def map_branch_contents(branch):
    """Return all files in branch at `branch_url`.

    :param branch_url: the URL for an accessible branch.
    :return: a dict mapping file paths to file contents.  Only regular
        files are included.
    """
    contents = {}
    tree = branch.basis_tree()
    tree.lock_read()
    try:
        for dir, entries in tree.walkdirs():
            dirname, id = dir
            for entry in entries:
                file_path, file_name, file_type = entry[:3]
                if file_type == 'file':
                    stored_file = tree.get_file_by_path(file_path)
                    contents[file_path] = stored_file.read()
    finally:
        tree.unlock()

    return contents


def validate_mock_class(mock_class):
    """Validate method signatures in mock classes derived from real classes.

    We often use mock classes in tests which are derived from real
    classes.

    This function ensures that methods redefined in the mock
    class have the same signature as the corresponding methods of
    the base class.

    >>> class A:
    ...
    ...     def method_one(self, a):
    ...         pass

    >>>
    >>> class B(A):
    ...     def method_one(self, a):
    ...        pass
    >>> validate_mock_class(B)

    If a class derived from A defines method_one with a different
    signature, we get an AssertionError.

    >>> class C(A):
    ...     def method_one(self, a, b):
    ...        pass
    >>> validate_mock_class(C)
    Traceback (most recent call last):
    ...
    AssertionError: Different method signature for method_one:...

    Even a parameter name must not be modified.

    >>> class D(A):
    ...     def method_one(self, b):
    ...        pass
    >>> validate_mock_class(D)
    Traceback (most recent call last):
    ...
    AssertionError: Different method signature for method_one:...

    If validate_mock_class() for anything but a class, we get an
    AssertionError.

    >>> validate_mock_class('a string')
    Traceback (most recent call last):
    ...
    AssertionError: validate_mock_class() must be called for a class
    """
    assert isclass(mock_class), (
        "validate_mock_class() must be called for a class")
    base_classes = getmro(mock_class)
    for name, obj in getmembers(mock_class):
        if ismethod(obj):
            for base_class in base_classes[1:]:
                if name in base_class.__dict__:
                    mock_args = getargspec(obj)
                    real_args = getargspec(base_class.__dict__[name])
                    if mock_args != real_args:
                        raise AssertionError(
                            'Different method signature for %s: %r %r' % (
                            name, mock_args, real_args))
                    else:
                        break


def ws_object(launchpad, obj):
    """Convert an object into its webservice version.

    :param launchpad: The Launchpad instance to convert from.
    :param obj: The object to convert.
    :return: A launchpadlib Entry object.
    """
    api_request = WebServiceTestRequest()
    obj_url = canonical_url(obj, request=api_request)
    return launchpad.load(
        obj_url.replace('http://api.launchpad.dev/',
        str(launchpad._root_uri)))


@contextmanager
def temp_dir():
    """Provide a temporary directory as a ContextManager."""
    tempdir = tempfile.mkdtemp()
    yield tempdir
    shutil.rmtree(tempdir)


def unlink_source_packages(product):
    """Remove all links between the product and source packages.

    A product cannot be deactivated if it is linked to source packages.
    """
    packaging_util = getUtility(IPackagingUtil)
    for source_package in product.sourcepackages:
        packaging_util.deletePackaging(
            source_package.productseries,
            source_package.sourcepackagename,
            source_package.distroseries)
