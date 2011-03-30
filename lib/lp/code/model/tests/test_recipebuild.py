# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for RecipeBuildRecordSet."""

__metaclass__ = type

from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer

from lp.code.interfaces.recipebuild import IRecipeBuildRecordSet
from lp.testing import TestCaseWithFactory


class TestRecipeBuildRecordSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestRecipeBuildRecordSet, self).setUp()
        all_records, recent_records = (
            self.factory.makeRecipeBuildRecords(6, 2))
        self.all_records = all_records
        self.recent_records = recent_records

    def test_findCompletedDailyBuilds(self):
        """Ensure findCompletedDailyBuilds returns expected records.

        We check that we can query for all completed builds.
        """
        recipe_build_set = getUtility(IRecipeBuildRecordSet)
        builds = recipe_build_set.findCompletedDailyBuilds(epoch_days=None)
        self.assertEqual(self.all_records, list(builds))

    def test_findRecentlyCompletedDailyBuilds(self):
        """Ensure findCompletedDailyBuilds returns expected records.

        We check that we can query for recently completed builds.
        """
        recipe_build_set = getUtility(IRecipeBuildRecordSet)
        builds = recipe_build_set.findCompletedDailyBuilds()
        self.assertEqual(self.recent_records, list(builds))
