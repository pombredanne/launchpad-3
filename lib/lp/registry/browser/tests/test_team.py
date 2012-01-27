# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import contextlib
from lazr.restful.interfaces import IJSONRequestCache
import simplejson
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.registry.browser.team import TeamOverviewMenu
from lp.registry.interfaces.mailinglist import MailingListStatus
from lp.registry.interfaces.person import (
    CLOSED_TEAM_POLICY,
    OPEN_TEAM_POLICY,
    PersonVisibility,
    TeamMembershipRenewalPolicy,
    TeamSubscriptionPolicy,
    )
from lp.registry.interfaces.persontransferjob import IPersonMergeJobSource
from lp.registry.interfaces.teammembership import (
    ITeamMembershipSet,
    TeamMembershipStatus,
    )
from lp.registry.browser.team import TeamMailingListArchiveView
from lp.services.propertycache import get_property_cache
from lp.services.webapp.authorization import check_permission
from lp.services.webapp.publisher import canonical_url
from lp.soyuz.enums import ArchiveStatus
from lp.testing import (
    login_celebrity,
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.matchers import IsConfiguredBatchNavigator
from lp.testing.menu import check_menu_links
from lp.testing.pages import (
    extract_text,
    find_tag_by_id,
    )
from lp.testing.views import (
    create_initialized_view,
    create_view,
    )


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


class TestTeamPersonRenameFormMixin:

    view_name = None

    def test_cannot_rename_team_with_active_ppa(self):
        # A team with an active PPA that contains publications cannot be
        # renamed.
        owner = self.factory.makePerson()
        team = self.factory.makeTeam(owner=owner)
        archive = self.factory.makeArchive(owner=team)
        self.factory.makeSourcePackagePublishingHistory(archive=archive)
        get_property_cache(team).archive = archive
        with person_logged_in(owner):
            view = create_initialized_view(team, name=self.view_name)
            self.assertTrue(view.form_fields['name'].for_display)
            self.assertEqual(
                'This team has an active PPA with packages published and '
                'may not be renamed.', view.widgets['name'].hint)

    def test_can_rename_team_with_deleted_ppa(self):
        # A team with a deleted PPA can be renamed.
        owner = self.factory.makePerson()
        team = self.factory.makeTeam(owner=owner)
        archive = self.factory.makeArchive()
        self.factory.makeSourcePackagePublishingHistory(archive=archive)
        removeSecurityProxy(archive).status = ArchiveStatus.DELETED
        get_property_cache(team).archive = archive
        with person_logged_in(owner):
            view = create_initialized_view(team, name=self.view_name)
            self.assertFalse(view.form_fields['name'].for_display)

    def test_cannot_rename_team_with_active_mailinglist(self):
        # Because renaming mailing lists is non-trivial in Mailman 2.1,
        # renaming teams with mailing lists is prohibited.
        owner = self.factory.makePerson()
        team = self.factory.makeTeam(owner=owner)
        self.factory.makeMailingList(team, owner)
        with person_logged_in(owner):
            view = create_initialized_view(team, name=self.view_name)
            self.assertTrue(view.form_fields['name'].for_display)
            self.assertEqual(
                'This team has a mailing list and may not be renamed.',
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
            view = create_initialized_view(team, name=self.view_name)
            self.assertFalse(view.form_fields['name'].for_display)

    def test_cannot_rename_team_with_multiple_reasons(self):
        # Since public teams can have mailing lists and PPAs simultaneously,
        # there will be scenarios where more than one of these conditions are
        # actually blocking the team to be renamed.
        owner = self.factory.makePerson()
        team = self.factory.makeTeam(owner=owner)
        self.factory.makeMailingList(team, owner)
        archive = self.factory.makeArchive(owner=team)
        self.factory.makeSourcePackagePublishingHistory(archive=archive)
        get_property_cache(team).archive = archive
        with person_logged_in(owner):
            view = create_initialized_view(team, name=self.view_name)
            self.assertTrue(view.form_fields['name'].for_display)
            self.assertEqual(
                'This team has an active PPA with packages published and '
                'a mailing list and may not be renamed.',
                view.widgets['name'].hint)


class TestTeamEditView(TestTeamPersonRenameFormMixin, TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer
    view_name = '+edit'

    def test_edit_team_view_permission(self):
        # Only an administrator or the team owner of a team can
        # change the details of that team.
        person = self.factory.makePerson()
        owner = self.factory.makePerson()
        team = self.factory.makeTeam(owner=owner)
        view = create_view(team, '+edit')
        login_person(person)
        self.assertFalse(check_permission('launchpad.Edit', view))
        login_person(owner)
        self.assertTrue(check_permission('launchpad.Edit', view))

    def test_edit_team_view_data(self):
        # The edit view renders the team's details correctly.
        owner = self.factory.makePerson()
        team = self.factory.makeTeam(
            name="team", displayname='A Team',
            description="A great team", owner=owner,
            subscription_policy=TeamSubscriptionPolicy.MODERATED)
        with person_logged_in(owner):
            view = create_initialized_view(team, name="+edit")
            self.assertEqual('team', view.widgets['name']._data)
            self.assertEqual(
                'A Team', view.widgets['displayname']._data)
            self.assertEqual(
                'A great team', view.widgets['teamdescription']._data)
            self.assertEqual(
                TeamSubscriptionPolicy.MODERATED,
                view.widgets['subscriptionpolicy']._data)
            self.assertEqual(
                TeamSubscriptionPolicy,
                view.widgets['subscriptionpolicy'].vocabulary)
            self.assertIsNone(view.widgets['subscriptionpolicy'].extra_hint)
            self.assertEqual(
                TeamMembershipRenewalPolicy.NONE,
                view.widgets['renewal_policy']._data)
            self.assertIsNone(view.widgets['defaultrenewalperiod']._data)

    def _test_edit_team_view_expected_subscription_vocab(self,
                                                         fn_setup,
                                                         expected_items):
        # The edit view renders only the specified policy choices when
        # the setup performed by fn_setup occurs.
        owner = self.factory.makePerson()
        team = self.factory.makeTeam(
            owner=owner, subscription_policy=TeamSubscriptionPolicy.MODERATED)
        fn_setup(team)
        with person_logged_in(owner):
            view = create_initialized_view(team, name="+edit")
            self.assertContentEqual(
                expected_items,
                [term.value
                 for term in view.widgets['subscriptionpolicy'].vocabulary])
            self.assertEqual(
                'sprite info',
                view.widgets['subscriptionpolicy'].extra_hint_class)
            self.assertIsNotNone(
                view.widgets['subscriptionpolicy'].extra_hint)

    def test_edit_team_view_pillar_owner(self):
        # The edit view renders only closed subscription policy choices when
        # the team is a pillar owner.

        def setup_team(team):
            self.factory.makeProduct(owner=team)

        self._test_edit_team_view_expected_subscription_vocab(
            setup_team, CLOSED_TEAM_POLICY)

    def test_edit_team_view_pillar_security_contact(self):
        # The edit view renders only closed subscription policy choices when
        # the team is a pillar security contact.

        def setup_team(team):
            self.factory.makeProduct(security_contact=team)

        self._test_edit_team_view_expected_subscription_vocab(
            setup_team, CLOSED_TEAM_POLICY)

    def test_edit_team_view_has_ppas(self):
        # The edit view renders only closed subscription policy choices when
        # the team has any ppas.

        def setup_team(team):
            team.createPPA()

        self._test_edit_team_view_expected_subscription_vocab(
            setup_team, CLOSED_TEAM_POLICY)

    def test_edit_team_view_has_closed_super_team(self):
        # The edit view renders only closed subscription policy choices when
        # the team has any closed super teams.

        def setup_team(team):
            super_team = self.factory.makeTeam(
                owner=team.teamowner,
                subscription_policy=TeamSubscriptionPolicy.RESTRICTED)
            with person_logged_in(team.teamowner):
                super_team.addMember(
                    team, team.teamowner, force_team_add=True)

        self._test_edit_team_view_expected_subscription_vocab(
            setup_team, CLOSED_TEAM_POLICY)

    def test_edit_team_view_subscribed_private_bug(self):
        # The edit view renders only closed subscription policy choices when
        # the team is subscribed to a private bug.

        def setup_team(team):
            bug = self.factory.makeBug(owner=team.teamowner, private=True)
            with person_logged_in(team.teamowner):
                bug.default_bugtask.transitionToAssignee(team)

        self._test_edit_team_view_expected_subscription_vocab(
            setup_team, CLOSED_TEAM_POLICY)

    def test_edit_team_view_has_open_member(self):
        # The edit view renders open closed subscription policy choices when
        # the team has any open sub teams.

        def setup_team(team):
            team_member = self.factory.makeTeam(
                owner=team.teamowner,
                subscription_policy=TeamSubscriptionPolicy.DELEGATED)
            with person_logged_in(team.teamowner):
                team.addMember(
                    team_member, team.teamowner, force_team_add=True)

        self._test_edit_team_view_expected_subscription_vocab(
            setup_team, OPEN_TEAM_POLICY)

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

        form = {
            'field.name': 'existing',
            'field.actions.save': 'Save',
            }
        login_person(owner)
        view = create_initialized_view(team, '+edit', form=form)
        self.assertEqual(1, len(view.errors))
        self.assertEqual(
            'existing is already in use by another person or team.',
            view.errors[0].doc())


class TeamAdminisiterViewTestCase(TestTeamPersonRenameFormMixin,
                                  TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer
    view_name = '+review'

    def test_init_admin(self):
        team = self.factory.makeTeam()
        login_celebrity('admin')
        view = create_initialized_view(team, name=self.view_name)
        self.assertEqual('Review team', view.label)
        self.assertEqual(
            ['name', 'displayname'], view.field_names)

    def test_init_registry_expert(self):
        team = self.factory.makeTeam()
        login_celebrity('registry_experts')
        view = create_initialized_view(team, name=self.view_name)
        self.assertEqual(['name'], view.field_names)


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


class TestMailingListArchiveView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_no_messages(self):
        team = self.factory.makeTeam()
        self.factory.makeMailingList(team, team.teamowner)
        view = create_view(team, name='+mailing-list-archive')
        messages = IJSONRequestCache(view.request).objects['mail']
        self.assertEqual(0, len(messages))

    @contextlib.contextmanager
    def _override_messages(self, view_class, messages):
        def _message_shim(self):
            return simplejson.loads(messages)
        tmp = TeamMailingListArchiveView._get_messages
        TeamMailingListArchiveView._get_messages = _message_shim
        yield TeamMailingListArchiveView
        TeamMailingListArchiveView._get_messages = tmp

    def test_messages_are_in_json(self):
        team = self.factory.makeTeam()
        self.factory.makeMailingList(team, team.teamowner)
        messages = '''[{
            "headers": {
                "To": "somelist@example.com",
                "From": "someguy@example.com",
                "Subject": "foobar"},
            "message_id": "foo"}]'''

        with self._override_messages(TeamMailingListArchiveView, messages):
            view = create_view(team, name='+mailing-list-archive')
            messages = IJSONRequestCache(view.request).objects['mail']
            self.assertEqual(1, len(messages))
            self.assertEqual('foo', messages[0]['message_id'])


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

    def test_user_without_launchpad_view(self):
        # When the user does not have launchpad.View on the context,
        user = self.factory.makePerson()
        owner = self.factory.makePerson()
        with person_logged_in(owner):
            team = self.factory.makeTeam(
                displayname='Waffles', owner=owner,
                visibility=PersonVisibility.PRIVATE)
            archive = self.factory.makeArchive(private=True, owner=team)
            archive.newSubscription(user, registrant=owner)
        with person_logged_in(user):
            view = create_initialized_view(
                team, name="+index",  server_url=canonical_url(team),
                path_info='', principal=user)
            document = find_tag_by_id(view(), 'document')
        self.assertIsNone(document.find(True, id='side-portlets'))
        self.assertIsNone(document.find(True, id='registration'))
        self.assertEndsWith(
            extract_text(document.find(True, id='maincontent')),
            'The information in this page is not shared with you.')
