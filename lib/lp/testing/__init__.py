# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0401,C0301,F0401

from __future__ import absolute_import

__metaclass__ = type
__all__ = [
    'ANONYMOUS',
    'anonymous_logged_in',
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
    'quote_jquery_expression'
    'record_statements',
    'run_with_login',
    'run_with_storm_debug',
    'run_script',
    'StormStatementRecorder',
    'TestCase',
    'TestCaseWithFactory',
    'test_tales',
    'time_counter',
    'unlink_source_packages',
    'validate_mock_class',
    'WindmillTestCase',
    'with_anonymous_login',
    'with_celebrity_logged_in',
    'with_person_logged_in',
    'ws_object',
    'YUIUnitTestCase',
    'ZopeTestInSubProcess',
    ]

from contextlib import contextmanager
from datetime import (
    datetime,
    timedelta,
    )
from inspect import (
    getargspec,
    getmro,
    isclass,
    ismethod,
    )
import logging
import os
from pprint import pformat
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

from bzrlib.bzrdir import (
    BzrDir,
    format_registry,
    )
from bzrlib import trace
from bzrlib.transport import get_transport
import fixtures
import pytz
from storm.expr import Variable
from storm.store import Store
from storm.tracer import (
    install_tracer,
    remove_tracer_type,
    )
import subunit
import testtools
from testtools.content import Content
from testtools.content_type import UTF8_TEXT
import transaction
from windmill.authoring import WindmillTestClient
from zope.component import (
    adapter,
    getUtility,
    )
import zope.event
from zope.interface.verify import verifyClass
from zope.security.proxy import (
    isinstance as zope_isinstance,
    removeSecurityProxy,
    )
from zope.testing.testrunner.runner import TestResult as ZopeTestResult

from canonical.config import config
from canonical.launchpad.webapp import (
    canonical_url,
    errorlog,
    )
from canonical.launchpad.webapp.adapter import (
    set_permit_timeout_from_features,
    )
from canonical.launchpad.webapp.errorlog import ErrorReportEvent
from canonical.launchpad.webapp.interaction import ANONYMOUS
from canonical.launchpad.webapp.servers import (
    LaunchpadTestRequest,
    WebServiceTestRequest,
    )
from lp.codehosting.vfs import (
    branch_id_to_path,
    get_rw_server,
    )
from lp.registry.interfaces.packaging import IPackagingUtil
from lp.services import features
from lp.services.features.flags import FeatureController
from lp.services.features.model import (
    FeatureFlag,
    getFeatureStore,
    )
from lp.services.features.webapp import ScopesFromRequest
from lp.services.osutils import override_environ
# Import the login helper functions here as it is a much better
# place to import them from in tests.
from lp.testing._login import (
    anonymous_logged_in,
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
    with_anonymous_login,
    with_celebrity_logged_in,
    with_person_logged_in,
    )
# canonical.launchpad.ftests expects test_tales to be imported from here.
# XXX: JonathanLange 2010-01-01: Why?!
from lp.testing._tales import test_tales
from lp.testing._webservice import (
    launchpadlib_credentials_for,
    launchpadlib_for,
    oauth_access_token_for,
    )
from lp.testing.fixture import ZopeEventHandlerFixture
from lp.testing.karma import KarmaRecorder
from lp.testing.matchers import Provides
from lp.testing.windmill import constants, lpuser


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
    """A storm tracer to count queries.

    This exposes the count and queries as
    lp.testing._webservice.QueryCollector does permitting its use with the
    HasQueryCount matcher.

    It also meets the context manager protocol, so you can gather queries
    easily:
    with StormStatementRecorder() as recorder:
        do somestuff
    self.assertThat(recorder, HasQueryCount(LessThan(42)))

    Note that due to the storm API used, only one of these recorders may be in
    place at a time: all will be removed when the first one is removed (by
    calling __exit__ or leaving the scope of a with statement).
    """

    def __init__(self):
        self.statements = []

    @property
    def count(self):
        return len(self.statements)

    @property
    def queries(self):
        """The statements executed as per get_request_statements."""
        # Perhaps we could just consolidate this code with the request tracer
        # code and not need a custom tracer at all - if we provided a context
        # factory to the tracer, which in the production tracers would
        # use the adapter magic, and in test created ones would log to a list.
        # We would need to be able to remove just one tracer though, which I
        # haven't looked into yet. RBC 20100831
        result = []
        for statement in self.statements:
            result.append((0, 0, 'unknown', statement))
        return result

    def __enter__(self):
        """Context manager protocol - return this object as the context."""
        install_tracer(self)
        return self

    def __exit__(self, _ignored, _ignored2, _ignored3):
        """Content manager protocol - do not swallow exceptions."""
        remove_tracer_type(StormStatementRecorder)
        return False

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
    with StormStatementRecorder() as recorder:
        ret = function(*args, **kwargs)
    return (ret, recorder.statements)


