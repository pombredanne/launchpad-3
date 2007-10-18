# Copyright 2007 Canonical Ltd

"""People Merge related wiew classes."""

__metaclass__ = type

__all__ = [
    'AdminPeopleMergeView',
    'AdminTeamMergeView',
    'FinishedPeopleMergeRequestView',
    'RequestPeopleMergeMultipleEmailsView',
    'RequestPeopleMergeView']

from zope.app.form.browser.add import AddView
from zope.component import getUtility

from canonical.database.sqlbase import flush_database_updates

from canonical.launchpad.interfaces import (
    EmailAddressStatus, IAdminPeopleMergeSchema, IAdminTeamMergeSchema,
    IEmailAddressSet, ILaunchBag, ILoginTokenSet, IMailingListSet, IPersonSet,
    LoginTokenType)

from canonical.launchpad import _
from canonical.launchpad.webapp import (
    action, canonical_url, LaunchpadFormView, LaunchpadView)


class RequestPeopleMergeView(AddView):
    """The view for the page where the user asks a merge of two accounts.

    If the dupe account have only one email address we send a message to that
    address and then redirect the user to other page saying that everything
    went fine. Otherwise we redirect the user to another page where we list
    all email addresses owned by the dupe account and the user selects which
    of those (s)he wants to claim.
    """

    _nextURL = '.'

    def nextURL(self):
        return self._nextURL

    def createAndAdd(self, data):
        user = getUtility(ILaunchBag).user
        dupeaccount = data['dupeaccount']
        if dupeaccount == user:
            # Please, don't try to merge you into yourself.
            return

        emails = getUtility(IEmailAddressSet).getByPerson(dupeaccount)
        emails_count = emails.count()
        if emails_count > 1:
            # The dupe account have more than one email address. Must redirect
            # the user to another page to ask which of those emails (s)he
            # wants to claim.
            self._nextURL = '+requestmerge-multiple?dupe=%d' % dupeaccount.id
            return

        assert emails_count == 1
        email = emails[0]
        login = getUtility(ILaunchBag).login
        logintokenset = getUtility(ILoginTokenSet)
        token = logintokenset.new(user, login, email.email,
                                  LoginTokenType.ACCOUNTMERGE)

        # XXX: SteveAlexander 2006-03-07: An experiment to see if this
        #      improves problems with merge people tests.
        import canonical.database.sqlbase
        canonical.database.sqlbase.flush_database_updates()
        token.sendMergeRequestEmail()
        self._nextURL = './+mergerequest-sent?dupe=%d' % dupeaccount.id


class AdminMergeBaseView(LaunchpadFormView):
    """Base view for the pages where admins can merge people/teams."""

    # Both subclasses share the same template so we need to define these
    # variables (which are used in the template) here rather than on
    # subclasses.
    should_confirm_email_reassignment = False
    should_confirm_member_deactivation = False

    dupe_person_emails = ()
    dupe_person = None
    target_person = None

    def validate(self, data):
        """Check that user is not attempting to merge a person into itself."""
        dupe_person = data.get('dupe_person')
        target_person = data.get('target_person')
        if dupe_person == target_person and dupe_person is not None:
            self.addError(
                _("You can't merge %s into itself." % dupe_person.name))

    def render(self):
        # Subclasses may define other actions that they will render manually
        # only in certain circunstances, so don't include them in the list of
        # actions to be rendered.
        self.actions = [self.merge_action]
        return super(AdminMergeBaseView, self).render()

    def setUpData(self, data):
        emailset = getUtility(IEmailAddressSet)
        self.dupe_person = data['dupe_person']
        self.target_person = data['target_person']
        self.dupe_person_emails = emailset.getByPerson(self.dupe_person)

    def doMerge(self, data):
        """Merge the two person/team entries specified in the form."""
        for email in self.dupe_person_emails:
            # XXX: Maybe this status change should be done only when merging
            # people but not when merging teams.
            # -- Guilherme Salgado, 2007-10-15
            email.status = EmailAddressStatus.NEW
            email.person = self.target_person
        flush_database_updates()
        getUtility(IPersonSet).merge(self.dupe_person, self.target_person)
        self.request.response.addInfoNotification(_(
            'Merge completed successfully.'))
        self.next_url = canonical_url(self.target_person)


class AdminPeopleMergeView(AdminMergeBaseView):

    label = "Merge Launchpad people"
    schema = IAdminPeopleMergeSchema

    @action('Merge', name='merge')
    def merge_action(self, action, data):
        """Merge the two person entries specified in the form.

        If we're merging a person which has email addresses associated with
        we'll ask for confirmation before actually performing the merge.
        """
        self.setUpData(data)
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
        self.setUpData(data)
        self.doMerge(data)


class AdminTeamMergeView(AdminMergeBaseView):
    """A view for merging two Teams.

    The duplicate team cannot be associated with a mailing list.
    """

    label = "Merge Launchpad teams"
    schema = IAdminTeamMergeSchema

    def validate(self, data):
        """Check there are no mailing lists associated with the dupe team."""
        super(AdminTeamMergeView, self).validate(data)
        mailing_list = getUtility(IMailingListSet).get(
            data['dupe_person'].name)
        if mailing_list is not None:
            self.addError(_(
                "%s is associated with a Launchpad mailing list; we can't "
                "merge it." % data['dupe_person'].name))

    @action('Merge', name='merge')
    def merge_action(self, action, data):
        """Merge the two team entries specified in the form.

        A confirmation will be asked if the team we're merging from still
        has active members, as in that case we'll have to deactivate all
        members first.
        """
        self.setUpData(data)
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
        self.setUpData(data)
        comment = (
            'Deactivating all members as this team is being merged into %s. '
            'Please contact the administrators of <%s> if you have any '
            'issues with this change.'
            % (self.target_person.unique_displayname,
               canonical_url(self.target_person)))
        self.dupe_person.deactivateAllMembers(comment, self.user)
        flush_database_updates()
        self.doMerge(data)


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
        self.dupe_email = results[0].email

    def render(self):
        if self.dupe_email:
            return LaunchpadView.render(self)
        else:
            return ''


class RequestPeopleMergeMultipleEmailsView:
    """A view for the page where the user asks a merge and the dupe account
    have more than one email address."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form_processed = False
        self.dupe = None
        self.notified_addresses = []

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

        self.form_processed = True
        user = getUtility(ILaunchBag).user
        login = getUtility(ILaunchBag).login
        logintokenset = getUtility(ILoginTokenSet)

        emails = self.request.form.get("selected")
        if emails is not None:
            # We can have multiple email adressess selected, and in this case
            # emails will be a list. Otherwise it will be a string and we need
            # to make a list with that value to use in the for loop.
            if not isinstance(emails, list):
                emails = [emails]

            for email in emails:
                emailaddress = emailaddrset.getByEmail(email)
                assert emailaddress in self.dupeemails
                token = logintokenset.new(
                    user, login, emailaddress.email,
                    LoginTokenType.ACCOUNTMERGE)
                token.sendMergeRequestEmail()
                self.notified_addresses.append(emailaddress.email)


