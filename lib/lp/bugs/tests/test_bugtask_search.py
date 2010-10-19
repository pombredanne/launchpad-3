# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from new import classobj
import sys
import unittest

from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer

from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskSearchParams,
    BugTaskStatus,
    IBugTaskSet,
    )
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class SearchTestBase(object):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(SearchTestBase, self).setUp()
        self.bugtask_set = getUtility(IBugTaskSet)

    def test_search_all_bugtasks_for_target(self):
        # BugTaskSet.search() returns all bug tasks for a given bug
        # target, if only the bug target is passed as a search parameter.
        params = self.getBugTaskSearchParams(user=None)
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks(self.bugtasks)
        self.assertEqual(expected, search_result)

    def test_private_bug_not_in_search_result_for_anonymous(self):
        # Private bugs are not included in search results for anonymous users.
        with person_logged_in(self.owner):
            self.bugtasks[-1].bug.setPrivate(True, self.owner)
        params = self.getBugTaskSearchParams(user=None)
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks(self.bugtasks)[:-1]
        self.assertEqual(expected, search_result)

    def test_private_bug_not_in_search_result_for_regular_user(self):
        # Private bugs are not included in search results for ordinary users.
        with person_logged_in(self.owner):
            self.bugtasks[-1].bug.setPrivate(True, self.owner)
        user = self.factory.makePerson()
        params = self.getBugTaskSearchParams(user=user)
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks(self.bugtasks)[:-1]
        self.assertEqual(expected, search_result)

    def test_private_bug_in_search_result_for_subscribed_user(self):
        # Private bugs are included in search results for ordinary users
        # which are subscribed to the bug.
        user = self.factory.makePerson()
        with person_logged_in(self.owner):
            self.bugtasks[-1].bug.setPrivate(True, self.owner)
            self.bugtasks[-1].bug.subscribe(user, self.owner)
        params = self.getBugTaskSearchParams(user=user)
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks(self.bugtasks)
        self.assertEqual(expected, search_result)


class BugTargetTestBase:
    """A base class for the bug target mixin classes."""

    def makeBugTasks(self, bugtarget):
        self.bugtasks = []
        with person_logged_in(self.owner):
            self.bugtasks.append(
                self.factory.makeBugTask(target=bugtarget))
            self.bugtasks[-1].importance = BugTaskImportance.HIGH
            self.bugtasks[-1].transitionToStatus(
                BugTaskStatus.TRIAGED, self.owner)

            self.bugtasks.append(
                self.factory.makeBugTask(target=bugtarget))
            self.bugtasks[-1].importance = BugTaskImportance.LOW
            self.bugtasks[-1].transitionToStatus(
                BugTaskStatus.NEW, self.owner)

            self.bugtasks.append(
                self.factory.makeBugTask(target=bugtarget))
            self.bugtasks[-1].importance = BugTaskImportance.CRITICAL
            self.bugtasks[-1].transitionToStatus(
                BugTaskStatus.FIXCOMMITTED, self.owner)


class BugTargetWithBugSuperVisor:
    """A base class for bug targets which have a bug supervisor."""

    def test_search_by_bug_supervisor(self):
        # We can search for bugs by bug supervisor.
        # We have by default no bug supervisor set, so searching for
        # bugs by supervisor returns no data.
        supervisor = self.factory.makeTeam(owner=self.owner)
        params = self.getBugTaskSearchParams(
            user=None, bug_supervisor=supervisor)
        search_result = self.runSearch(params)
        self.assertEqual([], search_result)

        # If we appoint a bug supervisor, searching for bug tasks
        # by supervisor will return all bugs for our test target.
        self.setSupervisor(supervisor)
        search_result = self.runSearch(params)
        expected = self.resultValuesForBugtasks(self.bugtasks)
        self.assertEqual(expected, search_result)

    def setSupervisor(self, supervisor):
        """Set the bug supervisor for the bug task target."""
        with person_logged_in(self.owner):
            self.searchtarget.setBugSupervisor(supervisor, self.owner)


class ProductTarget(BugTargetTestBase, BugTargetWithBugSuperVisor):
    """Use a product as the bug target."""

    def setUp(self):
        super(ProductTarget, self).setUp()
        self.searchtarget = self.factory.makeProduct()
        self.owner = self.searchtarget.owner
        self.makeBugTasks(self.searchtarget)

    def getBugTaskSearchParams(self, *args, **kw):
        """Return a BugTaskSearchParams object for the given parameters.

        Also, set the bug target.
        """
        params = BugTaskSearchParams(*args, **kw)
        params.setProduct(self.searchtarget)
        return params


