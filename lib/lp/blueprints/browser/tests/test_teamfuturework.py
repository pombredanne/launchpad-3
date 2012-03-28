# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import datetime

from zope.security.proxy import removeSecurityProxy

from lp.blueprints.browser.teamfuturework import (
    getWorkItemsDueBefore,
    TeamFutureWorkView,
    WorkItemContainer,
    )

from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


# XXX: This should probably be moved somewhere else, together with
# browser/teamfuturework.py
class Test_getWorkItemsDueBefore(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(Test_getWorkItemsDueBefore, self).setUp()
        self.today = datetime.today().date()
        current_milestone = self.factory.makeMilestone(
            dateexpected=self.today)
        self.current_milestone = current_milestone
        self.future_milestone = self.factory.makeMilestone(
            product=current_milestone.product,
            dateexpected=datetime(2060, 1, 1))
        self.team = self.factory.makeTeam()

    def test_basic(self):
        spec = self.factory.makeSpecification(
            product=self.current_milestone.product,
            assignee=self.team.teamowner, milestone=self.current_milestone)
        workitem = self.factory.makeSpecificationWorkItem(
            title=u'workitem 1', specification=spec)
        bugtask = self.factory.makeBug(
            milestone=self.current_milestone).bugtasks[0]
        removeSecurityProxy(bugtask).assignee = self.team.teamowner

        workitems = getWorkItemsDueBefore(
            self.team, self.current_milestone.dateexpected, user=None)

        self.assertEqual(
            [self.current_milestone.dateexpected], workitems.keys())
        containers = workitems[self.current_milestone.dateexpected]
        # We have one container for the work item from the spec and another
        # one for the bugtask.
        self.assertEqual(2, len(containers))
        [workitem_container, bugtask_container] = containers

        self.assertEqual(1, len(bugtask_container.items))
        self.assertEqual(bugtask.title, bugtask_container.items[0].title)
        self.assertFalse(bugtask_container.is_foreign)
        self.assertFalse(bugtask_container.is_future)

        self.assertEqual(1, len(workitem_container.items))
        self.assertEqual(workitem.title, workitem_container.items[0].title)
        self.assertFalse(workitem_container.is_foreign)
        self.assertFalse(workitem_container.is_future)

    def test_foreign_container(self):
        # This spec is targeted to a person who's not a member of our team, so
        # only those workitems that are explicitly assigned to a member of our
        # team will be returned.
        spec = self.factory.makeSpecification(
            product=self.current_milestone.product,
            milestone=self.current_milestone,
            assignee=self.factory.makePerson())
        self.factory.makeSpecificationWorkItem(
            title=u'workitem 1', specification=spec)
        workitem = self.factory.makeSpecificationWorkItem(
            title=u'workitem 2', specification=spec,
            assignee=self.team.teamowner)

        workitems = getWorkItemsDueBefore(
            self.team, self.current_milestone.dateexpected, user=None)

        self.assertEqual(
            [self.current_milestone.dateexpected], workitems.keys())
        containers = workitems[self.current_milestone.dateexpected]
        self.assertEqual(1, len(containers))
        [container] = containers
        self.assertEqual(1, len(container.items))
        self.assertEqual(workitem.title, container.items[0].title)
        self.assertTrue(container.is_foreign)

    def test_future_container(self):
        spec = self.factory.makeSpecification(
            product=self.current_milestone.product,
            assignee=self.team.teamowner)
        # This workitem is targeted to a future milestone so it won't be in
        # our results below.
        self.factory.makeSpecificationWorkItem(
            title=u'workitem 1', specification=spec,
            milestone=self.future_milestone)
        current_wi = self.factory.makeSpecificationWorkItem(
            title=u'workitem 2', specification=spec,
            milestone=self.current_milestone)

        workitems = getWorkItemsDueBefore(
            self.team, self.current_milestone.dateexpected, user=None)

        self.assertEqual(
            [self.current_milestone.dateexpected], workitems.keys())
        containers = workitems[self.current_milestone.dateexpected]
        self.assertEqual(1, len(containers))
        [container] = containers
        self.assertEqual(1, len(container.items))
        self.assertEqual(current_wi.title, container.items[0].title)
        self.assertTrue(container.is_future)

class TestWorkItemContainer(TestCase):

    class MockWorkItem:

        def __init__(self, is_done=False):
            self._is_done = is_done

        @property
        def is_done(self):
            return self._is_done

    def test_progress_bar(self):
        container = WorkItemContainer(None, None, None, None, None)
        container.append(self.MockWorkItem(True))
        container.append(self.MockWorkItem(False))
        container.append(self.MockWorkItem(True))
        container.append(self.MockWorkItem(True))
        self.assertIn('width:75.0%', container.progress_bar)

    def test_percent_done(self):
        container = WorkItemContainer(None, None, None, None, None)
        container.append(self.MockWorkItem(True))
        container.append(self.MockWorkItem(False))
        container.append(self.MockWorkItem(True))
        self.assertEqual(container.percent_done, 100.0*2/3)
        container.append(self.MockWorkItem(True))
        self.assertEqual(container.percent_done, 100.0*3/4)
        container.append(self.MockWorkItem(False))
        self.assertEqual(container.percent_done, 100.0*3/5)

class TestTeamFutureWorkView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestTeamFutureWorkView, self).setUp()
        self.today = datetime.today().date()
        current_milestone = self.factory.makeMilestone(
            dateexpected=self.today)
        self.current_milestone = current_milestone
        self.team = self.factory.makeTeam()

    def test_wanted_date(self):
        view = TeamFutureWorkView(None, None)
        delta = view.wanted_date - datetime.today()
        # The delta will be DELTA days minus a few milliseconds.
        self.assertEqual(delta.days, view.DELTA - 1)

    def test_completion(self):
        spec = self.factory.makeSpecification(
            product=self.current_milestone.product,
            assignee=self.team.teamowner, milestone=self.current_milestone)
        workitem = self.factory.makeSpecificationWorkItem(
            title=u'workitem 1', specification=spec)
        bugtask = self.factory.makeBug(
            milestone=self.current_milestone).bugtasks[0]
        removeSecurityProxy(bugtask).assignee = self.team.teamowner

        view = TeamFutureWorkView(self.team, None)
        n_blueprints, n_workitems, n_done = view.overall_completion()
        # The bugtask container is also a "blueprint" in this sense.
        self.assertEqual(n_blueprints, 2)
        # The bugtask is a work item.
        self.assertEqual(n_workitems, 2)
        self.assertEqual(n_done, 0)
