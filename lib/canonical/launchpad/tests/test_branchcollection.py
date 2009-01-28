# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for branch collections."""

__metaclass__ = type

from datetime import datetime, timedelta
import unittest

import pytz
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.database.branch import Branch
from canonical.launchpad.database.branchcollection import (
    GenericBranchCollection, PersonBranchCollection, ProductBranchCollection)
from canonical.launchpad.interfaces.branchcollection import IBranchCollection
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.testing.layers import DatabaseFunctionalLayer


class TestGenericBranchCollection(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.store = getUtility(IStoreSelector).get(
            MAIN_STORE, DEFAULT_FLAVOR)

    def test_name(self):
        subset = GenericBranchCollection(self.store, name="foo")
        self.assertEqual('foo', subset.name)

    def test_displayname(self):
        subset = GenericBranchCollection(self.store, displayname='Foo Bar')
        self.assertEqual('Foo Bar', subset.displayname)

    def test_getBranches_no_filter(self):
        subset = GenericBranchCollection(self.store)
        all_branches = self.store.find(Branch)
        self.assertEqual(list(all_branches), list(subset.getBranches()))

    def test_getBranches_product_filter(self):
        branch = self.factory.makeProductBranch()
        subset = GenericBranchCollection(
            self.store, Branch.product == branch.product)
        all_branches = self.store.find(Branch)
        self.assertEqual([branch], list(subset.getBranches()))

    def test_count(self):
        subset = GenericBranchCollection(self.store)
        num_all_branches = self.store.find(Branch).count()
        self.assertEqual(num_all_branches, subset.count)


class BranchCollectionTestsMixin:

    layer = DatabaseFunctionalLayer

    def makeComponent(self):
        raise NotImplementedError(self.makeComponent)

    def makeCollection(self, component):
        raise NotImplementedError(self.makeCollection)

    def makeBranchInCollection(self, component, **kwargs):
        raise NotImplementedError(self.makeBranchInCollection)

    def makeRevision(self, revision_date=None):
        return self.factory.makeRevision(revision_date=revision_date)

    def addRevisionsToBranch(self, branch, *revs):
        # Add the revisions to the the branch.
        for sequence, rev in enumerate(revs):
            branch.createBranchRevision(sequence, rev)

    def test_provides_interface(self):
        component = self.makeComponent()
        self.assertProvides(
            self.makeCollection(component), IBranchCollection)

    def test_name(self):
        # The name of a component subset is the name of the component.
        component = self.makeComponent()
        self.assertEqual(component.name, self.makeCollection(component).name)

    def test_displayname(self):
        # The display name of a component subset is the display name of the
        # component.
        component = self.makeComponent()
        self.assertEqual(
            component.displayname, self.makeCollection(component).displayname)

    def test_getBranches_empty(self):
        component = self.makeComponent()
        subset = self.makeCollection(component)
        self.assertEqual([], list(subset.getBranches()))

    def test_getBranches_non_empty(self):
        component = self.makeComponent()
        branch = self.makeBranchInCollection(component)
        subset = self.makeCollection(component)
        self.assertEqual([branch], list(subset.getBranches()))

    def test_count_empty(self):
        component = self.makeComponent()
        subset = self.makeCollection(component)
        self.assertEqual(0, subset.count)

    def test_count_non_empty(self):
        component = self.makeComponent()
        branch = self.makeBranchInCollection(component)
        subset = self.makeCollection(component)
        self.assertEqual(1, subset.count)

    def test_newest_revision_first(self):
        # The revisions are ordered with the newest first.
        component = self.makeComponent()
        subset = self.makeCollection(component)
        rev1 = self.makeRevision()
        rev2 = self.makeRevision()
        rev3 = self.makeRevision()
        self.addRevisionsToBranch(
            self.makeBranchInCollection(component), rev1, rev2, rev3)
        self.assertEqual([rev3, rev2, rev1], list(subset.getRevisions()))

    def test_revisions_only_returned_once(self):
        # If the revisions appear in multiple branches, they are only returned
        # once.
        component = self.makeComponent()
        subset = self.makeCollection(component)
        rev1 = self.makeRevision()
        rev2 = self.makeRevision()
        rev3 = self.makeRevision()
        self.addRevisionsToBranch(
            self.makeBranchInCollection(component), rev1, rev2, rev3)
        self.addRevisionsToBranch(
            self.makeBranchInCollection(component), rev1, rev2, rev3)
        self.assertEqual([rev3, rev2, rev1], list(subset.getRevisions()))

    def test_revisions_must_be_in_a_branch(self):
        # A revision authored by the person must be in a branch to be
        # returned.
        component = self.makeComponent()
        subset = self.makeCollection(component)
        rev1 = self.makeRevision()
        self.assertEqual([], list(subset.getRevisions()))
        b = self.makeBranchInCollection(component)
        b.createBranchRevision(1, rev1)
        self.assertEqual([rev1], list(subset.getRevisions()))

    def test_revisions_must_be_in_a_public_branch(self):
        # A revision authored by the person must be in a branch to be
        # returned.
        component = self.makeComponent()
        subset = self.makeCollection(component)
        rev1 = self.makeRevision()
        b = removeSecurityProxy(
            self.makeBranchInCollection(component, private=True))
        b.createBranchRevision(1, rev1)
        self.assertEqual([], list(subset.getRevisions()))

    def test_revision_date_range(self):
        # Revisions where the revision_date is older than the day_limit, or
        # some time in the future are not returned.
        component = self.makeComponent()
        subset = self.makeCollection(component)
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
            self.makeBranchInCollection(component), rev1, rev2, rev3)
        self.assertEqual([rev2], list(subset.getRevisions(day_limit)))


class TestProductBranchCollection(TestCaseWithFactory,
                                  BranchCollectionTestsMixin):

    layer = DatabaseFunctionalLayer

    def makeComponent(self):
        return self.factory.makeProduct()

    def makeCollection(self, component):
        return IBranchCollection(component)

    def makeBranchInCollection(self, component, **kwargs):
        return self.factory.makeProductBranch(product=component, **kwargs)


class TestPersonBranchCollection(TestCaseWithFactory,
                                 BranchCollectionTestsMixin):

    layer = DatabaseFunctionalLayer

    def makeComponent(self):
        return self.factory.makePerson()

    def makeCollection(self, person):
        return IBranchCollection(person)

    def makeBranchInCollection(self, component, **kwargs):
        return self.factory.makePersonalBranch(owner=component, **kwargs)


class TestAdapter(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_product(self):
        product = self.factory.makeProduct()
        subset = IBranchCollection(product)
        self.assertIsInstance(subset, ProductBranchCollection)
        self.assertEqual(product.name, subset.name)

    def test_person(self):
        # The default IBranchCollection for a person is all of the branches
        # owned by that person.
        # XXX: Is this a good idea? - jml
        person = self.factory.makePerson()
        subset = IBranchCollection(person)
        self.assertIsInstance(subset, PersonBranchCollection)
        self.assertEqual(person.name, subset.name)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

