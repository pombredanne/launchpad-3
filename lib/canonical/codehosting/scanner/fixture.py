# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Basic support for 'fixtures'.

In this case, 'fixture' means an object that has a setUp and a tearDown
method.
"""

__metaclass__ = type
__all__ = [
    'Fixtures',
    'FixtureWithCleanup',
    'IFixture',
    'make_zope_event_fixture',
    'run_with_fixture',
    'with_fixture',
    ]

from zope.component import getGlobalSiteManager, provideHandler
from twisted.python.util import mergeFunctionMetadata
from zope.interface import implements, Interface


class IFixture(Interface):
    """A fixture has a setUp and a tearDown method."""

    def setUp():
        """Set up the fixture."""

    def tearDown():
        """Tear down the fixture."""


class FixtureWithCleanup:
    """Fixture that allows arbitrary cleanup methods to be added.

    Subclass this if you'd like to define a fixture that calls 'addCleanup'.
    This is most often useful for fixtures that provide a way for users to
    acquire resources arbitrarily.

    Cleanups are run during 'tearDown' in reverse order to the order they were
    added. If any of the cleanups raise an error, this error will be bubbled
    up, causing tearDown to raise an exception, and the rest of the cleanups
    will be run in a finally block.
    """

    implements(IFixture)

    def setUp(self):
        """See `IFixture`."""
        self._cleanups = []

    def _runCleanups(self):
        if [] == self._cleanups:
            return
        f, args, kwargs = self._cleanups.pop()
        try:
            f(*args, **kwargs)
        finally:
            self._runCleanups()

    def tearDown(self):
        """See `IFixture`."""
        self._runCleanups()

    def addCleanup(self, function, *args, **kwargs):
        """Run 'function' with arguments during tear down."""
        self._cleanups.append((function, args, kwargs))


class Fixtures(FixtureWithCleanup):
    """A collection of `IFixture`s."""

    def __init__(self, fixtures):
        """Construct a fixture that groups many fixtures together.

        :param fixtures: A list of `IFixture` objects.
        """
        self._fixtures = fixtures

    def setUp(self):
        super(Fixtures, self).setUp()
        for fixture in self._fixtures:
            fixture.setUp()
            self.addCleanup(fixture.tearDown)


def with_fixture(fixture):
    """Decorate a function to run with a given fixture."""
    def decorator(f):
        def decorated(*args, **kwargs):
            return run_with_fixture(fixture, f, fixture, *args, **kwargs)
        return mergeFunctionMetadata(f, decorated)
    return decorator


def run_with_fixture(fixture, f, *args, **kwargs):
    """Run `f` within the given `fixture`."""
    try:
        fixture.setUp()
        return f(*args, **kwargs)
    finally:
        fixture.tearDown()


class ZopeEventHandlerFixture(FixtureWithCleanup):
    """A fixture that provides and then unprovides a Zope event handler."""

    def __init__(self, handler):
        self._handler = handler

    def setUp(self):
        super(ZopeEventHandlerFixture, self).setUp()
        gsm = getGlobalSiteManager()
        provideHandler(self._handler)
        self.addCleanup(gsm.unregisterHandler, self._handler)


def make_zope_event_fixture(*handlers):
    return Fixtures(map(ZopeEventHandlerFixture, handlers))
