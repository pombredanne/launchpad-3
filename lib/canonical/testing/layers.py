# Copyright 2006 Canonical Ltd.  All rights reserved.

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
    'Database', 'Librarian', 'Functional', 'Zopeless',
    'LaunchpadFunctional', 'LaunchpadZopeless', 'PageTest',
    ]

from urllib import urlopen

import psycopg
from sqlos.interfaces import IConnectionName
import transaction
from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError

from canonical.config import config
from canonical.database.sqlbase import ZopelessTransactionManager
from canonical.launchpad.interfaces import IOpenLaunchBag
from canonical.launchpad.ftests import logout, is_logged_in
import canonical.launchpad.mail.stub
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.lp import initZopeless
from canonical.librarian.ftests.harness import LibrarianTestSetup
from canonical.testing import reset_logging


def is_ca_available():
    """Returns true if the component architecture has been loaded"""
    try:
        getUtility(IOpenLaunchBag)
    except ComponentLookupError:
        return False
    else:
        return True


class Base:
    """Base layer.

    All out layers should subclass Base, as this is where we will put
    test isolation checks to ensure that tests to not leave global
    resources in a mess.

    XXX: Unit tests (tests with no layer) will not get this checks.
    The Z3 test runner should be updated so that a layer can be specified
    to use for unit tests. -- StuartBishop 20060712
    """
    # Set to True when we are running tests in this layer.
    isSetUp = False

    @classmethod
    def setUp(cls):
        cls.isSetUp = True

        # Kill any Librarian left running from a previous test run.
        LibrarianTestSetup()._maybe_kill_librarian()

        # Kill any database left lying around from a previous test run.
        try:
            Database.connect().close()
        except psycopg.Error:
            pass
        else:
            Database._dropDb()

    @classmethod
    def tearDown(cls):
        cls.isSetUp = False

    @classmethod
    def testSetUp(cls):
        Base.check()

    @classmethod
    def testTearDown(cls):
        reset_logging()
        del canonical.launchpad.mail.stub.test_emails[:]
        Base.check()

    @classmethod
    def check(cls):
        """Check that the environment is working as expected.

        We check here so we can detect tests that, for example,
        initialize the Zopeless or Functional environments and
        are using the incorrect layer.
        """
        assert not (Functional.isSetUp and Zopeless.isSetUp), \
                'Both Zopefull and Zopeless CA environments setup'

        if (is_ca_available() and not Functional.isSetUp
                and not Zopeless.isSetUp):
            raise Exception("Component architecture should not be available")
        
        if ZopelessTransactionManager._installed is not None:
            raise Exception('Zopeless environment was not torn down.')


class Librarian(Base):
    """Provides tests access to a Librarian instance.

    Calls to the Librarian will fail unless there is also a Launchpad
    database available.
    """
    _reset_between_tests = True

    @classmethod
    def setUp(cls):
        assert Librarian._reset_between_tests, \
                "_reset_between_tests changed too soon"
        LibrarianTestSetup().setUp()
        Librarian._check_and_reset()

    @classmethod
    def tearDown(cls):
        assert Librarian._reset_between_tests, \
                "_reset_between_tests not reset!"
        Librarian._check_and_reset()
        LibrarianTestSetup().tearDown()

    @classmethod
    def _check_and_reset(cls):
        """Raise an exception if the Librarian has been killed.
        Reset the storage unless this has been disabled.
        """
        try:
            f = urlopen(config.librarian.download_url)
            f.read()
        except:
            raise Exception("Librarian has been killed or has hung")
        if Librarian._reset_between_tests:
            LibrarianTestSetup().clear()

    @classmethod
    def testSetUp(cls):
        Librarian._check_and_reset()

    @classmethod
    def testTearDown(cls):
        Librarian._check_and_reset()


class Database(Base):
    """This Layer provides tests access to the Launchpad sample database."""

    # If set to False, database will not be reset between tests. It is
    # your responsibility to set it back to True and call
    # Database.force_dirty_database() when you do so.
    _reset_between_tests = True

    @classmethod
    def setUp(cls):
        cls.force_dirty_database()
        if is_ca_available():
            raise Exception("Component architecture should not be available")

    @classmethod
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
    def testSetUp(cls):
        # Imported here to avoid circular import issues. This
        # functionality should be migrated into this module at some
        # point. -- StuartBishop 20060712
        from canonical.launchpad.ftests.harness import LaunchpadTestSetup
        if Database._reset_between_tests:
            LaunchpadTestSetup().setUp()
        # Ensure that the database is connectable. Because we might have
        # just created it, keep trying for a few seconds incase PostgreSQL
        # is taking its time getting its house in order.
        for count in range(0,10):
            try:
                Database.connect().close()
            except psycopg.Error:
                if count == 9:
                    raise
                time.sleep(1)
            else:
                break

    @classmethod
    def testTearDown(cls):
        # Ensure that the database is connectable
        Database.connect().close()

        # Imported here to avoid circular import issues. This
        # functionality should be migrated into this module at some
        # point. -- StuartBishop 20060712
        from canonical.launchpad.ftests.harness import LaunchpadTestSetup
        if Database._reset_between_tests:
            LaunchpadTestSetup().tearDown()

    @classmethod
    def force_dirty_database(cls):
        from canonical.launchpad.ftests.harness import LaunchpadTestSetup
        LaunchpadTestSetup().force_dirty_database()

    @classmethod
    def connect(cls):
        from canonical.launchpad.ftests.harness import LaunchpadTestSetup
        return LaunchpadTestSetup().connect()

    @classmethod
    def _dropDb(cls):
        from canonical.launchpad.ftests.harness import LaunchpadTestSetup
        return LaunchpadTestSetup().dropDb()


