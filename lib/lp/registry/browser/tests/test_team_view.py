# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Test team views.
"""

__metaclass__ = type

import transaction
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from canonical.launchpad.testing.pages import (
    extract_text,
    find_tags_by_class,
    setupBrowser)
from canonical.launchpad.webapp.publisher import canonical_url
from lp.registry.interfaces.mailinglist import MailingListStatus
from lp.registry.interfaces.person import (
    PersonVisibility,
    TeamSubscriptionPolicy,
    )
from lp.testing import (
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestProposedTeamMembersEditView(TestCaseWithFactory):
    """Tests for ProposedTeamMembersEditView."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProposedTeamMembersEditView, self).setUp()
        self.owner = self.factory.makePerson(name="team-owner")
        self.a_team = self.makeTeam("team-a", "A-Team")
        self.b_team = self.makeTeam("team-b", "B-Team")
        transaction.commit()
        login_person(self.owner)

    def makeTeam(self, name, displayname):
        """Make a moderated team."""
        return self.factory.makeTeam(
            name=name,
            owner=self.owner,
            displayname=displayname,
            subscription_policy=TeamSubscriptionPolicy.MODERATED)

    def inviteToJoin(self, joinee, joiner):
        """Invite the joiner team into the joinee team."""
        # Joiner is proposed to join joinee.
        form = {
            'field.teams': joiner.name,
            'field.actions.continue': 'Continue',
            }
        view = create_initialized_view(
            joinee, "+add-my-teams", form=form)
        self.assertEqual([], view.errors)
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        expected = u"%s has been proposed to this team." % (
            joiner.displayname)
        self.assertEqual(
            expected,
            notifications[0].message)

    def acceptTeam(self, joinee, successful, failed):
        """Accept the teams into the joinee team.

        The teams in 'successful' are expected to be allowed.
        The teams in 'failed' are expected to fail.
        """
        failed_names = ', '.join([team.displayname for team in failed])
        if len(failed) == 1:
            failed_message = (
                u'%s is a member of the following team, '
                'so it could not be accepted:  %s.  '
                'You need to "Decline" that team.' %
                (joinee.displayname, failed_names))
        else:
            failed_message = (
                u'%s is a member of the following teams, '
                'so they could not be accepted:  %s.  '
                'You need to "Decline" those teams.' %
                (joinee.displayname, failed_names))

        form = {
            'field.actions.save': 'Save changes',
            }
        for team in successful + failed:
            # Construct the team selection field, based on the id of the
            # team.
            selector = 'action_%d' % team.id
            form[selector] = 'approve'

        view = create_initialized_view(
            joinee, "+editproposedmembers", form=form)
        self.assertEqual([], view.errors)
        notifications = view.request.response.notifications
        if len(failed) == 0:
            self.assertEqual(0, len(notifications))
        else:
            self.assertEqual(1, len(notifications))
            self.assertEqual(
                failed_message,
                notifications[0].message)

    def test_circular_proposal_acceptance(self):
        """Two teams can invite each other without horrifying results."""

        # Make the criss-cross invitations.

        # Owner proposes Team B join Team A.
        self.inviteToJoin(self.a_team, self.b_team)

        # Owner proposes Team A join Team B.
        self.inviteToJoin(self.b_team, self.a_team)

        # Accept Team B into Team A.
        self.acceptTeam(self.a_team, successful=(self.b_team,), failed=())

        # Accept Team A into Team B, and fail trying.
        self.acceptTeam(self.b_team, successful=(), failed=(self.a_team,))

    def test_circular_proposal_acceptance_with_some_noncircular(self):
        """Accepting a mix of successful and failed teams works."""
        # Create some extra teams.
        self.c_team = self.makeTeam("team-c", "C-Team")
        self.d_team = self.makeTeam("team-d", "D-Team")
        self.super_team = self.makeTeam("super-team", "Super Team")

        # Everyone wants to join Super Team.
        for team in [self.a_team, self.b_team, self.c_team, self.d_team]:
            self.inviteToJoin(self.super_team, team)

        # Super Team joins two teams.
        for team in [self.a_team, self.b_team]:
            self.inviteToJoin(team, self.super_team)

        # Super Team is accepted into both.
        for team in [self.a_team, self.b_team]:
            self.acceptTeam(team, successful=(self.super_team, ), failed=())

        # Now Super Team attempts to accept all teams.  Two succeed but the
        # two with that would cause a cycle fail.
        failed = (self.a_team, self.b_team)
        successful = (self.c_team, self.d_team)
        self.acceptTeam(self.super_team, successful, failed)


