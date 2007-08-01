# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Project Milestone related test helper."""

__metaclass__ = type

import unittest

from datetime import datetime
from unittest import TestCase
from zope.component import getUtility

from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.interfaces import (BugTaskSearchParams,
    CreateBugParams, IBugSet, IBugTaskSet, IPersonSet, IProductSet,
    IProjectSet, IProjectMilestoneSet, ISpecificationSet)
from canonical.lp.dbschema import (BugTaskStatus, BugTaskImportance,
    SpecificationPriority, SpecificationDefinitionStatus)
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
        if not helper_only:
            unittest.TestCase.__init__(self, methodName)

    def setUpProjectMilestoneTests(self):
        """Add milestones, bugs and specs to products of the Gnome project.
        """
        productset = getUtility(IProductSet)
        evolution = productset['evolution']
        applets = productset['applets']
        gnomebaker = productset['gnomebaker']
        from canonical.launchpad.interfaces import IProjectSet

        milestones = []
        day = 1
        for prod in (evolution, gnomebaker, applets):
            series = prod.getSeries('trunk')
            milestones.append(
                series.newMilestone(
                    name='1.1', dateexpected=datetime(2010, 4, day)))
            day += 1

        day = 1
        for prod in (evolution, gnomebaker):
            series = prod.getSeries('trunk')
            milestones.append(
                series.newMilestone(
                    name='1.2', dateexpected=datetime(2011, 4, day)))
            day += 1
        milestones[-1].visible = False
            
        day = 1
        for prod in (evolution, applets):
            series = prod.getSeries('trunk')
            milestone = series.newMilestone(
                name='1.3', dateexpected=datetime(2012, 4, day))
            milestone.visible = False
            milestones.append(milestone)
            day += 1

        specset = getUtility(ISpecificationSet)
        personset = getUtility(IPersonSet)
        persons = (personset.getByEmail('test@canonical.com'),
                   personset.getByEmail('no-priv@canonical.com'),
                   personset.getByEmail('one-membership@test.com'),
                   personset.getByEmail('foo.bar@canonical.com'))
        spec_status = (SpecificationDefinitionStatus.APPROVED,
                       SpecificationDefinitionStatus.PENDINGAPPROVAL,
                       SpecificationDefinitionStatus.PENDINGREVIEW,
                       SpecificationDefinitionStatus.DRAFT,
                       SpecificationDefinitionStatus.DISCUSSION,
                       SpecificationDefinitionStatus.NEW)
        spec_priority = (SpecificationPriority.LOW,
                         SpecificationPriority.MEDIUM,
                         SpecificationPriority.HIGH,
                         SpecificationPriority.ESSENTIAL)
        bug_status = (BugTaskStatus.CONFIRMED, BugTaskStatus.TRIAGED,
                  BugTaskStatus.INPROGRESS, BugTaskStatus.INCOMPLETE,
                  BugTaskStatus.FIXCOMMITTED, BugTaskStatus.FIXRELEASED)
        bug_importance = (BugTaskImportance.LOW, BugTaskImportance.MEDIUM,
                      BugTaskImportance.HIGH, BugTaskImportance.CRITICAL,
                      BugTaskImportance.WISHLIST)
        
        owner = personset.getByEmail('test@canonical.com')
        bugset = getUtility(IBugSet)
        attr_index = 0
        for milestone in milestones:
            for bug_no in range(2):
                spec_name = ('test-spec-%i-%s'
                             %(attr_index, milestone.product.name))
                spec_title = ('Test specification %i for %s'
                              % (attr_index, milestone.product.name))
                spec_url = ('http://www.example.com/project_spec/%i'
                            % attr_index)
                spec = specset.new(
                    name = spec_name,
                    title = spec_title,
                    specurl = spec_url,
                    summary = 'summary',
                    definition_status =
                        spec_status[attr_index % len(spec_status)],
                    priority = spec_priority[attr_index % len(spec_priority)],
                    owner = persons[attr_index % len(persons)],
                    assignee = persons[(attr_index + 1) % len(persons)],
                    product = milestone.product)
                spec.milestone = milestone

                bug_title = ('Milestone test bug %i for %s'
                             % (bug_no, milestone.product.name))
                params = CreateBugParams(
                    title=bug_title, comment='no comment', owner=owner,
                    status=bug_status[attr_index % len(bug_status)])
                params.setBugTarget(product = milestone.product)
                bug = bugset.createBug(params)
                task = bug.bugtasks[0]
                task.milestone = milestone
                task.transitionToAssignee(persons[attr_index % len(persons)])
                task.importance = bug_importance[
                    attr_index % len(bug_importance)]
                attr_index += 1

        # Another milestone with a deliberate typo in its name.
        netapplet = productset['netapplet']
        series = netapplet.getSeries('trunk')
        milestone = series.newMilestone(
            name='1.1.', dateexpected=datetime(2010, 4, 2))
        spec = specset.new(
            name = 'test-spec-netapplet',
            title = 'Test specification 1 for netapplet',
            specurl = 'http://www.example.com/project_spec/netapplet',
            summary = 'summary',
            definition_status = SpecificationDefinitionStatus.APPROVED,
            priority = SpecificationPriority.MEDIUM,
            owner = persons[0],
            product = milestone.product)
        spec.milestone = milestone

        params = CreateBugParams(
            title='test bug for netapplet', comment='no comment', owner=owner,
            status=BugTaskStatus.INPROGRESS)
        params.setBugTarget(product = milestone.product)
        bug = bugset.createBug(params)
        task = bug.bugtasks[0]
        task.milestone = milestone
        task.transitionToAssignee(owner)
        task.importance = BugTaskImportance.HIGH

        # A milestone for a product in another project.
        firefox = productset['firefox']
        series = firefox.getSeries('trunk')
        milestone = series.newMilestone(
            name='1.1', dateexpected=datetime(2010, 4, 2))
        spec = specset.new(
            name = 'test-spec-firefox',
            title = 'Test specification 1 for firefox',
            specurl = 'http://www.example.com/project_spec/firefox',
            summary = 'summary',
            definition_status = SpecificationDefinitionStatus.APPROVED,
            priority = SpecificationPriority.MEDIUM,
            owner = persons[0],
            product = milestone.product)
        spec.milestone = milestone

        params = CreateBugParams(
            title='test bug for firefox', comment='no comment', owner=owner,
            status=BugTaskStatus.INPROGRESS)
        params.setBugTarget(product = milestone.product)
        bug = bugset.createBug(params)
        task = bug.bugtasks[0]
        task.milestone = milestone
        task.transitionToAssignee(owner)
        task.importance = BugTaskImportance.HIGH

        flush_database_updates()

    def setUp(self):
        login('foo.bar@canonical.com')
        self.setUpProjectMilestoneTests()

    def test_milestone(self):
        projectset = getUtility(IProjectSet)
        gnome = projectset['gnome']
        # Four milestones are defined for the Gnome project, but only three
        # are visible. The method all_milestones returns all of them, while
        # the method milestones returns only the visible ones.
        self.assertEqual(len(gnome.all_milestones), 4)
        self.assertEqual(len(gnome.milestones), 3)

        # All specifications and bugtasks related to these milestones are
        # filed for products from the Gnome project.
        for milestone in gnome.all_milestones:
            for spec in milestone.specifications:
                self.assertEqual(spec.product.project, gnome)
            params = BugTaskSearchParams(None, milestone=milestone)
            for bugtask in getUtility(IBugTaskSet).search(params):
                self.assertEqual(bugtask.product.project, gnome)

        # Milestone 1.1 is defined for four products, but only three of
        # them belong to the Gnome project.
        project_milestone_set = getUtility(IProjectMilestoneSet)
        milestones = project_milestone_set.getMilestonesForProject(
            gnome, only_visible=False, milestone_name='1.1')
        milestone_1_1 = milestones[0]
        for spec in milestones[0].specifications:
            self.assertEqual(spec.product.project, gnome)

        # When a milestone name is specified, the number of milestones
        # returned by getMilestonesForProject must be zero or one.
        self.assertEqual(len(milestones), 1)
        no_milestones = project_milestone_set.getMilestonesForProject(
            gnome, only_visible=False, milestone_name='does not exist')
        self.assertEqual(len(no_milestones), 0)

        # The attribute `dateexpected` of a milestone is set to the minimum
        # of the `dateexpected` values of the product milestones.
        self.assertEqual(milestone_1_1.dateexpected, datetime(2010, 4, 1))

        # Milestones 1.1 and 1.2 are visible, because at least one of the
        # related product milestones is visible, while milestone 1.3
        # has no visible product milestones and is thus not visible.
        for name, num_expected in (('1.1', 1), ('1.2', 1), ('1.3', 0)):
            milestones = project_milestone_set.getMilestonesForProject(
                gnome, only_visible=True, milestone_name=name)
            self.assertEqual(len(milestones), num_expected)

        # Project.all_milestones returns all milestones, while
        # Project.milestones returns only visible milestones.
        visible_milestones = gnome.milestones
        all_milestones = gnome.all_milestones
        for milestone in visible_milestones:
            self.assertEqual(milestone.visible, True)

        # The milestones returned by Project.all_milestones but not by
        # Project.milestones are invisible.
        visible_names = set(milestone.name for milestone in visible_milestones)
        for milestone in all_milestones:
            if milestone.name not in visible_names:
                self.assertEqual(milestone.visible, False)

        # All milestones returned by Project.milestones are also returned
        # by Project.all_milestones
        all_names = set(milestone.name for milestone in all_milestones)
        self.assertEqual(visible_names.issubset(all_names), True)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

if __name__ == '__main__':
    unittest.main()
