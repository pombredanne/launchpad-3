# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for stormsugar."""

__metaclass__ = type

from unittest import TestLoader

from canonical.testing.layers import DatabaseFunctionalLayer
from storm.locals import Int

from canonical.launchpad.database.stormsugar import (
    ObjectNotFound, Sugar, UnknownProperty)
from canonical.launchpad.testing import TestCase



class SugarDerived(Sugar):
    """Class for testing.  (Because we can't test Sugar directly.)"""

    __storm_table__ = 'Job'

    status = Int()


class TestSugar(TestCase):

    layer = DatabaseFunctionalLayer

    def test_init_handles_kwargs(self):
        """Default constructor handles kwargs."""
        created = SugarDerived(id=500, status=0)
        self.assertEqual(500, created.id)
        self.assertEqual(0, created.status)

    def test_init_requires_known_kwargs(self):
        """Default constructor requires pre-defined kwargs.

        (This reduces the potential for typos to cause confusion or bugs.)
        """
        e = self.assertRaises(
            UnknownProperty, SugarDerived, id=500, status=0, foo='bar')
        self.assertEqual('Class SugarDerived has no property "foo".', str(e))

    def test_get(self):
        """Get either returns the desired object or raises."""
        e = self.assertRaises(ObjectNotFound, SugarDerived.get, 500)
        self.assertEqual('Not found: SugarDerived with id 500.', str(e))
        created = SugarDerived(id=500, status=0)
        gotten = SugarDerived.get(500)
        self.assertEqual(created, gotten)

    def test_destroySelf(self):
        """destroySelf destroys the object in question."""
        created = SugarDerived(id=500, status=0)
        created.destroySelf()
        self.assertRaises(ObjectNotFound, SugarDerived.get, 500)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
