# Copyright 2004-2008 Canonical Ltd

__metaclass__ = type
__all__ = [
    'HasRenewalPolicyMixin',
    'ProposedTeamMembersEditView',
    'TeamAddView',
    'TeamBrandingView',
    'TeamContactAddressView',
    'TeamEditView',
    'TeamMailingListConfigurationView',
    'TeamMailingListModerationView',
    'TeamMemberAddView',
    ]

from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.form.browser import TextAreaWidget
from zope.component import getUtility
from zope.formlib import form
from zope.interface import Interface
from zope.schema import Choice
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from canonical.database.sqlbase import flush_database_updates
from canonical.widgets import (
    HiddenUserWidget, LaunchpadRadioWidget, SinglePopupWidget)

from canonical.launchpad import _
from canonical.launchpad.fields import PublicPersonChoice
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, LaunchpadEditFormView,
    LaunchpadFormView)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.menu import structured
from canonical.launchpad.browser.branding import BrandingChangeView
from canonical.launchpad.interfaces import (
    EmailAddressStatus, IEmailAddressSet, ILaunchBag, ILoginTokenSet,
    IMailingList, IMailingListSet, IPersonSet, ITeam, ITeamContactAddressForm,
    ITeamCreation, LoginTokenType, MailingListStatus,
    PersonVisibility, TeamContactMethod, TeamMembershipStatus,
    TeamSubscriptionPolicy, UnexpectedFormData)
from canonical.launchpad.interfaces.validation import validate_new_team_email

class HasRenewalPolicyMixin:
    """Mixin to be used on forms which contain ITeam.renewal_policy.

    This mixin will short-circuit Launchpad*FormView when defining whether
    the renewal_policy widget should be displayed in a single or multi-line
    layout. We need that because that field has a very long title, thus
    breaking the page layout.

    Since this mixin short-circuits Launchpad*FormView in some cases, it must
    always precede Launchpad*FormView in the inheritance list.
    """

    def isMultiLineLayout(self, field_name):
        if field_name == 'renewal_policy':
            return True
        return super(HasRenewalPolicyMixin, self).isMultiLineLayout(
            field_name)

    def isSingleLineLayout(self, field_name):
        if field_name == 'renewal_policy':
            return False
        return super(HasRenewalPolicyMixin, self).isSingleLineLayout(
            field_name)


class TeamEditView(HasRenewalPolicyMixin, LaunchpadEditFormView):

    schema = ITeam
    field_names = [
        'teamowner', 'name', 'displayname', 'teamdescription',
        'subscriptionpolicy', 'defaultmembershipperiod',
        'renewal_policy', 'defaultrenewalperiod', 'visibility']
    custom_widget('teamowner', SinglePopupWidget, visible=False)
    custom_widget(
        'renewal_policy', LaunchpadRadioWidget, orientation='vertical')
    custom_widget(
        'subscriptionpolicy', LaunchpadRadioWidget, orientation='vertical')

    @action('Save', name='save')
    def action_save(self, action, data):
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)

    def validate(self, data):
        if 'visibility' in data:
            visibility = data['visibility']
        else:
            visibility = self.context.visibility
        if visibility != PersonVisibility.PUBLIC:
            if 'visibility' in data:
                warning = self.context.visibility_consistency_warning
                if warning is not None:
                    self.setFieldError('visibility', warning)
            if (data['subscriptionpolicy']
                != TeamSubscriptionPolicy.RESTRICTED):
                self.setFieldError(
                    'subscriptionpolicy',
                    'Private teams must have a Restricted subscription'
                    ' policy.')

    def setUpFields(self):
        """See `LaunchpadViewForm`.

        Only Launchpad Admins get to see the visibility field.
        """
        super(TeamEditView, self).setUpFields()
        if not check_permission('launchpad.Admin', self.context):
            self.form_fields = self.form_fields.omit('visibility')

    def setUpWidgets(self):
        """See `LaunchpadViewForm`.

        When a team has a mailing list, renames are prohibited.
        """
        mailing_list = getUtility(IMailingListSet).get(self.context.name)
        if mailing_list is not None:
            # This makes the field's widget display (i.e. read) only.
            self.form_fields['name'].for_display = True
        super(TeamEditView, self).setUpWidgets()
        if mailing_list is not None:
            # We can't change the widget's .hint directly because that's a
            # read-only property.  But that property just delegates to the
            # context's underlying description, so change that instead.
            self.widgets['name'].context.description = _(
                'This team has a mailing list and may not be renamed.')


