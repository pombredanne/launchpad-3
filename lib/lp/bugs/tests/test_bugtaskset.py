# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugTaskSet."""

__metaclass__ = type

from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.interfaces.bugtask import (
    BugTaskStatus,
    IBugTaskSet,
    )
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )


class TestStatusCountsForProductSeries(TestCaseWithFactory):
    """Test BugTaskSet.getStatusCountsForProductSeries()."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestStatusCountsForProductSeries, self).setUp()
        self.bugtask_set = getUtility(IBugTaskSet)
        self.owner = self.factory.makePerson()
        login_person(self.owner)
        self.product = self.factory.makeProduct(owner=self.owner)
        self.series = self.factory.makeProductSeries(product=self.product)
        self.milestone = self.factory.makeMilestone(productseries=self.series)

    def get_counts(self, user):
        counts = self.bugtask_set.getStatusCountsForProductSeries(
                user, self.series)
        return [
            (BugTaskStatus.items[status_id], count)
            for status_id, count in counts]

    def test_privacy_and_counts_for_unauthenticated_user(self):
        # An unauthenticated user should see bug counts for each status
        # that do not include private bugs.
        self.factory.makeBug(milestone=self.milestone)
        self.factory.makeBug(milestone=self.milestone, private=True)
        self.factory.makeBug(series=self.series)
        self.factory.makeBug(series=self.series, private=True)
        self.assertEqual(
            [(BugTaskStatus.NEW, 2)],
            self.get_counts(None))

    def test_privacy_and_counts_for_owner(self):
        # The owner should see bug counts for each status that do
        # include all private bugs.
        self.factory.makeBug(milestone=self.milestone)
        self.factory.makeBug(milestone=self.milestone, private=True)
        self.factory.makeBug(series=self.series)
        self.factory.makeBug(series=self.series, private=True)
        self.assertEqual(
            [(BugTaskStatus.NEW, 4)],
            self.get_counts(self.owner))

    def test_privacy_and_counts_for_other_user(self):
        # A random authenticated user should see bug counts for each
        # status that do include all private bugs, since it is costly to
        # query just the private bugs that the user has access to view,
        # and this query may be run many times on a single page.
        self.factory.makeBug(milestone=self.milestone)
        self.factory.makeBug(milestone=self.milestone, private=True)
        self.factory.makeBug(series=self.series)
        self.factory.makeBug(series=self.series, private=True)
        other = self.factory.makePerson()
        self.assertEqual(
            [(BugTaskStatus.NEW, 4)],
            self.get_counts(other))

    def test_multiple_statuses(self):
        # Test that separate counts are provided for each status that
        # bugs are found in.
        for status in (BugTaskStatus.INVALID, BugTaskStatus.OPINION):
            self.factory.makeBug(milestone=self.milestone, status=status)
            self.factory.makeBug(series=self.series, status=status)
        for i in range(3):
            self.factory.makeBug(series=self.series)
        self.assertEqual(
            [(BugTaskStatus.INVALID, 2),
             (BugTaskStatus.OPINION, 2),
             (BugTaskStatus.NEW, 3),
            ],
            self.get_counts(None))


class TestBugTaskMilestones(TestCaseWithFactory):
    """Tests that appropriate milestones are returned for bugtasks."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugTaskMilestones, self).setUp()
        self.product = self.factory.makeProduct()
        self.product_bug = self.factory.makeBug(product=self.product)
        self.product_milestone = self.factory.makeMilestone(
            product=self.product)
        self.distribution = self.factory.makeDistribution()
        self.distribution_bug = self.factory.makeBug(
            distribution=self.distribution)
        self.distribution_milestone = self.factory.makeMilestone(
            distribution=self.distribution)
        self.bugtaskset = getUtility(IBugTaskSet)

    def test_get_target_milestones_with_one_task(self):
        milestones = list(self.bugtaskset.getBugTaskTargetMilestones(
            [self.product_bug.default_bugtask]))
        self.assertEqual(
            [self.product_milestone],
            milestones)

    def test_get_target_milestones_multiple_tasks(self):
        tasks = [
            self.product_bug.default_bugtask,
            self.distribution_bug.default_bugtask,
            ]
        milestones = sorted(
            self.bugtaskset.getBugTaskTargetMilestones(tasks))
        self.assertEqual(
            sorted([self.product_milestone, self.distribution_milestone]),
            milestones)
