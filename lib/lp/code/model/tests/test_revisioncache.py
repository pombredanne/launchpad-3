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

    def makeCachedRevision(self):
        # A factory method for RevisionCache objects.
        revision = self.factory.makeRevision()
        return RevisionCache(revision)

    def test_simple_total_count(self):
        # Test that the count does in fact count the revisions we add.
        for i in range(4):
            self.makeCachedRevision()
        cache = getUtility(IRevisionCache)
        self.assertEqual(4, cache.count())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

