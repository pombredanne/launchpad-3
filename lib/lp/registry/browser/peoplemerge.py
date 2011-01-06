# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""People Merge related wiew classes."""

__metaclass__ = type

__all__ = [
    'AdminPeopleMergeView',
    'AdminTeamMergeView',
    'DeleteTeamView',
    'FinishedPeopleMergeRequestView',
    'RequestPeopleMergeMultipleEmailsView',
    'RequestPeopleMergeView',
    ]


from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad import _
from canonical.launchpad.interfaces.authtoken import LoginTokenType
from canonical.launchpad.interfaces.emailaddress import (
    EmailAddressStatus,
    IEmailAddressSet,
    )
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.interfaces.logintoken import ILoginTokenSet
from canonical.launchpad.interfaces.lpstorm import IMasterObject
from canonical.launchpad.webapp import (
    canonical_url,
    LaunchpadView,
    )
from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.app.browser.launchpadform import (
    action,
    LaunchpadFormView,
    )
from lp.registry.interfaces.mailinglist import (
    MailingListStatus,
    PURGE_STATES,
    )
from lp.registry.interfaces.person import (
    IAdminPeopleMergeSchema,
    IAdminTeamMergeSchema,
    IPersonSet,
    IRequestPeopleMerge,
    )
from lp.services.propertycache import cachedproperty
from lp.soyuz.enums import ArchiveStatus
from lp.soyuz.interfaces.archive import IArchiveSet


class AdminMergeBaseView(LaunchpadFormView):
    """Base view for the pages where admins can merge people/teams."""

    page_title = 'Merge Launchpad accounts'
    # Both subclasses share the same template so we need to define these
    # variables (which are used in the template) here rather than on
    # subclasses.
    should_confirm_email_reassignment = False
    should_confirm_member_deactivation = False
    merge_message = _('Merge completed successfully.')

    dupe_person_emails = ()
    dupe_person = None
    target_person = None

    @property
    def cancel_url(self):
        return canonical_url(getUtility(IPersonSet))

    @property
    def success_url(self):
        return canonical_url(self.target_person)

    def validate(self, data):
        """Check that user is not attempting to merge a person into itself."""
        dupe_person = data.get('dupe_person')
        target_person = data.get('target_person')
        if dupe_person == target_person and dupe_person is not None:
            self.addError(_("You can't merge ${name} into itself.",
                  mapping=dict(name=dupe_person.name)))
        # We cannot merge the teams if there is a PPA with published
        # packages on the duplicate person, unless that PPA is removed.
        dupe_person_ppas = getUtility(IArchiveSet).getPPAOwnedByPerson(
            dupe_person, statuses=[ArchiveStatus.ACTIVE,
                                   ArchiveStatus.DELETING])
        if dupe_person_ppas is not None:
            self.addError(_(
                "${name} has a PPA that must be deleted before it "
                "can be merged. It may take ten minutes to remove the "
                "deleted PPA's files.",
                mapping=dict(name=dupe_person.name)))

    def render(self):
        # Subclasses may define other actions that they will render manually
        # only in certain circunstances, so don't include them in the list of
        # actions to be rendered.
        self.actions = [self.merge_action]
        return super(AdminMergeBaseView, self).render()

    def setUpPeople(self, data):
        """Store the people to be merged in instance variables.

        Also store all emails associated with the dupe account in an
        instance variable.
        """
        emailset = getUtility(IEmailAddressSet)
        self.dupe_person = data['dupe_person']
        self.target_person = data['target_person']
        self.dupe_person_emails = emailset.getByPerson(self.dupe_person)

    def doMerge(self, data):
        """Merge the two person/team entries specified in the form."""
        for email in self.dupe_person_emails:
            email = IMasterObject(email)
            # EmailAddress.person and EmailAddress.account are readonly
            # fields, so we need to remove the security proxy here.
            naked_email = removeSecurityProxy(email)
            naked_email.personID = self.target_person.id
            naked_email.accountID = self.target_person.accountID
            # XXX: Guilherme Salgado 2007-10-15: Maybe this status change
            # should be done only when merging people but not when merging
            # teams.
            naked_email.status = EmailAddressStatus.NEW
        flush_database_updates()
        getUtility(IPersonSet).merge(self.dupe_person, self.target_person)
        self.request.response.addInfoNotification(self.merge_message)
        self.next_url = self.success_url