def generateTokenAndValidationEmail(email, team):
    """Send a validation message to the given email."""
    login = getUtility(ILaunchBag).login
    token = getUtility(ILoginTokenSet).new(
        team, login, email, LoginTokenType.VALIDATETEAMEMAIL)

    user = getUtility(ILaunchBag).user
    token.sendTeamEmailAddressValidationEmail(user)


class MailingListTeamBaseView(LaunchpadFormView):
    """A base view for manipulating a team's mailing list.

    This class contains common functionality for retrieving and
    checking the state of mailing lists.
    """

    def _getList(self):
        """Try to find a mailing list for this team.

        :return: The mailing list object, or None if this team has no
        mailing list.
        """
        return getUtility(IMailingListSet).get(self.context.name)

    def getListInState(self, *statuses):
        """Return this team's mailing list if it's in one of the given states.

        :param statuses: The states that the mailing list must be in for it to
            be returned.
        :return: This team's IMailingList or None if the team doesn't have
            a mailing list, or if it isn't in one of the given states.
        """
        mailing_list = self._getList()
        if mailing_list is not None and mailing_list.status in statuses:
            return mailing_list
        return None

    @property
    def list_is_usable(self):
        """Checks whether or not the list is usable; ie. accepting messages.

        The list must exist and must be in a state acceptable to
        MailingList.isUsable.
        """
        mailing_list = self._getList()
        return mailing_list is not None and mailing_list.isUsable()

    @property
    def mailinglist_address(self):
        """The address for this team's mailing list."""
        mailing_list = self._getList()
        assert mailing_list is not None, (
                'Attempt to find address of nonexistent mailing list.')
        return mailing_list.address


