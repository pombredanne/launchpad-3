# Copyright 2006-2008 Canonical Ltd.  All rights reserved.
# We like global!
# pylint: disable-msg=W0603,W0702

"""Layers used by Canonical tests.

Layers are the mechanism used by the Zope3 test runner to efficiently
provide environments for tests and are documented in the lib/zope/testing.

Note that every Layer should define all of setUp, tearDown, testSetUp
and testTearDown. If you don't do this, a base class' method will be called
instead probably breaking something.

Preferred style is to not use the 'cls' argument to Layer class methods,
as this is unambguious.

TODO: Make the Zope3 test runner handle multiple layers per test instead
of one, forcing us to attempt to make some sort of layer tree.
-- StuartBishop 20060619
"""

__metaclass__ = type

__all__ = [
    'BaseLayer', 'DatabaseLayer', 'GoogleServiceLayer',
    'LibrarianLayer', 'FunctionalLayer', 'LaunchpadLayer',
    'ZopelessLayer', 'LaunchpadFunctionalLayer',
    'LaunchpadZopelessLayer', 'LaunchpadScriptLayer', 'PageTestLayer',
    'LayerConsistencyError', 'LayerIsolationError', 'TwistedLayer',
    'ExperimentalLaunchpadZopelessLayer',
    'TwistedLaunchpadZopelessLayer'
    ]

import gc
import logging
import os
import signal
import socket
import sys
from textwrap import dedent
import threading
import time
from unittest import TestCase, TestResult
from urllib import urlopen

import psycopg
import transaction

import zope.app.testing.functional
from zope.app.testing.functional import FunctionalTestSetup, ZopePublication
from zope.component import getUtility, getGlobalSiteManager
from zope.component.interfaces import ComponentLookupError
from zope.security.management import getSecurityPolicy
from zope.security.simplepolicies import PermissiveSecurityPolicy
from zope.server.logger.pythonlogger import PythonLogger

from canonical.config import config
from canonical.database.sqlbase import ZopelessTransactionManager
from canonical.launchpad.interfaces import IMailBox, IOpenLaunchBag
from canonical.launchpad.ftests import ANONYMOUS, login, logout, is_logged_in
import canonical.launchpad.mail.stub
from canonical.launchpad.mail.mailbox import TestMailBox
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.testing.tests.googleserviceharness import (
    GoogleServiceTestSetup)
from canonical.launchpad.webapp.servers import (
    LaunchpadAccessLogger, register_launchpad_request_publication_factories)
from canonical.lazr.timeout import (
    get_default_timeout_function, set_default_timeout_function)
from canonical.lp import initZopeless
from canonical.librarian.ftests.harness import LibrarianTestSetup
from canonical.testing import reset_logging
from canonical.testing.profiled import profiled


orig__call__ = zope.app.testing.functional.HTTPCaller.__call__


class MockRootFolder:
    """Implement the minimum functionality required by Z3 ZODB dependencies

    Installed as part of FunctionalLayer.testSetUp() to allow the http()
    method (zope.app.testing.functional.HTTPCaller) to work.
    """
    @property
    def _p_jar(self):
        return self
    def sync(self):
        pass


class LayerError(Exception):
    pass


class LayerInvariantError(LayerError):
    """Layer self checks have detected a fault. Invariant has been violated.

    This indicates the Layer infrastructure has messed up. The test run
    should be aborted.
    """
    pass


class LayerIsolationError(LayerError):
    """Test isolation has been broken, probably by the test we just ran.

    This generally indicates a test has screwed up by not resetting
    something correctly to the default state.

    The test suite should abort if it cannot clean up the mess as further
    test failures may well be spurious.
    """


def is_ca_available():
    """Returns true if the component architecture has been loaded"""
    try:
        getUtility(IOpenLaunchBag)
    except ComponentLookupError:
        return False
    else:
        return True


