# Copyright 2006-2008 Canonical Ltd.  All rights reserved.

"""Layers used by Canonical tests.

Layers are the mechanism used by the Zope3 test runner to efficiently
provide environments for tests and are documented in the lib/zope/testing.

Note that every Layer should define all of setUp, tearDown, testSetUp
and testTearDown. If you don't do this, a base class' method will be called
instead probably breaking something.

TODO: Make the Zope3 test runner handle multiple layers per test instead
of one, forcing us to attempt to make some sort of layer tree.
-- StuartBishop 20060619
"""

__metaclass__ = type

__all__ = [
    'BaseLayer', 'DatabaseLayer', 'LibrarianLayer', 'FunctionalLayer',
    'LaunchpadLayer', 'ZopelessLayer', 'LaunchpadFunctionalLayer',
    'LaunchpadZopelessLayer', 'LaunchpadScriptLayer', 'PageTestLayer',
    'LayerConsistencyError', 'LayerIsolationError', 'TwistedLayer',
    'ExperimentalLaunchpadZopelessLayer',
    ]

import logging
import os
import socket
import time
from urllib import urlopen

import psycopg
import transaction

import zope.app.testing.functional
from zope.app.testing.functional import ZopePublication
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
from canonical.launchpad.webapp.servers import (
    LaunchpadAccessLogger, register_launchpad_request_publication_factories)
from canonical.lp import initZopeless
from canonical.librarian.ftests.harness import LibrarianTestSetup
from canonical.testing import reset_logging
from canonical.testing.profiled import profiled


orig__call__ = zope.app.testing.functional.HTTPCaller.__call__