class TeamContactAddressView(MailingListTeamBaseView):
    """A view for manipulating the team's contact address."""

    schema = ITeamContactAddressForm
    label = "Contact address"
    custom_widget(
        'contact_method', LaunchpadRadioWidget, orientation='vertical')

    def setUpFields(self):
        """See `LaunchpadFormView`.
        """
        super(TeamContactAddressView, self).setUpFields()

        # Replace the default contact_method field by a custom one.
        self.form_fields = (
            form.FormFields(self.getContactMethodField())
            + self.form_fields.omit('contact_method'))

    def getContactMethodField(self):
        """Create the form.Fields to use for the contact_method field.

        If the team has a mailing list that can be the team contact
        method, the full range of TeamContactMethod terms shows up
        in the contact_method vocabulary. Otherwise, the HOSTED_LIST
        term does not show up in the vocabulary.
        """
        terms = [term for term in TeamContactMethod]
        for i, term in enumerate(TeamContactMethod):
            if term.value == TeamContactMethod.HOSTED_LIST:
                hosted_list_term_index = i
                break
        if self.list_is_usable:
            # The team's mailing list can be used as the contact
            # address. However we need to change the title of the
            # corresponding term to include the list's email address.
            title = ('The Launchpad mailing list for this team - '
                     '<strong>%s</strong>' % self.mailinglist_address)
            hosted_list_term = SimpleTerm(
                TeamContactMethod.HOSTED_LIST,
                TeamContactMethod.HOSTED_LIST.name, title)
            terms[hosted_list_term_index] = hosted_list_term
        else:
            # The team's mailing list does not exist or can't be
            # used as the contact address. Remove the term from the
            # field.
            del terms[hosted_list_term_index]

        return form.FormField(
            Choice(__name__='contact_method',
                   title=_("How do people contact this team's members?"),
                   required=True, vocabulary=SimpleVocabulary(terms)),
            custom_widget=self.custom_widgets['contact_method'])

    def validate(self, data):
        """Validate the team contact email address.

        Validation only occurs if the user wants to use an external address,
        and the given email address is not already in use by this team.
        This also ensures the mailing list is active if the HOSTED_LIST option
        has been chosen.
        """
        if data['contact_method'] == TeamContactMethod.EXTERNAL_ADDRESS:
            email = data['contact_address']
            if not email:
                self.setFieldError(
                   'contact_address',
                   'Enter the contact address you want to use for this team.')
                return
            email = getUtility(IEmailAddressSet).getByEmail(
                data['contact_address'])
            if email is None or email.person != self.context:
                try:
                    validate_new_team_email(data['contact_address'])
                except LaunchpadValidationError, error:
                    # We need to wrap this in structured, so that the
                    # markup is preserved.  Note that this puts the
                    # responsibility for security on the exception thrower.
                    self.setFieldError('contact_address',
                                       structured(str(error)))
        elif data['contact_method'] == TeamContactMethod.HOSTED_LIST:
            mailing_list = getUtility(IMailingListSet).get(self.context.name)
            if mailing_list is None or not mailing_list.isUsable():
                self.addError(
                    "This team's mailing list is not active and may not be "
                    "used as its contact address yet")
        else:
            # Nothing to validate!
            pass

    @property
    def initial_values(self):
        """Infer the contact method from this team's preferredemail.

        Return a dictionary representing the contact_address and
        contact_method so inferred.
        """
        context = self.context
        if context.preferredemail is None:
            return dict(contact_method=TeamContactMethod.NONE)
        mailing_list = getUtility(IMailingListSet).get(context.name)
        if (mailing_list is not None
            and mailing_list.address == context.preferredemail.email):
            return dict(contact_method=TeamContactMethod.HOSTED_LIST)
        return dict(contact_address=context.preferredemail.email,
                    contact_method=TeamContactMethod.EXTERNAL_ADDRESS)

    @action('Change', name='change')
    def change_action(self, action, data):
        """Changes the contact address for this mailing list."""
        context = self.context
        email_set = getUtility(IEmailAddressSet)
        list_set = getUtility(IMailingListSet)
        contact_method = data['contact_method']
        if contact_method == TeamContactMethod.NONE:
            if context.preferredemail is not None:
                # The user wants the mailing list to stop being the
                # team's contact address, but not to be deactivated
                # altogether. So we demote the list address from
                # 'preferred' address to being just a regular address.
                context.preferredemail.status = EmailAddressStatus.VALIDATED
        elif contact_method == TeamContactMethod.HOSTED_LIST:
            mailing_list = list_set.get(context.name)
            assert mailing_list is not None and mailing_list.isUsable(), (
                "A team can only use a usable mailing list as its contact "
                "address.")
            context.setContactAddress(
                email_set.getByEmail(mailing_list.address))
        elif contact_method == TeamContactMethod.EXTERNAL_ADDRESS:
            contact_address = data['contact_address']
            email = email_set.getByEmail(contact_address)
            if email is None:
                generateTokenAndValidationEmail(contact_address, context)
                self.request.response.addInfoNotification(
                    "A confirmation message has been sent to '%s'. Follow "
                    "the instructions in that message to confirm the new "
                    "contact address for this team. (If the message "
                    "doesn't arrive in a few minutes, your mail provider "
                    "might use 'greylisting', which could delay the "
                    "message for up to an hour or two.)" % contact_address)
            else:
                context.setContactAddress(email)
        else:
            raise UnexpectedFormData(
                "Unknown contact_method: %s" % contact_method)

        self.next_url = canonical_url(self.context)


