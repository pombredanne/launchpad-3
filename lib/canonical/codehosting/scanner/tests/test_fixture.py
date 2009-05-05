# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

import unittest

from zope.interface import implements

from canonical.codehosting.scanner.fixture import (
    FixtureWithCleanup, IFixture, run_with_fixture, with_fixture)
from canonical.launchpad.testing import TestCase


class LoggingFixture:

    implements(IFixture)

    def __init__(self, log):
        self.log = log

    def setUp(self):
        self.log.append('setUp')

    def tearDown(self):
        self.log.append('tearDown')


class TestFixture(TestCase):

    def test_run_with_fixture(self):
        # run_with_fixture runs the setUp method of the fixture, the passed
        # function and then the tearDown method of the fixture.
        log = []
        fixture = LoggingFixture(log)
        run_with_fixture(fixture, log.append, 'hello')
        self.assertEqual(['setUp', 'hello', 'tearDown'], log)

    def test_run_tearDown_even_with_exception(self):
        # run_with_fixture runs the setUp method of the fixture, the passed
        # function and then the tearDown method of the fixture even if the
        # function raises an exception.
        log = []
        fixture = LoggingFixture(log)
        self.assertRaises(
            ZeroDivisionError, run_with_fixture, fixture, lambda: 1/0)
        self.assertEqual(['setUp', 'tearDown'], log)

    def test_with_fixture(self):
        # with_fixture decorates a function so that it gets passed the fixture
        # and the fixture is set up and torn down around the function.
        log = []
        fixture = LoggingFixture(log)
        @with_fixture(fixture)
        def function(fixture, **kwargs):
            log.append(fixture)
            log.append(kwargs)
            return 'oi'
        result = function(foo='bar')
        self.assertEqual('oi', result)
        self.assertEqual(['setUp', fixture, {'foo': 'bar'}, 'tearDown'], log)


class TestFixtureWithCleanup(TestCase):
    """Tests for `FixtureWithCleanup`."""

    def test_cleanup_called_during_teardown(self):
        log = []
        fixture = FixtureWithCleanup()
        fixture.setUp()
        fixture.addCleanup(log.append, 'foo')
        self.assertEqual([], log)
        fixture.tearDown()
        self.assertEqual(['foo'], log)

    def test_cleanup_called_in_reverse_order(self):
        log = []
        fixture = FixtureWithCleanup()
        fixture.setUp()
        fixture.addCleanup(log.append, 'foo')
        fixture.addCleanup(log.append, 'bar')
        fixture.tearDown()
        self.assertEqual(['bar', 'foo'], log)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