class MockRootFolder:
    """Implement the minimum functionality required by Z3 ZODB dependancies

    Installed as part of the FunctionalDocFileSuite to allow the http()
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

    The test suite should abort as further test failures may well
    be spurious.
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
        cls.isSetUp = True

        # Kill any Librarian left running from a previous test run.
        LibrarianTestSetup().killTac()

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
        cls.isSetUp = False

    @classmethod
    @profiled
    def testSetUp(cls):
        cls.check()

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
        reset_logging()
        del canonical.launchpad.mail.stub.test_emails[:]
        BaseLayer.test_name = None
        cls.check()

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


class LibrarianLayer(BaseLayer):
    """Provides tests access to a Librarian instance.

    Calls to the Librarian will fail unless there is also a Launchpad
    database available.
    """
    _reset_between_tests = True

    @classmethod
    @profiled
    def setUp(cls):
        if not cls._reset_between_tests:
            raise LayerInvariantError(
                    "_reset_between_tests changed before LibrarianLayer "
                    "was actually used."
                    )
        LibrarianTestSetup().setUp()
        cls._check_and_reset()

    @classmethod
    @profiled
    def tearDown(cls):
        if not cls._reset_between_tests:
            raise LayerInvariantError(
                    "_reset_between_tests not reset before LibrarianLayer "
                    "shutdown"
                    )
        cls._check_and_reset()
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
        if cls._reset_between_tests:
            LibrarianTestSetup().clear()

    @classmethod
    @profiled
    def testSetUp(cls):
        cls._check_and_reset()

    @classmethod
    @profiled
    def testTearDown(cls):
        if cls._hidden:
            cls.reveal()
        cls._check_and_reset()

    # The hide and reveal methods mess with the config. Store the
    # original values so things can be recovered.
    _orig_librarian_port = config.librarian.upload_port

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
        cls._hidden = True
        if cls._fake_upload_socket is None:
            # Bind to a socket, but don't listen to it.  This way we
            # guarantee that connections to the given port will fail.
            cls._fake_upload_socket = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            assert config.librarian.upload_host == 'localhost', (
                'Can only hide librarian if it is running locally')
            cls._fake_upload_socket.bind(('127.0.0.1', 0))

        host, port = cls._fake_upload_socket.getsockname()
        config.librarian.upload_port = port

    @classmethod
    @profiled
    def reveal(cls):
        """Reveal a hidden Librarian.

        This just involves restoring the config to the original value.
        """
        cls._hidden = False
        config.librarian.upload_port = cls._orig_librarian_port


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
        cls.force_dirty_database()

    @classmethod
    @profiled
    def tearDown(cls):
        # Don't leave the DB lying around or it might break tests
        # that depend on it not being there on startup, such as found
        # in test_layers.py
        cls.force_dirty_database()
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
        if cls._reset_between_tests:
            LaunchpadTestSetup().setUp()
        # Ensure that the database is connectable. Because we might have
        # just created it, keep trying for a few seconds incase PostgreSQL
        # is taking its time getting its house in order.
        attempts = 60
        for count in range(0, attempts):
            try:
                cls.connect().close()
            except psycopg.Error:
                if count == attempts - 1:
                    raise
                time.sleep(0.5)
            else:
                break

        if cls.use_mockdb is True:
            cls.installMockDb()

    @classmethod
    @profiled
    def testTearDown(cls):
        if cls.use_mockdb is True:
            cls.uninstallMockDb()

        # Ensure that the database is connectable
        cls.connect().close()

        # Imported here to avoid circular import issues. This
        # functionality should be migrated into this module at some
        # point. -- StuartBishop 20060712
        from canonical.launchpad.ftests.harness import LaunchpadTestSetup
        if cls._reset_between_tests:
            LaunchpadTestSetup().tearDown()

    use_mockdb = False
    mockdb_mode = None

    @classmethod
    @profiled
    def installMockDb(cls):
        assert cls.mockdb_mode is None, 'mock db already installed'

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
            cls.mockdb_mode = 'replay'
            cls.script = ScriptPlayer(test_key)
        else:
            cls.mockdb_mode = 'record'
            cls.script = ScriptRecorder(test_key)

        global _org_connect
        _org_connect = psycopg.connect
        # Proxy real connections with our mockdb.
        def fake_connect(*args, **kw):
            return cls.script.connect(_org_connect, *args, **kw)
        psycopg.connect = fake_connect

    @classmethod
    @profiled
    def uninstallMockDb(cls):
        if cls.mockdb_mode is None:
            return # Already uninstalled

        # Store results if we are recording
        if cls.mockdb_mode == 'record':
            cls.script.store()
            assert os.path.exists(cls.script.script_filename), (
                    "Stored results but no script on disk.")

        cls.mockdb_mode = None
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
        pass

    @classmethod
    @profiled
    def testTearDown(cls):
        pass


class FunctionalLayer(BaseLayer):
    """Loads the Zope3 component architecture in appserver mode."""

    # Set to True if tests using the Functional layer are currently being run.
    isSetUp = False

    @classmethod
    @profiled
    def setUp(cls):
        cls.isSetUp = True
        from canonical.functional import FunctionalTestSetup
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
        cls.isSetUp = False
        # Signal Layer cannot be torn down fully
        raise NotImplementedError

    @classmethod
    @profiled
    def testSetUp(cls):
        transaction.abort()
        transaction.begin()

        # Fake a root folder to keep Z3 ZODB dependencies happy.
        from canonical.functional import FunctionalTestSetup
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
        cls.isSetUp = True
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
        cls.isSetUp = False
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


class LaunchpadFunctionalLayer(LaunchpadLayer, FunctionalLayer):
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
        cls.txn = initZopeless()
        LaunchpadZopelessTestSetup.txn = cls.txn

        # Connect SQLOS
        from canonical.launchpad.ftests.harness import _reconnect_sqlos
        _reconnect_sqlos()

    @classmethod
    @profiled
    def testTearDown(cls):
        cls.txn.abort()
        cls.txn.uninstall()
        if ZopelessTransactionManager._installed is not None:
            raise LayerInvariantError(
                "Failed to uninstall ZopelessTransactionManager"
                )
        from canonical.launchpad.ftests.harness import _disconnect_sqlos
        _disconnect_sqlos()

    @classmethod
    @profiled
    def commit(cls):
        cls.txn.commit()

    @classmethod
    @profiled
    def abort(cls):
        cls.txn.abort()

    @classmethod
    @profiled
    def switchDbUser(cls, dbuser):
        cls.alterConnection(dbuser=dbuser)

    @classmethod
    @profiled
    def alterConnection(cls, **kw):
        """Reset the connection, and reopen the connection by calling
        initZopeless with the given keyword arguments.
        """
        from canonical.launchpad.ftests.harness import (
                LaunchpadZopelessTestSetup
                )
        cls.txn.abort()
        cls.txn.uninstall()
        cls.txn = initZopeless(**kw)
        LaunchpadZopelessTestSetup.txn = cls.txn

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

        cls.orig__call__ = zope.app.testing.functional.HTTPCaller.__call__
        zope.app.testing.functional.HTTPCaller.__call__ = my__call__
        cls.resetBetweenTests(True)

    @classmethod
    @profiled
    def tearDown(cls):
        cls.resetBetweenTests(True)
        zope.app.testing.functional.HTTPCaller.__call__ = cls.orig__call__

    @classmethod
    @profiled
    def startStory(cls):
        DatabaseLayer.testSetUp()
        LibrarianLayer.testSetUp()
        cls.resetBetweenTests(False)

    @classmethod
    @profiled
    def endStory(cls):
        cls.resetBetweenTests(True)
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


class TwistedLayer(LaunchpadZopelessLayer):
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
    @profiled
    def testSetUp(cls):
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