class AdminPeopleMergeView(AdminMergeBaseView):
    """A view for merging two Persons.

    If the duplicate person has any email addresses associated with we'll
    ask the user to confirm that it's okay to reassign these emails to the
    other account.  We do it because the fact that the dupe person still has
    email addresses is a possible indication that the admin may be merging
    the wrong person.
    """

    label = "Merge Launchpad people"
    schema = IAdminPeopleMergeSchema

    @action('Merge', name='merge')
    def merge_action(self, action, data):
        """Merge the two person entries specified in the form.

        If we're merging a person which has email addresses associated with
        we'll ask for confirmation before actually performing the merge.
        """
        self.setUpPeople(data)
        if self.dupe_person_emails.count() > 0:
            # We're merging a person which has one or more email addresses,
            # so we better warn the admin doing the operation and have him
            # check the emails that will be reassigned to ensure he's not
            # doing anything stupid.
            self.should_confirm_email_reassignment = True
            return
        self.doMerge(data)

    @action('Reassign E-mails and Merge', name='reassign_emails_and_merge')
    def reassign_emails_and_merge_action(self, action, data):
        """Reassign emails of the person to be merged and merge them."""
        self.setUpPeople(data)
        self.doMerge(data)


class AdminTeamMergeView(AdminMergeBaseView):
    """A view for merging two Teams.

    The duplicate team cannot be associated with a mailing list and if it
    has any active members we'll ask for confirmation from the user as we'll
    need to deactivate all members before we can do the merge.
    """

    label = "Merge Launchpad teams"
    schema = IAdminTeamMergeSchema

    def hasMailingList(self, team):
        unused_states = [state for state in PURGE_STATES]
        unused_states.append(MailingListStatus.PURGED)
        return (
            team.mailing_list is not None
            and team.mailing_list.status not in unused_states)

    @cachedproperty
    def registry_experts(self):
        return getUtility(ILaunchpadCelebrities).registry_experts

    def doMerge(self, data):
        """Purge the non-transferable team data and merge."""
        # A team cannot have more than one mailing list. The old list will
        # remain in the archive.
        purge_list = (self.dupe_person.mailing_list is not None
            and self.dupe_person.mailing_list.status in PURGE_STATES)
        if purge_list:
            self.dupe_person.mailing_list.purge()
        # Team email addresses are not transferable.
        self.dupe_person.setContactAddress(None)
        # The registry experts does not want to acquire super teams from a
        # merge. This operation requires unrestricted access to ensure
        # the user who has permission to delete a team can remove the
        # team from other teams.
        if self.target_person == self.registry_experts:
            all_super_teams = set(self.dupe_person.teams_participated_in)
            indirect_super_teams = set(
                self.dupe_person.teams_indirectly_participated_in)
            super_teams = all_super_teams - indirect_super_teams
            naked_dupe_person = removeSecurityProxy(self.dupe_person)
            for team in super_teams:
                naked_dupe_person.retractTeamMembership(team, self.user)
            del naked_dupe_person
        # We have sent another series of calls to the db, potentially a long
        # sequence depending on the merge. We want everything synced up
        # before proceeding.
        flush_database_updates()
        super(AdminTeamMergeView, self).doMerge(data)

    def validate(self, data):
        """Check there are no mailing lists associated with the dupe team."""
        # If errors have already been discovered there is no need to continue,
        # especially since some of our expected data may be missing in the
        # case of user-entered invalid data.
        if len(self.errors) > 0:
            return

        super(AdminTeamMergeView, self).validate(data)
        dupe_team = data['dupe_person']
        target_team = data['target_person']
        # Merge cannot reconcile cyclic membership in super teams.
        # Super team memberships are automatically removed when merging into
        # the registry experts team. When merging into any other team, an
        # error must be raised to explain that the user must remove the teams
        # himself.
        super_teams_count = dupe_team.super_teams.count()
        if target_team != self.registry_experts and super_teams_count > 0:
            self.addError(_(
                "${name} has super teams, so it can't be merged.",
                mapping=dict(name=dupe_team.name)))
        # We cannot merge the teams if there is a mailing list on the
        # duplicate person, unless that mailing list is purged.
        if self.hasMailingList(dupe_team):
            self.addError(_(
                "${name} is associated with a Launchpad mailing list; we "
                "can't merge it.", mapping=dict(name=dupe_team.name)))

    @action('Merge', name='merge')
    def merge_action(self, action, data):
        """Merge the two team entries specified in the form.

        A confirmation will be asked if the team we're merging from still
        has active members, as in that case we'll have to deactivate all
        members first.
        """
        self.setUpPeople(data)
        if self.dupe_person.activemembers.count() > 0:
            # Merging teams with active members is not possible, so we'll
            # ask the admin if he wants to deactivate all members and then
            # merge.
            self.should_confirm_member_deactivation = True
            return
        self.doMerge(data)

    @action('Deactivate Members and Merge',
            name='deactivate_members_and_merge')
    def deactivate_members_and_merge_action(self, action, data):
        """Deactivate all members of the team to be merged and merge them."""
        self.setUpPeople(data)
        comment = (
            'Deactivating all members as this team is being merged into %s. '
            'Please contact the administrators of <%s> if you have any '
            'issues with this change.'
            % (self.target_person.unique_displayname,
               canonical_url(self.target_person)))
        self.dupe_person.deactivateAllMembers(comment, self.user)
        flush_database_updates()
        self.doMerge(data)


