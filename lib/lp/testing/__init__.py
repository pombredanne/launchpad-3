# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0401,C0301

__metaclass__ = type
__all__ = [
    'ANONYMOUS',
    'capture_events',
    'FakeTime',
    'get_lsb_information',
    'is_logged_in',
    'login',
    'login_person',
    'logout',
    'map_branch_contents',
    'normalize_whitespace',
    'record_statements',
    'run_with_login',
    'run_with_storm_debug',
    'run_script',
    'TestCase',
    'TestCaseWithFactory',
    'test_tales',
    'time_counter',
    # XXX: This really shouldn't be exported from here. People should import
    # it from Zope.
    'verifyObject',
    'validate_mock_class',
    'with_anonymous_login',
    ]

import copy
from datetime import datetime, timedelta
from inspect import getargspec, getmembers, getmro, isclass, ismethod
import os
from pprint import pformat
import shutil
import subprocess
import tempfile
import time
import unittest

from bzrlib.branch import Branch as BzrBranch
from bzrlib.bzrdir import BzrDir, format_registry
from bzrlib.transport import get_transport

import pytz
from storm.expr import Variable
from storm.store import Store
from storm.tracer import install_tracer, remove_tracer_type

import testtools
import transaction

from twisted.python.util import mergeFunctionMetadata

from zope.component import getUtility
import zope.event
from zope.interface.verify import verifyClass, verifyObject
from zope.security.proxy import (
    isinstance as zope_isinstance, removeSecurityProxy)

from canonical.launchpad.webapp import errorlog
from canonical.config import config
from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.codehosting.vfs import branch_id_to_path, get_multi_server
# Import the login and logout functions here as it is a much better
# place to import them from in tests.
from lp.testing._login import (
    ANONYMOUS, is_logged_in, login, login_person, logout)
# canonical.launchpad.ftests expects test_tales to be imported from here.
# XXX: JonathanLange 2010-01-01: Why?!
from lp.testing._tales import test_tales

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

    def installFixture(self, fixture):
        """Install 'fixture', an object that has a `setUp` and `tearDown`.

        `installFixture` will run 'fixture.setUp' and schedule
        'fixture.tearDown' to be run during the test's tear down (using
        `addCleanup`).

        :param fixture: Any object that has a `setUp` and `tearDown` method.
        """
        fixture.setUp()
        self.addCleanup(fixture.tearDown)

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
            sql_class, **({'id': sql_object.id, attribute_name: date}))
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


