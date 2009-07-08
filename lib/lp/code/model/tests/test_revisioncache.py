# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests relating to the revision cache."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.interfaces.revisioncache import IRevisionCache
from lp.code.model.revision import RevisionCache
from lp.testing import TestCaseWithFactory


class TestRevisionCache(TestCaseWithFactory):
    """Test the revision cache filters and counts."""

    layer = DatabaseFunctionalLayer

    # Initially the RevisionCache table is completely empty, so we don't need
    # to clear it out in the setUp.  And these tests that do the counts should
    # confirm it's emptiness.

    def test_initially_empty(self):
        # A test just to confirm that the RevisionCache is empty.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        results = store.find(RevisionCache)
        self.assertEqual(0, results.count())

    def makeCachedRevision(self, revision=None, product=None,
                           package=None, private=False):
        # A factory method for RevisionCache objects.
        if revision is None:
            revision = self.factory.makeRevision()
        cached = RevisionCache(revision)
        cached.product = product
        if package is not None:
            cached.distroseries = package.distroseries
            cached.sourcepackagename = package.sourcepackagename
        cached.private = private
        return revision

    def test_simple_total_count(self):
        # Test that the count does in fact count the revisions we add.
        for i in range(4):
            self.makeCachedRevision()
        cache = getUtility(IRevisionCache)
        self.assertEqual(4, cache.count())

    def test_revision_in_multiple_namespaces_counted_once(self):
        # A revision that is in multiple namespaces is only counted once.
        revision = self.factory.makeRevision()
        # Make a cached revision of a revision in a junk branch.
        self.makeCachedRevision(revision)
        # Make the same revision appear in a product.
        self.makeCachedRevision(revision, product=self.factory.makeProduct())
        # And the same revision in a source package.
        self.makeCachedRevision(
            revision, package=self.factory.makeSourcePackage())
        cache = getUtility(IRevisionCache)
        self.assertEqual(1, cache.count())

    def assertRevisionsEqual(self, expected_revisions, revision_collection):
        # Check that the revisions returned from the revision collection match
        # the expected revisions.
        self.assertEqual(
            sorted(expected_revisions),
            sorted(revision_collection.getRevisions()))

    def test_private_revisions(self):
        # Private flags are honour.ed when only requesting public revisions.
        # If a revision is in both public and private branches, then there are
        # two entried in the revision cache for it, and it will be retrieved
        # in a revision query
        revision = self.factory.makeRevision()
        # Put that revision in both a public and private branch.
        self.makeCachedRevision(revision, private=False)
        self.makeCachedRevision(revision, private=True)
        # Make a random public cached revision.
        public_revision = self.makeCachedRevision()
        # Make a private cached revision.
        self.makeCachedRevision(private=True)

        cache = getUtility(IRevisionCache)
        # Counting all revisions gets public and private revisions.
        self.assertEqual(3, cache.count())
        # Limiting to public revisions does not get the private revisions.
        self.assertEqual(2, cache.public().count())
        self.assertRevisionsEqual([revision, public_revision], cache.public())

    def test_in_product(self):
        # Revisions in a particular product can be restricted using the
        # inProduct method.
        product = self.factory.makeProduct()
        rev1 = self.makeCachedRevision(product=product)
        rev2 = self.makeCachedRevision(product=product)
        # Make two other revisions, on in a different product, and another
        # general one.
        self.makeCachedRevision(product=self.factory.makeProduct())
        self.makeCachedRevision()
        revision_cache = getUtility(IRevisionCache).inProduct(product)
        self.assertRevisionsEqual([rev1, rev2], revision_cache)

    def test_in_project(self):
        # Revisions across a project group can be determined using the
        # inProject method.
        project = self.factory.makeProject()
        product1 = self.factory.makeProduct(project=project)
        product2 = self.factory.makeProduct(project=project)
        rev1 = self.makeCachedRevision(product=product1)
        rev2 = self.makeCachedRevision(product=product2)
        # Make two other revisions, on in a different product, and another
        # general one.
        self.makeCachedRevision(product=self.factory.makeProduct())
        self.makeCachedRevision()
        revision_cache = getUtility(IRevisionCache).inProject(project)
        self.assertRevisionsEqual([rev1, rev2], revision_cache)

    def test_in_source_package(self):
        # Revisions associated with a particular source package are available
        # using the inSourcePackage method.
        sourcepackage = self.factory.makeSourcePackage()
        rev1 = self.makeCachedRevision(package=sourcepackage)
        rev2 = self.makeCachedRevision(package=sourcepackage)
        # Make two other revisions, on in a different product, and another
        # general one.
        self.makeCachedRevision(package=self.factory.makeSourcePackage())
        self.makeCachedRevision()
        revision_cache = getUtility(IRevisionCache).inSourcePackage(
            sourcepackage)
        self.assertRevisionsEqual([rev1, rev2], revision_cache)
        
        
def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