class DeleteTeamView(AdminTeamMergeView):
    """A view that deletes a team by merging it with Registry experts."""

    page_title = 'Delete'
    field_names = ['dupe_person', 'target_person']
    merge_message = _('Team deleted.')

    @property
    def label(self):
        return 'Delete %s' % self.context.displayname

    def __init__(self, context, request):
        super(DeleteTeamView, self).__init__(context, request)
        if ('field.dupe_person' in self.request.form
            or 'field.target_person' in self.request.form):
            # These fields have fixed values and are managed by this method.
            # The user has crafted a request to gain ownership of the dupe
            # team's assets.
            self.addError('Unable to process submitted data.')
        elif 'field.actions.delete' in self.request.form:
            # In the case of deleting a team, the form values are always
            # the context team, and the registry experts team. These values
            # are injected during __init__ because the base classes assume the
            # values are submitted. The validations performed by the base
            # classes are still required to ensure the team can be deleted.
            self.request.form.update(self.default_values)
        else:
            # Show the page explaining the action.
            pass

    @property
    def default_values(self):
        return {
            'field.dupe_person': self.context.name,
            'field.target_person': getUtility(
                ILaunchpadCelebrities).registry_experts.name,
            }

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @property
    def success_url(self):
        return canonical_url(getUtility(IPersonSet))

    @property
    def has_mailing_list(self):
        return self.hasMailingList(self.context)

    def canDelete(self, data):
        return not self.has_mailing_list

    @action('Delete', name='delete', condition=canDelete)
    def merge_action(self, action, data):
        base = super(DeleteTeamView, self)
        base.deactivate_members_and_merge_action.success(data)


class FinishedPeopleMergeRequestView(LaunchpadView):
    """A simple view for a page where we only tell the user that we sent the
    email with further instructions to complete the merge.

    This view is used only when the dupe account has a single email address.
    """

    def initialize(self):
        user = getUtility(ILaunchBag).user
        try:
            dupe_id = int(self.request.get('dupe'))
        except (ValueError, TypeError):
            self.request.response.redirect(canonical_url(user))
            return

        dupe_account = getUtility(IPersonSet).get(dupe_id)
        results = getUtility(IEmailAddressSet).getByPerson(dupe_account)

        result_count = results.count()
        if not result_count:
            # The user came back to visit this page with nothing to
            # merge, so we redirect him away to somewhere useful.
            self.request.response.redirect(canonical_url(user))
            return
        assert result_count == 1
        # Need to remove the security proxy because the dupe account may have
        # hidden email addresses.
        self.dupe_email = removeSecurityProxy(results[0]).email

    def render(self):
        if self.dupe_email:
            return LaunchpadView.render(self)
        else:
            return ''


