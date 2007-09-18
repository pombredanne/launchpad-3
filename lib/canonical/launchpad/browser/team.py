# Copyright 2004 Canonical Ltd

__metaclass__ = type

__all__ = [
    'ProposedTeamMembersEditView',
    'TeamAddView',
    'TeamBrandingView',
    'TeamContactAddressView',
    'TeamEditView',
    'TeamMemberAddView',
    ]

from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.form.browser import TextAreaWidget
from zope.component import getUtility
from zope.formlib import form
from zope.schema import Choice

from canonical.database.sqlbase import flush_database_updates
from canonical.lazr import EnumeratedType, Item
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
    ITeamContactAddressForm, ITeamCreation, ITeamMember, ITeam,
    LoginTokenType, MailingListStatus, TeamMembershipStatus,
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


class TeamContactMethod(EnumeratedType):
    """The method used by Launchpad to contact a given team."""

    NONE = Item("""
        None; Launchpad will contact team members directly

        Notifications directed to this team will be sent to each of its
        members.
        """)

    HOSTED_LIST = Item("""
        Launchpad hosted team mailing list (i.e. ubuntumembers@teams.launchpad.net)

        Notifications directed to this team are sent to its Launchpad-hosted
        mailing list.
        """)

    EXTERNAL_ADDRESS = Item("""
        External contact email

        Notifications directed to this team are sent to the contact address
        specified.
        """)


class TeamContactAddressView(LaunchpadFormView):

    schema = ITeamContactAddressForm
    label = "Contact address"
    custom_widget(
        'contact_method', LaunchpadRadioWidget, orientation='vertical')

    def setUpFields(self):
        super(TeamContactAddressView, self).setUpFields()
        # XXX: Yeah, this is a hack but it'll go away as soon as we deploy the
        # mailman stuff on production.  -- Guilherme Salgado 2007-09-18
        if not config.mailman.expose_hosted_mailing_lists:
            TeamContactMethod.items.items.remove(TeamContactMethod.HOSTED_LIST)
        contact_method = form.Fields(
            Choice(__name__='contact_method',
                   title=_("How do people contact these team's members?"),
                   required=True, vocabulary=TeamContactMethod),
            custom_widget=self.custom_widgets['contact_method'],
            render_context=self.render_context)
        self.form_fields += contact_method

    def validate(self, data):
        # Only validate the email address if the user wants to use an external
        # address and the given email address is not already in use by this
        # team.
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

    def initialize(self):
        super(TeamContactAddressView, self).initialize()
        context = self.context
        list_set = getUtility(IMailingListSet)
        mailing_list = list_set.get(self.context.name)
        if mailing_list is not None:
            if mailing_list.status in [MailingListStatus.APPROVED,
                                       MailingListStatus.CONSTRUCTING]:
                self.request.response.addInfoNotification(
                    "This team's mailing list has been approved and is being "
                    "constructed; it will be available shortly.")
            elif mailing_list.status == MailingListStatus.REGISTERED:
                self.request.response.addInfoNotification(
                    "This team's mailing list has not been approved yet. "
                    "Once it's approved it'll be used as this team's contact "
                    "address.")
            elif mailing_list.status == MailingListStatus.DECLINED:
                self.request.response.addInfoNotification(
                    "This team's mailing list has not been approved; please "
                    "use an external contact address instead.")

    @property
    def initial_values(self):
        context = self.context
        if context.preferredemail is not None:
            mailing_list = getUtility(IMailingListSet).get(context.name)
            if (mailing_list is not None and
                mailing_list.status == MailingListStatus.ACTIVE):
                method = TeamContactMethod.HOSTED_LIST
            else:
                method = TeamContactMethod.EXTERNAL_ADDRESS
            return dict(contact_address=context.preferredemail.email,
                        contact_method=method)
        else:
            return dict(contact_method=TeamContactMethod.NONE)

    @action('Change', name='change')
    def change_action(self, action, data):
        context = self.context
        list_set = getUtility(IMailingListSet)
        contact_method = data['contact_method']
        if contact_method == TeamContactMethod.NONE:
            if context.preferredemail is not None:
                context.preferredemail.destroySelf()
            mailing_list = list_set.get(context.name)
            if (mailing_list is not None and
                mailing_list.status == MailingListStatus.ACTIVE):
                mailing_list.deactivate()
        elif contact_method == TeamContactMethod.HOSTED_LIST:
            mailing_list = list_set.get(context.name)
            if mailing_list is None:
                list_set.new(context)
                self.request.response.addInfoNotification(
                    "Mailing list requested and now queued for approval.")
            elif mailing_list.status == MailingListStatus.REGISTERED:
                self.request.response.addInfoNotification(
                    "Mailing list requested but not yet approved.")
            elif mailing_list.status in [MailingListStatus.APPROVED,
                                         MailingListStatus.CONSTRUCTING]:
                self.request.response.addInfoNotification(
                    "Mailing list is being created; it will be available "
                    "shortly.")
            elif mailing_list.status == MailingListStatus.ACTIVE:
                self.request.response.addInfoNotification(
                    "This team already has a Launchpad mailing list.")
            elif mailing_list.status == MailingListStatus.INACTIVE:
                # XXX: Can I set the status to REGISTERED manually here?
                # Or maybe when it's inactive I can even change it back to
                # approved?

                # mailing_list.status = MailingListStatus.REGISTERED
                # self.request.response.addInfoNotification(msg)
                pass
            else:
                # This is unlikely to happen, but since it's cheap we do it
                # anyway.
                self.request.response.addWarningNotification(
                    "This team's mailing list is undergoing some "
                    "maintenance; please wait a few minutes and try again.")
                # Return here so that we don't go to the next url.
                return
        elif contact_method == TeamContactMethod.EXTERNAL_ADDRESS:
            contact_address = data['contact_address']
            email = getUtility(IEmailAddressSet).getByEmail(contact_address)
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
                assert email.person == context, (
                    "This email belongs to somebody else.")
        else:
            raise UnexpectedFormData(
                "Unknown contact_method: %s" % contact_method)

        self.next_url = canonical_url(self.context)


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

