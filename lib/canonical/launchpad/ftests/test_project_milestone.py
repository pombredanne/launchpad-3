# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Project Milestone related test helper."""

__metaclass__ = type

import unittest

from datetime import datetime
from zope.component import getUtility

from canonical.launchpad.interfaces import (BugTaskSearchParams,
    BugTaskStatus, CreateBugParams, IBugTaskSet, IPersonSet,
    IProductSet, IProjectSet, ISpecificationSet, SpecificationPriority,
    SpecificationDefinitionStatus)
from canonical.launchpad.ftests import login, syncUpdate
from canonical.testing import LaunchpadFunctionalLayer


class ProjectMilestoneTest(unittest.TestCase):
    """Setup of several milestones and associated data.

    A project milestone aggreates information from similar product milestones.
    This class creates:
      - up to three milestones in three products which belong to the
        Gnome project
      - specs and bugs in these products and associates them with the
        milestones.

    Visibility:
      - All milestones named '1.1' are visible
      - One milestone named '1.2' is visible, the other is not visible
      - All milestones named '1.3' are not visible

    Additionally, a milestone with a "typo" in its name and a milestone
    for firefox, i.e., for the mozilla project, named '1.1' is created.
    """

    layer = LaunchpadFunctionalLayer

    def __init__(self, methodName='runTest', helper_only=False):
        """If helper_only is True, set up it only as a helper class."""
        if not helper_only:
            unittest.TestCase.__init__(self, methodName)

    def setUp(self):
        """Login an admin user to perform the tests."""
        # From the persons defined in the test data, only those with
        # admin rights can change the 'visible' attribute of milestones.
        login('foo.bar@canonical.com')

    def createProductMilestone(
        self, milestone_name, product_name, date_expected):
        """Create a milestone in the trunk series of a product."""
        product_set = getUtility(IProductSet)
        product = product_set[product_name]
        series = product.getSeries('trunk')
        return series.newMilestone(
            name=milestone_name, dateexpected=date_expected)

    def test_milestone_name(self):
        """The names of project milestones.

        A project milestone named `A` exists, if at least one product of this
        project has a milestone named `A`.
        """
        # None of the Products of the Gnome project has yet milestones.
        gnome = getUtility(IProjectSet)['gnome']
        for product in gnome.products:
            self.assertEqual(list(product.all_milestones), [])

        # Hence Gnome itself has neither any milestones.
        self.assertEqual(list(gnome.all_milestones), [])

        # When a milestone for a Gnome product is created, gnome has a
        # milestone of the same name.
        self.createProductMilestone('1.1', 'evolution', None)
        gnome_milestone_names = [
            milestone.name for milestone in gnome.all_milestones]
        self.assertEqual(gnome_milestone_names, ['1.1'])

        # There is only one project milestone named '1.1', regardless of the
        # number of product milestones with this name.
        self.createProductMilestone('1.1', 'gnomebaker', None)
        gnome_milestone_names = [
            milestone.name for milestone in gnome.all_milestones]
        self.assertEqual(gnome_milestone_names, ['1.1'])

    def test_milestone_date_expected(self):
        """The dateexpected attribute.

        dateexpected is set to min(productmilestones.dateexpected).
        """
        gnome = getUtility(IProjectSet)['gnome']
        evolution_milestone = self.createProductMilestone(
            '1.1', 'evolution', None)
        gnomebaker_milestone = self.createProductMilestone(
            '1.1', 'gnomebaker', None)
        gnome_milestone = gnome.getMilestone('1.1')

        self.assertEqual(evolution_milestone.dateexpected, None)
        self.assertEqual(gnomebaker_milestone.dateexpected, None)
        self.assertEqual(gnome_milestone.dateexpected, None)

        evolution_milestone.dateexpected = datetime(2007, 4, 2)
        syncUpdate(evolution_milestone)
        gnome_milestone = gnome.getMilestone('1.1')
        self.assertEqual(gnome_milestone.dateexpected, datetime(2007, 4, 2))

        gnomebaker_milestone.dateexpected = datetime(2007, 4, 1)
        syncUpdate(gnomebaker_milestone)
        gnome_milestone = gnome.getMilestone('1.1')
        self.assertEqual(gnome_milestone.dateexpected, datetime(2007, 4, 1))

    def test_milestone_visibility(self):
        """A project milestone is visible, if at least one product milestone
        is visible."""
        gnome = getUtility(IProjectSet)['gnome']
        evolution_milestone = self.createProductMilestone(
            '1.1', 'evolution', None)
        gnomebaker_milestone = self.createProductMilestone(
            '1.1', 'gnomebaker', None)

        self.assertEqual(evolution_milestone.visible, True)
        self.assertEqual(gnomebaker_milestone.visible, True)
        gnome_milestone = gnome.getMilestone('1.1')
        self.assertEqual(gnome_milestone.visible, True)

        gnomebaker_milestone.visible = False
        syncUpdate(gnomebaker_milestone)
        gnome_milestone = gnome.getMilestone('1.1')
        self.assertEqual(gnome_milestone.visible, True)

        evolution_milestone.visible = False
        syncUpdate(evolution_milestone)
        gnome_milestone = gnome.getMilestone('1.1')
        self.assertEqual(gnome_milestone.visible, False)

        # Since the milestone 1.1 is now invisible and other milestones
        # do not exist, Project.milestones no longer returns the milestone...
        self.assertEqual(
            [milestone.name for milestone in gnome.milestones], [])

        # ... while project.all_milestones lists invisible milestones too.
        self.assertEqual(
            [milestone.name for milestone in gnome.all_milestones], ['1.1'])

    def test_no_foreign_milestones(self):
        """Milestones in "foreign" products.

        Milestones from products which do not belong to a project are not
        returned by project.milestones and project.all_milestones.
        """
        # firefox does not belong to the Gnome project.
        firefox = getUtility(IProductSet)['firefox']
        self.assertNotEqual(firefox.project.name, 'gnome')

        self.createProductMilestone('1.1', 'firefox', None)
        gnome = getUtility(IProjectSet)['gnome']
        self.assertEqual(list(gnome.all_milestones), [])

    def createSpecification(self, milestone_name, product_name):
        """Create a specification, assigned to a milestone, for a product."""
        specset = getUtility(ISpecificationSet)
        personset = getUtility(IPersonSet)
        sample_person = personset.getByEmail('test@canonical.com')
        product = getUtility(IProductSet)[product_name]

        spec = specset.new(
            name='%s-specification' % product_name,
            title='Title %s specification' % product_name,
            specurl='http://www.example.com/spec/%s' %product_name ,
            summary='summary',
            definition_status=SpecificationDefinitionStatus.APPROVED,
            priority=SpecificationPriority.HIGH,
            owner=sample_person,
            product=product)
        spec.milestone = product.getMilestone(milestone_name)
        syncUpdate(spec)
        return spec

    def test_milestone_specifications(self):
        """Specifications of a project milestone.

        Specifications defined for products and assigned to a milestone
        are also assigned to the milestone of the project.
        """
        self.createProductMilestone('1.1', 'evolution', None)
        self.createProductMilestone('1.1', 'gnomebaker', None)
        self.createProductMilestone('1.1', 'firefox', None)
        self.createSpecification('1.1', 'evolution')
        self.createSpecification('1.1', 'gnomebaker')
        self.createSpecification('1.1', 'firefox')

        gnome_milestone = getUtility(IProjectSet)['gnome'].getMilestone('1.1')
        # The spec for firefox (not a gnome product) is not included
        # in the specifications, while the other two specs are included.
        self.assertEqual(
            [spec.name for spec in gnome_milestone.specifications],
            ['evolution-specification', 'gnomebaker-specification'])

    def _createBugtask(self, product_name, milestone_name):
        """Create a bugtask for a product, assign the task to a milestone."""
        personset = getUtility(IPersonSet)
        sample_person = personset.getByEmail('test@canonical.com')
        product = getUtility(IProductSet)[product_name]
        milestone = product.getMilestone(milestone_name)
        params = CreateBugParams(
            title='Milestone test bug for %s' % product_name,
            comment='comment',
            owner=sample_person,
            status=BugTaskStatus.CONFIRMED)
        bug = product.createBug(params)
        [bugtask] = bug.bugtasks
        bugtask.milestone = milestone
        syncUpdate(bugtask)

    def test_milestone_bugtasks(self):
        """Bugtasks and project milestones.

        Bugtasks assigned to product milestones are also assigned to
        the corresponding project milestone.
        """
        self.createProductMilestone('1.1', 'evolution', None)
        self.createProductMilestone('1.1', 'gnomebaker', None)
        self.createProductMilestone('1.1', 'firefox', None)
        self._createBugtask('evolution', '1.1')
        self._createBugtask('gnomebaker', '1.1')
        self._createBugtask('firefox', '1.1')

        milestone = getUtility(IProjectSet)['gnome'].getMilestone('1.1')
        searchparams = BugTaskSearchParams(user=None, milestone=milestone)
        bugtasks = list(getUtility(IBugTaskSet).search(searchparams))

        # Only the first two bugs created here belong to the gnome project.
        self.assertEqual(
            [bugtask.bug.title for bugtask in bugtasks],
            ['Milestone test bug for evolution',
             'Milestone test bug for gnomebaker'])

    def setUpProjectMilestoneTests(self):
        """Create product milestones for project milestone doctests."""
        self.createProductMilestone('1.1', 'evolution', datetime(2010, 4, 1))
        self.createProductMilestone('1.1', 'gnomebaker', datetime(2010, 4, 2))
        self.createProductMilestone('1.1.', 'netapplet', datetime(2010, 4, 2))

        self.createProductMilestone('1.2', 'evolution', datetime(2011, 4, 1))
        gnomebaker_milestone = self.createProductMilestone(
            '1.2', 'gnomebaker', datetime(2011, 4, 2))
        gnomebaker_milestone.visible = False
        syncUpdate(gnomebaker_milestone)

        evolution_milestone = self.createProductMilestone(
            '1.3', 'evolution', datetime(2012, 4, 1))
        evolution_milestone.visible = False
        gnomebaker_milestone = self.createProductMilestone(
            '1.3', 'gnomebaker', datetime(2012, 4, 2))
        gnomebaker_milestone.visible = False
        syncUpdate(evolution_milestone)
        syncUpdate(gnomebaker_milestone)

        self.createSpecification('1.1', 'evolution')
        self.createSpecification('1.1', 'gnomebaker')

        self._createBugtask('evolution', '1.1')
        self._createBugtask('gnomebaker', '1.1')


def test_suite():
    """Return the test suite for the tests in this module."""
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    unittest.main()
