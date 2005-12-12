# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Stuff to do with logging in and logging out."""

__metaclass__ = type

import cgi
import urllib
from datetime import datetime

from zope.component import getUtility
from zope.app.session.interfaces import ISession
from zope.event import notify
from zope.app.security.interfaces import IUnauthenticatedPrincipal

from canonical.launchpad import _
from canonical.launchpad.validators.email import valid_email
from canonical.launchpad.webapp.interfaces import IPlacelessLoginSource
from canonical.launchpad.webapp.interfaces import CookieAuthLoggedInEvent
from canonical.launchpad.webapp.interfaces import LoggedOutEvent
from canonical.launchpad.webapp.error import SystemErrorView
from canonical.launchpad.interfaces import ILoginTokenSet, IPersonSet
from canonical.launchpad.mail.sendmail import simple_sendmail
from canonical.lp.dbschema import LoginTokenType
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from canonical.launchpad.webapp.notification import NOTIFICATION_PARAMETER

class UnauthorizedView(SystemErrorView):

    response_code = None

    forbidden_page = ViewPageTemplateFile(
        '../templates/launchpad-forbidden.pt')

    def __call__(self):
        if IUnauthenticatedPrincipal.providedBy(self.request.principal):
            if 'loggingout' in self.request.form:
                target = '%s?loggingout=1' % self.request.URL[-2]
                self.request.response.redirect(target)
                return ''
            if self.request.method == 'POST':
                # If we got a POST then that's a problem.  We can only
                # redirect with a GET, so when we redirect after a successful
                # login, the wrong method would be used.
                # If we get a POST here, it is an application error.  We
                # must ensure that form pages require the same rights
                # as the pages that process those forms.  So, we should never
                # need to newly authenticate on a POST.
                self.request.response.setStatus(500) # Internal Server Error
                self.request.response.setHeader('Content-type', 'text/plain')
                return ('Application error.  Unauthenticated user POSTing to '
                        'page that requires authentication.')
            # If we got any query parameters, then preserve them in the
            # new URL. Except for the BrowserNotifications
            query_string = self.request.get('QUERY_STRING', '')
            if query_string:
                query_string = '?' + query_string
            target = self.request.getURL() + '/+login' + query_string
            self.request.response.addNoticeNotification(_(
                    'To continue, you must log in to Launchpad.'
                    ))
            self.request.response.redirect(target)
            # Maybe render page with a link to the redirection?
            return ''
        else:
            self.request.response.setStatus(403) # Forbidden
            return self.forbidden_page()


class BasicLoginPage:

    def isSameHost(self, url):
        """Returns True if the url appears to be from the same host as we are.
        """
        return url.startswith(self.request.getApplicationURL())

    def login(self):
        if IUnauthenticatedPrincipal.providedBy(self.request.principal):
            self.request.principal.__parent__.unauthorized(
                self.request.principal.id, self.request)
            return 'Launchpad basic auth login page'
        referer = self.request.getHeader('referer')  # Traditional w3c speling
        if referer and self.isSameHost(referer):
            self.request.response.redirect(referer)
        else:
            self.request.response.redirect(self.request.getURL(1))
        return ''