class BaseLayer:
    """Base layer.

    All out layers should subclass Base, as this is where we will put
    test isolation checks to ensure that tests to not leave global
    resources in a mess.

    XXX: StuartBishop 2006-07-12: Unit tests (tests with no layer) will not
    get these checks. The Z3 test runner should be updated so that a layer
    can be specified to use for unit tests.
    """
    # Set to True when we are running tests in this layer.
    isSetUp = False

    # The name of this test - this is the same output that the testrunner
    # displays. It is probably unique, but not guaranteed to be so.
    test_name = None

    @classmethod
    @profiled
    def setUp(cls):
        BaseLayer.isSetUp = True

        # Kill any Librarian left running from a previous test run.
        LibrarianTestSetup().tearDown()

        # Kill any database left lying around from a previous test run.
        try:
            DatabaseLayer.connect().close()
        except psycopg.Error:
            pass
        else:
            DatabaseLayer._dropDb()

    @classmethod
    @profiled
    def tearDown(cls):
        BaseLayer.isSetUp = False

    @classmethod
    @profiled
    def testSetUp(cls):
        # Store currently running threads so we can detect if a test
        # leaves new threads running.
        BaseLayer._threads = threading.enumerate()

        BaseLayer.check()

        BaseLayer.original_working_directory = os.getcwd()

        # Tests and test infrastruture sometimes needs to know the test
        # name.  The testrunner doesn't provide this, so we have to do
        # some snooping.
        import inspect
        frame = inspect.currentframe()
        try:
            while frame.f_code.co_name != 'startTest':
                frame = frame.f_back
            BaseLayer.test_name = str(frame.f_locals['test'])
        finally:
            del frame # As per no-leak stack inspection in Python reference.

    @classmethod
    @profiled
    def testTearDown(cls):

        # Get our current working directory, handling the case where it no
        # longer exists (!).
        try:
            cwd = os.getcwd()
        except OSError:
            cwd = None

        # Handle a changed working directory. If the test succeeded,
        # add an error. Then restore the working directory so the test
        # run can continue.
        if cwd != BaseLayer.original_working_directory:
            BaseLayer.flagTestIsolationFailure(
                    "Test failed to restore working directory.")
            os.chdir(BaseLayer.original_working_directory)

        BaseLayer.original_working_directory = None

        reset_logging()

        del canonical.launchpad.mail.stub.test_emails[:]

        BaseLayer.test_name = None

        BaseLayer.check()

        # Check for tests that leave live threads around early.
        # A live thread may be the cause of other failures, such as
        # uncollectable garbage.
        new_threads = [
                thread for thread in threading.enumerate()
                    if thread not in BaseLayer._threads and thread.isAlive()]
        if new_threads:
            BaseLayer.flagTestIsolationFailure(
                    "Test left new live threads: %s" % repr(new_threads))
        del BaseLayer._threads

        # Objects with __del__ methods cannot participate in refence cycles.
        # Fail tests with memory leaks now rather than when Launchpad crashes
        # due to a leak because someone ignored the warnings.
        if gc.garbage:
            gc.collect() # Expensive, so only do if there might be garbage.
            if gc.garbage:
                BaseLayer.flagTestIsolationFailure(
                        "Test left uncollectable garbage\n"
                        "%s (referenced from %s)"
                        % (gc.garbage, gc.get_referrers(*gc.garbage)))

    @classmethod
    @profiled
    def check(cls):
        """Check that the environment is working as expected.

        We check here so we can detect tests that, for example,
        initialize the Zopeless or Functional environments and
        are using the incorrect layer.
        """
        if FunctionalLayer.isSetUp and ZopelessLayer.isSetUp:
            raise LayerInvariantError(
                "Both Zopefull and Zopeless CA environments setup"
                )

        # Detect a test that causes the component architecture to be loaded.
        # This breaks test isolation, as it cannot be torn down.
        if (is_ca_available() and not FunctionalLayer.isSetUp
                and not ZopelessLayer.isSetUp):
            raise LayerIsolationError(
                "Component architecture should not be loaded by tests. "
                "This should only be loaded by the Layer."
                )

        # Detect a test that installed the Zopeless database adapter
        # but failed to unregister it. This could be done automatically,
        # but it is better for the tear down to be explicit.
        if ZopelessTransactionManager._installed is not None:
            raise LayerIsolationError(
                    "Zopeless environment was setup and not torn down."
                    )

        # Detect a test that forgot to reset the default socket timeout.
        # This safety belt is cheap and protects us from very nasty
        # intermittent test failures: see bug #140068 for an example.
        if socket.getdefaulttimeout() is not None:
            raise LayerIsolationError(
                "Test didn't reset the socket default timeout.")

    @classmethod
    def flagTestIsolationFailure(cls, message):
        """Handle a breakdown in test isolation.

        If the test that broke isolation thinks it succeeded,
        add an error. If the test failed, don't add a notification
        as the isolation breakdown is probably just fallout.

        The layer that detected the isolation failure still needs to
        repair the damage, or in the worst case abort the test run.
        """
        test_result = BaseLayer.getCurrentTestResult()
        if test_result.wasSuccessful():
            # pylint: disable-msg=W0702
            test_case = BaseLayer.getCurrentTestCase()
            try:
                raise LayerIsolationError(message)
            except:
                test_result.addError(test_case, sys.exc_info())

    @classmethod
    def getCurrentTestResult(cls):
        """Return the TestResult currently in play."""
        import inspect
        frame = inspect.currentframe()
        try:
            while True:
                f_self = frame.f_locals.get('self', None)
                if isinstance(f_self, TestResult):
                    return frame.f_locals['self']
                frame = frame.f_back
        finally:
            del frame # As per no-leak stack inspection in Python reference.

    @classmethod
    def getCurrentTestCase(cls):
        """Return the test currently in play."""
        import inspect
        frame = inspect.currentframe()
        try:
            while True:
                f_self = frame.f_locals.get('self', None)
                if isinstance(f_self, TestCase):
                    return f_self
                f_test = frame.f_locals.get('test', None)
                if isinstance(f_test, TestCase):
                    return f_test
                frame = frame.f_back
            return frame.f_locals['test']
        finally:
            del frame # As per no-leak stack inspection in Python reference.