class TeamMailingListConfigurationView(MailingListTeamBaseView):
    """A view for creating and configuring a team's mailing list.

    Allows creating a request for a list, cancelling the request,
    setting the welcome message, deactivating, and reactivating the
    list.
    """

    schema = IMailingList
    field_names = ['welcome_message']
    label = "Mailing list configuration"
    custom_widget('welcome_message', TextAreaWidget, width=72, height=10)

    def __init__(self, context, request):
        """Set feedback messages for users who want to edit the mailing list.

        There are a number of reasons why your changes to the mailing
        list might not take effect immediately. First, the mailing
        list may not actually be set as the team contact
        address. Second, the mailing list may be in a transitional
        state: from MODIFIED to UPDATING to ACTIVE can take a while.
        """
        super(TeamMailingListConfigurationView, self).__init__(
            context, request)
        list_set = getUtility(IMailingListSet)
        self.mailing_list = list_set.get(self.context.name)

    @action('Save', name='save')
    def save_action(self, action, data):
        """Sets the welcome message for a mailing list."""
        welcome_message = data.get('welcome_message')
        assert (self.mailing_list is not None
                and self.mailing_list.isUsable()), (
            "Only a usable mailing list can be configured.")

        if (welcome_message is not None
            and welcome_message != self.mailing_list.welcome_message):
            self.mailing_list.welcome_message = welcome_message

        self.next_url = canonical_url(self.context)

    def cancel_list_creation_validator(self, action, data):
        """Validator for the `cancel_list_creation` action.

        Adds an error if someone tries to cancel a request that's
        already been approved or declined. This can only happen
        through bypassing the UI.
        """
        mailing_list = getUtility(IMailingListSet).get(self.context.name)
        if self.getListInState(MailingListStatus.REGISTERED) is None:
            self.addError("This application can't be cancelled.")

    @action('Cancel Application', name='cancel_list_creation',
            validator=cancel_list_creation_validator)
    def cancel_list_creation(self, action, data):
        """Cancels a pending mailing list registration."""
        mailing_list_set = getUtility(IMailingListSet)
        mailing_list_set.get(self.context.name).cancelRegistration()
        self.request.response.addInfoNotification(
            "Mailing list application cancelled.")
        self.next_url = canonical_url(self.context)

    def request_list_creation_validator(self, action, data):
        """Validator for the `request_list_creation` action.

        Adds an error if someone tries to request a mailing list for a
        team that already has one. This can only happen through
        bypassing the UI.
        """
        if not self.list_can_be_requested:
            self.addError(
                "You cannot request a new mailing list for this team.")

    @action('Apply for Mailing List', name='request_list_creation',
            validator=request_list_creation_validator)
    def request_list_creation(self, action, data):
        """Creates a new mailing list."""
        list_set = getUtility(IMailingListSet)
        mailing_list = list_set.get(self.context.name)
        assert mailing_list is None, (
            'Tried to create a mailing list for a team that already has one.')
        list_set.new(self.context)
        self.request.response.addInfoNotification(
            "Mailing list requested and queued for approval.")
        self.next_url = canonical_url(self.context)

    def deactivate_list_validator(self, action, data):
        """Adds an error if someone tries to deactivate a non-active list.

        This can only happen through bypassing the UI.
        """
        if not self.list_can_be_deactivated:
            self.addError("This list can't be deactivated.")

    @action('Deactivate this Mailing List', name='deactivate_list',
            validator=deactivate_list_validator)
    def deactivate_list(self, action, data):
        """Deactivates a mailing list."""
        getUtility(IMailingListSet).get(self.context.name).deactivate()
        self.request.response.addInfoNotification(
            "The mailing list will be deactivated within a few minutes.")
        self.next_url = canonical_url(self.context)

    def reactivate_list_validator(self, action, data):
        """Adds an error if a non-deactivated list is reactivated.

        This can only happen through bypassing the UI.
        """
        if not self.list_can_be_reactivated:
            self.addError("Only a deactivated list can be reactivated.")

    @action('Reactivate this Mailing List', name='reactivate_list',
            validator=reactivate_list_validator)
    def reactivate_list(self, action, data):
        getUtility(IMailingListSet).get(self.context.name).reactivate()
        self.request.response.addInfoNotification(
            "The mailing list will be reactivated within a few minutes.")
        self.next_url = canonical_url(self.context)

    @property
    def list_is_usable_but_not_contact_method(self):
        """The list could be the contact method for its team, but isn't.

        The list exists and is usable, but isn't set as the contact
        method.
        """

        return (self.list_is_usable and
                (self.context.preferredemail is None or
                 self.mailing_list.address !=
                 self.context.preferredemail.email))

    @property
    def mailing_list_status_message(self):
        """A status message describing the state of the mailing list.

        This status message helps a user be aware of behind-the-scenes
        processes that would otherwise manifest only as mysterious
        failures and inconsistencies.
        """

        if not self.mailing_list:
            return None
        elif self.mailing_list.status == MailingListStatus.REGISTERED:
            return None
        elif self.mailing_list.status in [MailingListStatus.APPROVED,
                                          MailingListStatus.CONSTRUCTING]:
            return _("This team's mailing list will be available within "
                     "a few minutes.")
        elif self.mailing_list.status == MailingListStatus.DECLINED:
            return _("The application for this team's mailing list has been "
                     'declined. Please '
                     '<a href="https://help.launchpad.net/FAQ#contact-admin">'
                     'contact a Launchpad administrator</a> for further '
                     'assistance.')
        elif self.mailing_list.status == MailingListStatus.ACTIVE:
            return None
        elif self.mailing_list.status == MailingListStatus.DEACTIVATING:
            return _("This team's mailing list is being deactivated.")
        elif self.mailing_list.status == MailingListStatus.INACTIVE:
            return _("This team's mailing list has been deactivated.")
        elif self.mailing_list.status == MailingListStatus.FAILED:
            return _("This team's mailing list could not be created. Please "
                     '<a href="https://help.launchpad.net/FAQ#contact-admin">'
                     'contact a Launchpad administrator</a> for further '
                     'assistance.')
        elif self.mailing_list.status == MailingListStatus.MODIFIED:
            return _("An update to this team's mailing list is pending "
                     "and has not yet taken effect.")
        elif self.mailing_list.status == MailingListStatus.UPDATING:
            return _("A change to this team's mailing list is currently "
                     "being applied.")
        elif self.mailing_list.status == MailingListStatus.MOD_FAILED:
            return _("This team's mailing list is in an inconsistent state "
                     'because a change to its configuration was not applied. '
                     'Please '
                     '<a href="https://help.launchpad.net/FAQ#contact-admin">'
                     'contact a Launchpad administrator</a> for further '
                     'assistance.')
        else:
            raise AssertionError(
                "Unknown mailing list status: %s" % self.mailing_list.status)

    @property
    def initial_values(self):
        """The initial value of welcome_message comes from the database.

        :return: A dictionary containing the current welcome message.
        """
        context = self.context
        if self.mailing_list is not None:
            return dict(welcome_message=self.mailing_list.welcome_message)
        else:
            return {}

    @property
    def list_application_can_be_cancelled(self):
        """Can this team's mailing list request be cancelled?

        It can only be cancelled if its state is REGISTERED.
        """
        return self.getListInState(MailingListStatus.REGISTERED) is not None

    @property
    def list_can_be_requested(self):
        """Can a mailing list be requested for this team?

        It can only be requested if there's no mailing list associated with
        this team.
        """
        mailing_list = getUtility(IMailingListSet).get(self.context.name)
        return mailing_list is None

    @property
    def list_can_be_deactivated(self):
        """Is this team's list in a state where it can be deactivated?

        The list must exist and be in the ACTIVE state.
        """
        return self.getListInState(MailingListStatus.ACTIVE) is not None

    @property
    def list_can_be_reactivated(self):
        """Is this team's list in a state where it can be reactivated?

        The list must exist and be in the INACTIVE state.
        """
        return self.getListInState(MailingListStatus.INACTIVE) is not None


