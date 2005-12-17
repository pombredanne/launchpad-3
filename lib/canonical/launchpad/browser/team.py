# Copyright 2004 Canonical Ltd

__metaclass__ = type

__all__ = ['TeamEditView', 'TeamEmailView', 'TeamAddView', 'TeamMembersView',
           'TeamMemberAddView', 'ProposedTeamMembersEditView']

from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.form.browser.add import AddView
from zope.component import getUtility

from canonical.config import config
from canonical.lp.dbschema import LoginTokenType, TeamMembershipStatus
from canonical.database.sqlbase import flush_database_updates

from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.validators.email import valid_email
from canonical.launchpad.mail.sendmail import simple_sendmail
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.interfaces import (
    IPersonSet, ILaunchBag, IEmailAddressSet, ILoginTokenSet,
    ITeamMembershipSet)


class TeamEditView(SQLObjectEditView):

    def __init__(self, context, request):
        SQLObjectEditView.__init__(self, context, request)
        self.team = context

    def changed(self):
        """Redirect to the team  page.

        We need this because people can now change team names, and this will
        make their canonical_url to change too.
        """
        self.request.response.redirect(canonical_url(self.context))

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
                getUtility(ILoginTokenSet).deleteByEmailAndRequester(
                    email, self.context)
                self.feedback = (
                    "The email address '%s' has been removed." % email)
            elif request.form.get('VALIDATE'):
                self._sendEmailValidationRequest(email)

            flush_database_updates()
            return

    def _sendEmailValidationRequest(self, email):
        """Send a validation message to <email> and update self.feedback."""
        appurl = self.request.getApplicationURL()
        sendEmailValidationRequest(self.team, email, appurl)
        self.feedback = (
            "An email message was sent to '%s'. Follow the "
            "instructions in that message to confirm the new "
            "contact address for this team." % email)


class TeamAddView(AddView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        AddView.__init__(self, context, request)
        self._nextURL = '.'

    def nextURL(self):
        return self._nextURL

    def createAndAdd(self, data):
        name = data.get('name')
        displayname = data.get('displayname')
        teamdescription = data.get('teamdescription')
        defaultmembershipperiod = data.get('defaultmembershipperiod')
        defaultrenewalperiod = data.get('defaultrenewalperiod')
        subscriptionpolicy = data.get('subscriptionpolicy')
        teamowner = getUtility(ILaunchBag).user
        team = getUtility(IPersonSet).newTeam(
            teamowner, name, displayname, teamdescription,
            subscriptionpolicy, defaultmembershipperiod, defaultrenewalperiod)
        notify(ObjectCreatedEvent(team))

        email = data.get('contactemail')
        if email is not None:
            appurl = self.request.getApplicationURL()
            sendEmailValidationRequest(team, email, appurl)

        self._nextURL = canonical_url(team)
        return team


def sendEmailValidationRequest(team, email, appurl):
    """Send a validation message to <email>, so it can be registered to <team>.

    We create the necessary LoginToken entry and then send the message to
    <email>, with <team> as the requester. The user which actually made the
    request in behalf of the team is also shown on the message.
    """
    template = open(
        'lib/canonical/launchpad/emailtemplates/validate-teamemail.txt').read()

    fromaddress = "Launchpad Email Validator <noreply@ubuntu.com>"
    subject = "Launchpad: Validate your team's contact email address"
    login = getUtility(ILaunchBag).login
    user = getUtility(ILaunchBag).user
    token = getUtility(ILoginTokenSet).new(
                team, login, email, LoginTokenType.VALIDATETEAMEMAIL)

    replacements = {'longstring': token.token,
                    'team': token.requester.browsername,
                    'requester': '%s (%s)' % (user.browsername, user.name),
                    'toaddress': token.email,
                    'appurl': appurl,
                    'admin_email': config.admin_address}
    message = template % replacements
    simple_sendmail(fromaddress, token.email, subject, message)


class TeamMembersView:

    def allMembersCount(self):
        return getUtility(ITeamMembershipSet).getTeamMembersCount(self.context)

    def activeMemberships(self):
        return getUtility(ITeamMembershipSet).getActiveMemberships(self.context)

    def proposedMemberships(self):
        return getUtility(ITeamMembershipSet).getProposedMemberships(
            self.context)

    def inactiveMemberships(self):
        return getUtility(ITeamMembershipSet).getInactiveMemberships(
            self.context)


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

            team.setMembershipStatus(person, status, expires,
                                     reviewer=self.user)

        # Need to flush all changes we made, so subsequent queries we make
        # with this transaction will see this changes and thus they'll be
        # displayed on the page that calls this method.
        flush_database_updates()


class TeamMemberAddView(AddView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        self.alreadyMember = None
        self.addedMember = None
        added = self.request.get('added')
        notadded = self.request.get('notadded')
        if added:
            self.addedMember = getUtility(IPersonSet).get(added)
        elif notadded:
            self.alreadyMember = getUtility(IPersonSet).get(notadded)
        AddView.__init__(self, context, request)

    def nextURL(self):
        if self.addedMember:
            return '+addmember?added=%d' % self.addedMember.id
        elif self.alreadyMember:
            return '+addmember?notadded=%d' % self.alreadyMember.id
        else:
            return '+addmember'

    def createAndAdd(self, data):
        team = self.context
        approved = TeamMembershipStatus.APPROVED

        newmember = data['newmember']
        # If we get to this point with the member being the team itself,
        # it means the ValidTeamMemberVocabulary is broken.
        assert newmember != team, newmember

        if newmember in team.activemembers:
            self.alreadyMember = newmember
            return

        expires = team.defaultexpirationdate
        if newmember.hasMembershipEntryFor(team):
            team.setMembershipStatus(newmember, approved, expires,
                                     reviewer=self.user)
        else:
            team.addMember(newmember, approved, reviewer=self.user)

        self.addedMember = newmember

