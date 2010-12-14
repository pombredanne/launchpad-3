# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for the exclude_conjoined_tasks param for BugTaskSearchParams."""

__metaclass__ = type

__all__ = []

from testtools.matchers import Equals

from storm.store import Store
from zope.component import getUtility

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.series import SeriesStatus
from lp.bugs.interfaces.bugtask import (
    BugTaskSearchParams,
    BugTaskStatus,
    )
from lp.testing import (
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.matchers import HasQueryCount


class TestSearchBase(TestCaseWithFactory):
    """Tests of exclude_conjoined_tasks param."""

    #_reset_between_tests = False

    def makeBug(self, milestone):
        bug = self.factory.makeBug(
            product=milestone.product, distribution=milestone.distribution)
        with person_logged_in(milestone.target.owner):
            bug.default_bugtask.transitionToMilestone(
                milestone, milestone.target.owner)
        store = Store.of(bug)
        store.flush()
        store.invalidate()
        return bug


class TestProjectExcludeConjoinedMasterSearch(TestSearchBase):
    """Tests of exclude_conjoined_tasks param for project milestones."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProjectExcludeConjoinedMasterSearch, self).setUp()
        # Test that the right number of bugtasks are returned when bugs
        # with conjoined masters are excluded.
        self.product = self.factory.makeProduct()
        self.milestone = self.factory.makeMilestone(
            product=self.product, name='foo')
        self.bug_count = 2
        self.bugs = [
            self.makeBug(self.milestone)
            for i in range(self.bug_count)]
        self.params = BugTaskSearchParams(
            user=None, milestone=self.milestone, exclude_conjoined_tasks=True)

    def test_search_results_count_simple(self):
        # Verify number of results with no conjoined masters.
        self.assertEqual(
            self.bug_count,
            self.milestone.target.searchTasks(self.params).count())

    def test_search_query_count(self):
        # Verify query count.
        with StormStatementRecorder() as recorder:
            list(self.milestone.target.searchTasks(self.params))
        self.assertThat(recorder, HasQueryCount(Equals(4)))

    def test_search_results_count_with_other_productseries_tasks(self):
        # Test with zero conjoined masters and bugtasks targeted to
        # productseries that are not the development focus.
        productseries = self.factory.makeProductSeries(product=self.product)
        for bug in self.bugs:
            self.factory.makeBugTask(bug=bug, target=productseries)
            self.assertEqual(
                self.bug_count,
                self.milestone.target.searchTasks(self.params).count())

    def test_search_results_count_with_conjoined_masters(self):
        # Test with increasing numbers of conjoined masters.
        conjoined_master_count = 0
        for bug in self.bugs:
            conjoined_master_count += 1
            self.factory.makeBugTask(
                bug=bug, target=self.product.development_focus)
            self.assertEqual(
                self.bug_count - conjoined_master_count,
                self.milestone.target.searchTasks(self.params).count())

    def test_search_results_count_with_wontfix_conjoined_masters(self):
        # Test that conjoined master bugtasks in the WONTFIX status
        # don't cause the bug to be excluded.
        masters = [
            self.factory.makeBugTask(
                bug=bug, target=self.product.development_focus)
            for bug in self.bugs]
        conjoined_master_count = len(masters)
        for bugtask in masters:
            conjoined_master_count -= 1
            with person_logged_in(self.product.owner):
                bugtask.transitionToStatus(
                    BugTaskStatus.WONTFIX, self.product.owner)
            self.assertEqual(
                self.bug_count - conjoined_master_count,
                self.milestone.target.searchTasks(self.params).count())


class TestProjectGroupExcludeConjoinedMasterSearch(TestSearchBase):
    """Tests of exclude_conjoined_tasks param for project group milestones."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProjectGroupExcludeConjoinedMasterSearch, self).setUp()
        self.projectgroup = self.factory.makeProject()
        self.bug_count = 2
        self.bug_products = {}
        for i in range(self.bug_count):
            product = self.factory.makeProduct(project=self.projectgroup)
            product_milestone = self.factory.makeMilestone(
                product=product, name='foo')
            bug = self.makeBug(product_milestone)
            self.bug_products[bug] = product
        self.milestone = self.projectgroup.getMilestone('foo')
        self.params = BugTaskSearchParams(
            user=None, milestone=self.milestone, exclude_conjoined_tasks=True)

    def test_search_results_count_simple(self):
        # Verify number of results with no conjoined masters.
        self.assertEqual(
            self.bug_count,
            self.milestone.target.searchTasks(self.params).count())

    def test_search_query_count(self):
        with StormStatementRecorder() as recorder:
            list(self.milestone.target.searchTasks(self.params))
        self.assertThat(recorder, HasQueryCount(Equals(1)))

    def test_search_results_count_with_other_productseries_tasks(self):
        # Test with zero conjoined masters and bugtasks targeted to
        # productseries that are not the development focus.
        for bug, product in self.bug_products.items():
            productseries = self.factory.makeProductSeries(product=product)
            self.factory.makeBugTask(bug=bug, target=productseries)
            self.assertEqual(
                self.bug_count,
                self.milestone.target.searchTasks(self.params).count())

    def test_search_results_count_with_conjoined_masters(self):
        # Test with increasing numbers of conjoined masters.
        conjoined_master_count = 0
        for bug, product in self.bug_products.items():
            conjoined_master_count += 1
            self.factory.makeBugTask(
                bug=bug, target=product.development_focus)
            self.assertEqual(
                self.bug_count - conjoined_master_count,
                self.milestone.target.searchTasks(self.params).count())

    def test_search_results_count_with_irrelevant_conjoined_masters(self):
        # Verify that a conjoined master in one project of the project
        # group doesn't cause a bugtask on another project in the group
        # to be excluded from the project group milestone's bugs.
        for bug, product in self.bug_products.items():
            other_product = self.factory.makeProduct(
                project=self.projectgroup)
            # Create a new milestone with the same name.
            other_product_milestone = self.factory.makeMilestone(
                product=other_product,
                name=bug.default_bugtask.milestone.name)
            # Add bugtask on the new product and select the milestone.
            other_product_bugtask = self.factory.makeBugTask(
                bug=bug, target=other_product)
            with person_logged_in(other_product.owner):
                other_product_bugtask.transitionToMilestone(
                    other_product_milestone, other_product.owner)
            # Add conjoined master for the milestone on the new product.
            self.factory.makeBugTask(
                bug=bug, target=other_product.development_focus)
            # The bug count should not change, since we are just adding
            # bugtasks on existing bugs.
            self.assertEqual(
                self.bug_count,
                self.milestone.target.searchTasks(self.params).count())

    def test_search_results_count_with_wontfix_conjoined_masters(self):
        # Test that conjoined master bugtasks in the WONTFIX status
        # don't cause the bug to be excluded.
        masters = [
            self.factory.makeBugTask(
                bug=bug, target=product.development_focus)
            for bug, product in self.bug_products.items()]
        conjoined_master_count = len(masters)
        for bugtask in masters:
            conjoined_master_count -= 1
            with person_logged_in(product.owner):
                bugtask.transitionToStatus(
                    BugTaskStatus.WONTFIX, bugtask.target.owner)
            self.assertEqual(
                self.bug_count - conjoined_master_count,
                self.milestone.target.searchTasks(self.params).count())


class TestDistributionExcludeConjoinedMasterSearch(TestSearchBase):
    """Tests of exclude_conjoined_tasks param for distribution milestones."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDistributionExcludeConjoinedMasterSearch, self).setUp()
        self.distro = getUtility(ILaunchpadCelebrities).ubuntu
        self.milestone = self.factory.makeMilestone(
            distribution=self.distro, name='foo')
        self.bug_count = 2
        self.bugs = [
            self.makeBug(self.milestone)
            for i in range(self.bug_count)]
        self.params = BugTaskSearchParams(
            user=None, milestone=self.milestone, exclude_conjoined_tasks=True)

    def test_search_results_count_simple(self):
        # Verify number of results with no conjoined masters.
        self.assertEqual(
            self.bug_count,
            self.milestone.target.searchTasks(self.params).count())

    def test_search_query_count(self):
        # Verify query count.
        with StormStatementRecorder() as recorder:
            list(self.milestone.target.searchTasks(self.params))
        self.assertThat(recorder, HasQueryCount(Equals(4)))

    def test_search_results_count_with_other_productseries_tasks(self):
        # Test with zero conjoined masters and bugtasks targeted to
        # productseries that are not the development focus.
        distroseries = self.factory.makeDistroSeries(
            distribution=self.distro, status=SeriesStatus.SUPPORTED)
        for bug in self.bugs:
            self.factory.makeBugTask(bug=bug, target=distroseries)
            self.assertEqual(
                self.bug_count,
                self.milestone.target.searchTasks(self.params).count())

    def test_search_results_count_with_conjoined_masters(self):
        # Test with increasing numbers of conjoined masters.
        conjoined_master_count = 0
        for bug in self.bugs:
            conjoined_master_count += 1
            self.factory.makeBugTask(
                bug=bug, target=self.distro.currentseries)
            self.assertEqual(
                self.bug_count - conjoined_master_count,
                self.milestone.target.searchTasks(self.params).count())

    def test_search_results_count_with_wontfix_conjoined_masters(self):
        # Test that conjoined master bugtasks in the WONTFIX status
        # don't cause the bug to be excluded.
        masters = [
            self.factory.makeBugTask(
                bug=bug, target=self.distro.currentseries)
            for bug in self.bugs]
        conjoined_master_count = len(masters)
        for bugtask in masters:
            conjoined_master_count -= 1
            with person_logged_in(self.distro.owner):
                bugtask.transitionToStatus(
                    BugTaskStatus.WONTFIX, self.distro.owner)
            self.assertEqual(
                self.bug_count - conjoined_master_count,
                self.milestone.target.searchTasks(self.params).count())
