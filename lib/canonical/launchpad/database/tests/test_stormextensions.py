# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for extensions in stormsugar, but not stormsugar proper."""

__metaclass__ = type


from unittest import TestLoader

from storm.expr import Lower
from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.database import Person
from canonical.launchpad.database.stormsugar import StartsWith
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, MASTER_FLAVOR)


class TestStormExpressions(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        selector = getUtility(IStoreSelector)
        self.store = selector.get(MAIN_STORE, MASTER_FLAVOR)

    def test_StartsWith(self):
        """StartWith correctly performs searches."""

        person1 = self.factory.makePerson(name='aa', displayname="John Doe")
        person2 = self.factory.makePerson(name='bb', displayname="Johan Doe")
        person3 = self.factory.makePerson(name='cc', displayname="Joh%n Doe")

        # Successful search from the start of the name.
        expr = StartsWith(Person.displayname, 'John')
        results = self.store.find(Person, expr)
        self.assertEqual([person1], [p for p in results])

        # Searching for a missing pattern returns no result.
        expr = StartsWith(Person.displayname, 'John Roe')
        results = self.store.find(Person, expr)
        self.assertEqual([], [p for p in results])


        # Searching for a non-initial pattern returns no result.
        expr = StartsWith(Person.displayname, 'Roe')
        results = self.store.find(Person, expr)
        self.assertEqual([], [p for p in results])

        # Multiple matches are returned.
        expr = StartsWith(Person.displayname, 'Joh')
        results = self.store.find(Person, expr)
        results.order_by('name')
        self.assertEqual([person1, person2, person3], [p for p in results])

        # Wildcards are properly escaped.  No need for quote_like or equivalent.
        expr = StartsWith(Person.displayname, 'Joh%n')
        results = self.store.find(Person, expr)
        self.assertEqual([person3], [p for p in results])

        # Searches are case-sensitive.
        expr = StartsWith(Person.displayname, 'john')
        results = self.store.find(Person, expr)
        self.assertEqual([], [p for p in results])

        # Use of .lower allows case-insensitive searching.
        expr = StartsWith(Person.displayname.lower(), 'john')
        results = self.store.find(Person, expr)
        self.assertEqual([person1], [p for p in results])

        # Use of Lower allows case-insensitive searching.
        expr = StartsWith(Lower(Person.displayname), 'john')
        results = self.store.find(Person, expr)
        self.assertEqual([person1], [p for p in results])

        #

def test_suite():
    return TestLoader().loadTestsFromName(__name__)