def run_with_storm_debug(function, *args, **kwargs):
    """A helper function to run a function with storm debug tracing on."""
    from storm.tracer import debug
    debug(True)
    try:
        return function(*args, **kwargs)
    finally:
        debug(False)


class TestCase(testtools.TestCase, fixtures.TestWithFixtures):
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

    def installKarmaRecorder(self, *args, **kwargs):
        """Set up and return a `KarmaRecorder`.

        Registers the karma recorder immediately, and ensures that it is
        unregistered after the test.
        """
        recorder = KarmaRecorder(*args, **kwargs)
        recorder.register_listener()
        self.addCleanup(recorder.unregister_listener)
        return recorder

    def assertProvides(self, obj, interface):
        """Assert 'obj' correctly provides 'interface'."""
        self.assertThat(obj, Provides(interface))

    def assertClassImplements(self, cls, interface):
        """Assert 'cls' may correctly implement 'interface'."""
        self.assertTrue(
            verifyClass(interface, cls),
            "%r does not correctly implement %r." % (cls, interface))

    def assertNotifies(self, event_types, callable_obj, *args, **kwargs):
        """Assert that a callable performs a given notification.

        :param event_type: One or more event types that notification is
            expected for.
        :param callable_obj: The callable to call.
        :param *args: The arguments to pass to the callable.
        :param **kwargs: The keyword arguments to pass to the callable.
        :return: (result, event), where result was the return value of the
            callable, and event is the event emitted by the callable.
        """
        if not isinstance(event_types, (list, tuple)):
            event_types = [event_types]
        with EventRecorder() as recorder:
            result = callable_obj(*args, **kwargs)
        if len(recorder.events) == 0:
            raise AssertionError('No notification was performed.')
        self.assertEqual(len(event_types), len(recorder.events))
        for event, expected_type in zip(recorder.events, event_types):
            self.assertIsInstance(event, expected_type)
        return result, recorder.events

    def assertNoNotification(self, callable_obj, *args, **kwargs):
        """Assert that no notifications are generated by the callable.

        :param callable_obj: The callable to call.
        :param *args: The arguments to pass to the callable.
        :param **kwargs: The keyword arguments to pass to the callable.
        """
        with EventRecorder() as recorder:
            result = callable_obj(*args, **kwargs)
        if len(recorder.events) == 1:
            raise AssertionError(
                'An event was generated: %r.' % recorder.events[0])
        elif len(recorder.events) > 1:
            event_list = ', '.join(
                [repr(event) for event in recorder.events])
            raise AssertionError(
                'Events were generated: %s.' % event_list)
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

    def assertTextMatchesExpressionIgnoreWhitespace(self,
                                                    regular_expression_txt,
                                                    text):

        def normalise_whitespace(text):
            return ' '.join(text.split())
        pattern = re.compile(
            normalise_whitespace(regular_expression_txt), re.S)
        self.assertIsNot(
            None, pattern.search(normalise_whitespace(text)), text)

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

    def attachOopses(self):
        if len(self.oopses) > 0:
            for (i, oops) in enumerate(self.oopses):
                content = Content(UTF8_TEXT, oops.get_chunks)
                self.addDetail("oops-%d" % i, content)

    def attachLibrarianLog(self, fixture):
        """Include the logChunks from fixture in the test details."""
        # Evaluate the log when called, not later, to permit the librarian to
        # be shutdown before the detail is rendered.
        chunks = fixture.getLogChunks()
        content = Content(UTF8_TEXT, lambda: chunks)
        self.addDetail('librarian-log', content)

    def setUp(self):
        super(TestCase, self).setUp()
        # Circular imports.
        from lp.testing.factory import ObjectFactory
        from canonical.testing.layers import LibrarianLayer
        self.factory = ObjectFactory()
        # Record the oopses generated during the test run.
        self.oopses = []
        self.useFixture(ZopeEventHandlerFixture(self._recordOops))
        self.addCleanup(self.attachOopses)
        if LibrarianLayer.librarian_fixture is not None:
            self.addCleanup(
                self.attachLibrarianLog,
                LibrarianLayer.librarian_fixture)
        set_permit_timeout_from_features(False)

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
        super(TestCaseWithFactory, self).setUp()
        login(user)
        self.addCleanup(logout)
        from lp.testing.factory import LaunchpadObjectFactory
        self.factory = LaunchpadObjectFactory()
        self.direct_database_server = False
        self._use_bzr_branch_called = False
        # XXX: JonathanLange 2010-12-24 bug=694140: Because of Launchpad's
        # messing with global log state (see
        # canonical.launchpad.scripts.logger), trace._bzr_logger does not
        # necessarily equal logging.getLogger('bzr'), so we have to explicitly
        # make it so in order to avoid "No handlers for "bzr" logger'
        # messages.
        trace._bzr_logger = logging.getLogger('bzr')

    def getUserBrowser(self, url=None, user=None, password='test'):
        """Return a Browser logged in as a fresh user, maybe opened at `url`.

        :param user: The user to open a browser for.
        :param password: The password to use.  (This cannot be determined
            because it's stored as a hash.)
        """
        # Do the import here to avoid issues with import cycles.
        from canonical.launchpad.testing.pages import setupBrowserForUser
        login(ANONYMOUS)
        if user is None:
            user = self.factory.makePerson(password=password)
        browser = setupBrowserForUser(user, password)
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
            naked_branch = removeSecurityProxy(db_branch)
            naked_branch.last_scanned_id = bzr_branch.last_revision()
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
        self.useTempDir()
        # Avoid leaking local user configuration into tests.
        self.useContext(override_environ(
            BZR_HOME=os.getcwd(), BZR_EMAIL=None, EMAIL=None,
            ))

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

    def getViewBrowser(self, context, view_name=None, no_login=False,
                       rootsite=None, user=None):
        if user is None:
            user = self.user
        # Make sure that there is a user interaction in order to generate the
        # canonical url for the context object.
        login(ANONYMOUS)
        url = canonical_url(context, view_name=view_name, rootsite=rootsite)
        logout()
        if no_login:
            from canonical.launchpad.testing.pages import setupBrowser
            browser = setupBrowser()
            browser.open(url)
            return browser
        else:
            return self.getUserBrowser(url, user)

    def getMainContent(self, context, view_name=None, rootsite=None,
                       no_login=False, user=None):
        """Beautiful soup of the main content area of context's page."""
        from canonical.launchpad.testing.pages import find_main_content
        browser = self.getViewBrowser(
            context, view_name, rootsite=rootsite, no_login=no_login,
            user=user)
        return find_main_content(browser.contents)

    def getMainText(self, context, view_name=None, rootsite=None,
                    no_login=False, user=None):
        """Return the main text of a context's page."""
        from canonical.launchpad.testing.pages import extract_text
        return extract_text(
            self.getMainContent(context, view_name, rootsite, no_login, user))


