# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Project Milestone related test helper."""

__metaclass__ = type

import unittest

from datetime import datetime
from zope.component import getUtility

from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.interfaces import (BugTaskSearchParams,
    CreateBugParams, IBugSet, IBugTaskSet, IPersonSet, IProductSet,
    IProjectSet, ISpecificationSet)
from canonical.lp.dbschema import (BugTaskStatus, SpecificationPriority,
    SpecificationDefinitionStatus)
from canonical.launchpad.ftests import login
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
        self.milestones = {}
        if not helper_only:
            unittest.TestCase.__init__(self, methodName)

    def setUp(self):
        login('foo.bar@canonical.com')

    def _createProductMilestone(
        self, milestone_name, product_name, date_expected):
        """ Create a milestone in a product."""
        product_set = getUtility(IProductSet)
        product = product_set[product_name]
        series = product.getSeries('trunk')
        if self.milestones.has_key(product_name):
            self.milestones[product_name][milestone_name] = (
                series.newMilestone(
                    name=milestone_name, dateexpected=date_expected))
        else:self.milestones[product_name] = {
            milestone_name: series.newMilestone(
                name=milestone_name, dateexpected=date_expected)}
            

    def milestoneNameDateExpected(self):
        """A project milestone has the same name as a product milestone.
        if this product is part of the project."""
        self._createProductMilestone('1.1', 'evolution', datetime(2010, 4, 2))
        self._createProductMilestone('1.1', 'gnomebaker', datetime(2010, 4, 1))

        # There is only one project milestone named '1.1', regardless of the
        # number of product milestones with this name.
        # Since the default test data does not define any milestones for
        # products of the Gnome project, we have now one milestone.
        project = getUtility(IProjectSet)['gnome']
        milestones = project.milestones
        all_milestones = project.all_milestones
        self.assertEqual(len(milestones), 1)
        self.assertEqual(len(all_milestones), 1)
        self.assertEqual(milestones[0].name, '1.1')
        self.assertEqual(all_milestones[0].name, '1.1')

        # The dateexpected attribute of a milestone is set to the minimum
        # of the the dateexpected attributes of the product milestones.
        self.assertEqual(milestones[0].dateexpected, datetime(2010, 4, 1))

        # project.getMilestone returns either a project milestone, or
        # or None, if no milestone of the given name exists.
        milestone = project.getMilestone('1.1')
        self.assertEqual(milestone.name, '1.1')
        self.assertEqual(project.getMilestone('invalid'), None)

    def milestoneVisibility(self):
        """A project milestone is visible, if at least one product milestone
        is visible."""
        # the default state of a product milestone is 'visible', hence
        # the project milestone is visible too.
        project = getUtility(IProjectSet)['gnome']
        milestone = project.getMilestone('1.1')
        self.assertEqual(milestone.visible, 1)

        self.milestones['gnomebaker']['1.1'].visible = False
        flush_database_updates()
        milestone = project.getMilestone('1.1')
        self.assertEqual(milestone.visible, 1)

        self.milestones['evolution']['1.1'].visible = False
        flush_database_updates()
        milestone = project.getMilestone('1.1')
        self.assertEqual(milestone.visible, 0)

        # Since the milestone is no invisible, Project.milestones no
        # longer returns the milestone.
        self.assertEqual(len(project.milestones), 0)

        # Project.all_milestones lists invisible milestones too
        self.assertEqual(len(project.all_milestones), 1)
        
    def noForeignMilestones(self):
        """Milestones from products which do not belong to "our" project
        are not returned by project.milestones and project.all_milestones.
        """
        # firefox does not belong to the Gnome project.
        self._createProductMilestone('1.1', 'firefox', datetime(2020, 4, 3))
        project = getUtility(IProjectSet)['gnome']
        for milestone in project.all_milestones:
            self.assertNotEqual(milestone.target.name, 'firefox')

    def _createSpecification(self, product_name, milestone_name):
        specset = getUtility(ISpecificationSet)
        personset = getUtility(IPersonSet)
        sample_person = personset.getByEmail('test@canonical.com')
        product = self.milestones[product_name][milestone_name].product

        spec = specset.new(
            name = '%s-specification' % product_name,
            title = 'Title %s specification' % product_name,
            specurl = 'http://www.example.com/spec/%s' %product_name ,
            summary = 'summary',
            definition_status = SpecificationDefinitionStatus.APPROVED,
            priority = SpecificationPriority.HIGH,
            owner = sample_person,
            product = product)
        spec.milestone = self.milestones[product_name][milestone_name]

        project = getUtility(IProjectSet)['gnome']
        milestone = project.getMilestone('1.1')
        flush_database_updates()

    def milestoneSpecifications(self):
        """Specifications defined for products and assigned to a milestone
        are also assigned to the milestone of the project.
        """
        self._createSpecification('evolution', '1.1')
        self._createSpecification('gnomebaker', '1.1')
        self._createSpecification('firefox', '1.1')

        milestone = getUtility(IProjectSet)['gnome'].getMilestone('1.1')
        specs = list(milestone.specifications)
        # The spec for firefox (not a gnome product) is not included
        # in the specifications, while the other two specs are included.
        self.assertEqual(len(specs), 2)
        self.assertEqual(specs[0].name, 'evolution-specification')
        self.assertEqual(specs[1].name, 'gnomebaker-specification')

    def _createBugtask(self, product_name, milestone_name):
        personset = getUtility(IPersonSet)
        sample_person = personset.getByEmail('test@canonical.com')
        milestone = self.milestones[product_name][milestone_name]
        params = CreateBugParams(
            title = 'Milestone test bug for %s' % product_name,
            comment = 'comment',
            owner = sample_person,
            status = BugTaskStatus.CONFIRMED)
        params.setBugTarget(product = milestone.product)
        bug = getUtility(IBugSet).createBug(params)
        bugtask = bug.bugtasks[0]
        bugtask.milestone = milestone
        flush_database_updates()

    def milestoneBugtasks(self):
        """Bugtasks assigned to product milestones are also assigned to
        the corresponding project milestone.
        """
        self._createBugtask('evolution', '1.1')
        self._createBugtask('gnomebaker', '1.1')
        self._createBugtask('firefox', '1.1')

        milestone = getUtility(IProjectSet)['gnome'].getMilestone('1.1')
        searchparams = BugTaskSearchParams(user=None, milestone=milestone)
        bugtasks = list(getUtility(IBugTaskSet).search(searchparams))

        # Only the first two bugs created here belong to the gnome project.
        self.assertEqual(len(bugtasks), 2)
        self.assertEqual(
            bugtasks[0].bug.title, 'Milestone test bug for evolution')
        self.assertEqual(
            bugtasks[1].bug.title, 'Milestone test bug for gnomebaker')
 
    def test_milestone(self):
        self.milestoneNameDateExpected()
        self.milestoneVisibility()
        self.noForeignMilestones()
        self.milestoneSpecifications()
        self.milestoneBugtasks()

    def setUpProjectMilestoneTests(self):
        """Create product milestones for project milestone doctests
        """
        self._createProductMilestone('1.1', 'evolution', datetime(2010, 4, 1))
        self._createProductMilestone('1.1', 'gnomebaker', datetime(2010, 4, 2))

        self._createProductMilestone('1.1.', 'netapplet', datetime(2010, 4, 2))

        self._createProductMilestone('1.2', 'evolution', datetime(2011, 4, 1))
        self._createProductMilestone('1.2', 'gnomebaker', datetime(2011, 4, 2))
        self.milestones['gnomebaker']['1.2'].visible = False

        self._createProductMilestone('1.3', 'evolution', datetime(2012, 4, 1))
        self._createProductMilestone('1.3', 'gnomebaker', datetime(2012, 4, 2))
        self.milestones['evolution']['1.3'].visible = False
        self.milestones['gnomebaker']['1.3'].visible = False

        self._createSpecification('evolution', '1.1')
        self._createSpecification('gnomebaker', '1.1')

        self._createBugtask('evolution', '1.1')
        self._createBugtask('gnomebaker', '1.1')

        flush_database_updates()

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

if __name__ == '__main__':
    unittest.main()