class LibrarianLayer(BaseLayer):
    """Provides tests access to a Librarian instance.

    Calls to the Librarian will fail unless there is also a Launchpad
    database available.
    """
    _reset_between_tests = True

    @classmethod
    @profiled
    def setUp(cls):
        if not LibrarianLayer._reset_between_tests:
            raise LayerInvariantError(
                    "_reset_between_tests changed before LibrarianLayer "
                    "was actually used."
                    )
        LibrarianTestSetup().setUp()
        LibrarianLayer._check_and_reset()

    @classmethod
    @profiled
    def tearDown(cls):
        if not LibrarianLayer._reset_between_tests:
            raise LayerInvariantError(
                    "_reset_between_tests not reset before LibrarianLayer "
                    "shutdown"
                    )
        LibrarianLayer._check_and_reset()
        LibrarianTestSetup().tearDown()

    @classmethod
    @profiled
    def _check_and_reset(cls):
        """Raise an exception if the Librarian has been killed.
        Reset the storage unless this has been disabled.
        """
        try:
            f = urlopen(config.librarian.download_url)
            f.read()
        except Exception, e:
            raise LayerIsolationError(
                    "Librarian has been killed or has hung."
                    "Tests should use LibrarianLayer.hide() and "
                    "LibrarianLayer.reveal() where possible, and ensure "
                    "the Librarian is restarted if it absolutetly must be "
                    "shutdown: " + str(e)
                    )
        if LibrarianLayer._reset_between_tests:
            LibrarianTestSetup().clear()

    @classmethod
    @profiled
    def testSetUp(cls):
        LibrarianLayer._check_and_reset()

    @classmethod
    @profiled
    def testTearDown(cls):
        if LibrarianLayer._hidden:
            LibrarianLayer.reveal()
        LibrarianLayer._check_and_reset()

    # Flag maintaining state of hide()/reveal() calls
    _hidden = False

    # Fake upload socket used when the librarian is hidden
    _fake_upload_socket = None

    @classmethod
    @profiled
    def hide(cls):
        """Hide the Librarian so nothing can find it. We don't want to
        actually shut it down because starting it up again is expensive.

        We do this by altering the configuration so the Librarian client
        looks for the Librarian server on the wrong port.
        """
        LibrarianLayer._hidden = True
        if LibrarianLayer._fake_upload_socket is None:
            # Bind to a socket, but don't listen to it.  This way we
            # guarantee that connections to the given port will fail.
            LibrarianLayer._fake_upload_socket = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            assert config.librarian.upload_host == 'localhost', (
                'Can only hide librarian if it is running locally')
            LibrarianLayer._fake_upload_socket.bind(('127.0.0.1', 0))

        host, port = LibrarianLayer._fake_upload_socket.getsockname()
        librarian_data = dedent("""
            [librarian]
            upload_port: %s
            """ % port)
        config.push('hide_librarian', librarian_data)

    @classmethod
    @profiled
    def reveal(cls):
        """Reveal a hidden Librarian.

        This just involves restoring the config to the original value.
        """
        LibrarianLayer._hidden = False
        config.pop('hide_librarian')