class WindmillTestCase(TestCaseWithFactory):
    """A TestCase class for Windmill tests.

    It provides a WindmillTestClient (self.client) with Launchpad's front
    page loaded.
    """

    suite_name = ''

    def setUp(self):
        super(WindmillTestCase, self).setUp()
        self.client = WindmillTestClient(self.suite_name)
        # Load the front page to make sure we don't get fooled by stale pages
        # left by the previous test. (For some reason, when you create a new
        # WindmillTestClient you get a new session and everything, but if you
        # do anything before you open() something you'd be operating on the
        # page that was last accessed by the previous test, which is the cause
        # of things like https://launchpad.net/bugs/515494)
        self.client.open(url=self.layer.appserver_root_url())

    def getClientFor(self, obj, user=None, password='test', view_name=None):
        """Return a new client, and the url that it has loaded."""
        client = WindmillTestClient(self.suite_name)
        if user is not None:
            email = removeSecurityProxy(user).preferredemail.email
            client.open(url=lpuser.get_basic_login_url(email, password))
            client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        if isinstance(obj, basestring):
            url = obj
        else:
            url = canonical_url(
                obj, view_name=view_name, force_local_path=True)
        obj_url = self.layer.base_url + url
        client.open(url=obj_url)
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        return client, obj_url


class WebServiceTestCase(TestCaseWithFactory):
    """Test case optimized for testing the web service using launchpadlib."""

    @property
    def layer(self):
        # XXX wgrant 2011-03-09 bug=505913:
        # TestTwistedJobRunner.test_timeout fails if this is at the
        # module level. There is probably some hidden circular import.
        from canonical.testing.layers import AppServerLayer
        return AppServerLayer

    def setUp(self):
        super(WebServiceTestCase, self).setUp()
        self.ws_version = 'devel'
        self.service = self.factory.makeLaunchpadService(
            version=self.ws_version)

    def wsObject(self, obj, user=None):
        """Return the launchpadlib version of the supplied object.

        :param obj: The object to find the launchpadlib equivalent of.
        :param user: The user to use for accessing the object over
            lauchpadlib.  Defaults to an arbitrary logged-in user.
        """
        if user is not None:
            service = self.factory.makeLaunchpadService(
                user, version=self.ws_version)
        else:
            service = self.service
        return ws_object(service, obj)


def quote_jquery_expression(expression):
    """jquery requires meta chars used in literals escaped with \\"""
    return re.sub(
        "([#!$%&()+,./:;?@~|^{}\\[\\]`*\\\'\\\"])", r"\\\\\1", expression)


