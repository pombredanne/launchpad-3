# Copyright 2004 Canonical Ltd

__metaclass__ = type

__all__ = [
    'ProposedTeamMembersEditView',
    'TeamAddView',
    'TeamBrandingView',
    'TeamContactAddressView',
    'TeamMailingListConfigurationView',
    'TeamEditView',
    'TeamMemberAddView',
    ]

from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.form.browser import TextAreaWidget
from zope.component import getUtility
from zope.formlib import form
from zope.schema import Choice
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from canonical.database.sqlbase import flush_database_updates
from canonical.widgets import (
    HiddenUserWidget, LaunchpadRadioWidget, SinglePopupWidget)

from canonical.config import config
from canonical.launchpad import _
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, LaunchpadEditFormView,
    LaunchpadFormView)
from canonical.launchpad.browser.branding import BrandingChangeView
from canonical.launchpad.interfaces import (
    IEmailAddressSet, ILaunchBag, ILoginTokenSet, IMailingListSet, IPersonSet,
    ITeamContactAddressForm, ITeamCreation, ITeamMailingListConfigurationForm,
    ITeamMember, ITeam, LoginTokenType, MailingListStatus,
    MAILING_LISTS_DOMAIN, TeamContactMethod, TeamMembershipStatus,
    UnexpectedFormData)
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
        'renewal_policy', 'defaultrenewalperiod']
    custom_widget('teamowner', SinglePopupWidget, visible=False)
    custom_widget(
        'renewal_policy', LaunchpadRadioWidget, orientation='vertical')
    custom_widget(
        'subscriptionpolicy', LaunchpadRadioWidget, orientation='vertical')

    @action('Save', name='save')
    def action_save(self, action, data):
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)


def generateTokenAndValidationEmail(email, team):
    """Send a validation message to the given email."""
    login = getUtility(ILaunchBag).login
    token = getUtility(ILoginTokenSet).new(
        team, login, email, LoginTokenType.VALIDATETEAMEMAIL)

    user = getUtility(ILaunchBag).user
    token.sendTeamEmailAddressValidationEmail(user)


