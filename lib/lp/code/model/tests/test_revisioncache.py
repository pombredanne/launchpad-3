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
                           distroseries=None, sourcepackagename=None,
                           private=False):
        # A factory method for RevisionCache objects.
        if revision is None:
            revision = self.factory.makeRevision()
        cached = RevisionCache(revision)
        cached.product = product
        cached.distroseries = distroseries
        cached.sourcepackagename = sourcepackagename
        cached.private = private
        return cached

    def test_simple_total_count(self):
        # Test that the count does in fact count the revisions we add.
        for i in range(4):
            self.makeCachedRevision()
        cache = getUtility(IRevisionCache)
        self.assertEqual(4, cache.count())

    def test_revision_in_multiple_namespaces_counted_once(self):
        # A revision that is in multiple namespaces is only counted once.
        revision = self.factory.makeRevision()
        product = self.factory.makeProduct()
        source_package = self.factory.makeSourcePackage()
        # Make a cached revision of a revision in a junk branch.
        self.makeCachedRevision(revision)
        # Make the same revision appear in a product.
        self.makeCachedRevision(revision, product=product)
        # And the same revision in a source package.
        self.makeCachedRevision(
            revision, distroseries=source_package.distroseries,
            sourcepackagename=source_package.sourcepackagename)
        cache = getUtility(IRevisionCache)
        self.assertEqual(1, cache.count())

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
        public_revision = self.makeCachedRevision().revision
        # Make a private cached revision.
        self.makeCachedRevision(private=True)

        cache = getUtility(IRevisionCache)
        # Counting all revisions gets public and private revisions.
        self.assertEqual(3, cache.count())
        # Limiting to public revisions does not get the private revisions.
        self.assertEqual(2, cache.public().count())
        self.assertEqual(
            sorted([revision, public_revision]),
            sorted(cache.public().getRevisions()))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

