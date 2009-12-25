# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Stuff to do with logging in and logging out."""

__metaclass__ = type

import cgi
import urllib
from datetime import datetime, timedelta
import md5
import random

from BeautifulSoup import UnicodeDammit

from openid.consumer.consumer import CANCEL, Consumer, FAILURE, SUCCESS

from zope.component import getUtility
from zope.session.interfaces import ISession, IClientIdManager
from zope.event import notify
from zope.app.security.interfaces import IUnauthenticatedPrincipal

from z3c.ptcompat import ViewPageTemplateFile

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.launchpad import _
from canonical.launchpad.interfaces.account import AccountStatus, IAccountSet
from canonical.launchpad.interfaces.authtoken import (
    IAuthTokenSet, LoginTokenType)
from canonical.launchpad.interfaces.emailaddress import IEmailAddressSet
from canonical.launchpad.interfaces.logintoken import ILoginTokenSet
from canonical.launchpad.interfaces.openidconsumer import IOpenIDConsumerStore
from lp.registry.interfaces.person import (
    IPerson, IPersonSet, PersonCreationRationale)
from canonical.launchpad.interfaces.validation import valid_password
from canonical.launchpad.validators.email import valid_email
from canonical.launchpad.webapp.error import SystemErrorView
from canonical.launchpad.webapp.interfaces import (
    CookieAuthLoggedInEvent, ILaunchpadPrincipal, IPlacelessAuthUtility,
    IPlacelessLoginSource, LoggedOutEvent)
from canonical.launchpad.webapp.metazcml import ILaunchpadPermission
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.launchpad.webapp.url import urlappend
from canonical.launchpad.webapp.vhosts import allvhosts


class UnauthorizedView(SystemErrorView):

    response_code = None

    forbidden_page = ViewPageTemplateFile(
        '../templates/launchpad-forbidden.pt')

    read_only_page = ViewPageTemplateFile(
        '../templates/launchpad-readonlyfailure.pt')

    notification_message = _('To continue, you must log in to Launchpad.')

    def __call__(self):
        # In read only mode, Unauthorized exceptions get raised by the
        # security policy when write permissions are requested. We need
        # to render the read-only failure screen so the user knows their
        # request failed for operational reasons rather than a genuine
        # permission problem.
        if config.launchpad.read_only:
            # Our context is an Unauthorized exception, which acts like
            # a tuple containing (object, attribute_requested, permission).
            lp_permission = getUtility(ILaunchpadPermission, self.context[2])
            if lp_permission.access_level != "read":
                self.request.response.setStatus(503) # Service Unavailable
                return self.read_only_page()

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
            current_url = self.request.getURL()
            while True:
                nextstep = self.request.stepstogo.consume()
                if nextstep is None:
                    break
                current_url = urlappend(current_url, nextstep)
            query_string = self.request.get('QUERY_STRING', '')
            if query_string:
                query_string = '?' + query_string
            target = self.getRedirectURL(current_url, query_string)
            # A dance to assert that we want to break the rules about no
            # unauthenticated sessions. Only after this next line is it safe
            # to use the ``addNoticeNotification`` method.
            allowUnauthenticatedSession(self.request)
            self.request.response.addNoticeNotification(
                self.notification_message)
            self.request.response.redirect(target)
            # Maybe render page with a link to the redirection?
            return ''
        else:
            self.request.response.setStatus(403) # Forbidden
            return self.forbidden_page()

    def getRedirectURL(self, current_url, query_string):
        """Get the URL to redirect to.
        :param current_url: The URL of the current page.
        :param query_string: The string that should be appended to the current
            url.
        """
        return urlappend(current_url, '+login' + query_string)


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


class RestrictedLoginInfo:
    """On a team-restricted launchpad server, show who may access the server.

    Otherwise, show that this is an unrestricted server.
    """

    def isTeamRestrictedServer(self):
        return bool(config.launchpad.restrict_to_team)

    def getAllowedTeamURL(self):
        return 'https://launchpad.net/people/%s' % (
            config.launchpad.restrict_to_team)

    def getAllowedTeamDescription(self):
        return getUtility(IPersonSet).getByName(
            config.launchpad.restrict_to_team).title