class LoginOrRegister:
    """Merges the former CookieLoginPage and JoinLaunchpadView classes
    to allow the two forms to appear on a single page.

    This page is a self-posting form.  Actually, there are two forms
    on the page.  The first time this page is loaded, when there's been
    no POST of its form, we want to preserve any query parameters, and put
    them into hidden inputs.
    """

    # Names used in the template's HTML form.
    form_prefix = 'loginpage_'
    submit_login = form_prefix + 'submit_login'
    submit_registration = form_prefix + 'submit_registration'
    input_email = form_prefix + 'email'
    input_password = form_prefix + 'password'

    # Instance variables that represent the state of the form.
    login_error = None
    registration_error = None
    submitted = False
    email = None

    def process_form(self):
        """Determines whether this is the login form or the register
        form, and delegates to the appropriate function.
        """
        if self.request.method != "POST":
            return 

        self.submitted = True
        if self.request.form.get(self.submit_login):
            self.process_login_form()
        elif self.request.form.get(self.submit_registration):
            self.process_registration_form()

    def get_application_url(self):
        return self.request.getApplicationURL()

    def process_login_form(self):
        """Process the form data.

        If there is an error, assign a string containing a description
        of the error to self.login_error for presentation to the user.
        """
        email = self.request.form.get(self.input_email)
        password = self.request.form.get(self.input_password)
        if not email or not password:
            self.login_error = _("Enter your email address and password.")
            return

        appurl = self.get_application_url()
        loginsource = getUtility(IPlacelessLoginSource)
        principal = loginsource.getPrincipalByLogin(email)
        if principal is not None and principal.validate(password):
            person = getUtility(IPersonSet).getByEmail(email)
            if person.preferredemail is None:
                self.login_error = _(
                    "The email address '%s', which you're trying to use to "
                    "login has not yet been validated to use in Launchpad. We "
                    "sent an email to that address with instructions on how "
                    "to confirm that it belongs to you. As soon as we have "
                    "that confirmation you'll be able to log into Launchpad."
                    ) % email
                token = getUtility(ILoginTokenSet).new(
                            person, email, email, LoginTokenType.VALIDATEEMAIL)
                token.sendEmailValidationRequest(appurl)
                return

            logInPerson(self.request, principal, email)
            self.redirectMinusLogin()
        else:
            self.login_error = "The email address and password do not match."

    def process_registration_form(self):
        """A user has asked to join launchpad.

        Check if everything is ok with the email address and send an email
        with a link to the user complete the registration process.
        """
        self.email = self.request.form.get(self.input_email).strip()
        person = getUtility(IPersonSet).getByEmail(self.email)
        if person is not None:
            msg = ('The email address %s is already registered in our system. '
                   'If you are sure this is your email address, please go to '
                   'the <a href="/+forgottenpassword">Forgotten Password</a> '
                   'page and follow the instructions to retrieve your '
                   'password.') % cgi.escape(self.email)
            self.registration_error = msg
            return

        if not valid_email(self.email):
            self.registration_error = (
                "The email address you provided isn't valid. "
                "Please verify it and try again.")
            return

        logintokenset = getUtility(ILoginTokenSet)
        # This is a new user, so requester and requesteremail (first two
        # parameters of LoginTokenSet.new()) are None.
        token = logintokenset.new(None, None, self.email,
                                  LoginTokenType.NEWACCOUNT)
        sendNewUserEmail(token, self.request.getApplicationURL())

    def login_success(self):
        return (self.submitted and
                self.request.form.get(self.submit_login) and 
                not self.login_error)

    def registration_success(self):
        return (self.submitted and 
                self.request.form.get(self.submit_registration) and 
                not self.registration_error)

    def redirectMinusLogin(self):
        """Redirect to the URL with the '/+login' removed from the end.

        Also, take into account the preserved query from the URL.
        """
        target = self.request.URL[-1]
        query_string = urllib.urlencode(
            list(self.iter_form_items()), doseq=True)
        if query_string:
            target = '%s?%s' % (target, query_string)
        self.request.response.redirect(target)

    def iter_form_items(self):
        """Iterate over keys and single values, excluding stuff we don't
        want such as '-C' and things starting with self.form_prefix.
        """
        for name, value in self.request.form.items():
            # XXX: Exclude '-C' because this is left in from sys.argv in Zope3
            #      using python's cgi.FieldStorage to process requests.
            # -- SteveAlexander, 2005-04-11
            if name == '-C' or name == 'loggingout':
                continue
            if name.startswith(self.form_prefix):
                continue
            if isinstance(value, list):
                value_list = value
            else:
                value_list = [value]
            for value_list_item in value_list:
                yield (name, value_list_item)

    def preserve_query(self):
        """Returns zero or more hidden inputs that preserve the URL's query."""
        L = []
        for name, value in self.iter_form_items():
            if name != NOTIFICATION_PARAMETER:
                L.append('<input type="hidden" name="%s" value="%s" />' %
                        (name, cgi.escape(value, quote=True)))
        return '\n'.join(L)

def logInPerson(request, principal, email):
    """Log the person in. Password validation must be done in callsites."""
    session = ISession(request)
    authdata = session['launchpad.authenticateduser']
    previous_login = authdata.get('personid')
    authdata['personid'] = principal.id
    authdata['logintime'] = datetime.utcnow()
    authdata['login'] = email
    notify(CookieAuthLoggedInEvent(request, email))
    request.response.addNoticeNotification(
        _(u'You have been logged in')
        )


class CookieLogoutPage:

    def logout(self):
        session = ISession(self.request)
        authdata = session['launchpad.authenticateduser']
        previous_login = authdata.get('personid')
        if previous_login is not None:
            authdata['personid'] = None
            authdata['logintime'] = datetime.utcnow()
            notify(LoggedOutEvent(self.request))
        else:
            # There is no cookie-based login currently.
            # So, don't attempt to log out.  Just redirect
            pass
        self.request.response.addNoticeNotification(
            _(u'You have been logged out')
            )
        target = '%s/?loggingout=1' % self.request.URL[-1]
        self.request.response.redirect(target)
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
    template = open(
        'lib/canonical/launchpad/emailtemplates/forgottenpassword.txt').read()
    fromaddress = "Launchpad Team <noreply@canonical.com>"

    replacements = {'longstring': token.token,
                    'toaddress': token.email, 
                    'appurl': appurl}
    message = template % replacements

    subject = "Launchpad: Forgotten Password"
    simple_sendmail(fromaddress, str(token.email), subject, message)



def sendNewUserEmail(token, appurl):
    template = open(
        'lib/canonical/launchpad/emailtemplates/newuser-email.txt').read()
    replacements = {'longstring': token.token, 'appurl': appurl}
    message = template % replacements

    fromaddress = "The Launchpad Team <noreply@canonical.com>"
    subject = "Launchpad Account Creation Instructions"
    simple_sendmail(fromaddress, str(token.email), subject, message)