class TeamContactAddressView(LaunchpadFormView):

    schema = ITeamContactAddressForm
    label = "Contact address"
    custom_widget(
        'contact_method', LaunchpadRadioWidget, orientation='vertical')
    custom_widget(
        'welcome_message', TextAreaWidget, width=72, height=10)

    def _getList(self):
        """Return this team's mailing list."""
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
    def can_be_contact_method(self):
        """See `MailingList.canByContactMethod`.
        """
        mailing_list = self._getList() 
        return mailing_list and mailing_list.canBeContactMethod()

    def shouldRenderHostedListOptionManually(self):
        """Should the HOSTED_LIST option be rendered manually?

        Normally, we let Zope 3 render the radio buttons as it normally would,
        except under the following specific situation.  When
        config.mailman.expose_hosted_mailing_lists is True but the team does
        not yet have an active mailing list, we'll render this as a disabled
        radio button with a 'submit' button that allows the user to request
        the mailing list creation.
        """
        return config.mailman.expose_hosted_mailing_lists

    @property
    def mailing_list_status_message(self):
        mailing_list = getUtility(IMailingListSet).get(self.context.name)
        if mailing_list is None:
            return ("Not available because you haven't applied for a "
                    "mailing list.")

        msg = "Not available because "
        if mailing_list.status in [MailingListStatus.APPROVED,
                                   MailingListStatus.CONSTRUCTING]:
            msg += "mailing list is being constructed."
        elif mailing_list.status == MailingListStatus.REGISTERED:
            msg += ("the application for a mailing list is pending "
                    "approval.")
        elif mailing_list.status == MailingListStatus.DECLINED:
            msg += ('the application for a mailing list has been declined. '
                    'Please '
                    '<a href="https://help.launchpad.net/FAQ#contact-admin">'
                    'contact a Launchpad administrator</a> for further '
                    'assistance.')
        elif mailing_list.status in [MailingListStatus.INACTIVE,
                                     MailingListStatus.DEACTIVATING]:
            msg += "mailing list is currently deactivated."
        elif mailing_list.status == MailingListStatus.FAILED:
            msg += "mailing list creation failed."
        elif mailing_list.status == MailingListStatus.MODIFIED:
            msg += "mailing list is pending an update."
        elif mailing_list.status == MailingListStatus.UPDATING:
            msg += "mailing list is being updated."
        elif mailing_list.status == MailingListStatus.ACTIVE:
            # Mailing list is active and the option will be enabled; there's
            # no need to display a status message.
            msg = ''
        else:
            raise AssertionError(
                "Unknown mailing list status: %s" % mailing_list.status)
        return msg

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
        this team or if the associated one is in the INACTIVE state.
        """
        mailing_list = getUtility(IMailingListSet).get(self.context.name)
        return (mailing_list is None
                or mailing_list.status == MailingListStatus.INACTIVE)

    @property
    def mailinglist_address(self):
        """The address for this team's mailing list."""
        return '%s@%s' % (self.context.name, MAILING_LISTS_DOMAIN)

    def setUpFields(self):
        """See `LaunchpadFormView`.

        The welcome message control will only be displayed if the
        mailing list's state is ACTIVE, MODIFIED, or UPDATING.
        """
        super(TeamContactAddressView, self).setUpFields()

        # Replace the default contact_method field by a custom one.
        self.form_fields = (
            form.FormFields(self.getContactMethodField())
            + self.form_fields.omit('contact_method'))
            
        mailing_list = self.getListInState(MailingListStatus.ACTIVE,
                                           MailingListStatus.MODIFIED,
                                           MailingListStatus.UPDATING)
        if mailing_list is None:
            self.form_fields = self.form_fields.omit('welcome_message')

    def getContactMethodField(self):
        """Create the form.Fields to use for the contact_method field.

        Check if the HOSTED_LIST option of our contact_method widget
        should be rendered by Zope3, manually (by ourselves) in the
        template or not rendered at all and change the vocabulary
        accordingly.
        """
        terms = [term for term in TeamContactMethod
                 if term.value != TeamContactMethod.HOSTED_LIST]
        if (config.mailman.expose_hosted_mailing_lists
            and self.can_be_contact_method):
            # The HOSTED_LIST option will be rendered normally by zope3, so
            # we just need to change its title to include the actual email
            # address of the mailing list.
            title = ('The Launchpad mailing list for this team - '
                     '<strong>%s</strong>' % self.mailinglist_address)
            hosted_list_term = SimpleTerm(
                TeamContactMethod.HOSTED_LIST,
                TeamContactMethod.HOSTED_LIST.name, title)
            terms.insert(0, hosted_list_term)

        return form.FormField(
            Choice(__name__='contact_method',
                   title=_("How do people contact these team's members?"),
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
                    self.setFieldError('contact_address', str(error))
        elif data['contact_method'] == TeamContactMethod.HOSTED_LIST:
            mailing_list = getUtility(IMailingListSet).get(self.context.name)
            if (mailing_list is None or not mailing_list.canBeContactMethod()):
                self.addError(
                    "This team's mailing list is not active and may not be "
                    "used as its contact address yet")
        else:
            # Nothing to validate!
            pass

    def request_list_creation_validator(self, action, data):
        if self.getListInState(MailingListStatus.DECLINED,
                               MailingListStatus.INACTIVE) is not None:
            self.addError(
                "There is an application for a mailing list already.")

    def cancel_list_creation_validator(self, action, data):
        mailing_list = getUtility(IMailingListSet).get(self.context.name)
        if (mailing_list is None
            or mailing_list.status != MailingListStatus.REGISTERED):
            self.addError("This application can't be cancelled.")

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

    @action('Cancel Application', name='cancel_list_creation',
            validator=cancel_list_creation_validator)
    def cancel_list_creation(self, action, data):
        getUtility(IMailingListSet).get(self.context.name).cancelRegistration()
        self.request.response.addInfoNotification(
            "Mailing list application cancelled.")
        self.next_url = canonical_url(self.context)

    @action('Apply for Mailing List', name='request_list',
            validator=request_list_creation_validator)
    def request_list_creation(self, action, data):
        list_set = getUtility(IMailingListSet)
        mailing_list = list_set.get(self.context.name)
        if mailing_list is None:
            list_set.new(self.context)
            self.request.response.addInfoNotification(
                "Mailing list requested and queued for approval.")
        else:
            mailing_list.reactivate()
            self.request.response.addInfoNotification(
                "This team's Launchpad mailing list is currently "
                "inactive and will be reactivated shortly.")
        self.next_url = canonical_url(self.context)    

    @action('Change', name='change')
    def change_action(self, action, data):
        context = self.context
        email_set = getUtility(IEmailAddressSet)
        list_set = getUtility(IMailingListSet)
        contact_method = data['contact_method']
        
        if contact_method == TeamContactMethod.NONE:
            if context.preferredemail is not None:
                context.preferredemail.destroySelf()
        elif contact_method == TeamContactMethod.HOSTED_LIST:
            mailing_list = list_set.get(context.name)
            assert (mailing_list is not None 
                    and mailing_list.canBeContactMethod()), (
                "A team can only use an active mailing list as its contact "
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

class TeamMailingListConfigurationView(LaunchpadFormView):

    schema = ITeamMailingListConfigurationForm
    label = "Mailing list configuration"
    custom_widget(
        'welcome_message', TextAreaWidget, width=72, height=10)

    @action('Change', name='change')
    def change_action(self, action, data):
        print "CHANGE ACTION"
        list_set = getUtility(IMailingListSet)
        mailing_list = list_set.get(self.context.name)
        welcome_message = data.get('welcome_message', None)
        assert (mailing_list is not None 
                and mailing_list.canBeContactMethod()), (
            "Only an active mailing list can be configured.")

        print "WELCOME %s" % welcome_message
        if (welcome_message is not None
            and welcome_message != mailing_list.welcome_message):
            print "SETTING"
            mailing_list.welcome_message = welcome_message

        self.next_url = canonical_url(self.context)

    @property
    def initial_values(self):
        """The initial value of welcome_message comes from the database.
        
        :return: A dictionary containing the current welcome message.
        """
        context = self.context
        mailing_list = getUtility(IMailingListSet).get(context.name)
        if mailing_list is not None:            
            return dict(welcome_message=mailing_list.welcome_message)
        else:
            return {}
        
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