# We store a reference to the DB-API connect method here when we
# put a proxy in its place.
_org_connect = None


class DatabaseLayer(BaseLayer):
    """Provides tests access to the Launchpad sample database."""

    # If set to False, database will not be reset between tests. It is
    # your responsibility to set it back to True and call
    # Database.force_dirty_database() when you do so.
    _reset_between_tests = True

    @classmethod
    @profiled
    def setUp(cls):
        DatabaseLayer.force_dirty_database()

    @classmethod
    @profiled
    def tearDown(cls):
        # Don't leave the DB lying around or it might break tests
        # that depend on it not being there on startup, such as found
        # in test_layers.py
        DatabaseLayer.force_dirty_database()
        # Imported here to avoid circular import issues. This
        # functionality should be migrated into this module at some
        # point. -- StuartBishop 20060712
        from canonical.launchpad.ftests.harness import LaunchpadTestSetup
        LaunchpadTestSetup().tearDown()

    @classmethod
    @profiled
    def testSetUp(cls):
        # Imported here to avoid circular import issues. This
        # functionality should be migrated into this module at some
        # point. -- StuartBishop 20060712
        from canonical.launchpad.ftests.harness import LaunchpadTestSetup
        if DatabaseLayer._reset_between_tests:
            LaunchpadTestSetup().setUp()
        # Ensure that the database is connectable. Because we might have
        # just created it, keep trying for a few seconds incase PostgreSQL
        # is taking its time getting its house in order.
        attempts = 60
        for count in range(0, attempts):
            try:
                DatabaseLayer.connect().close()
            except psycopg.Error:
                if count == attempts - 1:
                    raise
                time.sleep(0.5)
            else:
                break

        if DatabaseLayer.use_mockdb is True:
            DatabaseLayer.installMockDb()

    @classmethod
    @profiled
    def testTearDown(cls):
        if DatabaseLayer.use_mockdb is True:
            DatabaseLayer.uninstallMockDb()

        # Ensure that the database is connectable
        DatabaseLayer.connect().close()

        # Imported here to avoid circular import issues. This
        # functionality should be migrated into this module at some
        # point. -- StuartBishop 20060712
        from canonical.launchpad.ftests.harness import LaunchpadTestSetup
        if DatabaseLayer._reset_between_tests:
            LaunchpadTestSetup().tearDown()

    use_mockdb = False
    mockdb_mode = None

    @classmethod
    @profiled
    def installMockDb(cls):
        assert DatabaseLayer.mockdb_mode is None, 'mock db already installed'

        from canonical.testing.mockdb import (
                script_filename, ScriptRecorder, ScriptPlayer,
                )

        # We need a unique key for each test to store the mock db script.
        test_key = BaseLayer.test_name
        assert test_key, "Invalid test_key %r" % (test_key,)

        # Determine if we are in replay or record mode and setup our
        # mock db script.
        filename = script_filename(test_key)
        if os.path.exists(filename):
            DatabaseLayer.mockdb_mode = 'replay'
            DatabaseLayer.script = ScriptPlayer(test_key)
        else:
            DatabaseLayer.mockdb_mode = 'record'
            DatabaseLayer.script = ScriptRecorder(test_key)

        global _org_connect
        _org_connect = psycopg.connect
        # Proxy real connections with our mockdb.
        def fake_connect(*args, **kw):
            return DatabaseLayer.script.connect(_org_connect, *args, **kw)
        psycopg.connect = fake_connect

    @classmethod
    @profiled
    def uninstallMockDb(cls):
        if DatabaseLayer.mockdb_mode is None:
            return # Already uninstalled

        # Store results if we are recording
        if DatabaseLayer.mockdb_mode == 'record':
            DatabaseLayer.script.store()
            assert os.path.exists(DatabaseLayer.script.script_filename), (
                    "Stored results but no script on disk.")

        DatabaseLayer.mockdb_mode = None
        global _org_connect
        psycopg.connect = _org_connect
        _org_connect = None

    @classmethod
    @profiled
    def force_dirty_database(cls):
        from canonical.launchpad.ftests.harness import LaunchpadTestSetup
        LaunchpadTestSetup().force_dirty_database()

    @classmethod
    @profiled
    def connect(cls):
        from canonical.launchpad.ftests.harness import LaunchpadTestSetup
        return LaunchpadTestSetup().connect()

    @classmethod
    @profiled
    def _dropDb(cls):
        from canonical.launchpad.ftests.harness import LaunchpadTestSetup
        return LaunchpadTestSetup().dropDb()