class CaptchaMixin:
    """Mixin class to provide simple captcha capabilities."""
    def validateCaptcha(self):
        """Validate the submitted captcha value matches what we expect."""
        expected = self.request.form.get(self.captcha_hash)
        submitted = self.request.form.get(self.captcha_submission)
        if expected is not None and submitted is not None:
            return md5.new(submitted).hexdigest() == expected
        return False

    @cachedproperty
    def captcha_answer(self):
        """Get the answer for the current captcha challenge.

        With each failed attempt a new challenge will be given.  Our answer
        space is acknowledged to be ridiculously small but is chosen in the
        interest of ease-of-use.  We're not trying to create an iron-clad
        challenge but only a minimal obstacle to dumb bots.
        """
        return random.randint(10, 20)

    @property
    def get_captcha_hash(self):
        """Get the captcha hash.

        The hash is the value we put in the form for later comparison.
        """
        return md5.new(str(self.captcha_answer)).hexdigest()

    @property
    def captcha_problem(self):
        """Create the captcha challenge."""
        op1 = random.randint(1, self.captcha_answer - 1)
        op2 = self.captcha_answer - op1
        return '%d + %d =' % (op1, op2)


class OpenIDLogin(LaunchpadView):
    _openid_session_ns = 'OPENID'

    def _getConsumer(self):
        session = ISession(self.request)[self._openid_session_ns]
        openid_store = getUtility(IOpenIDConsumerStore)
        return Consumer(session, openid_store)

    def render(self):
        # Allow unauthenticated users to have sessions for the OpenID
        # handshake to work.
        allowUnauthenticatedSession(self.request)
        consumer = self._getConsumer()
        self.openid_request = consumer.begin(
            #allvhosts.configs['openid'].rooturl)
            'https://launchpad.dev/testopenid')

        return_to = self.return_to_url
        trust_root = self.request.getApplicationURL()
        assert not self.openid_request.shouldSendRedirect(), (
            "Our fixed OpenID server should not need us to redirect.")
        form_html = self.openid_request.htmlMarkup(trust_root, return_to)

        # Need to commit here because the consumer.begin() call above will
        # insert rows into the OpenIDAssociations table.
        import transaction
        transaction.commit()

        return form_html

    @property
    def return_to_url(self):
        url = self.request.getURL(1)
        return urlappend(url, '+openid-callback')

    # XXX: Copied here from the old login view; currently unused here.
    def iter_form_items(self):
        """Iterate over keys and single values, excluding stuff we don't
        want such as '-C' and things starting with self.form_prefix.
        """
        for name, value in self.request.form.items():
            # XXX SteveAlexander 2005-04-11: Exclude '-C' because this is
            #     left in from sys.argv in Zope3 using python's
            #     cgi.FieldStorage to process requests.
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

    # XXX: Copied here from the old login view; currently unused here.
    def preserve_query(self):
        """Return zero or more hidden inputs that preserve the URL's query."""
        L = []
        html = u'<input type="hidden" name="%s" value="%s" />'
        for name, value in self.iter_form_items():
            # Thanks to apport (https://launchpad.net/bugs/61171), we need to
            # do this here.
            value = UnicodeDammit(value).markup
            L.append(html % (name, cgi.escape(value, quote=True)))
        return '\n'.join(L)


class OpenIDCallbackView(OpenIDLogin):
    """The OpenID callback page for logging into Launchpad.

    This is the page the OpenID provider will send the user's browser to,
    after the user has authenticated on the provider.
    """

    @cachedproperty
    def openid_response(self):
        consumer = self._getConsumer()
        return consumer.complete(self.request.form, self.request.getURL())

    def login(self, account):
        loginsource = getUtility(IPlacelessLoginSource)
        # We don't have a logged in principal, so we must remove the security
        # proxy of the account's preferred email.
        from zope.security.proxy import removeSecurityProxy
        email = removeSecurityProxy(account.preferredemail).email
        logInPrincipal(
            self.request, loginsource.getPrincipalByLogin(email), email)

    def render(self):
        if self.openid_response.status == SUCCESS:
            account = getUtility(IAccountSet).getByOpenIDIdentifier(
                self.openid_response.identity_url.split('/')[-1])
            self.login(account)
            # TODO: Preserve the query string for everything other than openid
            # stuff.
            self.request.response.redirect(self.request.getURL(1))
        else:
            return OpenIDLoginErrorView(
                self.context, self.request, self.openid_response)()


