# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for stormsugar."""

__metaclass__ = type

from unittest import TestLoader

from canonical.testing.layers import DatabaseFunctionalLayer
from psycopg2 import IntegrityError
from storm.locals import Int

from canonical.launchpad.database.stormsugar import (
    ForeignKey, ObjectNotFound, Sugar, UnknownProperty)
from canonical.launchpad.testing import TestCase



class SugarDerived(Sugar):
    """Class for testing.  (Because we can't test Sugar directly.)"""

    __storm_table__ = 'Job'

    status = Int()


class ReferencingObject(Sugar):

    __storm_table__ = 'BranchJob'

    branch = Int()

    job_type = Int()

    job = ForeignKey(SugarDerived.id)


class ReferencingObjectWithName(Sugar):

    __storm_table__ = 'BranchJob'

    foo = ForeignKey(SugarDerived.id, 'job')


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

    def test_sync_exercises_constraints(self):
        """Sugar.sync causes constraints to be tested."""
        created = SugarDerived(id=500)
        self.assertRaises(IntegrityError, created.sync)

    def test_selectBy(self):
        """Sugar selectBy works."""
        obj1 = SugarDerived(id=500, status=5)
        obj2 = SugarDerived(id=501, status=6)
        self.assertEqual([obj1], list(SugarDerived.selectBy(status=5)))
        self.assertEqual([], list(SugarDerived.selectBy(status=4)))
        self.assertRaises(AssertionError, SugarDerived.selectBy)

    def test_ForeignKey(self):
        obj1 = SugarDerived(status=0)
        obj2 = ReferencingObject(job=obj1, branch=1, job_type=0)
        obj2.sync()

    def test_ForeignKey_with_name(self):
        obj1 = SugarDerived(status=0)
        obj2 = ReferencingObjectWithName(foo=obj1)
        self.assertEqual(obj1, obj2.foo)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