def test_default_timeout():
    """Don't timeout by default in tests."""
    return None


class LaunchpadLayer(DatabaseLayer, LibrarianLayer):
    """Provides access to the Launchpad database and daemons.

    We need to ensure that the database setup runs before the daemon
    setup, or the database setup will fail because the daemons are
    already connected to the database.

    This layer is mainly used by tests that call initZopeless() themselves.
    """
    @classmethod
    @profiled
    def setUp(cls):
        pass

    @classmethod
    @profiled
    def tearDown(cls):
        pass

    @classmethod
    @profiled
    def testSetUp(cls):
        # By default, don't make external service tests timeout.
        if get_default_timeout_function() is not None:
            raise LayerIsolationError(
                "Global default timeout function should be None.")
        set_default_timeout_function(test_default_timeout)

    @classmethod
    @profiled
    def testTearDown(cls):
        if get_default_timeout_function() is not test_default_timeout:
            raise LayerIsolationError(
                "Test didn't reset default timeout function.")
        set_default_timeout_function(None)


class FunctionalLayer(BaseLayer):
    """Loads the Zope3 component architecture in appserver mode."""

    # Set to True if tests using the Functional layer are currently being run.
    isSetUp = False

    @classmethod
    @profiled
    def setUp(cls):
        FunctionalLayer.isSetUp = True
        FunctionalTestSetup().setUp()

        # Assert that FunctionalTestSetup did what it says it does
        if not is_ca_available():
            raise LayerInvariantError("Component architecture failed to load")

        # If our request publication factories were defined using ZCML,
        # they'd be set up by FunctionalTestSetup().setUp(). Since
        # they're defined by Python code, we need to call that code
        # here.
        register_launchpad_request_publication_factories()

    @classmethod
    @profiled
    def tearDown(cls):
        FunctionalLayer.isSetUp = False
        # Signal Layer cannot be torn down fully
        raise NotImplementedError

    @classmethod
    @profiled
    def testSetUp(cls):
        transaction.abort()
        transaction.begin()

        # Fake a root folder to keep Z3 ZODB dependencies happy.
        fs = FunctionalTestSetup()
        if not fs.connection:
            fs.connection = fs.db.open()
        root = fs.connection.root()
        root[ZopePublication.root_name] = MockRootFolder()

        # Should be impossible, as the CA cannot be unloaded. Something
        # mighty nasty has happened if this is triggered.
        if not is_ca_available():
            raise LayerInvariantError(
                "Component architecture not loaded or totally screwed"
                )

    @classmethod
    @profiled
    def testTearDown(cls):
        # Should be impossible, as the CA cannot be unloaded. Something
        # mighty nasty has happened if this is triggered.
        if not is_ca_available():
            raise LayerInvariantError(
                "Component architecture not loaded or totally screwed"
                )

        transaction.abort()