class TeamMailingListModerationView(MailingListTeamBaseView):
    """A view for moderating the held messages of a mailing list."""

    schema = IMailingList
    field_names = []
    label = 'Mailing list moderation'

    def __init__(self, context, request):
        """Set feedback messages for users who want to edit the mailing list.

        There are a number of reasons why your changes to the mailing
        list might not take effect immediately. First, the mailing
        list may not actually be set as the team contact
        address. Second, the mailing list may be in a transitional
        state: from MODIFIED to UPDATING to ACTIVE can take a while.
        """
        super(TeamMailingListModerationView, self).__init__(
            context, request)
        list_set = getUtility(IMailingListSet)
        self.mailing_list = list_set.get(self.context.name)


class TeamAddView(HasRenewalPolicyMixin, LaunchpadFormView):

    schema = ITeamCreation
    label = ''
    field_names = ["name", "displayname", "contactemail", "teamdescription",
                   "subscriptionpolicy", "defaultmembershipperiod",
                   "renewal_policy", "defaultrenewalperiod", "teamowner"]
    custom_widget('teamowner', HiddenUserWidget)
    custom_widget('teamdescription', TextAreaWidget, height=10, width=30)
    custom_widget(
        'renewal_policy', LaunchpadRadioWidget, orientation='vertical')
    custom_widget(
        'subscriptionpolicy', LaunchpadRadioWidget, orientation='vertical')

    @action('Create', name='create')
    def create_action(self, action, data):
        name = data.get('name')
        displayname = data.get('displayname')
        teamdescription = data.get('teamdescription')
        defaultmembershipperiod = data.get('defaultmembershipperiod')
        defaultrenewalperiod = data.get('defaultrenewalperiod')
        subscriptionpolicy = data.get('subscriptionpolicy')
        teamowner = data.get('teamowner')
        team = getUtility(IPersonSet).newTeam(
            teamowner, name, displayname, teamdescription,
            subscriptionpolicy, defaultmembershipperiod, defaultrenewalperiod)
        notify(ObjectCreatedEvent(team))

        email = data.get('contactemail')
        if email is not None:
            generateTokenAndValidationEmail(email, team)
            self.request.response.addNotification(
                "A confirmation message has been sent to '%s'. Follow the "
                "instructions in that message to confirm the new "
                "contact address for this team. "
                "(If the message doesn't arrive in a few minutes, your mail "
                "provider might use 'greylisting', which could delay the "
                "message for up to an hour or two.)" % email)

        self.next_url = canonical_url(team)


