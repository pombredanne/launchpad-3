# Copyright 2004-2009 Canonical Ltd

__metaclass__ = type
__all__ = [
    'HasRenewalPolicyMixin',
    'ProposedTeamMembersEditView',
    'TeamAddView',
    'TeamBadges',
    'TeamBrandingView',
    'TeamContactAddressView',
    'TeamEditView',
    'TeamMailingListConfigurationView',
    'TeamMailingListModerationView',
    'TeamMapView',
    'TeamMapData',
    'TeamMemberAddView',
    'TeamPrivacyAdapter',
    ]

from urllib import quote
from datetime import datetime
import pytz

from zope.app.form.browser import TextAreaWidget
from zope.component import getUtility
from zope.formlib import form
from zope.interface import Interface, implements
from zope.schema import Choice
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from canonical.widgets import (
    HiddenUserWidget, LaunchpadRadioWidget, SinglePopupWidget)

from canonical.launchpad import _
from canonical.launchpad.browser.branding import BrandingChangeView
from canonical.launchpad.fields import PublicPersonChoice
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.cachedproperty import cachedproperty
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, LaunchpadEditFormView,
    LaunchpadFormView, LaunchpadView)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.badge import HasBadgeBase
from canonical.launchpad.webapp.interfaces import (
    ILaunchBag, UnexpectedFormData)
from canonical.launchpad.webapp.menu import structured
from canonical.launchpad.interfaces.emailaddress import IEmailAddressSet
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.interfaces.logintoken import (
    ILoginTokenSet, LoginTokenType)
from canonical.launchpad.interfaces.mailinglist import (
    IMailingList, IMailingListSet, MailingListStatus, PURGE_STATES,
    PostedMessageStatus)
from canonical.launchpad.interfaces.person import (
    IPerson, IPersonSet, ITeam, ITeamContactAddressForm, ITeamCreation,
    ImmutableVisibilityError, PRIVATE_TEAM_PREFIX, PersonVisibility,
    TeamContactMethod, TeamSubscriptionPolicy)
from canonical.launchpad.interfaces.teammembership import TeamMembershipStatus
from canonical.launchpad.interfaces.validation import validate_new_team_email
from canonical.lazr.interfaces import IObjectPrivacy


class TeamPrivacyAdapter:
    """Provides `IObjectPrivacy` for `ITeam`."""

    implements(IObjectPrivacy)

    def __init__(self, context):
        self.context = context

    @property
    def is_private(self):
        """Return True if the team is private, otherwise False."""
        return self.context.visibility != PersonVisibility.PUBLIC


class TeamBadges(HasBadgeBase):
    """Provides `IHasBadges` for `ITeam`."""

    def getPrivateBadgeTitle(self):
        """Return private badge info useful for a tooltip."""
        return "This is a %s team" % self.context.visibility.title.lower()


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


class TeamFormMixin:
    """Form to be used on forms which conditionally display team visiblity.

    The visibility field should only be shown to users with
    launchpad.Commercial permission on the team.
    """
    field_names = [
        "name", "visibility", "displayname", "contactemail",
        "teamdescription", "subscriptionpolicy",
        "defaultmembershipperiod", "renewal_policy",
        "defaultrenewalperiod",  "teamowner",
        ]
    private_prefix = PRIVATE_TEAM_PREFIX

    @property
    def _validate_visibility_consistency(self):
        """Perform a consistency check regarding visibility.

        This property must be overridden if the current context is not an
        IPerson.
        """
        return self.context.visibility_consistency_warning

    @property
    def _visibility(self):
        """Return the visibility for the object."""
        return self.context.visibility

    @property
    def _name(self):
        return self.context.name

    def validate(self, data):
        if 'visibility' in data:
            visibility = data['visibility']
        else:
            visibility = self._visibility
        if visibility != PersonVisibility.PUBLIC:
            if 'visibility' in data:
                warning = self._validate_visibility_consistency
                if warning is not None:
                    self.setFieldError('visibility', warning)
            if (data['subscriptionpolicy']
                != TeamSubscriptionPolicy.RESTRICTED):
                self.setFieldError(
                    'subscriptionpolicy',
                    'Private teams must have a Restricted subscription '
                    'policy.')

    def conditionallyOmitVisibility(self):
        """Remove the visibility field if not authorized."""
        if not check_permission('launchpad.Commercial', self.context):
            self.form_fields = self.form_fields.omit('visibility')


