# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests from branch subset."""

__metaclass__ = type

from datetime import datetime, timedelta
import unittest

import pytz
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.database.branchsubset import (
    PersonBranchSubset, ProductBranchSubset)
from canonical.launchpad.interfaces.branchsubset import IBranchSubset
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing.layers import DatabaseFunctionalLayer


class BranchSubsetTestsMixin:

    layer = DatabaseFunctionalLayer

    def makeComponent(self):
        raise NotImplementedError(self.makeComponent)

    def makeSubset(self, component):
        raise NotImplementedError(self.makeSubset)

    def makeBranchInSubset(self, component, **kwargs):
        raise NotImplementedError(self.makeBranchInSubset)

    def makeRevision(self, revision_date=None):
        return self.factory.makeRevision(revision_date=revision_date)

    def addRevisionsToBranch(self, branch, *revs):
        # Add the revisions to the the branch.
        for sequence, rev in enumerate(revs):
            branch.createBranchRevision(sequence, rev)

    def test_provides_interface(self):
        component = self.makeComponent()
        self.assertProvides(
            self.makeSubset(component), IBranchSubset)

    def test_name(self):
        # The name of a component subset is the name of the component.
        component = self.makeComponent()
        self.assertEqual(component.name, self.makeSubset(component).name)

    def test_displayname(self):
        # The display name of a component subset is the display name of the
        # component.
        component = self.makeComponent()
        self.assertEqual(
            component.displayname, self.makeSubset(component).displayname)

    def test_getBranches_empty(self):
        component = self.makeComponent()
        subset = self.makeSubset(component)
        self.assertEqual([], list(subset.getBranches()))

    def test_getBranches_non_empty(self):
        component = self.makeComponent()
        branch = self.makeBranchInSubset(component)
        subset = self.makeSubset(component)
        self.assertEqual([branch], list(subset.getBranches()))

    def test_count_empty(self):
        component = self.makeComponent()
        subset = self.makeSubset(component)
        self.assertEqual(0, subset.count)

    def test_count_non_empty(self):
        component = self.makeComponent()
        branch = self.makeBranchInSubset(component)
        subset = self.makeSubset(component)
        self.assertEqual(1, subset.count)

    def test_newest_revision_first(self):
        # The revisions are ordered with the newest first.
        component = self.makeComponent()
        subset = self.makeSubset(component)
        rev1 = self.makeRevision()
        rev2 = self.makeRevision()
        rev3 = self.makeRevision()
        self.addRevisionsToBranch(
            self.makeBranchInSubset(component), rev1, rev2, rev3)
        self.assertEqual([rev3, rev2, rev1], list(subset.getRevisions()))

    def test_revisions_only_returned_once(self):
        # If the revisions appear in multiple branches, they are only returned
        # once.
        component = self.makeComponent()
        subset = self.makeSubset(component)
        rev1 = self.makeRevision()
        rev2 = self.makeRevision()
        rev3 = self.makeRevision()
        self.addRevisionsToBranch(
            self.makeBranchInSubset(component), rev1, rev2, rev3)
        self.addRevisionsToBranch(
            self.makeBranchInSubset(component), rev1, rev2, rev3)
        self.assertEqual([rev3, rev2, rev1], list(subset.getRevisions()))

    def test_revisions_must_be_in_a_branch(self):
        # A revision authored by the person must be in a branch to be
        # returned.
        component = self.makeComponent()
        subset = self.makeSubset(component)
        rev1 = self.makeRevision()
        self.assertEqual([], list(subset.getRevisions()))
        b = self.makeBranchInSubset(component)
        b.createBranchRevision(1, rev1)
        self.assertEqual([rev1], list(subset.getRevisions()))

    def test_revisions_must_be_in_a_public_branch(self):
        # A revision authored by the person must be in a branch to be
        # returned.
        component = self.makeComponent()
        subset = self.makeSubset(component)
        rev1 = self.makeRevision()
        b = removeSecurityProxy(
            self.makeBranchInSubset(component, private=True))
        b.createBranchRevision(1, rev1)
        self.assertEqual([], list(subset.getRevisions()))

    def test_revision_date_range(self):
        # Revisions where the revision_date is older than the day_limit, or
        # some time in the future are not returned.
        component = self.makeComponent()
        subset = self.makeSubset(component)
        now = datetime.now(pytz.UTC)
        day_limit = 5
        # Make the first revision earlier than our day limit.
        rev1 = self.makeRevision(
            revision_date=(now - timedelta(days=(day_limit + 2))))
        # The second one is just two days ago.
        rev2 = self.makeRevision(
            revision_date=(now - timedelta(days=2)))
        # The third is in the future
        rev3 = self.makeRevision(
            revision_date=(now + timedelta(days=2)))
        self.addRevisionsToBranch(
            self.makeBranchInSubset(component), rev1, rev2, rev3)
        self.assertEqual([rev2], list(subset.getRevisions(day_limit)))


class TestProductBranchSubset(TestCaseWithFactory, BranchSubsetTestsMixin):

    layer = DatabaseFunctionalLayer

    def makeComponent(self):
        return self.factory.makeProduct()

    def makeSubset(self, component):
        return IBranchSubset(component)

    def makeBranchInSubset(self, component, **kwargs):
        return self.factory.makeProductBranch(product=component, **kwargs)


class TestPersonBranchSubset(TestCaseWithFactory, BranchSubsetTestsMixin):

    layer = DatabaseFunctionalLayer

    def makeComponent(self):
        return self.factory.makePerson()

    def makeSubset(self, person):
        return IBranchSubset(person)

    def makeBranchInSubset(self, component, **kwargs):
        return self.factory.makePersonalBranch(owner=component, **kwargs)


class TestAdapter(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_product(self):
        product = self.factory.makeProduct()
        subset = IBranchSubset(product)
        self.assertIsInstance(subset, ProductBranchSubset)
        self.assertEqual(product.name, subset.name)

    def test_person(self):
        # The default IBranchSubset for a person is all of the branches owned
        # by that person.
        # XXX: Is this a good idea? - jml
        person = self.factory.makePerson()
        subset = IBranchSubset(person)
        self.assertIsInstance(subset, PersonBranchSubset)
        self.assertEqual(person.name, subset.name)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

