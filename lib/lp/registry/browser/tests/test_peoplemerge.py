# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test the peoplemerge browser module."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.interfaces.emailaddress import (
    EmailAddressStatus,
    IEmailAddressSet,
    )
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.mailinglist import MailingListStatus
from lp.registry.interfaces.person import (
    IPersonSet,
    TeamSubscriptionPolicy,
    )
from lp.testing import (
    celebrity_logged_in,
    login_celebrity,
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import (
    create_initialized_view,
    create_view,
    )


class TestRequestPeopleMergeMultipleEmailsView(TestCaseWithFactory):
    """Test the RequestPeopleMergeMultipleEmailsView rules."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestRequestPeopleMergeMultipleEmailsView, self).setUp()
        self.personset = getUtility(IPersonSet)
        self.dupe_user = self.factory.makePerson()
        self.email_2 = self.factory.makeEmail(
            'dupe@place.dom', self.dupe_user)
        self.original_user = self.factory.makePerson()
        login_person(self.original_user)

    def verify_user_must_reselect_email_addresses(self, view):
        self.assertFalse(view.form_processed)
        self.assertEqual(0, len(view.notified_addresses))
        self.assertEqual(1, len(view.request.notifications))
        message = view.request.notifications[0].message
        self.assertTrue(message.endswith('Select again.'))

    def test_removed_email(self):
        # When the duplicate user deletes an email addres while the merge
        # form is being complete, the view must abort and ask the user
        # to restart the merge request.
        form = {
            'dupe': self.dupe_user.id,
            }
        view = create_view(
            self.personset, name='+requestmerge-multiple', form=form)
        view.processForm()
        dupe_emails = [address for address in view.dupeemails]
        form['selected'] = [address.email for address in dupe_emails]
        with person_logged_in(self.dupe_user):
            dupe_emails.remove(self.email_2)
            self.email_2.destroySelf()
        view = create_view(
            self.personset, name='+requestmerge-multiple', form=form,
            method='POST')
        view.processForm()
        self.verify_user_must_reselect_email_addresses(view)

    def test_email_address_cannot_be_substituted(self):
        # A person cannot hack the form to use another user's email address
        # to take control of a profile.
        controlled_user = self.factory.makePerson()
        form = {
            'dupe': self.dupe_user.id,
            'selected': [controlled_user.preferredemail.email],
            }
        view = create_view(
            self.personset, name='+requestmerge-multiple', form=form,
            method='POST')
        view.processForm()
        self.verify_user_must_reselect_email_addresses(view)


class TestAdminTeamMergeView(TestCaseWithFactory):
    """Test the AdminTeamMergeView rules."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestAdminTeamMergeView, self).setUp()
        self.person_set = getUtility(IPersonSet)
        self.dupe_team = self.factory.makeTeam(name='dupe-team')
        self.target_team = self.factory.makeTeam(name='target-team')
        login_celebrity('registry_experts')

    def getView(self, form=None):
        if form is None:
            form = {
                'field.dupe_person': self.dupe_team.name,
                'field.target_person': self.target_team.name,
                'field.actions.deactivate_members_and_merge': 'Merge',
                }
        return create_initialized_view(
            self.person_set, '+adminteammerge', form=form)

    def test_merge_team_with_inactive_mailing_list(self):
        # Inactive lists do not block merges.
        mailing_list = self.factory.makeMailingList(
            self.dupe_team, self.dupe_team.teamowner)
        mailing_list.deactivate()
        mailing_list.transitionToStatus(MailingListStatus.INACTIVE)
        view = self.getView()
        self.assertEqual([], view.errors)
        self.assertEqual(self.target_team, self.dupe_team.merged)

    def test_merge_team_with_email_address(self):
        # Team email addresses are not transferred.
        self.factory.makeEmail(
            "del@ex.dom", self.dupe_team, email_status=EmailAddressStatus.NEW)
        view = self.getView()
        self.assertEqual([], view.errors)
        self.assertEqual(self.target_team, self.dupe_team.merged)
        emails = getUtility(IEmailAddressSet).getByPerson(self.target_team)
        self.assertEqual(0, emails.count())

    def test_merge_team_with_super_teams_into_registry_experts(self):
        # Super team memberships are removed.
        self.target_team = getUtility(ILaunchpadCelebrities).registry_experts
        super_team = self.factory.makeTeam()
        login_celebrity('admin')
        self.dupe_team.join(super_team, self.dupe_team.teamowner)
        login_person(self.dupe_team.teamowner)
        form = {
            'field.dupe_person': self.dupe_team.name,
            'field.target_person': self.target_team.name,
            'field.actions.merge': 'Merge',
            }
        view = self.getView()
        self.assertEqual([], view.errors)
        self.assertEqual(self.target_team, self.dupe_team.merged)

    def test_owner_delete_team_with_super_teams(self):
        # Super team memberships are removed.
        self.target_team = getUtility(ILaunchpadCelebrities).registry_experts
        super_team = self.factory.makeTeam()
        login_celebrity('admin')
        self.dupe_team.join(super_team, self.dupe_team.teamowner)
        login_person(self.dupe_team.teamowner)
        view = self.getView()
        self.assertEqual([], view.errors)
        self.assertEqual(self.target_team, self.dupe_team.merged)

    def test_cannot_merge_team_with_ppa(self):
        # A team with a PPA cannot be merged.
        login_celebrity('admin')
        self.dupe_team.subscriptionpolicy = TeamSubscriptionPolicy.MODERATED
        archive = self.dupe_team.createPPA()
        login_celebrity('registry_experts')
        view = self.getView()
        self.assertEqual(
            [u"dupe-team has a PPA that must be deleted before it can be "
              "merged. It may take ten minutes to remove the deleted PPA's "
              "files."],
            view.errors)

    def test_registry_delete_team_with_super_teams(self):
        # Registry admins can delete teams with super team memberships.
        self.target_team = getUtility(ILaunchpadCelebrities).registry_experts
        super_team = self.factory.makeTeam()
        # Use admin to avoid the team invitation dance. The Registry admin
        # is logged back in.
        with celebrity_logged_in('admin'):
            self.dupe_team.join(super_team, super_team.teamowner)
        view = self.getView()
        self.assertEqual([], view.errors)
        self.assertEqual(self.target_team, self.dupe_team.merged)


class TestAdminPeopleMergeView(TestCaseWithFactory):
    """Test the AdminPeopleMergeView rules."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestAdminPeopleMergeView, self).setUp()
        self.person_set = getUtility(IPersonSet)
        self.dupe_person = self.factory.makePerson(name='dupe-person')
        self.target_person = self.factory.makePerson()
        login_celebrity('registry_experts')

    def getView(self, form=None):
        if form is None:
            form = {
                'field.dupe_person': self.dupe_person.name,
                'field.target_person': self.target_person.name,
                'field.actions.reassign_emails_and_merge':
                    'Reassign E-mails and Merge',
                }
        return create_initialized_view(
            self.person_set, '+adminpeoplemerge', form=form)

    def test_cannot_merge_person_with_ppa(self):
        # A person with a PPA cannot be merged.
        login_celebrity('admin')
        archive = self.dupe_person.createPPA()
        view = self.getView()
        self.assertEqual(
            [u"dupe-person has a PPA that must be deleted before it can be "
              "merged. It may take ten minutes to remove the deleted PPA's "
              "files."],
            view.errors)
