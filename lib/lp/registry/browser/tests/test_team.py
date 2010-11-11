# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.browser.person import TeamOverviewMenu
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.matchers import IsConfiguredBatchNavigator
from lp.testing.menu import check_menu_links
from lp.testing.views import create_initialized_view


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
        mailing_list = self.factory.makeMailingList(
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


class TestTeamMemberAddView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestTeamMemberAddView, self).setUp()
        self.team = self.factory.makeTeam()
        login_person(self.team.teamowner)

    def test_newmember_empty_before_add(self):
        view = create_initialized_view(self.team, "+addmember")
        self.assertEqual([], view.errors)
        self.assertEqual(
            None, view.widgets['newmember']._getCurrentValue())

    def test_newmember_add_success(self):
        member = self.factory.makePerson(name="a-member")
        form = {
            'field.newmember': 'a-member',
            'field.actions.add': 'Add Member',
            }
        view = create_initialized_view(
            self.team, "+addmember", form=form)
        self.assertEqual([], view.errors)
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'A-member (a-member) has been added as a member of this team.',
            notifications[0].message)
        self.assertTrue(member.inTeam(self.team))
        self.assertEqual(
            None, view.widgets['newmember']._getCurrentValue())