class TestTeamEditView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_cannot_rename_team_with_ppa(self):
        # A team with a ppa cannot be renamed.
        owner = self.factory.makePerson()
        team = self.factory.makeTeam(owner=owner)
        removeSecurityProxy(team).archive = self.factory.makeArchive()
        with person_logged_in(owner):
            view = create_initialized_view(team, name="+edit")
            self.assertTrue(view.form_fields['name'].for_display)
            self.assertEqual(
                'This team cannot be renamed because it has a PPA.',
                view.widgets['name'].hint)

    def test_cannot_rename_team_with_active_mailinglist(self):
        # Because renaming mailing lists is non-trivial in Mailman 2.1,
        # renaming teams with mailing lists is prohibited.
        owner = self.factory.makePerson()
        team = self.factory.makeTeam(owner=owner)
        self.factory.makeMailingList(team, owner)
        with person_logged_in(owner):
            view = create_initialized_view(team, name="+edit")
            self.assertTrue(view.form_fields['name'].for_display)
            self.assertEqual(
                'This team cannot be renamed because it has a mailing list.',
                view.widgets['name'].hint)

    def test_can_rename_team_with_purged_mailinglist(self):
        # A team with a mailing list which is purged can be renamed.
        owner = self.factory.makePerson()
        team = self.factory.makeTeam(owner=owner)
        team_list = self.factory.makeMailingList(team, owner)
        team_list.deactivate()
        team_list.transitionToStatus(MailingListStatus.INACTIVE)
        team_list.purge()
        with person_logged_in(owner):
            view = create_initialized_view(team, name="+edit")
            self.assertFalse(view.form_fields['name'].for_display)

    def test_cannot_rename_team_with_multiple_reasons(self):
        # Since public teams can have mailing lists and PPAs simultaneously,
        # there will be scenarios where more than one of these conditions are
        # actually blocking the team to be renamed.
        owner = self.factory.makePerson()
        team = self.factory.makeTeam(owner=owner)
        self.factory.makeMailingList(team, owner)
        removeSecurityProxy(team).archive = self.factory.makeArchive()
        with person_logged_in(owner):
            view = create_initialized_view(team, name="+edit")
            self.assertTrue(view.form_fields['name'].for_display)
            self.assertEqual(
                ('This team cannot be renamed because it has a mailing list '
                 'and has a PPA.'),
                view.widgets['name'].hint)

    def test_edit_team_view_permission(self):
        # Only an administrator (as well as the team owner) of a team can
        # change the details of that team.
        person = self.factory.makePerson()
        team = self.factory.makeTeam()
        url = canonical_url(team, view_name='+edit')
        self.assertRaises(
            Unauthorized, self.getUserBrowser, url, person)
        browser = setupBrowser(auth='Basic mark@example.com:test')
        browser.open(url)

    def test_edit_team_view_data(self):
        # The edit view renders the team's details correctly.
        owner = self.factory.makePerson()
        team = self.factory.makeTeam(
            name="team", displayname='A Team',
            description="A great team", owner=owner,
            subscription_policy=TeamSubscriptionPolicy.MODERATED)
        browser = self.getUserBrowser(
            canonical_url(team), user=owner)
        browser.getLink('Change details').click()
        self.assertEqual('team', browser.getControl('Name', index=0).value)
        self.assertEqual(
            'A Team', browser.getControl('Display Name', index=0).value)
        self.assertEqual(
            'A great team',
            browser.getControl('Team Description', index=0).value)
        self.assertTrue(
            browser.getControl('Moderated Team', index=0).selected)
        self.assertTrue(
            browser.getControl('invite them to apply for renewal').selected)
        self.assertEqual(
            '', browser.getControl('Renewal period', index=0).value)

    def test_edit_team_view_save(self):
        # A team can be edited and saved, including a name change, even if it
        # is a private team and has a purged mailing list.
        owner = self.factory.makePerson()
        team = self.factory.makeTeam(
            name="team", displayname='A Team',
            description="A great team", owner=owner,
            visibility=PersonVisibility.PRIVATE,
            subscription_policy=TeamSubscriptionPolicy.MODERATED)

        with person_logged_in(owner):
            team_list = self.factory.makeMailingList(team, owner)
            team_list.deactivate()
            team_list.transitionToStatus(MailingListStatus.INACTIVE)
            team_list.purge()
            url = canonical_url(team)
        browser = self.getUserBrowser(url, user=owner)
        browser.getLink('Change details').click()
        browser.getControl('Name', index=0).value = 'ubuntuteam'
        browser.getControl('Display Name').value = 'Ubuntu Team'
        browser.getControl('Team Description').value = ''
        browser.getControl('Restricted Team').selected = True
        browser.getControl('Save').click()

        # We're now redirected to the team's home page, which is now on a
        # different URL since we changed its name.
        self.assertEqual('http://launchpad.dev/~ubuntuteam', browser.url)

        # Check the values again.
        browser.getLink('Change details').click()
        self.assertEqual(
            'ubuntuteam', browser.getControl('Name', index=0).value)
        self.assertEqual(
            'Ubuntu Team', browser.getControl('Display Name', index=0).value)
        self.assertEqual(
            '', browser.getControl('Team Description', index=0).value)
        self.assertTrue(
            browser.getControl('Restricted Team', index=0).selected)

    def test_team_name_already_used(self):
        # If we try to use a name which is already in use, we'll get an error
        # message explaining it.

        self.factory.makeTeam(name="existing")
        owner = self.factory.makePerson()
        team = self.factory.makeTeam(name="team", owner=owner)

        #with person_logged_in(owner):
        url = canonical_url(team)
        browser = self.getUserBrowser(url, user=owner)
        browser.getLink('Change details').click()
        browser.getControl('Name', index=0).value = 'existing'
        browser.getControl('Save').click()
        self.assertEqual('http://launchpad.dev/%7Eteam/+edit', browser.url)

        messages = []
        for tag in find_tags_by_class(browser.contents, 'message'):
            messages.append(extract_text(tag))
        self.assertEqual(
            ['There is 1 error.',
            'existing is already in use by another person or team.'],
            messages)
