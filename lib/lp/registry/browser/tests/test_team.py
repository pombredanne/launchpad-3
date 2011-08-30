# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.browser.person import TeamOverviewMenu
from lp.registry.interfaces.persontransferjob import IPersonMergeJobSource
from lp.registry.interfaces.teammembership import (
    ITeamMembershipSet,
    TeamMembershipStatus,
    )
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    person_logged_in,
    )
from lp.testing.matchers import IsConfiguredBatchNavigator
from lp.testing.menu import check_menu_links
from lp.testing.views import (
    create_initialized_view,
    create_view,
    )


class TestTeamMenu(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestTeamMenu, self).setUp()
        self.team = self.factory.makeTeam()

    def test_TeamOverviewMenu_check_menu_links_without_mailing(self):
        menu = TeamOverviewMenu(self.team)
        # Remove moderate_mailing_list because it asserts that there is
        # a mailing list.
        no_mailinst_list_links = [
            link for link in menu.links if link != 'moderate_mailing_list']
        menu.links = no_mailinst_list_links
        self.assertEqual(True, check_menu_links(menu))
        link = menu.configure_mailing_list()
        self.assertEqual('Create a mailing list', link.text)

    def test_TeamOverviewMenu_check_menu_links_with_mailing(self):
        self.factory.makeMailingList(
            self.team, self.team.teamowner)
        menu = TeamOverviewMenu(self.team)
        self.assertEqual(True, check_menu_links(menu))
        link = menu.configure_mailing_list()
        self.assertEqual('Configure mailing list', link.text)


class TestModeration(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_held_messages_is_batch_navigator(self):
        team = self.factory.makeTeam()
        self.factory.makeMailingList(team, team.teamowner)
        view = create_initialized_view(team, name='+mailinglist-moderate')
        self.assertThat(
            view.held_messages,
            IsConfiguredBatchNavigator('message', 'messages'))

    def test_no_mailing_list_redirect(self):
        team = self.factory.makeTeam()
        login_person(team.teamowner)
        view = create_view(team, name='+mailinglist-moderate')
        response = view.request.response
        self.assertEqual(302, response.getStatus())
        self.assertEqual(canonical_url(team), response.getHeader('location'))
        self.assertEqual(1, len(response.notifications))
        self.assertEqual(
            '%s does not have a mailing list.' % (team.displayname),
            response.notifications[0].message)


class TestTeamMemberAddView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestTeamMemberAddView, self).setUp()
        self.team = self.factory.makeTeam(name='test-team')
        login_person(self.team.teamowner)

    def getForm(self, new_member):
        return {
            'field.newmember': new_member.name,
            'field.actions.add': 'Add Member',
            }

    def test_add_member_success(self):
        member = self.factory.makePerson(name="a-member")
        form = self.getForm(member)
        view = create_initialized_view(self.team, "+addmember", form=form)
        self.assertEqual([], view.errors)
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'A-member (a-member) has been added as a member of this team.',
            notifications[0].message)
        self.assertTrue(member.inTeam(self.team))
        self.assertEqual(
            None, view.widgets['newmember']._getCurrentValue())

    def test_add_former_member_success(self):
        member = self.factory.makePerson(name="a-member")
        self.team.addMember(member, self.team.teamowner)
        with person_logged_in(member):
            member.leave(self.team)
        form = self.getForm(member)
        view = create_initialized_view(self.team, "+addmember", form=form)
        self.assertEqual([], view.errors)
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'A-member (a-member) has been added as a member of this team.',
            notifications[0].message)
        self.assertTrue(member.inTeam(self.team))

    def test_add_existing_member_fail(self):
        member = self.factory.makePerson(name="a-member")
        self.team.addMember(member, self.team.teamowner)
        form = self.getForm(member)
        view = create_initialized_view(self.team, "+addmember", form=form)
        self.assertEqual(1, len(view.errors))
        self.assertEqual(
            "A-member (a-member) is already a member of Test Team.",
            view.errors[0])

    def test_add_empty_team_fail(self):
        empty_team = self.factory.makeTeam(owner=self.team.teamowner)
        self.team.teamowner.leave(empty_team)
        form = self.getForm(empty_team)
        view = create_initialized_view(self.team, "+addmember", form=form)
        self.assertEqual(1, len(view.errors))
        self.assertEqual(
            "You can't add a team that doesn't have any active members.",
            view.errors[0])

    def test_no_TeamMembershipTransitionError(self):
        # Attempting to add a team never triggers a
        # TeamMembershipTransitionError
        member_team = self.factory.makeTeam()
        self.team.addMember(member_team, self.team.teamowner)
        tm = getUtility(ITeamMembershipSet).getByPersonAndTeam(
            member_team, self.team)
        for status in TeamMembershipStatus.items:
            removeSecurityProxy(tm).status = status
            view = create_initialized_view(self.team, "+addmember")
            view.add_action.success(data={'newmember': member_team})


class TestTeamIndexView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestTeamIndexView, self).setUp()
        self.team = self.factory.makeTeam(name='test-team')
        login_person(self.team.teamowner)

    def test_add_member_step_title(self):
        view = create_initialized_view(self.team, '+index')
        self.assertEqual('Search', view.add_member_step_title)

    def test_is_merge_pending(self):
        target_team = self.factory.makeTeam()
        job_source = getUtility(IPersonMergeJobSource)
        job_source.create(
            from_person=self.team, to_person=target_team,
            reviewer=target_team.teamowner)
        view = create_initialized_view(self.team, name="+index")
        notifications = view.request.response.notifications
        message = (
            'Test Team is queued to be be merged or deleted '
            'in a few minutes.')
        self.assertEqual(1, len(notifications))
        self.assertEqual(message, notifications[0].message)