class ZopelessLayer(BaseLayer):
    """Layer for tests that need the Zopeless component architecture
    loaded using execute_zcml_for_scrips()
    """

    # Set to True if tests in the Zopeless layer are currently being run.
    isSetUp = False

    @classmethod
    @profiled
    def setUp(cls):
        ZopelessLayer.isSetUp = True
        execute_zcml_for_scripts()

        # Assert that execute_zcml_for_scripts did what it says it does.
        if not is_ca_available():
            raise LayerInvariantError(
                "Component architecture not loaded by "
                "execute_zcml_for_scripts")

        # If our request publication factories were defined using
        # ZCML, they'd be set up by execute_zcml_for_scripts(). Since
        # they're defined by Python code, we need to call that code
        # here.
        register_launchpad_request_publication_factories()

    @classmethod
    @profiled
    def tearDown(cls):
        ZopelessLayer.isSetUp = False
        # Signal Layer cannot be torn down fully
        raise NotImplementedError

    @classmethod
    @profiled
    def testSetUp(cls):
        # Should be impossible, as the CA cannot be unloaded. Something
        # mighty nasty has happened if this is triggered.
        if not is_ca_available():
            raise LayerInvariantError(
                "Component architecture not loaded or totally screwed"
                )
        # This should not happen here, it should be caught by the
        # testTearDown() method. If it does, something very nasty
        # happened.
        if getSecurityPolicy() != PermissiveSecurityPolicy:
            raise LayerInvariantError(
                "Previous test removed the PermissiveSecurityPolicy.")

        # execute_zcml_for_scripts() sets up an interaction for the
        # anonymous user. A previous script may have changed or removed
        # the interaction, so set it up again
        login(ANONYMOUS)

    @classmethod
    @profiled
    def testTearDown(cls):
        # Should be impossible, as the CA cannot be unloaded. Something
        # mighty nasty has happened if this is triggered.
        if not is_ca_available():
            raise LayerInvariantError(
                "Component architecture not loaded or totally screwed"
                )
        # Make sure that a test that changed the security policy, reset it
        # back to its default value.
        if getSecurityPolicy() != PermissiveSecurityPolicy:
            raise LayerInvariantError(
                "This test removed the PermissiveSecurityPolicy and didn't "
                "restore it.")
        logout()


class TwistedLayer(BaseLayer):
    """A layer for cleaning up the Twisted thread pool."""

    @classmethod
    @profiled
    def setUp(cls):
        pass

    @classmethod
    @profiled
    def tearDown(cls):
        pass

    @classmethod
    def _save_signals(cls):
        """Save the current signal handlers."""
        TwistedLayer._original_sigint = signal.getsignal(signal.SIGINT)
        TwistedLayer._original_sigterm = signal.getsignal(signal.SIGTERM)
        TwistedLayer._original_sigchld = signal.getsignal(signal.SIGCHLD)

    @classmethod
    def _restore_signals(cls):
        """Restore the signal handlers."""
        signal.signal(signal.SIGINT, TwistedLayer._original_sigint)
        signal.signal(signal.SIGTERM, TwistedLayer._original_sigterm)
        signal.signal(signal.SIGCHLD, TwistedLayer._original_sigchld)

    @classmethod
    @profiled
    def testSetUp(cls):
        TwistedLayer._save_signals()
        from twisted.internet import interfaces, reactor
        from twisted.python import threadpool
        if interfaces.IReactorThreads.providedBy(reactor):
            pool = getattr(reactor, 'threadpool', None)
            # If the Twisted threadpool has been obliterated (probably by
            # testTearDown), then re-build it using the values that Twisted
            # uses.
            if pool is None:
                reactor.threadpool = threadpool.ThreadPool(0, 10)
                reactor.threadpool.start()

    @classmethod
    @profiled
    def testTearDown(cls):
        # Shutdown and obliterate the Twisted threadpool, to plug up leaking
        # threads.
        from twisted.internet import interfaces, reactor
        if interfaces.IReactorThreads.providedBy(reactor):
            reactor.suggestThreadPoolSize(0)
            pool = getattr(reactor, 'threadpool', None)
            if pool is not None:
                reactor.threadpool.stop()
                reactor.threadpool = None
        TwistedLayer._restore_signals()


class GoogleServiceLayer(BaseLayer):
    """Tests for Google web service integration."""

    @classmethod
    def setUp(cls):
        GoogleServiceTestSetup().setUp()

    @classmethod
    def tearDown(cls):
        GoogleServiceTestSetup().tearDown()

    @classmethod
    def testSetUp(self):
        # We need to prevent BaseLayer.testSetUp() from
        # firing, or else we will get a LayerIsolationError.
        pass

    @classmethod
    def testTearDown(self):
        # We need to prevent BaseLayer.testTearDown() from
        # firing, or else we will get a LayerIsolationError.
        pass