class SQLOS(Base):
    """Maintains the SQLOS connection.

    This Layer is not useful by itself, but it intended to be used as
    a mixin to the Functional and Zopeless Layers.
    """
    @classmethod
    def setUp(cls):
        pass

    @classmethod
    def tearDown(cls):
        pass

    @classmethod
    def testSetUp(cls):
        from canonical.launchpad.ftests.harness import _reconnect_sqlos
        _reconnect_sqlos()

    @classmethod
    def testTearDown(cls):
        from canonical.launchpad.ftests.harness import _disconnect_sqlos
        _disconnect_sqlos()


class Launchpad(Database, Librarian):
    """Provides access to the Launchpad database and daemons.
    
    We need to ensure that the database setup runs before the daemon
    setup, or the database setup will fail because the daemons are
    already connected to the database.

    This layer is mainly used by tests that call initZopeless() themselves.
    """
    @classmethod
    def setUp(cls):
        pass

    @classmethod
    def tearDown(cls):
        pass

    @classmethod
    def testSetUp(cls):
        pass

    @classmethod
    def testTearDown(cls):
        pass


class Functional(Base):
    """Loads the Zope3 component architecture in appserver mode."""

    # Set to True if tests using the Functional layer are currently being run.
    isSetUp = False

    @classmethod
    def setUp(cls):
        cls.isSetUp = True
        from canonical.functional import FunctionalTestSetup
        FunctionalTestSetup().setUp()

        # Assert that FunctionalTestSetup did what it says it does
        assert is_ca_available(), "Component architecture not loaded!"

    @classmethod
    def tearDown(cls):
        cls.isSetUp = False
        # Signal Layer cannot be torn down fully
        raise NotImplementedError

    @classmethod
    def testSetUp(cls):
        transaction.abort()
        transaction.begin()

        # Should be impossible, as the CA cannot be unloaded. Something
        # mighty nasty has happened if this is triggered.
        assert is_ca_available(), "Component architecture not loaded!"

    @classmethod
    def testTearDown(cls):
        # Should be impossible, as the CA cannot be unloaded. Something
        # mighty nasty has happened if this is triggered.
        assert is_ca_available(), "Component architecture not loaded!"

        transaction.abort()


class Zopeless(Launchpad):
    """Layer for tests that need the Zopeless component architecture
    loaded using execute_zcml_for_scrips()
    """

    # Set to True if tests in the Zopeless layer are currently being run.
    isSetUp = False

    @classmethod
    def setUp(cls):
        cls.isSetUp = True
        execute_zcml_for_scripts()

        # Assert that execute_zcml_for_scripts did what it says it does.
        assert is_ca_available(), "Component architecture not loaded!"

    @classmethod
    def tearDown(cls):
        cls.isSetUp = False
        # Signal Layer cannot be torn down fully
        raise NotImplementedError

    @classmethod
    def testSetUp(cls):
        # Should be impossible, as the CA cannot be unloaded. Something
        # mighty nasty has happened if this is triggered.
        assert is_ca_available(), "Component architecture not loaded!"

    @classmethod
    def testTearDown(cls):
        # Should be impossible, as the CA cannot be unloaded. Something
        # mighty nasty has happened if this is triggered.
        assert is_ca_available(), "Component architecture not loaded!"


class LaunchpadFunctional(Database, Librarian, Functional, SQLOS):
    """Provides the Launchpad Zope3 application server environment."""
    @classmethod
    def setUp(cls):
        pass

    @classmethod
    def tearDown(cls):
        pass

    @classmethod
    def testSetUp(cls):
        pass

    @classmethod
    def testTearDown(cls):
        getUtility(IOpenLaunchBag).clear()
        
        # If tests forget to logout, we can do it for them.
        if is_logged_in():
            logout()


class LaunchpadZopeless(Zopeless, Database, Librarian, SQLOS):
    """Full Zopeless environment including Component Architecture and
    database connections initialized.
    """
    @classmethod
    def setUp(cls):
        pass

    @classmethod
    def tearDown(cls):
        # Signal Layer cannot be torn down fully
        raise NotImplementedError

    @classmethod
    def testSetUp(cls):
        from canonical.launchpad.ftests.harness import (
                LaunchpadZopelessTestSetup
                )
        assert ZopelessTransactionManager._installed is None, \
                'Last test using Zopeless failed to tearDown correctly'
        LaunchpadZopeless.txn = initZopeless()
        LaunchpadZopelessTestSetup.txn = LaunchpadZopeless.txn

    @classmethod
    def testTearDown(cls):
        from canonical.launchpad.ftests.harness import (
                LaunchpadZopelessTestSetup
                )
        LaunchpadZopelessTestSetup.txn.abort()
        LaunchpadZopelessTestSetup.txn.uninstall()
        assert ZopelessTransactionManager._installed is None, \
                'Failed to tearDown Zopeless correctly'


class PageTest(LaunchpadFunctional):
    """Environment for page tests.
    """
    @classmethod
    def resetBetweenTests(cls, flag):
        Librarian._reset_between_tests = flag
        Database._reset_between_tests = flag

    @classmethod
    def setUp(cls):
        cls.resetBetweenTests(True)

    @classmethod
    def tearDown(cls):
        cls.resetBetweenTests(True)

    @classmethod
    def startStory(cls):
        cls.resetBetweenTests(False)

    @classmethod
    def endStory(cls):
        from canonical.launchpad.ftests.harness import LaunchpadTestSetup
        LaunchpadTestSetup().force_dirty_database()
        cls.resetBetweenTests(True)

    @classmethod
    def testSetUp(cls):
        pass

    @classmethod
    def testTearDown(cls):
        pass