class YUIUnitTestCase(WindmillTestCase):

    layer = None
    suite_name = ''

    _yui_results = None

    def initialize(self, test_path):
        self.test_path = test_path

    def setUp(self):
        super(YUIUnitTestCase, self).setUp()
        #This goes here to prevent circular import issues
        from canonical.testing.layers import BaseLayer
        _view_name = u'%s/+yui-unittest/' % BaseLayer.appserver_root_url()
        yui_runner_url = _view_name + self.test_path

        client = self.client
        client.open(url=yui_runner_url)
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        # This is very fragile for some reason, so we need a long delay here.
        client.waits.forElement(id='complete', timeout=constants.PAGE_LOAD)
        response = client.commands.getPageText()
        self._yui_results = {}
        # Maybe testing.pages should move to lp to avoid circular imports.
        from canonical.launchpad.testing.pages import find_tags_by_class
        entries = find_tags_by_class(
            response['result'], 'yui3-console-entry-TestRunner')
        for entry in entries:
            category = entry.find(
                attrs={'class': 'yui3-console-entry-cat'})
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
            "result must be a Zope result object, not %r." % (result, ))
        pread, pwrite = os.pipe()
        pid = os.fork()
        if pid == 0:
            # Child.
            os.close(pread)
            fdwrite = os.fdopen(pwrite, 'wb', 1)
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
            fdread = os.fdopen(pread, 'rb')
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


class EventRecorder:
    """Intercept and record Zope events.

    This prevents the events from propagating to their normal subscribers.
    The recorded events can be accessed via the 'events' list.
    """
    def __init__(self):
        self.events = []
        self.old_subscribers = None

    def __enter__(self):
        self.old_subscribers = zope.event.subscribers[:]
        zope.event.subscribers[:] = [self.events.append]
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        assert zope.event.subscribers == [self.events.append], (
            'Subscriber list has been changed while running!')
        zope.event.subscribers[:] = self.old_subscribers


@contextmanager
def feature_flags():
    """Provide a context in which feature flags work."""
    empty_request = LaunchpadTestRequest()
    old_features = getattr(features.per_thread, 'features', None)
    features.per_thread.features = FeatureController(
        ScopesFromRequest(empty_request).lookup)
    try:
        yield
    finally:
        features.per_thread.features = old_features


def get_lsb_information():
    """Returns a dictionary with the LSB host information.

    Code stolen form /usr/bin/lsb-release
    """
    # XXX: This doesn't seem like a generically-useful testing function.
    # Perhaps it should go in a sub-module or something? -- jml
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


def map_branch_contents(branch):
    """Return all files in branch at `branch_url`.

    :param branch_url: the URL for an accessible branch.
    :return: a dict mapping file paths to file contents.  Only regular
        files are included.
    """
    # XXX: This doesn't seem to be a generically useful testing function.
    # Perhaps it should go into a sub-module? -- jml
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


def set_feature_flag(name, value, scope=u'default', priority=1):
    """Set a feature flag to the specified value.

    In order to access the flag, use the feature_flags context manager or
    populate features.per_thread.features some other way.
    :param name: The name of the flag.
    :param value: The value of the flag.
    :param scope: The scope in which the specified value applies.
    """
    assert getattr(features.per_thread, 'features', None) is not None
    flag = FeatureFlag(
        scope=scope, flag=name, value=value, priority=priority)
    store = getFeatureStore()
    store.add(flag)
    # Make sure that the feature is saved into the db right now.
    store.flush()


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
    # Don't use inspect.getmembers() here because it fails on __provides__, a
    # descriptor added by zope.interface as part of its caching strategy. See
    # http://comments.gmane.org/gmane.comp.python.zope.interface/241.
    for name in dir(mock_class):
        if name == '__provides__':
            continue
        obj = getattr(mock_class, name)
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
    api_request = WebServiceTestRequest(SERVER_URL=str(launchpad._root_uri))
    return launchpad.load(canonical_url(obj, request=api_request))


@contextmanager
def temp_dir():
    """Provide a temporary directory as a ContextManager."""
    tempdir = tempfile.mkdtemp()
    yield tempdir
    shutil.rmtree(tempdir)


@contextmanager
def monkey_patch(context, **kwargs):
    """In the ContextManager scope, monkey-patch values.

    The context may be anything that supports setattr.  Packages,
    modules, objects, etc.  The kwargs are the name/value pairs for the
    values to set.
    """
    old_values = {}
    not_set = object()
    for name, value in kwargs.iteritems():
        old_values[name] = getattr(context, name, not_set)
        setattr(context, name, value)
    try:
        yield
    finally:
        for name, value in old_values.iteritems():
            if value is not_set:
                delattr(context, name)
            else:
                setattr(context, name, value)


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