class LaunchpadFunctionalLayer(LaunchpadLayer, FunctionalLayer,
                               GoogleServiceLayer):
    """Provides the Launchpad Zope3 application server environment."""
    @classmethod
    @profiled
    def setUp(cls):
        pass

    @classmethod
    @profiled
    def tearDown(cls):
        pass

    @classmethod
    @profiled
    def testSetUp(cls):
        # Reset any statistics
        from canonical.launchpad.webapp.opstats import OpStats
        OpStats.resetStats()
        from canonical.launchpad.ftests.harness import _reconnect_sqlos

        # Connect SQLOS
        _reconnect_sqlos()

    @classmethod
    @profiled
    def testTearDown(cls):
        getUtility(IOpenLaunchBag).clear()

        # If tests forget to logout, we can do it for them.
        if is_logged_in():
            logout()

        # Reset any statistics
        from canonical.launchpad.webapp.opstats import OpStats
        OpStats.resetStats()

        # Disconnect SQLOS so it doesn't get in the way of database resets
        from canonical.launchpad.ftests.harness import _disconnect_sqlos
        _disconnect_sqlos()


class LaunchpadZopelessLayer(ZopelessLayer, LaunchpadLayer):
    """Full Zopeless environment including Component Architecture and
    database connections initialized.
    """
    @classmethod
    @profiled
    def setUp(cls):
        # Make a TestMailBox available
        # This is registered via ZCML in the LaunchpadFunctionalLayer
        # XXX flacoste 2006-10-25 bug=68189: This should be configured
        # from ZCML but execute_zcml_for_scripts() doesn't cannot support
        # a different testing configuration.
        getGlobalSiteManager().provideUtility(IMailBox, TestMailBox())

    @classmethod
    @profiled
    def tearDown(cls):
        # Signal Layer cannot be torn down fully
        raise NotImplementedError

    @classmethod
    @profiled
    def testSetUp(cls):
        from canonical.launchpad.ftests.harness import (
                LaunchpadZopelessTestSetup
                )
        if ZopelessTransactionManager._installed is not None:
            raise LayerIsolationError(
                "Last test using Zopeless failed to tearDown correctly"
                )
        LaunchpadZopelessLayer.txn = initZopeless()
        LaunchpadZopelessTestSetup.txn = LaunchpadZopelessLayer.txn

        # Connect SQLOS
        from canonical.launchpad.ftests.harness import _reconnect_sqlos
        _reconnect_sqlos()

    @classmethod
    @profiled
    def testTearDown(cls):
        LaunchpadZopelessLayer.txn.abort()
        LaunchpadZopelessLayer.txn.uninstall()
        if ZopelessTransactionManager._installed is not None:
            raise LayerInvariantError(
                "Failed to uninstall ZopelessTransactionManager"
                )
        from canonical.launchpad.ftests.harness import _disconnect_sqlos
        _disconnect_sqlos()

    @classmethod
    @profiled
    def commit(cls):
        LaunchpadZopelessLayer.txn.commit()

    @classmethod
    @profiled
    def abort(cls):
        LaunchpadZopelessLayer.txn.abort()

    @classmethod
    @profiled
    def switchDbUser(cls, dbuser):
        LaunchpadZopelessLayer.alterConnection(dbuser=dbuser)

    @classmethod
    @profiled
    def alterConnection(cls, **kw):
        """Reset the connection, and reopen the connection by calling
        initZopeless with the given keyword arguments.
        """
        from canonical.launchpad.ftests.harness import (
                LaunchpadZopelessTestSetup
                )
        LaunchpadZopelessLayer.txn.abort()
        LaunchpadZopelessLayer.txn.uninstall()
        LaunchpadZopelessLayer.txn = initZopeless(**kw)
        LaunchpadZopelessTestSetup.txn = LaunchpadZopelessLayer.txn


class ExperimentalLaunchpadZopelessLayer(LaunchpadZopelessLayer):
    """LaunchpadZopelessLayer using the mock database."""

    @classmethod
    def setUp(cls):
        DatabaseLayer.use_mockdb = True

    @classmethod
    def tearDown(cls):
        DatabaseLayer.use_mockdb = False

    @classmethod
    def testSetUp(cls):
        pass

    @classmethod
    def testTearDown(cls):
        pass