class OpenIDLoginErrorView(LaunchpadView):

    page_title = 'Foo'
    template = ViewPageTemplateFile("../templates/login-error.pt")

    def __init__(self, context, request, openid_response):
        super(OpenIDLoginErrorView, self).__init__(context, request)
        assert self.account is None, (
            "Don't try to render this page when the user is logged in.")
        if openid_response.status == CANCEL:
            self.login_error = "User cancelled"
        elif openid_response.status == FAILURE:
            self.login_error = openid_response.message
        else:
            self.login_error = "Unknown error: %s" % openid_response


class LoginOrRegister(CaptchaMixin):
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
    captcha_submission = form_prefix + 'captcha_submission'
    captcha_hash = form_prefix + 'captcha_hash'

    # Instance variables that represent the state of the form.
    login_error = None
    registration_error = None
    submitted = False
    email = None

    def process_restricted_form(self):
        """Entry-point for the team-restricted login page.

        If we're not running in team-restricted mode, then redirect to a
        regular login page.  Otherwise, process_form as usual.
        """
        if config.launchpad.restrict_to_team:
            self.process_form()
        else:
            self.request.response.redirect('/+login',
                                           temporary_if_possible=True)

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

    def getRedirectionURL(self):
        """Return the URL we should redirect the user to, after finishing a
        registration or password reset process.

        IOW, the current URL without the "/+login" bit.
        """
        return self.request.getURL(1)

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

        # XXX matsubara 2006-05-08 bug=43675: This class should inherit from
        # LaunchpadFormView, that way we could take advantage of Zope's widget
        # validation, instead of checking manually for password validity.
        if not valid_password(password):
            self.login_error = _(
                "The password provided contains non-ASCII characters.")
            return

        loginsource = getUtility(IPlacelessLoginSource)
        principal = loginsource.getPrincipalByLogin(email)
        if principal is None or not principal.validate(password):
            self.login_error = "The email address and password do not match."
        elif principal.person is None:
            logInPrincipalAndMaybeCreatePerson(self.request, principal, email)
            self.redirectMinusLogin()
        elif principal.person.account_status == AccountStatus.DEACTIVATED:
            self.login_error = _(
                'The email address belongs to a deactivated account. '
                'Use the "Forgotten your password" link to reactivate it.')
        elif principal.person.account_status == AccountStatus.SUSPENDED:
            email_link = (
                'mailto:feedback@launchpad.net?subject=SUSPENDED%20account')
            self.login_error = _(
                'The email address belongs to a suspended account. '
                'Contact a <a href="%s">Launchpad admin</a> '
                'about this issue.' % email_link)
        else:
            person = getUtility(IPersonSet).getByEmail(email)
            if person.preferredemail is None:
                self.login_error = _(
                    "The email address '%s', which you're trying to use to "
                    "login has not yet been validated to use in Launchpad. "
                    "We sent an email to that address with instructions on "
                    "how to confirm that it belongs to you. As soon as we "
                    "have that confirmation you'll be able to log into "
                    "Launchpad."
                    ) % email
                token = getUtility(ILoginTokenSet).new(
                    person, email, email, LoginTokenType.VALIDATEEMAIL)
                token.sendEmailValidationRequest()
                return
            if person.is_valid_person:
                logInPrincipal(self.request, principal, email)
                self.redirectMinusLogin()
            else:
                # Normally invalid accounts will have a NULL password
                # so this will be rarely seen, if ever. An account with no
                # valid email addresses might end up in this situation,
                # such as having them flagged as OLD by a email bounce
                # processor or manual changes by the DBA.
                self.login_error = "This account cannot be used."

    def process_registration_form(self):
        """A user has asked to join launchpad.

        Check if everything is ok with the email address and send an email
        with a link to the user complete the registration process.
        """
        request = self.request
        # For some reason, redirection_url can sometimes be a list, and
        # sometimes a string.  See OOPS-68D508, where redirection_url has
        # the following value:
        # [u'https://launchpad.net/.../it/+translate/+login', u'']
        redirection_url = request.form.get('redirection_url')
        if isinstance(redirection_url, list):
            # Remove blank entries.
            redirection_url_list = [url for url in redirection_url if url]
            # XXX Guilherme Salgado 2006-09-27:
            # Shouldn't this be an UnexpectedFormData?
            assert len(redirection_url_list) == 1, redirection_url_list
            redirection_url = redirection_url_list[0]

        self.email = request.form.get(self.input_email).strip()

        if not valid_email(self.email):
            self.registration_error = (
                "The email address you provided isn't valid. "
                "Please verify it and try again.")
            return

        # Validate the user is human, more or less.
        if not self.validateCaptcha():
            self.registration_error = (
                "The answer to the simple math question was incorrect "
                "or missing.  Please try again.")
            return

        registered_email = getUtility(IEmailAddressSet).getByEmail(self.email)
        if registered_email is not None:
            person = registered_email.person
            if person is not None:
                if person.is_valid_person:
                    self.registration_error = (
                        "Sorry, someone with the address %s already has a "
                        "Launchpad account. If this is you and you've "
                        "forgotten your password, Launchpad can "
                        '<a href="/+forgottenpassword">reset it for you.</a>'
                        % cgi.escape(self.email))
                    return
                else:
                    # This is an unvalidated profile; let's move on with the
                    # registration process as if we had never seen it.
                    pass
            else:
                account = registered_email.account
                assert IPerson(account, None) is None, (
                    "This email address should be linked to the person who "
                    "owns it.")
                self.registration_error = (
                    'The email address %s is already registered in the '
                    'Launchpad Login Service (used by the Ubuntu shop and '
                    'other OpenID sites). Please use the same email and '
                    'password to log into Launchpad.'
                    % cgi.escape(self.email))
                return

        logintokenset = getUtility(ILoginTokenSet)
        token = logintokenset.new(
            requester=None, requesteremail=None, email=self.email,
            tokentype=LoginTokenType.NEWACCOUNT,
            redirection_url=redirection_url)
        token.sendNewUserEmail()

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
        self.request.response.redirect(target, temporary_if_possible=True)

    def iter_form_items(self):
        """Iterate over keys and single values, excluding stuff we don't
        want such as '-C' and things starting with self.form_prefix.
        """
        for name, value in self.request.form.items():
            # XXX SteveAlexander 2005-04-11: Exclude '-C' because this is
            #     left in from sys.argv in Zope3 using python's
            #     cgi.FieldStorage to process requests.
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
        """Return zero or more hidden inputs that preserve the URL's query."""
        L = []
        html = u'<input type="hidden" name="%s" value="%s" />'
        for name, value in self.iter_form_items():
            # Thanks to apport (https://launchpad.net/bugs/61171), we need to
            # do this here.
            value = UnicodeDammit(value).markup
            L.append(html % (name, cgi.escape(value, quote=True)))
        return '\n'.join(L)

