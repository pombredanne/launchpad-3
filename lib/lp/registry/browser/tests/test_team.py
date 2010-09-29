# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.testing import DatabaseFunctionalLayer
from lp.registry.browser.person import TeamOverviewMenu
from lp.testing import TestCaseWithFactory
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