class LaunchpadScriptLayer(ZopelessLayer, LaunchpadLayer):
    """Testing layer for scripts using the main Launchpad database adapter"""

    @classmethod
    @profiled
    def setUp(cls):
        # Make a TestMailBox available
        # This is registered via ZCML in the LaunchpadFunctionalLayer
        # XXX flacoste 2006-10-25 bug=68189: This should be configured from
        # ZCML but execute_zcml_for_scripts() doesn't cannot support a
        # different testing configuration.
        getGlobalSiteManager().provideUtility(IMailBox, TestMailBox())

    @classmethod
    @profiled
    def tearDown(cls):
        # Signal Layer cannot be torn down fully
        raise NotImplementedError

    @classmethod
    @profiled
    def testSetUp(cls):
        from canonical.launchpad.ftests.harness import _reconnect_sqlos
        # Connect SQLOS
        _reconnect_sqlos()

    @classmethod
    @profiled
    def testTearDown(cls):
        # Disconnect SQLOS so it doesn't get in the way of database resets
        from canonical.launchpad.ftests.harness import _disconnect_sqlos
        _disconnect_sqlos()

    @classmethod
    @profiled
    def switchDbConfig(cls, database_config_section):
        from canonical.launchpad.ftests.harness import _reconnect_sqlos
        # Connect SQLOS
        _reconnect_sqlos(database_config_section=database_config_section)


class MockHTTPTask:

    class MockHTTPRequestParser:
        headers = None
        first_line = None

    class MockHTTPServerChannel:
        # This is not important to us, so we can hardcode it here.
        addr = ['127.0.0.88', 80]

    request_data = MockHTTPRequestParser()
    channel = MockHTTPServerChannel()

    def __init__(self, response, first_line):
        self.request = response._request
        # We have no way of knowing when the task started, so we use
        # the current time here. That shouldn't be a problem since we don't
        # care about that for our tests anyway.
        self.start_time = time.time()
        self.status = response.getStatus()
        self.bytes_written = int(response.getHeader('Content-length'))
        self.request_data.headers = self.request.headers
        self.request_data.first_line = first_line

    def getCGIEnvironment(self):
        return self.request._orig_env


class PageTestLayer(LaunchpadFunctionalLayer):
    """Environment for page tests.
    """
    @classmethod
    @profiled
    def resetBetweenTests(cls, flag):
        LibrarianLayer._reset_between_tests = flag
        DatabaseLayer._reset_between_tests = flag

    @classmethod
    @profiled
    def setUp(cls):
        file_handler = logging.FileHandler('pagetests-access.log', 'w')
        file_handler.setFormatter(logging.Formatter())
        logger = PythonLogger('pagetests-access')
        logger.logger.addHandler(file_handler)
        logger.logger.setLevel(logging.INFO)
        access_logger = LaunchpadAccessLogger(logger)
        def my__call__(obj, request_string, handle_errors=True, form=None):
            """Call HTTPCaller.__call__ and log the page hit."""
            response = orig__call__(
                obj, request_string, handle_errors=handle_errors, form=form)
            first_line = request_string.strip().splitlines()[0]
            access_logger.log(MockHTTPTask(response._response, first_line))
            return response

        PageTestLayer.orig__call__ = (
                zope.app.testing.functional.HTTPCaller.__call__)
        zope.app.testing.functional.HTTPCaller.__call__ = my__call__
        PageTestLayer.resetBetweenTests(True)

    @classmethod
    @profiled
    def tearDown(cls):
        PageTestLayer.resetBetweenTests(True)
        zope.app.testing.functional.HTTPCaller.__call__ = (
                PageTestLayer.orig__call__)

    @classmethod
    @profiled
    def startStory(cls):
        DatabaseLayer.testSetUp()
        LibrarianLayer.testSetUp()
        PageTestLayer.resetBetweenTests(False)

    @classmethod
    @profiled
    def endStory(cls):
        PageTestLayer.resetBetweenTests(True)
        LibrarianLayer.testTearDown()
        DatabaseLayer.testTearDown()

    @classmethod
    @profiled
    def testSetUp(cls):
        pass

    @classmethod
    @profiled
    def testTearDown(cls):
        pass


class TwistedLaunchpadZopelessLayer(TwistedLayer, LaunchpadZopelessLayer):
    """A layer for cleaning up the Twisted thread pool."""
