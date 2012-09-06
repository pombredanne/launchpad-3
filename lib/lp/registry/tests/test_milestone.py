# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Milestone related test helper."""

__metaclass__ = type

from operator import attrgetter
import unittest

from zope.component import getUtility

from lp.app.errors import NotFoundError
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.milestone import (
    IHasMilestones,
    IMilestoneSet,
    )
from lp.registry.interfaces.product import IProductSet
from lp.testing import (
    ANONYMOUS,
    login,
    logout,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.matchers import DoesNotSnapshot


class MilestoneTest(unittest.TestCase):
    """Milestone tests."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login(ANONYMOUS)

    def tearDown(self):
        logout()

    def testMilestoneSetIterator(self):
        """Test of MilestoneSet.__iter__()."""
        all_milestones_ids = set(
            milestone.id for milestone in getUtility(IMilestoneSet))
        self.assertEqual(all_milestones_ids,
                         set((1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)))

    def testMilestoneSetGet(self):
        """Test of MilestoneSet.get()"""
        milestone_set = getUtility(IMilestoneSet)
        self.assertEqual(milestone_set.get(1).id, 1)
        self.assertRaises(NotFoundError, milestone_set.get, 100000)

    def testMilestoneSetGetIDs(self):
        """Test of MilestoneSet.getByIds()"""
        milestone_set = getUtility(IMilestoneSet)
        milestones = milestone_set.getByIds([1, 3])
        ids = sorted(map(attrgetter('id'), milestones))
        self.assertEqual([1, 3], ids)

    def testMilestoneSetGetByIDs_ignores_missing(self):
        milestone_set = getUtility(IMilestoneSet)
        self.assertEqual([], list(milestone_set.getByIds([100000])))

    def testMilestoneSetGetByNameAndProduct(self):
        """Test of MilestoneSet.getByNameAndProduct()"""
        firefox = getUtility(IProductSet).getByName('firefox')
        milestone_set = getUtility(IMilestoneSet)
        milestone = milestone_set.getByNameAndProduct('1.0', firefox)
        self.assertEqual(milestone.name, '1.0')
        self.assertEqual(milestone.target, firefox)

        marker = object()
        milestone = milestone_set.getByNameAndProduct(
            'does not exist', firefox, default=marker)
        self.assertEqual(milestone, marker)

    def testMilestoneSetGetByNameAndDistribution(self):
        """Test of MilestoneSet.getByNameAndDistribution()"""
        debian = getUtility(IDistributionSet).getByName('debian')
        milestone_set = getUtility(IMilestoneSet)
        milestone = milestone_set.getByNameAndDistribution('3.1', debian)
        self.assertEqual(milestone.name, '3.1')
        self.assertEqual(milestone.target, debian)

        marker = object()
        milestone = milestone_set.getByNameAndDistribution(
            'does not exist', debian, default=marker)
        self.assertEqual(milestone, marker)

    def testMilestoneSetGetVisibleMilestones(self):
        all_visible_milestones_ids = [
            milestone.id
            for milestone in getUtility(IMilestoneSet).getVisibleMilestones()]
        self.assertEqual(
            all_visible_milestones_ids,
            [1, 2, 3])


class HasMilestonesSnapshotTestCase(TestCaseWithFactory):
    """A TestCase for snapshots of pillars with milestones."""

    layer = DatabaseFunctionalLayer

    def check_skipped(self, target):
        """Asserts that fields marked doNotSnapshot are skipped."""
        skipped = [
            'milestones',
            'all_milestones',
            ]
        self.assertThat(target, DoesNotSnapshot(skipped, IHasMilestones))

    def test_product(self):
        product = self.factory.makeProduct()
        self.check_skipped(product)

    def test_distribution(self):
        distribution = self.factory.makeDistribution()
        self.check_skipped(distribution)

    def test_distroseries(self):
        distroseries = self.factory.makeDistroSeries()
        self.check_skipped(distroseries)

    def test_projectgroup(self):
        projectgroup = self.factory.makeProject()
        self.check_skipped(projectgroup)


class MilestoneBugTaskSpecificationTest(TestCaseWithFactory):
    """Test cases for retrieving bugtasks and specifications for a milestone.
    """

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(MilestoneBugTaskSpecificationTest, self).setUp()
        self.owner = self.factory.makePerson()
        self.product = self.factory.makeProduct(name="product1")
        self.milestone = self.factory.makeMilestone(product=self.product)

    def _make_bug(self, **kwargs):
        milestone = kwargs.pop('milestone', None)
        bugtask = self.factory.makeBugTask(**kwargs)
        bugtask.milestone = milestone
        return bugtask

    def _create_items(self, num, factory, **kwargs):
        items = []
        with person_logged_in(self.owner):
            for n in xrange(num):
                items.append(factory(**kwargs))
        return items

    def test_bugtask_retrieval(self):
        # Ensure that all bugtasks on a milestone can be retrieved.
        bugtasks = self._create_items(
            5, self._make_bug,
            milestone=self.milestone,
            owner=self.owner,
            target=self.product,
            )
        self.assertContentEqual(bugtasks, self.milestone.bugtasks(self.owner))

    def test_specification_retrieval(self):
        # Ensure that all specifications on a milestone can be retrieved.
        specifications = self._create_items(
            5, self.factory.makeSpecification,
            milestone=self.milestone,
            owner=self.owner,
            product=self.product,
            )
        self.assertContentEqual(specifications, self.milestone.specifications)


class MilestonesContainsPartialSpecifications(TestCaseWithFactory):
    """Milestones list specifications with some workitems targeted to it."""

    layer = DatabaseFunctionalLayer

    def _create_milestones_on_target(self, **kwargs):
        """Create a milestone on a target with work targeted to it.

        Target should be specified using either product or distribution
        argument which is directly passed into makeMilestone call.
        """
        other_milestone = self.factory.makeMilestone(**kwargs)
        target_milestone = self.factory.makeMilestone(**kwargs)
        specification = self.factory.makeSpecification(
            milestone=other_milestone, **kwargs)
        # Create two workitems to ensure this doesn't cause
        # two specifications to be returned.
        self.factory.makeSpecificationWorkItem(
            specification=specification, milestone=target_milestone)
        self.factory.makeSpecificationWorkItem(
            specification=specification, milestone=target_milestone)
        return specification, target_milestone

    def test_milestones_on_product(self):
        specification, target_milestone = self._create_milestones_on_target(
            product=self.factory.makeProduct())
        self.assertEqual([specification],
                         list(target_milestone.specifications))

    def test_milestones_on_distribution(self):
        specification, target_milestone = self._create_milestones_on_target(
            distribution=self.factory.makeDistribution())
        self.assertEqual([specification],
                         list(target_milestone.specifications))

    def test_milestones_on_project(self):
        # A Project (Project Group) milestone contains all specifications
        # targetted to contained Products (Projects) for milestones of
        # a certain name.
        projectgroup = self.factory.makeProject()
        product = self.factory.makeProduct(project=projectgroup)
        specification, target_milestone = self._create_milestones_on_target(
            product=product)
        milestone = projectgroup.getMilestone(name=target_milestone.name)
        self.assertEqual([specification],
                         list(milestone.specifications))

    def test_milestones_with_deleted_workitems(self):
        # Deleted work items do not cause the specification to show up
        # in the milestone page.
        milestone = self.factory.makeMilestone(
            product=self.factory.makeProduct())
        specification = self.factory.makeSpecification(
            milestone=milestone, product=milestone.product)
        self.factory.makeSpecificationWorkItem(
            specification=specification, milestone=milestone, deleted=True)
        self.assertEqual([], list(milestone.specifications))