class TestCaseWithFactory(TestCase):

    def setUp(self, user=ANONYMOUS):
        TestCase.setUp(self)
        login(user)
        self.addCleanup(logout)
        from lp.testing.factory import LaunchpadObjectFactory
        self.factory = LaunchpadObjectFactory()
        self.real_bzr_server = False

    def useTempDir(self):
        """Use a temporary directory for this test."""
        tempdir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(tempdir))
        cwd = os.getcwd()
        os.chdir(tempdir)
        self.addCleanup(lambda: os.chdir(cwd))

    def getUserBrowser(self, url=None):
        """Return a Browser logged in as a fresh user, maybe opened at `url`.
        """
        # Do the import here to avoid issues with import cycles.
        from canonical.launchpad.testing.pages import setupBrowser
        login(ANONYMOUS)
        user = self.factory.makePerson(password='test')
        naked_user = removeSecurityProxy(user)
        email = naked_user.preferredemail.email
        logout()
        browser = setupBrowser(
            auth="Basic %s:test" % str(email))
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
        transport = get_transport(branch_url)
        if not self.real_bzr_server:
            # for real bzr servers, the prefix always exists.
            transport.create_prefix()
        self.addCleanup(transport.delete_tree, '.')
        return BzrDir.create_branch_convenience(
            branch_url, format=format)

    def create_branch_and_tree(self, tree_location='.', product=None,
                               hosted=False, db_branch=None, format=None,
                               **kwargs):
        """Create a database branch, bzr branch and bzr checkout.

        :param tree_location: The path on disk to create the tree at.
        :param product: The product to associate with the branch.
        :param hosted: If True, create in the hosted area.  Otherwise, create
            in the mirrored area.
        :param db_branch: If supplied, the database branch to use.
        :param format: Override the default bzrdir format to create.
        :return: a `Branch` and a workingtree.
        """
        if db_branch is None:
            if product is None:
                db_branch = self.factory.makeAnyBranch(**kwargs)
            else:
                db_branch = self.factory.makeProductBranch(product, **kwargs)
        if hosted:
            branch_url = db_branch.getPullURL()
        else:
            branch_url = db_branch.warehouse_url
        if self.real_bzr_server:
            transaction.commit()
        bzr_branch = self.createBranchAtURL(branch_url, format=format)
        return db_branch, bzr_branch.create_checkout(
            tree_location, lightweight=True)

    def createBzrBranch(self, db_branch, parent=None):
        """Create a bzr branch for a database branch.

        :param db_branch: The database branch to create the branch for.
        :param parent: If supplied, the bzr branch to use as a parent.
        """
        bzr_branch = self.createBranchAtURL(db_branch.warehouse_url)
        if parent:
            bzr_branch.pull(parent)
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

    def createMirroredBranchAndTree(self):
        """Create a database branch, bzr branch and bzr checkout.

        This always uses the configured mirrored area, ignoring whatever
        server might be providing lp-mirrored: urls.

        Unlike normal codehosting operation, the working tree is stored in the
        branch directory.

        The branch and tree files are automatically deleted at the end of the
        test.

        :return: a `Branch` and a workingtree.
        """
        db_branch = self.factory.makeAnyBranch()
        bzr_branch = self.createBranchAtURL(self.getBranchPath(
                db_branch, config.codehosting.internal_branch_by_id_root))
        return db_branch, bzr_branch.bzrdir.open_workingtree()

    def useTempBzrHome(self):
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

    def useBzrBranches(self, real_server=False, direct_database=False):
        """Prepare for using bzr branches.

        This sets up support for lp-hosted and lp-mirrored URLs,
        changes to a temp directory, and overrides the bzr home directory.

        :param real_server: If true, use the "real" code hosting server,
            using an xmlrpc server, etc.
        """
        from lp.codehosting.scanner.tests.test_bzrsync import (
            FakeTransportServer)
        self.useTempBzrHome()
        self.real_bzr_server = real_server
        if real_server:
            server = get_multi_server(
                write_hosted=True, write_mirrored=True,
                direct_database=direct_database)
            server.setUp()
            self.addCleanup(server.destroy)
        else:
            os.mkdir('lp-mirrored')
            mirror_server = FakeTransportServer(get_transport('lp-mirrored'))
            mirror_server.setUp()
            self.addCleanup(mirror_server.tearDown)
            os.mkdir('lp-hosted')
            hosted_server = FakeTransportServer(
                get_transport('lp-hosted'), url_prefix='lp-hosted:///')
            hosted_server.setUp()
            self.addCleanup(hosted_server.tearDown)


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


def with_anonymous_login(function):
    """Decorate 'function' so that it runs in an anonymous login."""
    def wrapped(*args, **kwargs):
        login(ANONYMOUS)
        try:
            return function(*args, **kwargs)
        finally:
            logout()
    return mergeFunctionMetadata(function, wrapped)


def run_with_login(person, function, *args, **kwargs):
    """Run 'function' with 'person' logged in."""
    current_person = getUtility(ILaunchBag).user
    logout()
    login_person(person)
    try:
        return function(*args, **kwargs)
    finally:
        logout()
        login_person(current_person)


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
    env = copy.copy(os.environ)
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
def map_branch_contents(branch_url):
    """Return all files in branch at `branch_url`.

    :param branch_url: the URL for an accessible branch.
    :return: a dict mapping file paths to file contents.  Only regular
        files are included.
    """
    contents = {}
    branch = BzrBranch.open(branch_url)
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