class RequestPeopleMergeMultipleEmailsView:
    """Merge request view when dupe account has multiple email addresses."""

    label = 'Merge Launchpad accounts'
    page_title = label

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form_processed = False
        self.dupe = None
        self.notified_addresses = []
        self.user = getUtility(ILaunchBag).user

    def processForm(self):
        dupe = self.request.form.get('dupe')
        if dupe is None:
            # We just got redirected to this page and we don't have the dupe
            # hidden field in request.form.
            dupe = self.request.get('dupe')
            if dupe is None:
                return

        self.dupe = getUtility(IPersonSet).get(int(dupe))
        emailaddrset = getUtility(IEmailAddressSet)
        self.dupeemails = emailaddrset.getByPerson(self.dupe)

        if self.request.method != "POST":
            return

        login = getUtility(ILaunchBag).login
        logintokenset = getUtility(ILoginTokenSet)

        email_addresses = []
        if self.email_hidden:
            # If the email addresses are hidden we must send a merge request
            # to each of them.  But first we've got to remove the security
            # proxy so we can get to them.
            email_addresses = [removeSecurityProxy(email).email
                               for email in self.dupeemails]
        else:
            # Otherwise we send a merge request only to the ones the user
            # selected.
            emails = self.request.form.get("selected")
            if emails is not None:
                # We can have multiple email addresses selected, and in this
                # case emails will be a list. Otherwise it will be a string
                # and we need to make a list with that value to use in the for
                # loop.
                if not isinstance(emails, list):
                    emails = [emails]

                for emailaddress in emails:
                    email = emailaddrset.getByEmail(emailaddress)
                    if email is None or email not in self.dupeemails:
                        # The dupe person has changes his email addresses.
                        # See bug 239838.
                        self.request.response.addNotification(
                            "An address was removed from the duplicate "
                            "account while you were making this merge "
                            "request. Select again.")
                        return
                    email_addresses.append(emailaddress)

        for emailaddress in email_addresses:
            token = logintokenset.new(
                self.user, login, emailaddress, LoginTokenType.ACCOUNTMERGE)
            token.sendMergeRequestEmail()
            self.notified_addresses.append(emailaddress)
        self.form_processed = True

    @property
    def cancel_url(self):
        """Cancel URL."""
        return canonical_url(self.user)

    @property
    def email_hidden(self):
        """Does the duplicate account hide email addresses?"""
        return self.dupe.hide_email_addresses
    

class RequestPeopleMergeView(LaunchpadFormView):
    """The view for the page where the user asks a merge of two accounts.

    If the dupe account have only one email address we send a message to that
    address and then redirect the user to other page saying that everything
    went fine. Otherwise we redirect the user to another page where we list
    all email addresses owned by the dupe account and the user selects which
    of those (s)he wants to claim.
    """

    label = 'Merge Launchpad accounts'
    page_title = label
    schema = IRequestPeopleMerge

    def validate(self, data):
        """Check that user is not attempting to merge a person into itself."""
        dupe_person = data.get('dupe_person')
        target_person = data.get('target_person')
        if dupe_person == target_person and dupe_person is not None:
            self.addError(_("You can't merge ${name} into itself.",
                  mapping=dict(name=dupe_person.name)))
        # We cannot merge the teams if there is a PPA with published
        # packages on the duplicate person, unless that PPA is removed.
        dupe_person_ppas = getUtility(IArchiveSet).getPPAOwnedByPerson(
            dupe_person, statuses=[ArchiveStatus.ACTIVE,
                                   ArchiveStatus.DELETING])
        if dupe_person_ppas is not None:
            self.addError(_(
                "${name} has a PPA that must be deleted before it "
                "can be merged. It may take ten minutes to remove the "
                "deleted PPA's files.",
                mapping=dict(name=dupe_person.name)))

    @property
    def cancel_url(self):
        return canonical_url(getUtility(IPersonSet))

    @action('Continue', name='continue')
    def continue_action(self, action, data):
        dupeaccount = data['dupe_person']
        if dupeaccount == self.user:
            # Please, don't try to merge you into yourself.
            return

        emails = getUtility(IEmailAddressSet).getByPerson(dupeaccount)
        emails_count = emails.count()
        if emails_count > 1:
            # The dupe account have more than one email address. Must redirect
            # the user to another page to ask which of those emails (s)he
            # wants to claim.
            self.next_url = '+requestmerge-multiple?dupe=%d' % dupeaccount.id
            return

        assert emails_count == 1
        email = emails[0]
        login = getUtility(ILaunchBag).login
        logintokenset = getUtility(ILoginTokenSet)
        # Need to remove the security proxy because the dupe account may have
        # hidden email addresses.
        token = logintokenset.new(
            self.user, login, removeSecurityProxy(email).email,
            LoginTokenType.ACCOUNTMERGE)

        # XXX: SteveAlexander 2006-03-07: An experiment to see if this
        #      improves problems with merge people tests.
        import canonical.database.sqlbase
        canonical.database.sqlbase.flush_database_updates()
        token.sendMergeRequestEmail()
        self.next_url = './+mergerequest-sent?dupe=%d' % dupeaccount.id
