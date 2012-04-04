# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
from operator import attrgetter

from zope.security.proxy import removeSecurityProxy

from lp.blueprints.enums import SpecificationWorkItemStatus
from lp.registry.browser.team import (
    GenericWorkItem,
    getWorkItemsDueBefore,
    WorkItemContainer,
    )
from lp.testing import (
    anonymous_logged_in,
    BrowserTestCase,
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.pages import (
    extract_text,
    find_tag_by_id,
    find_tags_by_class,
    )
from lp.testing.views import create_initialized_view


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
        self.assertEqual(bugtask, bugtask_container.items[0].actual_workitem)

        self.assertEqual(1, len(workitem_container.items))
        self.assertEqual(
            workitem, workitem_container.items[0].actual_workitem)

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
        self.assertEqual(workitem, container.items[0].actual_workitem)

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
        self.assertEqual(current_wi, container.items[0].actual_workitem)


class TestGenericWorkItem(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGenericWorkItem, self).setUp()
        today = datetime.today().date()
        self.milestone = self.factory.makeMilestone(dateexpected=today)

    def test_from_bugtask(self):
        bugtask = self.factory.makeBug(milestone=self.milestone).bugtasks[0]
        workitem = GenericWorkItem.from_bugtask(bugtask)
        self.assertEqual(workitem.assignee, bugtask.assignee)
        self.assertEqual(workitem.status, bugtask.status)
        self.assertEqual(workitem.priority, bugtask.importance)
        self.assertEqual(workitem.target, bugtask.target)
        self.assertEqual(workitem.title, bugtask.bug.description)
        self.assertEqual(workitem.actual_workitem, bugtask)

    def test_from_workitem(self):
        workitem = self.factory.makeSpecificationWorkItem(
            milestone=self.milestone)
        generic_wi = GenericWorkItem.from_workitem(workitem)
        self.assertEqual(generic_wi.assignee, workitem.assignee)
        self.assertEqual(generic_wi.status, workitem.status)
        self.assertEqual(generic_wi.priority, workitem.specification.priority)
        self.assertEqual(generic_wi.target, workitem.specification.target)
        self.assertEqual(generic_wi.title, workitem.title)
        self.assertEqual(generic_wi.actual_workitem, workitem)


class TestWorkItemContainer(TestCase):

    class MockWorkItem:

        def __init__(self, is_complete):
            self.is_complete = is_complete

    def test_percent_done(self):
        container = WorkItemContainer()
        container.append(self.MockWorkItem(True))
        container.append(self.MockWorkItem(False))
        container.append(self.MockWorkItem(True))
        self.assertEqual('67', container.percent_done)


class TestTeamUpcomingWork(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestTeamUpcomingWork, self).setUp()
        self.today = datetime.today().date()
        self.tomorrow = self.today + timedelta(days=1)
        self.today_milestone = self.factory.makeMilestone(
            dateexpected=self.today)
        self.tomorrow_milestone = self.factory.makeMilestone(
            dateexpected=self.tomorrow)
        self.team = self.factory.makeTeam()

    def test_basic(self):
        workitem1 = self.factory.makeSpecificationWorkItem(
            assignee=self.team.teamowner, milestone=self.today_milestone)
        workitem2 = self.factory.makeSpecificationWorkItem(
            assignee=self.team.teamowner, milestone=self.tomorrow_milestone)
        bugtask1 = self.factory.makeBug(
            milestone=self.today_milestone).bugtasks[0]
        bugtask2 = self.factory.makeBug(
            milestone=self.tomorrow_milestone).bugtasks[0]
        for bugtask in [bugtask1, bugtask2]:
            removeSecurityProxy(bugtask).assignee = self.team.teamowner

        browser = self.getViewBrowser(
            self.team, view_name='+upcomingwork', no_login=True)

        groups = find_tags_by_class(browser.contents, 'workitems-group')
        self.assertEqual(2, len(groups))
        todays_group = extract_text(groups[0])
        tomorrows_group = extract_text(groups[1])
        self.assertStartsWith(
            todays_group, 'Work items due in %s' % self.today)
        self.assertIn(workitem1.title, todays_group)
        with anonymous_logged_in():
            self.assertIn(bugtask1.bug.title, todays_group)

        self.assertStartsWith(
            tomorrows_group, 'Work items due in %s' % self.tomorrow)
        self.assertIn(workitem2.title, tomorrows_group)
        with anonymous_logged_in():
            self.assertIn(bugtask2.bug.title, tomorrows_group)

    def test_overall_progressbar(self):
        self.factory.makeSpecificationWorkItem(
            assignee=self.team.teamowner, milestone=self.today_milestone,
            status=SpecificationWorkItemStatus.DONE)
        self.factory.makeSpecificationWorkItem(
            assignee=self.team.teamowner, milestone=self.today_milestone,
            status=SpecificationWorkItemStatus.INPROGRESS)

        browser = self.getViewBrowser(
            self.team, view_name='+upcomingwork', no_login=True)

        progressbar = find_tag_by_id(browser.contents, 'progressbar_0')
        self.assertEqual('50%', progressbar.get('width'))

    def test_container_progressbar(self):
        self.factory.makeSpecificationWorkItem(
            assignee=self.team.teamowner, milestone=self.today_milestone,
            status=SpecificationWorkItemStatus.DONE)
        self.factory.makeSpecificationWorkItem(
            assignee=self.team.teamowner, milestone=self.today_milestone,
            status=SpecificationWorkItemStatus.TODO)

        browser = self.getViewBrowser(
            self.team, view_name='+upcomingwork', no_login=True)

        container1_progressbar = find_tag_by_id(
            browser.contents, 'container_progressbar_0')
        container2_progressbar = find_tag_by_id(
            browser.contents, 'container_progressbar_1')
        self.assertEqual('100%', container1_progressbar.get('width'))
        self.assertEqual('0%', container2_progressbar.get('width'))


class TestTeamUpcomingWorkView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestTeamUpcomingWorkView, self).setUp()
        self.today = datetime.today().date()
        self.tomorrow = self.today + timedelta(days=1)
        self.today_milestone = self.factory.makeMilestone(
            dateexpected=self.today)
        self.tomorrow_milestone = self.factory.makeMilestone(
            dateexpected=self.tomorrow)
        self.team = self.factory.makeTeam()

    def test_workitem_counts(self):
        self.factory.makeSpecificationWorkItem(
            assignee=self.team.teamowner, milestone=self.today_milestone)
        self.factory.makeSpecificationWorkItem(
            assignee=self.team.teamowner, milestone=self.today_milestone)
        self.factory.makeSpecificationWorkItem(
            assignee=self.team.teamowner, milestone=self.tomorrow_milestone)

        view = create_initialized_view(self.team, '+upcomingwork')
        self.assertEqual(2, view.workitem_counts[self.today])
        self.assertEqual(1, view.workitem_counts[self.tomorrow])

    def test_bugtask_counts(self):
        bugtask1 = self.factory.makeBug(
            milestone=self.today_milestone).bugtasks[0]
        bugtask2 = self.factory.makeBug(
            milestone=self.tomorrow_milestone).bugtasks[0]
        bugtask3 = self.factory.makeBug(
            milestone=self.tomorrow_milestone).bugtasks[0]
        for bugtask in [bugtask1, bugtask2, bugtask3]:
            removeSecurityProxy(bugtask).assignee = self.team.teamowner

        view = create_initialized_view(self.team, '+upcomingwork')
        self.assertEqual(1, view.bugtask_counts[self.today])
        self.assertEqual(2, view.bugtask_counts[self.tomorrow])

    def test_milestones_per_date(self):
        another_milestone_due_today = self.factory.makeMilestone(
            dateexpected=self.today)
        self.factory.makeSpecificationWorkItem(
            assignee=self.team.teamowner, milestone=self.today_milestone)
        self.factory.makeSpecificationWorkItem(
            assignee=self.team.teamowner,
            milestone=another_milestone_due_today)
        self.factory.makeSpecificationWorkItem(
            assignee=self.team.teamowner, milestone=self.tomorrow_milestone)

        view = create_initialized_view(self.team, '+upcomingwork')
        self.assertEqual(
            sorted([self.today_milestone, another_milestone_due_today],
                   key=attrgetter('displayname')),
            view.milestones_per_date[self.today])
        self.assertEqual(
            [self.tomorrow_milestone],
            view.milestones_per_date[self.tomorrow])

    def test_work_item_containers_are_sorted_by_date(self):
        self.factory.makeSpecificationWorkItem(
            assignee=self.team.teamowner, milestone=self.today_milestone)
        self.factory.makeSpecificationWorkItem(
            assignee=self.team.teamowner, milestone=self.tomorrow_milestone)

        view = create_initialized_view(self.team, '+upcomingwork')
        self.assertEqual(2, len(view.work_item_containers))
        self.assertEqual(
            [self.today, self.tomorrow],
            [date for date, containers in view.work_item_containers])