def logInPrincipal(request, principal, email):
    """Log the principal in. Password validation must be done in callsites."""
    session = ISession(request)
    authdata = session['launchpad.authenticateduser']
    assert principal.id is not None, 'principal.id is None!'
    request.setPrincipal(principal)
    authdata['accountid'] = principal.id
    authdata['logintime'] = datetime.utcnow()
    authdata['login'] = email
    notify(CookieAuthLoggedInEvent(request, email))


def logInPrincipalAndMaybeCreatePerson(request, principal, email):
    """Log the principal in, creating a Person if necessary.

    If the given principal has no associated person, we create a new
    person, fetch a new principal and set it in the request.

    Password validation must be done in callsites.
    """
    logInPrincipal(request, principal, email)
    if ILaunchpadPrincipal.providedBy(principal) and principal.person is None:
        person = principal.account.createPerson(
            PersonCreationRationale.OWNER_CREATED_LAUNCHPAD)
        new_principal = getUtility(IPlacelessLoginSource).getPrincipal(
            principal.id)
        assert ILaunchpadPrincipal.providedBy(new_principal)
        request.setPrincipal(new_principal)


def expireSessionCookie(request, client_id_manager=None,
                        delta=timedelta(minutes=10)):
    if client_id_manager is None:
        client_id_manager = getUtility(IClientIdManager)
    session_cookiename = client_id_manager.namespace
    value = request.response.getCookie(session_cookiename)['value']
    expiration = (datetime.utcnow() + delta).strftime(
        '%a, %d %b %Y %H:%M:%S GMT')
    request.response.setCookie(
        session_cookiename, value, expires=expiration)


