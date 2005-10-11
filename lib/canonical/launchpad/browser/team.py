# Copyright 2004 Canonical Ltd

__metaclass__ = type

__all__ = [
    'TeamEditView',
    'TeamEmailView',
    'TeamAddView',
    ]

from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.form.browser.add import AddView
from zope.component import getUtility
from zope.i18nmessageid import MessageIDFactory

from canonical.config import config
from canonical.lp.dbschema import LoginTokenType
from canonical.database.sqlbase import flush_database_updates

from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.validators.email import valid_email
from canonical.launchpad.mail.sendmail import simple_sendmail
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.interfaces import (
    IPersonSet, ILaunchBag, IEmailAddressSet, ILoginTokenSet)

_ = MessageIDFactory('launchpad')


class TeamEditView(SQLObjectEditView):

    def __init__(self, context, request):
        SQLObjectEditView.__init__(self, context, request)
        self.team = context


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
            "An e-mail message was sent to '%s'. Follow the "
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

        email = data.get('contactemail', None)
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


