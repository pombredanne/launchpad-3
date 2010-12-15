
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test harness for mailinglist views unit tests."""

__metaclass__ = type


from canonical.launchpad.ftests import login_person
from canonical.launchpad.testing.pages import (
    extract_text,
    find_tag_by_id,
    )
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.person import PersonVisibility
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import create_view


class MailingListSubscriptionControlsTestCase(TestCaseWithFactory):
    """Verify the team index subscribe/unsubscribe to mailing list content."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(MailingListSubscriptionControlsTestCase, self).setUp()
        self.a_team = self.factory.makeTeam(name='a')
        self.b_team = self.factory.makeTeam(name='b', owner=self.a_team)
        self.b_team_list = self.factory.makeMailingList(team=self.b_team,
            owner=self.b_team.teamowner)
        self.user = self.factory.makePerson()
        with person_logged_in(self.a_team.teamowner):
            self.a_team.addMember(self.user, self.a_team.teamowner)

    def test_subscribe_control_renders(self):
        login_person(self.user)
        view = create_view(self.b_team, name='+index',
            principal=self.user, server_url='http://launchpad.dev',
            path_info='/~%s' % self.b_team.name)
        content = view.render()
        link_tag = find_tag_by_id(content, "link-list-subscribe")
        self.assertNotEqual(None, link_tag)

    def test_subscribe_control_doesnt_render_for_non_member(self):
        other_person = self.factory.makePerson()
        login_person(other_person)
        view = create_view(self.b_team, name='+index',
            principal=other_person, server_url='http://launchpad.dev',
            path_info='/~%s' % self.b_team.name)
        content = view.render()
        self.assertNotEqual('', content)
        link_tag = find_tag_by_id(content, "link-list-subscribe")
        self.assertEqual(None, link_tag)


class MailingListPortletTestCase(TestCaseWithFactory):
    """Verify the team index subscribe/unsubscribe to mailing list content."""

    layer = DatabaseFunctionalLayer

    def makeTeamAndMailingList(self, visibility=None):
        team = self.factory.makeTeam(visibility=visibility)
        login_person(team.teamowner)
        team_list = self.factory.makeMailingList(
            team=team, owner=team.teamowner)
        return team

    def test_public_archive(self):
        # Public teams have public archives.
        team = self.makeTeamAndMailingList()
        view = create_view(
            team, name='+portlet-mailinglist',
            server_url='http://launchpad.dev', path_info='/~%s' % team.name)
        link = find_tag_by_id(view(), 'mailing-list-archive')
        self.assertEqual('View public archive', extract_text(link))

    def test_private_archive(self):
        # Private teams have private archives.
        team = self.makeTeamAndMailingList(
            visibility=PersonVisibility.PRIVATE)
        view = create_view(
            team, name='+portlet-mailinglist',
            server_url='http://launchpad.dev', path_info='/~%s' % team.name)
        link = find_tag_by_id(view(), 'mailing-list-archive')
        self.assertEqual('View private archive', extract_text(link))