class ProductSeriesTarget(BugTargetTestBase):
    """Use a product series as the bug target."""

    def setUp(self):
        super(ProductSeriesTarget, self).setUp()
        self.searchtarget = self.factory.makeProductSeries()
        self.owner = self.searchtarget.owner
        self.makeBugTasks(self.searchtarget)

    def getBugTaskSearchParams(self, *args, **kw):
        """Return a BugTaskSearchParams object for the given parameters.

        Also, set the bug target.
        """
        params = BugTaskSearchParams(*args, **kw)
        params.setProductSeries(self.searchtarget)
        return params


class ProjectGroupTarget(BugTargetTestBase, BugTargetWithBugSuperVisor):
    """Use a project  group as the bug target."""

    def setUp(self):
        super(ProjectGroupTarget, self).setUp()
        self.searchtarget = self.factory.makeProject()
        self.owner = self.searchtarget.owner
        self.makeBugTasks()

    def getBugTaskSearchParams(self, *args, **kw):
        """Return a BugTaskSearchParams object for the given parameters.

        Also, set the bug target.
        """
        params = BugTaskSearchParams(*args, **kw)
        params.setProject(self.searchtarget)
        return params

    def makeBugTasks(self):
        """Create bug tasks for the search target."""
        self.bugtasks = []
        with person_logged_in(self.owner):
            product = self.factory.makeProduct(owner=self.owner)
            product.project = self.searchtarget
            self.bugtasks.append(
                self.factory.makeBugTask(target=product))
            self.bugtasks[-1].importance = BugTaskImportance.HIGH
            self.bugtasks[-1].transitionToStatus(
                BugTaskStatus.TRIAGED, self.owner)

            product = self.factory.makeProduct(owner=self.owner)
            product.project = self.searchtarget
            self.bugtasks[-1].importance = BugTaskImportance.LOW
            self.bugtasks[-1].transitionToStatus(
            BugTaskStatus.NEW, self.owner)

            product = self.factory.makeProduct(owner=self.owner)
            product.project = self.searchtarget
            self.bugtasks.append(
                self.factory.makeBugTask(target=product))
            self.bugtasks[-1].importance = BugTaskImportance.CRITICAL
            self.bugtasks[-1].transitionToStatus(
                BugTaskStatus.FIXCOMMITTED, self.owner)

    def setSupervisor(self, supervisor):
        """Set the bug supervisor for the bug task targets."""
        with person_logged_in(self.owner):
            # We must set the bug supervisor for each bug task target
            for bugtask in self.bugtasks:
                bugtask.target.setBugSupervisor(supervisor, self.owner)


class MilestoneTarget(BugTargetTestBase):
    """Use a milestone as the bug target."""

    def setUp(self):
        super(MilestoneTarget, self).setUp()
        self.product = self.factory.makeProduct()
        self.searchtarget = self.factory.makeMilestone(product=self.product)
        self.owner = self.product.owner
        self.makeBugTasks(self.product)

    def getBugTaskSearchParams(self, *args, **kw):
        """Return a BugTaskSearchParams object for the given parameters.

        Also, set the bug target.
        """
        params = BugTaskSearchParams(milestone=self.searchtarget, *args, **kw)
        return params

    def makeBugTasks(self, bugtarget):
        """Create bug tasks for a product and assign them to a milestone."""
        super(MilestoneTarget, self).makeBugTasks(bugtarget)
        with person_logged_in(self.owner):
            for bugtask in self.bugtasks:
                bugtask.transitionToMilestone(self.searchtarget, self.owner)


class DistributionTarget(BugTargetTestBase, BugTargetWithBugSuperVisor):
    """Use a dirstibution as the bug target."""

    def setUp(self):
        super(DistributionTarget, self).setUp()
        self.searchtarget = self.factory.makeDistribution()
        self.owner = self.searchtarget.owner
        self.makeBugTasks(self.searchtarget)

    def getBugTaskSearchParams(self, *args, **kw):
        """Return a BugTaskSearchParams object for the given parameters.

        Also, set the bug target.
        """
        params = BugTaskSearchParams(*args, **kw)
        params.setDistribution(self.searchtarget)
        return params