class ProposedTeamMembersEditView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user

    def processProposed(self):
        if self.request.method != "POST":
            return

        team = self.context
        expires = team.defaultexpirationdate
        for person in team.proposedmembers:
            action = self.request.form.get('action_%d' % person.id)
            if action == "approve":
                status = TeamMembershipStatus.APPROVED
            elif action == "decline":
                status = TeamMembershipStatus.DECLINED
            elif action == "hold":
                continue

            team.setMembershipData(
                person, status, reviewer=self.user, expires=expires)

        # Need to flush all changes we made, so subsequent queries we make
        # with this transaction will see this changes and thus they'll be
        # displayed on the page that calls this method.
        flush_database_updates()
        self.request.response.redirect('%s/+members' % canonical_url(team))


class TeamBrandingView(BrandingChangeView):

    schema = ITeam
    field_names = ['icon', 'logo', 'mugshot']


class ITeamMember(Interface):
    """The interface used in the form to add a new member to a team."""

    newmember = PublicPersonChoice(
        title=_('New member'), required=True,
        vocabulary='ValidTeamMember',
        description=_("The user or team which is going to be "
                        "added as the new member of this team."))


class TeamMemberAddView(LaunchpadFormView):

    schema = ITeamMember
    label = "Select the new member"

    def validate(self, data):
        """Verify new member.

        This checks that the new member has some active members and is not
        already an active team member.
        """
        newmember = data.get('newmember')
        error = None
        if newmember is not None:
            if newmember.isTeam() and not newmember.activemembers:
                error = _("You can't add a team that doesn't have any active"
                          " members.")
            elif newmember in self.context.activemembers:
                error = _("%s (%s) is already a member of %s." % (
                    newmember.browsername, newmember.name,
                    self.context.browsername))

        if error:
            self.setFieldError("newmember", error)

    @action(u"Add Member", name="add")
    def add_action(self, action, data):
        """Add the new member to the team."""
        newmember = data['newmember']
        # If we get to this point with the member being the team itself,
        # it means the ValidTeamMemberVocabulary is broken.
        assert newmember != self.context, (
            "Can't add team to itself: %s" % newmember)

        self.context.addMember(newmember, reviewer=self.user,
                               status=TeamMembershipStatus.APPROVED)
        if newmember.isTeam():
            msg = "%s has been invited to join this team." % (
                  newmember.unique_displayname)
        else:
            msg = "%s has been added as a member of this team." % (
                  newmember.unique_displayname)
        self.request.response.addInfoNotification(msg)

