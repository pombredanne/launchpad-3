# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Stuff to do with logging in and logging out."""

__metaclass__ = type

from datetime import datetime

from zope.component import getUtility
from zope.app.session.interfaces import ISession
from zope.event import notify

from canonical.launchpad.webapp.interfaces import IPlacelessLoginSource
from canonical.launchpad.webapp.interfaces import CookieAuthLoggedInEvent
from canonical.launchpad.webapp.interfaces import LoggedOutEvent
from canonical.launchpad.interfaces import ILoginTokenSet, IPersonSet
from canonical.launchpad.mail.sendmail import simple_sendmail
from canonical.lp.dbschema import LoginTokenType
from canonical.auth.browser import well_formed_email


class BasicLoginPage:

    def isSameHost(self, url):
        """Returns True if the url appears to be from the same host as we are.
        """
        return url.startswith(self.request.getApplicationURL())

    def login(self):
        referer = self.request.getHeader('referer')  # Traditional w3c speling
        if referer and self.isSameHost(referer):
            self.request.response.redirect(referer)
        else:
            self.request.response.redirect(self.request.getURL(1))
        return ''

class LoginOrRegister:
    """
    Merges the former CookieLoginPage and JoinLaunchpadView classes
    to allow the two forms to appear on a single page.
    """

    login_error = None
    registration_error = None
    submitted = False
    email = None

    def process_form(self):
        """
        Determines whether this is the login form or the register
        form, and delegates to the appropriate function.
        """
        if self.request.method != "POST":
            return 

        self.submitted = True
        if self.request.form.get('submit_login'):
            self.process_login_form()
        elif self.request.form.get('submit_registration'):
            self.process_registration_form()

    def process_login_form(self):
        """Process the form data.

        If there is an error, assign a string containing a description
        of the error to self.login_error for presentation to the user.
        """
        email = self.request.form.get('email')
        password = self.request.form.get('password')
        if not email or not password:
            self.login_error = "Enter your email address and password."
            return

        loginsource = getUtility(IPlacelessLoginSource)
        principal = loginsource.getPrincipalByLogin(email)
        if principal is not None and principal.validate(password):
            logInPerson(self.request, principal, email)
        else:
            self.login_error = "The email address and password do not match."

    def process_registration_form(self):
        """A user has asked to join launchpad.

        Check if everything is ok with the email address and send an email
        with a link to the user complete the registration process.
        """
        self.email = self.request.form.get("email").strip()
        person = getUtility(IPersonSet).getByEmail(self.email)
        if person is not None:
            msg = ('The email address %s is already registered in our system. '
                   'If you are sure this is your email address, please go to '
                   'the <a href="+forgottenpassword">Forgotten Password</a> '
                   'page and follow the instructions to retrieve your '
                   'password.') % self.email
            self.registration_error = msg
            return

        if not well_formed_email(self.email):
            self.registration_error = ("The email address you provided isn't "
                "valid. Please verify it and try again.")
            return

        logintokenset = getUtility(ILoginTokenSet)
        # This is a new user, so requester and requesteremail (first two
        # parameters of LoginTokenSet.new()) are None.
        token = logintokenset.new(None, None, self.email,
                                  LoginTokenType.NEWACCOUNT)
        sendNewUserEmail(token, self.request.getApplicationURL())

    def login_success(self):
        return (self.submitted and self.request.form.get('submit_login') and 
                not self.login_error)

    def registration_success(self):
        return (self.submitted and 
                self.request.form.get('submit_registration') and 
                not self.registration_error)


def logInPerson(request, principal, email):
    """Log the person in. Password validation must be done in callsites."""
    session = ISession(request)
    authdata = session['launchpad.authenticateduser']
    previous_login = authdata.get('personid')
    authdata['personid'] = principal.id
    authdata['logintime'] = datetime.utcnow()
    authdata['login'] = email
    notify(CookieAuthLoggedInEvent(request, email))


class CookieLogoutPage:

    def logout(self):
        session = ISession(self.request)
        authdata = session['launchpad.authenticateduser']
        previous_login = authdata.get('personid')
        authdata['personid'] = None
        authdata['logintime'] = datetime.utcnow()
        notify(LoggedOutEvent(self.request))
        return ''


class ForgottenPasswordPage:

    errortext = None
    submitted = False

    def process_form(self):
        if self.request.method != "POST":
            return

        email = self.request.form.get("email").strip()
        person = getUtility(IPersonSet).getByEmail(email)
        if person is None:
            self.errortext = ("Your account details have not been found. "
                              "Please check your subscription email "
                              "address and try again.")
            return

        logintokenset = getUtility(ILoginTokenSet)
        token = logintokenset.new(person, email, email,
                                  LoginTokenType.PASSWORDRECOVERY)
        sendPasswordResetEmail(token, self.request.getApplicationURL())
        self.submitted = True
        return

    def success(self):
        return self.submitted and not self.errortext


def sendPasswordResetEmail(token, appurl):
    template_file = 'lib/canonical/launchpad/templates/forgottenpassword.txt'
    template = open(template_file).read()
    fromaddress = "Launchpad Team <noreply@canonical.com>"

    replacements = {'longstring': token.token,
                    'toaddress': token.email, 
                    'appurl': appurl}
    message = template % replacements

    subject = "Launchpad: Forgotten Password"
    simple_sendmail(fromaddress, token.email, subject, message)



def sendNewUserEmail(token, appurl):
    template = open('lib/canonical/launchpad/templates/newuser-email.txt').read()
    replacements = {'longstring': token.token, 'appurl': appurl}
    message = template % replacements

    fromaddress = "The Launchpad Team <noreply@canonical.com>"
    subject = "Launchpad Account Creation Instructions"
    simple_sendmail(fromaddress, token.email, subject, message)