class DistroseriesTarget(BugTargetTestBase):
    """Use a distro series as the bug target."""

    def setUp(self):
        super(DistroseriesTarget, self).setUp()
        self.searchtarget = self.factory.makeDistroSeries()
        self.owner = self.searchtarget.owner
        self.makeBugTasks(self.searchtarget)

    def getBugTaskSearchParams(self, *args, **kw):
        """Return a BugTaskSearchParams object for the given parameters.

        Also, set the bug target.
        """
        params = BugTaskSearchParams(*args, **kw)
        params.setDistroSeries(self.searchtarget)
        return params


class SourcePackageTarget(BugTargetTestBase):
    """Use a source package as the bug target."""

    def setUp(self):
        super(SourcePackageTarget, self).setUp()
        self.searchtarget = self.factory.makeSourcePackage()
        self.owner = self.searchtarget.distroseries.owner
        self.makeBugTasks(self.searchtarget)

    def getBugTaskSearchParams(self, *args, **kw):
        """Return a BugTaskSearchParams object for the given parameters.

        Also, set the bug target.
        """
        params = BugTaskSearchParams(*args, **kw)
        params.setSourcePackage(self.searchtarget)
        return params


class DistributionSourcePackageTarget(BugTargetTestBase,
                                      BugTargetWithBugSuperVisor):
    """Use a distribution source package as the bug target."""

    def setUp(self):
        super(DistributionSourcePackageTarget, self).setUp()
        self.searchtarget = self.factory.makeDistributionSourcePackage()
        self.owner = self.searchtarget.distribution.owner
        self.makeBugTasks(self.searchtarget)

    def getBugTaskSearchParams(self, *args, **kw):
        """Return a BugTaskSearchParams object for the given parameters.

        Also, set the bug target.
        """
        params = BugTaskSearchParams(*args, **kw)
        params.setSourcePackage(self.searchtarget)
        return params

    def setSupervisor(self, supervisor):
        """Set the bug supervisor for the bug task target."""
        with person_logged_in(self.owner):
            self.searchtarget.distribution.setBugSupervisor(
                supervisor, self.owner)


bug_targets_mixins = (
    DistributionTarget,
    DistributionSourcePackageTarget,
    DistroseriesTarget,
    MilestoneTarget,
    ProductSeriesTarget,
    ProductTarget,
    ProjectGroupTarget,
    SourcePackageTarget,
    )


class PreloadBugtaskTargets:
    """Preload bug targets during a BugTaskSet.search() query."""

    def setUp(self):
        super(PreloadBugtaskTargets, self).setUp()

    def runSearch(self, params, *args):
        """Run BugTaskSet.search() and preload bugtask target objects."""
        return list(self.bugtask_set.search(params, *args, _noprejoins=False))

    def resultValuesForBugtasks(self, expected_bugtasks):
        return expected_bugtasks


class NoPreloadBugtaskTargets:
    """Do not preload bug targets during a BugTaskSet.search() query."""

    def setUp(self):
        super(NoPreloadBugtaskTargets, self).setUp()

    def runSearch(self, params, *args):
        """Run BugTaskSet.search() without preloading bugtask targets."""
        return list(self.bugtask_set.search(params, *args, _noprejoins=True))

    def resultValuesForBugtasks(self, expected_bugtasks):
        return expected_bugtasks


class QueryBugIDs:
    """Do not preload bug targets during a BugTaskSet.search() query."""

    def setUp(self):
        super(QueryBugIDs, self).setUp()

    def runSearch(self, params, *args):
        """Run BugTaskSet.searchBugIds()."""
        return list(self.bugtask_set.searchBugIds(params))

    def resultValuesForBugtasks(self, expected_bugtasks):
        return [bugtask.bug.id for bugtask in expected_bugtasks]


def test_suite():
    module = sys.modules[__name__]
    for bug_targetsearch_type_class in (
        PreloadBugtaskTargets, NoPreloadBugtaskTargets, QueryBugIDs):
        for target_mixin in bug_targets_mixins:
            class_name = 'Test%s%s' % (
                bug_targetsearch_type_class.__name__,
                target_mixin.__name__)
            test_class = classobj(
                class_name,
                (target_mixin, bug_targetsearch_type_class, SearchTestBase,
                 TestCaseWithFactory),
                {})
            module.__dict__[class_name] = test_class
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    return suite
