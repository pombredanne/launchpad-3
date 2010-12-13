# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for the exclude_conjoined_tasks param for BugTaskSearchParams."""

__metaclass__ = type

__all__ = []

import random
from testtools.matchers import Equals

from storm.store import Store
from zope.component import getUtility

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.series import SeriesStatus
from lp.bugs.interfaces.bug import CreateBugParams
from lp.bugs.interfaces.bugtask import (
    BugTaskSearchParams,
    BugTaskStatus,
    IBugTaskSet,
    )
from lp.testing import (
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.matchers import HasQueryCount


def bugtarget_filebug(bugtarget, summary, status=None):
    """File a bug as the current user on the bug target and return it."""
    return bugtarget.createBug(CreateBugParams(
        getUtility(ILaunchBag).user, summary, comment=summary, status=status))


def project_filebug(project, summary, status=None):
    """File a bug on a project.

    Since it's not possible to file a bug on a project directly, the bug
    will be filed on one of its products.
    """
    # It doesn't matter which product the bug is filed on.
    product = random.choice(list(project.products))
    bug = bugtarget_filebug(product, summary, status=status)
    return bug


def productseries_filebug(productseries, summary, status=None):
    """File a bug on a product series.

    Since it's not possible to file a bug on a product series directly,
    the bug will first be filed on its product, then a series task will
    be created.
    """
    bug = bugtarget_filebug(productseries.product, summary, status=status)
    getUtility(IBugTaskSet).createTask(
        bug, getUtility(ILaunchBag).user, productseries=productseries,
        status=status)
    return bug


class TestExcludeConjoinedMasterSearch(TestCaseWithFactory):
    """Tests of exclude_conjoined_tasks param."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestExcludeConjoinedMasterSearch, self).setUp()
        self.product = self.factory.makeProduct()

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

    def test_product_milestone(self):
        # Test that the right number of bugtasks are returned when bugs
        # with conjoined masters are excluded.
        product = self.factory.makeProduct()
        milestone = self.factory.makeMilestone(
            product=product, name='foo')
        bug_count = 3
        bugs = [
            self.makeBug(milestone)
            for i in range(bug_count)]
        params = BugTaskSearchParams(
            user=None, milestone=milestone, exclude_conjoined_tasks=True)

        # Test with zero conjoined masters.
        with StormStatementRecorder() as recorder:
            self.assertEqual(bug_count,
                             milestone.target.searchTasks(params).count())
        self.assertThat(recorder, HasQueryCount(Equals(4)))

        # Test with zero conjoined masters and bugtasks targeted to
        # productseries that are not the development focus.
        productseries = self.factory.makeProductSeries(product=product)
        for bug in bugs:
            self.factory.makeBugTask(bug=bug, target=productseries)
            self.assertEqual(bug_count,
                             milestone.target.searchTasks(params).count())

        # Test with increasing numbers of conjoined masters.
        conjoined_master_count = 0
        masters = []
        for bug in bugs:
            conjoined_master_count += 1
            masters.append(self.factory.makeBugTask(
                bug=bug, target=product.development_focus))
            self.assertEqual(bug_count - conjoined_master_count,
                             milestone.target.searchTasks(params).count())

        # Test that conjoined master bugtasks in the WONTFIX status
        # don't cause the bug to be excluded.
        for bugtask in masters:
            conjoined_master_count -= 1
            with person_logged_in(product.owner):
                bugtask.transitionToStatus(
                    BugTaskStatus.WONTFIX, product.owner)
            self.assertEqual(bug_count - conjoined_master_count,
                             milestone.target.searchTasks(params).count())

    def test_distribution_milestone(self):
        # Test that the right number of bugtasks are returned when bugs
        # with conjoined masters are excluded.
        distro = getUtility(ILaunchpadCelebrities).ubuntu
        milestone = self.factory.makeMilestone(
            distribution=distro, name='foo')
        bug_count = 3
        bugs = [
            self.makeBug(milestone)
            for i in range(bug_count)]
        params = BugTaskSearchParams(
            user=None, milestone=milestone, exclude_conjoined_tasks=True)

        # Test with zero conjoined masters.
        with StormStatementRecorder() as recorder:
            self.assertEqual(bug_count,
                             milestone.target.searchTasks(params).count())
        self.assertThat(recorder, HasQueryCount(Equals(4)))

        # Test with zero conjoined masters and bugtasks targeted to
        # productseries that are not the development focus.
        distroseries = self.factory.makeDistroSeries(
            distribution=distro, status=SeriesStatus.SUPPORTED)
        for bug in bugs:
            self.factory.makeBugTask(bug=bug, target=distroseries)
            self.assertEqual(bug_count,
                             milestone.target.searchTasks(params).count())

        # Test with increasing numbers of conjoined masters.
        conjoined_master_count = 0
        for bug in bugs:
            conjoined_master_count += 1
            self.factory.makeBugTask(
                bug=bug, target=distro.currentseries)
            self.assertEqual(bug_count - conjoined_master_count,
                             milestone.target.searchTasks(params).count())
