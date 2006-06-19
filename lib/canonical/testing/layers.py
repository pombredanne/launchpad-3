# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Layers used by Canonical tests.

Layers are the mechanism used by the Zope3 test runner to efficiently
provide environments for tests and are documented in the lib/zope/testing.

TODO: Make the Zope3 test runner handle multiple layers per test instead
of one, forcing us to attempt to make some sort of layer tree.
-- StuartBishop 20060619
"""

__all__ = [
    'Database', 'Librarian', 'Launchpad', 'Functional', 'Zopeless',
    'PageTest', 'SystemDoctest',
    ]

from canonical.librarian.ftests.harness import LibrarianTestSetup
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.testing import reset_logging


class Base:
    @classmethod
    def setUp(cls):
        pass

    @classmethod
    def tearDown(cls):
        reset_logging()


class Librarian(Base):
    """Provides tests access to a Librarian instance.

    Calls to the Librarian will fail unless there is also a Launchpad
    database available.
    """
    @classmethod
    def setUp(cls):
        LibrarianTestSetup().setUp()

    @classmethod
    def tearDown(cls):
        LibrarianTestSetup().tearDown()

    @classmethod
    def testSetUp(cls):
        LibrarianTestSetup().clear()

    @classmethod
    def testTearDown(cls):
        LibrarianTestSetup().clear()


class Database(Base):
    """This Layer provides tests access to the Launchpad sample database."""
    @classmethod
    def setUp(cls):
        pass

    @classmethod
    def tearDown(cls):
        pass

    @classmethod
    def testSetUp(cls):
        from canonical.launchpad.ftests.harness import LaunchpadTestSetup
        LaunchpadTestSetup().setUp()

    @classmethod
    def testTearDown(cls):
        from canonical.launchpad.ftests.harness import LaunchpadTestSetup
        LaunchpadTestSetup().tearDown()


class Launchpad(Librarian, Database):
    """Provides access to the Launchpad database and daemons."""
    @classmethod
    def setUp(cls):
        pass

    @classmethod
    def tearDown(cls):
        pass


class Functional(Database):
    """Provides the Launchpad Zope3 application server environment."""
    @classmethod
    def setUp(cls):
        from canonical.functional import FunctionalTestSetup
        FunctionalTestSetup().setUp()

    @classmethod
    def tearDown(cls):
        raise NotImplementedError


class Zopeless(Launchpad):
    """Provides the Launchpad Zopeless environment."""
    @classmethod
    def setUp(cls):
        execute_zcml_for_scripts()

    @classmethod
    def tearDown(cls):
        raise NotImplementedError


class PageTest(Librarian):
    """Provides environment for the page tests.
    
    Note that the page test runner handles database setup and teardown
    as the database reset should only occur at the end of a story.
    """
    @classmethod
    def setUp(cls):
        from canonical.functional import FunctionalTestSetup
        FunctionalTestSetup().setUp()

    @classmethod
    def tearDown(cls):
        raise NotImplementedError


class SystemDoctest(Base):
    @classmethod
    def setUp(cls):
        pass

    @classmethod
    def tearDown(cls):
        raise NotImplementedError



