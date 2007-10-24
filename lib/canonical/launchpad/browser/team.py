# Copyright 2004 Canonical Ltd

__metaclass__ = type

__all__ = [
    'HasRenewalPolicyMixin',
    'ProposedTeamMembersEditView',
    'TeamAddView',
    'TeamBrandingView',
    'TeamEditView',
    'TeamEmailView',
    'TeamMemberAddView',
    ]

from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.form.browser import TextAreaWidget
from zope.component import getUtility

from canonical.database.sqlbase import flush_database_updates
from canonical.widgets import (
    HiddenUserWidget, LaunchpadRadioWidget, SinglePopupWidget)

from canonical.launchpad import _
from canonical.launchpad.validators.email import valid_email
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, LaunchpadEditFormView,
    LaunchpadFormView)
from canonical.launchpad.browser.branding import BrandingChangeView
from canonical.launchpad.interfaces import (
    IEmailAddressSet, ILaunchBag, ILoginTokenSet, IPersonSet,
    ITeamCreation, ITeamMember, ITeam, LoginTokenType, TeamMembershipStatus)


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


class TeamEmailView:
    """A View to edit a team's contact email address."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.team = self.context
        self.wrongemail = None
        self.errormessage = ""
        self.feedback = ""

    def processForm(self):
        """Process the form, if it was submitted."""
        # Any self-posting form that updates the database and want to display
        # these updated values have to flush all db updates. This is why we
        # call flush_database_updates() here.

        request = self.request
        if request.method != "POST":
            # Nothing to do
            return

        emailset = getUtility(IEmailAddressSet)

        if request.form.get('ADD_EMAIL') or request.form.get('CHANGE_EMAIL'):
            emailaddress = request.form.get('newcontactemail', "")
            emailaddress = emailaddress.lower().strip()
            if not valid_email(emailaddress):
                self.errormessage = (
                    "The email address you're trying to add doesn't seem to "
                    "be valid. Please make sure it's correct and try again.")
                # We want to display the invalid address so the user can just
                # fix what's wrong and send again.
                self.wrongemail = emailaddress
                return

            email = emailset.getByEmail(emailaddress)
            if email is not None:
                if email.person.id != self.team.id:
                    self.errormessage = (
                        "The email address you're trying to add is already "
                        "registered in Launchpad for %s."
                        % email.person.browsername)
                else:
                    self.errormessage = (
                        "This is the current contact email address of this "
                        "team. There's no need to add it again.")
                return

            self._sendEmailValidationRequest(emailaddress)
            flush_database_updates()
            return
        elif request.form.get('REMOVE_EMAIL'):
            if self.team.preferredemail is None:
                self.errormessage = "This team has no contact email address."
                return
            self.team.preferredemail.destroySelf()
            self.feedback = (
                "The contact email address of this team has been removed. "
                "From now on, all notifications directed to this team will "
                "be sent to all team members.")
            flush_database_updates()
            return
        elif (request.form.get('REMOVE_UNVALIDATED') or
              request.form.get('VALIDATE')):
            email = self.request.form.get("UNVALIDATED_SELECTED")
            if email is None:
                self.feedback = ("You must select the email address you want "
                                 "to remove/confirm.")
                return

            if request.form.get('REMOVE_UNVALIDATED'):
                getUtility(ILoginTokenSet).deleteByEmailRequesterAndType(
                    email, self.context, LoginTokenType.VALIDATETEAMEMAIL)
                self.feedback = (
                    "The email address '%s' has been removed." % email)
            elif request.form.get('VALIDATE'):
                self._sendEmailValidationRequest(email)

            flush_database_updates()
            return

    def _sendEmailValidationRequest(self, email):
        """Send a validation message to <email> and update self.feedback."""
        generateTokenAndValidationEmail(email, self.team)
        self.feedback = (
            "A confirmation message has been sent to '%s'. Follow the "
            "instructions in that message to confirm the new "
            "contact address for this team. "
            "(If the message doesn't arrive in a few minutes, your mail "
            "provider might use 'greylisting', which could delay the message "
            "for up to an hour or two.)" % email)


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

