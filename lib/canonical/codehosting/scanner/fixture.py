# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type
__all__ = []

from twisted.python.util import mergeFunctionMetadata
from zope.interface import Interface


class IFixture(Interface):
    """A fixture has a setUp and a tearDown method."""

    def setUp():
        """Set up the fixture."""

    def tearDown():
        """Tear down the fixture."""


def with_fixture(fixture):
    """Decorate a function to run with a given fixture."""
    def decorator(f):
        def decorated(*args, **kwargs):
            return run_with_fixture(fixture, f, fixture, *args, **kwargs)
        return mergeFunctionMetadata(f, decorated)
    return decorator


def run_with_fixture(fixture, f, *args, **kwargs):
    """Run `f` within the given `fixture`."""
    fixture.setUp()
    try:
        return f(*args, **kwargs)
    finally:
        fixture.tearDown()