def allowUnauthenticatedSession(request, duration=timedelta(minutes=10)):
    # As a rule, we do not want to send a cookie to an unauthenticated user,
    # because it breaks cacheing; and we do not want to create a session for
    # an unauthenticated user, because it unnecessarily consumes valuable
    # database resources. We have an assertion to ensure this. However,
    # sometimes we want to break the rules. To do this, first we set the
    # session cookie; then we assert that we only want it to last for a given
    # duration, so that, if the user does not log in, they can go back to
    # getting cached pages. Only after an unauthenticated user's session
    # cookie is set is it safe to write to it.
    if not IUnauthenticatedPrincipal.providedBy(request.principal):
        return
    client_id_manager = getUtility(IClientIdManager)
    if request.response.getCookie(client_id_manager.namespace) is None:
        client_id_manager.setRequestId(
            request, client_id_manager.getClientId(request))
        expireSessionCookie(request, client_id_manager, duration)


# XXX: salgado, 2009-02-19: Rename this to logOutPrincipal(), to be consistent
# with logInPrincipal().  Or maybe logUserOut(), in case we don't care about
# consistency.
def logoutPerson(request):
    """Log the user out."""
    session = ISession(request)
    authdata = session['launchpad.authenticateduser']
    account_variable_name = 'accountid'
    previous_login = authdata.get(account_variable_name)
    if previous_login is None:
        # This is for backwards compatibility, when we used to store the
        # person's ID in the 'personid' session variable.
        account_variable_name = 'personid'
        previous_login = authdata.get(account_variable_name)
    if previous_login is not None:
        authdata[account_variable_name] = None
        authdata['logintime'] = datetime.utcnow()
        auth_utility = getUtility(IPlacelessAuthUtility)
        principal = auth_utility.unauthenticatedPrincipal()
        request.setPrincipal(principal)
        # We want to clear the session cookie so anonymous users can get
        # cached pages again. We need to do this after setting the session
        # values (e.g., ``authdata['personid'] = None``, above), because that
        # code will itself try to set the cookie in the browser.  We need to
        # provide a bit of time before the cookie clears (10 minutes at the
        # moment) so that, if code wants to send a notification (such as "your
        # account has been deactivated"), the session will still be available
        # long enough to give the message to the now-unauthenticated user.
        # The time period could probably be 5 or 10 seconds, if everyone were
        # on NTP, but...they're not, so we use a pretty high fudge factor of
        # ten minutes.
        expireSessionCookie(request)
        notify(LoggedOutEvent(request))


class CookieLogoutPage:

    def logout(self):
        logoutPerson(self.request)
        self.request.response.addNoticeNotification(
            _(u'You have been logged out')
            )
        target = '%s/?loggingout=1' % self.request.URL[-1]
        self.request.response.redirect(target)
        return ''


class ForgottenPasswordPage(CaptchaMixin):

    errortext = None
    submitted = False
    captcha_submission = 'captcha_submission'
    captcha_hash = 'captcha_hash'
    page_title = 'Need a new Launchpad password?'

    def process_form(self):
        request = self.request
        if request.method != "POST":
            return

        # Validate the user is human, more or less.
        if not self.validateCaptcha():
            self.errortext = (
                "The answer to the simple math question was incorrect "
                "or missing.  Please try again.")
            return

        email = request.form.get("email").strip()
        email_address = getUtility(IEmailAddressSet).getByEmail(email)
        if email_address is None:
            self.errortext = ("Your account details have not been found. "
                              "Please check your subscription email "
                              "address and try again.")
            return

        person = email_address.person
        if person is not None and person.isTeam():
            self.errortext = ("The email address <strong>%s</strong> "
                              "belongs to a team, and teams cannot log in to "
                              "Launchpad." % email)
            return

        if person is None:
            account = email_address.account
            redirection_url = urlappend(
                self.request.getApplicationURL(), '+login')
            token = getUtility(IAuthTokenSet).new(
                account, email, email, LoginTokenType.PASSWORDRECOVERY,
                redirection_url=redirection_url)
        else:
            token = getUtility(ILoginTokenSet).new(
                person, email, email, LoginTokenType.PASSWORDRECOVERY)
        token.sendPasswordResetEmail()
        self.submitted = True
        return

    def success(self):
        return self.submitted and not self.errortext


class FeedsUnauthorizedView(UnauthorizedView):
    """All users of feeds are anonymous, so don't redirect to login."""

    def __call__(self):
        assert IUnauthenticatedPrincipal.providedBy(self.request.principal), (
            "Feeds user should always be anonymous.")
        self.request.response.setStatus(403) # Forbidden
        return self.forbidden_page()