class TeamEditView(TeamFormMixin, HasRenewalPolicyMixin,
                   LaunchpadEditFormView):
    """View for editing team details."""
    schema = ITeam

    # teamowner cannot be a HiddenUserWidget or the edit form would change the
    # owner to the person doing the editing.
    custom_widget('teamowner', SinglePopupWidget, visible=False)
    custom_widget(
        'renewal_policy', LaunchpadRadioWidget, orientation='vertical')
    custom_widget(
        'subscriptionpolicy', LaunchpadRadioWidget, orientation='vertical')
    custom_widget('teamdescription', TextAreaWidget, height=10, width=30)

    def setUpFields(self):
        """See `LaunchpadViewForm`.

        When editing a team the contactemail field is not displayed.
        """
        # Make an instance copy of field_names so as to not modify the single
        # class list.
        self.field_names = list(self.field_names)
        self.field_names.remove('contactemail')
        super(TeamEditView, self).setUpFields()
        self.conditionallyOmitVisibility()

    @action('Save', name='save')
    def action_save(self, action, data):
        try:
            self.updateContextFromData(data)
        except ImmutableVisibilityError, error:
            self.request.response.addErrorNotification(str(error))
        self.next_url = canonical_url(self.context)

    def setUpWidgets(self):
        """See `LaunchpadViewForm`.

        When a team has a mailing list, renames are prohibited.
        """
        mailing_list = getUtility(IMailingListSet).get(self.context.name)
        writable = (mailing_list is None or
                    mailing_list.status == MailingListStatus.PURGED)
        if not writable:
            # This makes the field's widget display (i.e. read) only.
            self.form_fields['name'].for_display = True
        super(TeamEditView, self).setUpWidgets()
        if not writable:
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
        MailingList.is_usable.
        """
        mailing_list = self._getList()
        return mailing_list is not None and mailing_list.is_usable

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
                   required=True, vocabulary=SimpleVocabulary(terms)))

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
            if mailing_list is None or not mailing_list.is_usable:
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
            context.setContactAddress(None)
        elif contact_method == TeamContactMethod.HOSTED_LIST:
            mailing_list = list_set.get(context.name)
            assert mailing_list is not None and mailing_list.is_usable, (
                "A team can only use a usable mailing list as its contact "
                "address.")
            email = email_set.getByEmail(mailing_list.address)
            assert email is not None, (
                "Cannot find mailing list's posting address")
            context.setContactAddress(email)
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
                and self.mailing_list.is_usable), (
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
        getUtility(IMailingListSet).new(self.context)
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

    def purge_list_validator(self, action, data):
        """Adds an error if the list is not safe to purge.

        This can only happen through bypassing the UI.
        """
        if not self.list_can_be_purged:
            self.addError('This list cannot be purged.')

    @action('Purge this Mailing List', name='purge_list',
            validator=purge_list_validator)
    def purge_list(self, action, data):
        getUtility(IMailingListSet).get(self.context.name).purge()
        self.request.response.addInfoNotification(
            'The mailing list has been purged.')
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

        if (self.mailing_list is None or
            self.mailing_list.status == MailingListStatus.PURGED):
            # Purged lists act as if they don't exist.
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
        this team, or the mailing list has been purged.
        """
        mailing_list = getUtility(IMailingListSet).get(self.context.name)
        return (mailing_list is None or
                mailing_list.status == MailingListStatus.PURGED)

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

    @property
    def list_can_be_purged(self):
        """Is this team's list in a state where it can be purged?

        The list must exist and be in one of the REGISTERED, DECLINED, FAILED,
        or INACTIVE states.  Further, the user doing the purging, must be
        a Launchpad administrator or mailing list expert.
        """
        requester = IPerson(self.request.principal, None)
        celebrities = getUtility(ILaunchpadCelebrities)
        if (requester is None or
            (not requester.inTeam(celebrities.admin) and
             not requester.inTeam(celebrities.mailing_list_experts))):
            return False
        return self.getListInState(*PURGE_STATES) is not None


class TeamMailingListModerationView(MailingListTeamBaseView):
    """A view for moderating the held messages of a mailing list."""

    schema = Interface
    label = 'Mailing list moderation'

    def __init__(self, context, request):
        """Allow for review and moderation of held mailing list posts."""
        super(TeamMailingListModerationView, self).__init__(context, request)
        list_set = getUtility(IMailingListSet)
        self.mailing_list = list_set.get(self.context.name)
        assert(self.mailing_list is not None), (
            'No mailing list: %s' % self.context.name)

    @property
    def hold_count(self):
        """The number of message being held for moderator approval.

        :return: Number of message being held for moderator approval.
        """
        return self.mailing_list.getReviewableMessages().count()

    @property
    def held_messages(self):
        """All the messages being held for moderator approval.

        :return: Sequence of held messages.
        """
        return self.mailing_list.getReviewableMessages()

    @action('Moderate', name='moderate')
    def moderate_action(self, action, data):
        """Commits the moderation actions."""
        # We're somewhat abusing LaunchpadFormView, so the interesting bits
        # won't be in data.  Instead, get it out of the request.
        reviewable = self.hold_count
        disposed_count = 0
        for message in self.held_messages:
            action_name = self.request.form_ng.getOne(
                'field.' + quote(message.message_id))
            # This essentially acts like a switch statement or if/elifs.  It
            # looks the action up in a map of allowed actions, watching out
            # for bogus input.
            try:
                action, status = dict(
                    approve=(message.approve, PostedMessageStatus.APPROVED),
                    reject=(message.reject, PostedMessageStatus.REJECTED),
                    discard=(message.discard, PostedMessageStatus.DISCARDED),
                    # hold is a no-op.  Using None here avoids the bogus input
                    # trigger.
                    hold=(None, None),
                    )[action_name]
            except KeyError:
                raise UnexpectedFormData(
                    'Invalid moderation action for held message %s: %s' %
                    (message.message_id, action_name))
            if action is not None:
                disposed_count += 1
                action(self.user)
                self.request.response.addInfoNotification(
                    'Held message %s; Message-ID: %s' % (
                        status.title.lower(), message.message_id))
        still_held = reviewable - disposed_count
        if still_held > 0:
            self.request.response.addInfoNotification(
                'Messages still held for review: %d of %d' %
                (still_held, reviewable))
        self.next_url = canonical_url(self.context)


