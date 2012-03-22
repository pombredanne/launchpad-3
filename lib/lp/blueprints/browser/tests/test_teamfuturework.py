# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )

from testtools.matchers import (
    LessThan,
    )
from zope.security.proxy import removeSecurityProxy

from lp.blueprints.browser.teamfuturework import getWorkItemsDueBefore
from lp.blueprints.enums import SpecificationPriority
from lp.registry.model.distributionsourcepackage import (
    DistributionSourcePackage,
    )
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.productseries import ProductSeries
from lp.registry.model.sourcepackage import SourcePackage
from lp.services.database.sqlbase import flush_database_caches
from lp.services.webapp.publisher import canonical_url

from lp.testing import (
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount


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

    def test_skips_private_bugs_the_user_is_not_allowed_to_see(self):
        private_bug = removeSecurityProxy(
            self.factory.makeBug(
                milestone=self.current_milestone, private=True))
        private_bug.bugtasks[0].assignee = self.team.teamowner
        private_bug2 = removeSecurityProxy(
            self.factory.makeBug(
                milestone=self.current_milestone, private=True))
        private_bug2.bugtasks[0].assignee = self.team.teamowner

        # Now we do a search as the owner of private_bug2 and since the owner
        # of that bug has no rights to see private_bug, the return value
        # contains only private_bug2.
        with person_logged_in(self.team.teamowner):
            workitems = getWorkItemsDueBefore(
                self.team, self.today + timedelta(days=1),
                user=private_bug2.owner)

        items = []
        for containers in workitems.values():
            for container in containers:
                items.extend([item for item in container.items])
        self.assertEqual(1, len(items))
        self.assertEqual(private_bug2.bugtasks[0].title, items[0].title)

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

    def test_query_counts(self):
        self._createWorkItems()
        dateexpected = self.current_milestone.dateexpected
        flush_database_caches()
        with StormStatementRecorder() as recorder:
            containers = getWorkItemsDueBefore(
                self.team, dateexpected, user=None)
        # 1. One query to get all team members;
        # 2. One to get all SpecWorkItems;
        # 3. One to get all BugTasks.
        # 4. And one to get the current series of a distribution
        #    (Distribution.currentseries) to decide whether or not the bug is
        #    part of a conjoined relationship. The code that executes this
        #    query runs for every distroseriespackage bugtask but since
        #    .currentseries is a cached property and there's a single
        #    distribution with bugs in production, this will not cause an
        #    extra DB query every time it runs.
        self.assertThat(recorder, HasQueryCount(LessThan(5)))

        with StormStatementRecorder() as recorder:
            for date, containers in containers.items():
                for container in containers:
                    for item in container.items:
                        item.assignee
                        canonical_url(item.assignee)
                        item.status
                        item.priority
                        canonical_url(item.target)
        self.assertThat(recorder, HasQueryCount(LessThan(1)))

    def _createWorkItems(self):
        """Create a bunch of SpecificationWorkItems and BugTasks.

        BE CAREFUL! Using this will make your tests hard to follow because it
        creates a lot of objects and it is not trivial to check that they're
        all returned by getWorkItemsDueBefore() because the objects created
        here are burried two levels deep on the hierarchy returned there.

        This is meant to be used in a test that checks the number of DB
        queries issued by getWorkItemsDueBefore() does not grow according to
        the number of returned objects.
        """
        team = self.team
        current_milestone = self.current_milestone
        future_milestone = self.future_milestone

        # Create a spec assigned to a member of our team and targeted to the
        # current milestone. Also creates a workitem with no explicit
        # assignee/milestone.
        assigned_spec = self.factory.makeSpecification(
            assignee=team.teamowner, milestone=current_milestone,
            product=current_milestone.product)
        self.factory.makeSpecificationWorkItem(
            title=u'workitem_from_assigned_spec', specification=assigned_spec)

        # Create a spec assigned to a member of our team but targeted to a
        # future milestone, together with a workitem targeted to the current
        # milestone.
        future_spec = self.factory.makeSpecification(
            milestone=future_milestone, product=future_milestone.product,
            priority=SpecificationPriority.HIGH, assignee=team.teamowner)
        self.factory.makeSpecificationWorkItem(
            title=u'workitem_from_future_spec assigned to team member',
            specification=future_spec, milestone=current_milestone)

        # Create a spec assigned to nobody and targeted to the current
        # milestone, together with a workitem explicitly assigned to a member
        # of our team.
        foreign_spec = self.factory.makeSpecification(
            milestone=current_milestone, product=current_milestone.product)
        self.factory.makeSpecificationWorkItem(
            title=u'workitem_from_foreign_spec assigned to team member',
            specification=foreign_spec, assignee=team.teamowner)

        # Create a bug targeted to the current milestone and assign it to a
        # member of our team.
        bugtask = self.factory.makeBug(
            milestone=current_milestone).bugtasks[0]
        removeSecurityProxy(bugtask).assignee = team.teamowner

        # Create a BugTask whose target is a ProductSeries
        bugtask2 = self.factory.makeBug(
            series=current_milestone.productseries).bugtasks[1]
        self.assertIsInstance(bugtask2.target, ProductSeries)
        removeSecurityProxy(bugtask2).assignee = team.teamowner
        removeSecurityProxy(bugtask2).milestone = current_milestone

        # Create a BugTask whose target is a DistroSeries
        current_distro_milestone = self.factory.makeMilestone(
            distribution=self.factory.makeDistribution(),
            dateexpected=self.today)
        bugtask3 = self.factory.makeBug(
            series=current_distro_milestone.distroseries).bugtasks[1]
        self.assertIsInstance(bugtask3.target, DistroSeries)
        removeSecurityProxy(bugtask3).assignee = team.teamowner
        removeSecurityProxy(bugtask3).milestone = current_distro_milestone

        # Create a bug with two conjoined BugTasks whose target is a
        # SourcePackage.
        distroseries = current_distro_milestone.distroseries
        sourcepackagename = self.factory.makeSourcePackageName()
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=distroseries, sourcepackagename=sourcepackagename)
        bug = self.factory.makeBug(
            milestone=current_distro_milestone,
            sourcepackagename=sourcepackagename,
            distribution=distroseries.distribution)
        slave_task = bug.bugtasks[0]
        package = distroseries.getSourcePackage(sourcepackagename.name)
        master_task = removeSecurityProxy(bug).addTask(bug.owner, package)
        self.assertIsInstance(master_task.target, SourcePackage)
        self.assertIsInstance(slave_task.target, DistributionSourcePackage)
        removeSecurityProxy(master_task).assignee = team.teamowner
        removeSecurityProxy(master_task).milestone = current_distro_milestone
