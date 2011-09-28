# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for bug nomination views."""

__metaclass__ = type

from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.webapp.interaction import get_current_principal
from canonical.launchpad.webapp.interfaces import (
    BrowserNotificationLevel,
    ILaunchBag,
    )
from canonical.launchpad.webapp.publisher import canonical_url
from lp.registry.interfaces.series import SeriesStatus
from lp.testing import (
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.matchers import Contains
from lp.testing.views import create_initialized_view


class TestBugNominationView(TestCaseWithFactory):
    """Tests for BugNominationView."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugNominationView, self).setUp()
        self.distribution = self.factory.makeDistribution()
        owner = self.distribution.owner
        bug_team = self.factory.makeTeam(owner=owner)
        self.bug_worker = self.factory.makePerson()
        with person_logged_in(owner):
            bug_team.addMember(self.bug_worker, owner)
            self.distribution.setBugSupervisor(bug_team, owner)
            self.distribution.driver = self.factory.makePerson()
        self.bug_task = self.factory.makeBugTask(target=self.distribution)
        launchbag = getUtility(ILaunchBag)
        launchbag.add(self.distribution)
        launchbag.add(self.bug_task)

    def test_submit_action_bug_supervisor(self):
        # A bug supervisor sees the Nominate action label.
        login_person(self.bug_worker)
        view = create_initialized_view(self.bug_task, name='+nominate')
        action = view.__class__.actions.byname['actions.submit']
        self.assertEqual('Nominate', action.label)

    def test_submit_action_driver(self):
        # A driver sees the Target action label.
        login_person(self.distribution.driver)
        view = create_initialized_view(self.bug_task, name='+nominate')
        action = view.__class__.actions.byname['actions.submit']
        self.assertEqual('Target', action.label)

    def test_submit_action_unauthorised(self):
        # An unauthorised user sees an error on the bug target page.
        login_person(None)
        view = create_initialized_view(self.bug_task, name='+nominate')
        self.assertEqual(
            canonical_url(self.bug_task),
            view.request.response.getHeader('Location'))
        notifications = view.request.notifications
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            BrowserNotificationLevel.ERROR, notifications[0].level)
        self.assertEqual(
            "You do not have permission to nominate this bug.",
            notifications[0].message)

    def test_nominate_another_series_distribution(self):
        person = self.factory.makePerson(
            name='main-person-test', password='test')
        distro = self.factory.makeDistribution()
        owner = distro.owner
        members = [self.factory.makePerson() for i in range(2)]
        members.append(person)
        bug_supervisor = self.factory.makeTeam(members=members, owner=owner)
        with person_logged_in(owner):
            distro.setBugSupervisor(bug_supervisor, owner)
        current_series = self.factory.makeDistroSeries(
            distribution=distro, status=SeriesStatus.CURRENT)
        older_series = self.factory.makeDistroSeries(distribution=distro)
        bug = self.factory.makeBug(distribution=distro, series=current_series)
        series_bugtask = bug.bugtasks[1]
        login_person(person)
        view = create_initialized_view(series_bugtask, name='+nominate')
        self.assertEqual(0, len(view.request.notifications))
        nomination = bug.addNomination(person, older_series)
        self.assertTrue(nomination is not None)

    def test_nominate_another_series_source_package(self):
        person = self.factory.makePerson(
            name='main-person-test', password='test')
        distro = self.factory.makeDistribution()
        owner = distro.owner
        members = [self.factory.makePerson() for i in range(2)]
        members.append(person)
        bug_supervisor = self.factory.makeTeam(members=members, owner=owner)
        with person_logged_in(owner):
            distro.setBugSupervisor(bug_supervisor, owner)
        current_series = self.factory.makeDistroSeries(
            distribution=distro, status=SeriesStatus.CURRENT)
        older_series = self.factory.makeDistroSeries(distribution=distro)
        package = self.factory.makeDistributionSourcePackage(
            distribution=distro)
        bug = self.factory.makeBug(
            distribution=distro, series=current_series,
            sourcepackagename=package.name)
        series_bugtask = bug.bugtasks[1]
        login_person(person)
        view = create_initialized_view(series_bugtask, name='+nominate')
        self.assertEqual(0, len(view.request.notifications))
        nomination = bug.addNomination(person, older_series)
        self.assertTrue(nomination is not None)

    def test_nominate_another_series_product(self):
        person = self.factory.makePerson(
            name='main-person-test-product', password='test')
        product = self.factory.makeProduct()
        owner = product.owner
        members = [self.factory.makePerson() for i in range(2)]
        members.append(person)
        bug_supervisor = self.factory.makeTeam(members=members, owner=owner)
        with person_logged_in(owner):
            product.setBugSupervisor(bug_supervisor, owner)
        current_series = self.factory.makeProductSeries(product=product)
        older_series = self.factory.makeProductSeries(product=product)
        bug = self.factory.makeBug(product=product, series=current_series)
        series_bugtask = bug.bugtasks[1]
        login_person(person)
        view = create_initialized_view(series_bugtask, name='+nominate')
        self.assertEqual(0, len(view.request.notifications))
        nomination = bug.addNomination(person, older_series)
        self.assertTrue(nomination is not None)


class TestBugNominationEditView(TestCaseWithFactory):
    """Tests for BugNominationEditView."""

    layer = DatabaseFunctionalLayer

    def getNomination(self):
        nomination = self.factory.makeBugNomination(
            target=self.factory.makeProductSeries())
        login_person(nomination.productseries.product.owner)
        return nomination

    def getNominationEditView(self, nomination, form):
        getUtility(ILaunchBag).add(nomination.bug.default_bugtask)
        view = create_initialized_view(
            nomination, name='+editstatus',
            current_request=True,
            principal=get_current_principal(),
            form=form)
        return view

    def assertApproves(self, nomination):
        self.assertEquals(
            302,
            self.getNominationEditView(
                nomination,
                {'field.actions.approve': 'Approve'},
                ).request.response.getStatus())
        self.assertTrue(nomination.isApproved())

    def test_approving_twice_is_noop(self):
        nomination = self.getNomination()
        self.assertApproves(nomination)
        self.assertThat(
            self.getNominationEditView(
                nomination,
                {'field.actions.approve': 'Approve'}).render(),
            Contains("This nomination has already been approved."))

    def test_declining_approved_is_noop(self):
        nomination = self.getNomination()
        self.assertApproves(nomination)
        self.assertThat(
            self.getNominationEditView(
                nomination,
                {'field.actions.decline': 'Decline'}).render(),
            Contains("This nomination has already been approved."))