class TeamAddView(TeamFormMixin, HasRenewalPolicyMixin, LaunchpadFormView):
    """View for adding a new team."""
    schema = ITeamCreation
    label = ''

    custom_widget('teamowner', HiddenUserWidget)
    custom_widget(
        'renewal_policy', LaunchpadRadioWidget, orientation='vertical')
    custom_widget(
        'subscriptionpolicy', LaunchpadRadioWidget, orientation='vertical')
    custom_widget('teamdescription', TextAreaWidget, height=10, width=30)

    def setUpFields(self):
        """See `LaunchpadViewForm`.

        Only Launchpad Admins get to see the visibility field.
        """
        super(TeamAddView, self).setUpFields()
        self.conditionallyOmitVisibility()

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
        visibility = data.get('visibility')
        if visibility:
            team.visibility = visibility
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

    @property
    def _validate_visibility_consistency(self):
        """See `TeamFormMixin`."""
        return None

    @property
    def _visibility(self):
        """Return the visibility for the object.

        For a new team it is PUBLIC unless otherwise set in the form data.
        """
        return PersonVisibility.PUBLIC

    @property
    def _name(self):
        return None



class ProposedTeamMembersEditView(LaunchpadFormView):
    schema = Interface
    label = 'Proposed team members'

    @action('Save changes', name='save')
    def action_save(self, action, data):
        expires = self.context.defaultexpirationdate
        for person in self.context.proposedmembers:
            action = self.request.form.get('action_%d' % person.id)
            if action == "approve":
                status = TeamMembershipStatus.APPROVED
            elif action == "decline":
                status = TeamMembershipStatus.DECLINED
            elif action == "hold":
                continue

            self.context.setMembershipData(
                person, status, reviewer=self.user, expires=expires,
                comment=self.request.form.get('comment'))

    @property
    def next_url(self):
        return '%s/+members' % canonical_url(self.context)


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


class TeamMapView(LaunchpadView):
    """Show all people with known locations on a map.

    Also provides links to edit the locations of people in the team without
    known locations.
    """

    def initialize(self):
        # Tell our main-template to include Google's gmap2 javascript so that
        # we can render the map.
        if self.mapped_participants_count > 0:
            self.request.needs_gmap2 = True

    @cachedproperty
    def mapped_participants(self):
        """Participants with locations."""
        return self.context.mapped_participants

    @cachedproperty
    def mapped_participants_count(self):
        """Count of participants with locations."""
        return self.context.mapped_participants_count

    @property
    def has_mapped_participants(self):
        """Does the team have any mapped participants?"""
        return self.mapped_participants_count > 0

    @cachedproperty
    def unmapped_participants(self):
        """Participants (ordered by name) with no recorded locations."""
        return list(self.context.unmapped_participants)

    @cachedproperty
    def unmapped_participants_count(self):
        """Count of participants with no recorded locations."""
        return self.context.unmapped_participants_count

    @cachedproperty
    def times(self):
        """The current times in time zones with members."""
        zones = set(participant.time_zone
                    for participant in self.mapped_participants)
        times = [datetime.now(pytz.timezone(zone))
                 for zone in zones]
        timeformat = '%H:%M'
        return sorted(
            set(time.strftime(timeformat) for time in times))

    @cachedproperty
    def bounds(self):
        """A dictionary with the bounds and center of the map, or None"""
        if self.has_mapped_participants:
            return self.context.getMappedParticipantsBounds()
        return None

    @property
    def map_html(self):
        """HTML which shows the map with location of the team's members."""
        return """
            <script type="text/javascript">
                YUI().use('node', 'lp.mapping', function(Y) {
                    function renderMap() {
                        Y.lp.mapping.renderTeamMap(
                            %(min_lat)s, %(max_lat)s, %(min_lng)s,
                            %(max_lng)s, %(center_lat)s, %(center_lng)s);
                     }
                     Y.on("domready", renderMap);
                });
            </script>""" % self.bounds

    @property
    def map_portlet_html(self):
        """The HTML which shows a small version of the team's map."""
        return """
            <script type="text/javascript">
                YUI().use('node', 'lp.mapping', function(Y) {
                    function renderMap() {
                        Y.lp.mapping.renderTeamMapSmall(
                            %(center_lat)s, %(center_lng)s);
                     }
                     Y.on("domready", renderMap);
                });
            </script>""" % self.bounds


class TeamMapData(TeamMapView):
    """An XML dump of the locations of all team members."""

    def render(self):
        self.request.response.setHeader(
            'content-type', 'application/xml;charset=utf-8')
        body = LaunchpadView.render(self)
        return body.encode('utf-8')
