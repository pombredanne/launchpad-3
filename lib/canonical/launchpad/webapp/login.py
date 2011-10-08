# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Stuff to do with logging in and logging out."""

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
import urllib

from BeautifulSoup import UnicodeDammit
from openid.consumer.consumer import (
    CANCEL,
    Consumer,
    FAILURE,
    SUCCESS,
    )
from openid.extensions import sreg
from openid.fetchers import (
    setDefaultFetcher,
    Urllib2Fetcher,
    )
import transaction
from z3c.ptcompat import ViewPageTemplateFile
from zope.app.security.interfaces import IUnauthenticatedPrincipal
from zope.component import (
    getSiteManager,
    getUtility,
    )
from zope.event import notify
from zope.interface import Interface
from zope.publisher.browser import BrowserPage
from zope.publisher.interfaces.http import IHTTPApplicationRequest
from zope.security.proxy import removeSecurityProxy
from zope.session.interfaces import (
    IClientIdManager,
    ISession,
    )

from canonical.config import config
from canonical.launchpad import _
from canonical.launchpad.interfaces.account import AccountSuspendedError
from canonical.launchpad.interfaces.openidconsumer import IOpenIDConsumerStore
from canonical.launchpad.readonly import is_read_only
from canonical.launchpad.webapp.dbpolicy import MasterDatabasePolicy
from canonical.launchpad.webapp.error import SystemErrorView
from canonical.launchpad.webapp.interfaces import (
    CookieAuthLoggedInEvent,
    ILaunchpadApplication,
    IPlacelessAuthUtility,
    IPlacelessLoginSource,
    LoggedOutEvent,
    )
from canonical.launchpad.webapp.metazcml import ILaunchpadPermission
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.launchpad.webapp.url import urlappend
from canonical.launchpad.webapp.vhosts import allvhosts
from lp.registry.interfaces.person import (
    IPersonSet,
    PersonCreationRationale,
    )
from lp.services.propertycache import cachedproperty
from lp.services.timeline.requesttimeline import get_request_timeline


class UnauthorizedView(SystemErrorView):

    response_code = None

    forbidden_page = ViewPageTemplateFile(
        '../../../lp/app/templates/launchpad-forbidden.pt')

    read_only_page = ViewPageTemplateFile(
        '../../../lp/app/templates/launchpad-readonlyfailure.pt')

    def page_title(self):
        if is_read_only():
            return super(UnauthorizedView, self).page_title
        else:
            return 'Forbidden'

    def __call__(self):
        # In read only mode, Unauthorized exceptions get raised by the
        # security policy when write permissions are requested. We need
        # to render the read-only failure screen so the user knows their
        # request failed for operational reasons rather than a genuine
        # permission problem.
        if is_read_only():
            # Our context is an Unauthorized exception, which acts like
            # a tuple containing (object, attribute_requested, permission).
            lp_permission = getUtility(ILaunchpadPermission, self.context[2])
            if lp_permission.access_level != "read":
                self.request.response.setStatus(503)  # Service Unavailable
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
                self.request.response.setStatus(500)  # Internal Server Error
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
            # to use the ``addInfoNotification`` method.
            allowUnauthenticatedSession(self.request)
            self.request.response.redirect(target)
            # Maybe render page with a link to the redirection?
            return ''
        else:
            self.request.response.setStatus(403)  # Forbidden
            return self.forbidden_page()

    def getRedirectURL(self, current_url, query_string):
        """Get the URL to redirect to.
        :param current_url: The URL of the current page.
        :param query_string: The string that should be appended to the current
            url.
        """
        return urlappend(current_url, '+login' + query_string)


class BasicLoginPage(BrowserPage):

    def isSameHost(self, url):
        """Returns True if the url appears to be from the same host as we are.
        """
        return url.startswith(self.request.getApplicationURL())

    def __call__(self):
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


def register_basiclogin(event):
    # The +basiclogin page should only be enabled for development and tests,
    # but we can't rely on config.devmode because it's turned off for
    # AppServerLayer tests, so we (ab)use the config switch for the test
    # OpenID provider, which has similar requirements.
    if config.launchpad.enable_test_openid_provider:
        getSiteManager().registerAdapter(
            BasicLoginPage,
            required=(ILaunchpadApplication, IHTTPApplicationRequest),
            provided=Interface,
            name='+basiclogin')


# The Python OpenID package uses pycurl by default, but pycurl chokes on
# self-signed certificates (like the ones we use when developing), so we
# change the default to urllib2 here.  That's also a good thing because it
# ensures we test the same thing that we run on production.
setDefaultFetcher(Urllib2Fetcher())


class OpenIDLogin(LaunchpadView):
    """A view which initiates the OpenID handshake with our provider."""
    _openid_session_ns = 'OPENID'

    def _getConsumer(self):
        session = ISession(self.request)[self._openid_session_ns]
        openid_store = getUtility(IOpenIDConsumerStore)
        return Consumer(session, openid_store)

    def render(self):
        if self.account is not None:
            return AlreadyLoggedInView(self.context, self.request)()

        # Allow unauthenticated users to have sessions for the OpenID
        # handshake to work.
        allowUnauthenticatedSession(self.request)
        consumer = self._getConsumer()

        timeline_action = get_request_timeline(self.request).start(
            "openid-association-begin",
            config.launchpad.openid_provider_root,
            allow_nested=True)
        try:
            self.openid_request = consumer.begin(
                config.launchpad.openid_provider_root)
        finally:
            timeline_action.finish()
        self.openid_request.addExtension(
            sreg.SRegRequest(required=['email', 'fullname']))

        assert not self.openid_request.shouldSendRedirect(), (
            "Our fixed OpenID server should not need us to redirect.")
        # Once the user authenticates with the OpenID provider they will be
        # sent to the /+openid-callback page, where we log them in, but
        # once that's done they must be sent back to the URL they were when
        # they started the login process (i.e. the current URL without the
        # '+login' bit). To do that we encode that URL as a query arg in the
        # return_to URL passed to the OpenID Provider
        starting_url = urllib.urlencode(
            [('starting_url', self.starting_url.encode('utf-8'))])
        trust_root = allvhosts.configs['mainsite'].rooturl
        return_to = urlappend(trust_root, '+openid-callback')
        return_to = "%s?%s" % (return_to, starting_url)
        form_html = self.openid_request.htmlMarkup(trust_root, return_to)

        # The consumer.begin() call above will insert rows into the
        # OpenIDAssociations table, but since this will be a GET request, the
        # transaction would be rolled back, so we need an explicit commit
        # here.
        transaction.commit()

        return form_html

    @property
    def starting_url(self):
        starting_url = self.request.getURL(1)
        query_string = "&".join([arg for arg in self.form_args])
        if query_string:
            starting_url += "?%s" % query_string
        return starting_url

    @property
    def form_args(self):
        """Iterate over form args, yielding 'key=value' strings for them.

        Exclude things such as 'loggingout' and starting with 'openid.', which
        we don't want.
        """
        for name, value in self.request.form.items():
            if name == 'loggingout' or name.startswith('openid.'):
                continue
            if isinstance(value, list):
                value_list = value
            else:
                value_list = [value]
            for value_list_item in value_list:
                # Thanks to apport (https://launchpad.net/bugs/61171), we need
                # to do this here.
                value_list_item = UnicodeDammit(value_list_item).markup
                yield "%s=%s" % (name, value_list_item)


class OpenIDCallbackView(OpenIDLogin):
    """The OpenID callback page for logging into Launchpad.

    This is the page the OpenID provider will send the user's browser to,
    after the user has authenticated on the provider.
    """

    suspended_account_template = ViewPageTemplateFile(
        'templates/login-suspended-account.pt')

    def _gather_params(self, request):
        params = dict(request.form)
        for key, value in request.query_string_params.iteritems():
            if len(value) > 1:
                raise ValueError(
                    'Did not expect multi-valued fields.')
            params[key] = value[0]

        return params

    def _get_requested_url(self, request):
        requested_url = request.getURL()
        query_string = request.get('QUERY_STRING')
        if query_string is not None:
            requested_url += '?' + query_string
        return requested_url

    def initialize(self):
        params = self._gather_params(self.request)
        requested_url = self._get_requested_url(self.request)
        consumer = self._getConsumer()
        timeline_action = get_request_timeline(self.request).start(
            "openid-association-complete", '', allow_nested=True)
        try:
            self.openid_response = consumer.complete(params, requested_url)
        finally:
            timeline_action.finish()

    def login(self, account):
        loginsource = getUtility(IPlacelessLoginSource)
        # We don't have a logged in principal, so we must remove the security
        # proxy of the account's preferred email.
        email = removeSecurityProxy(account.preferredemail).email
        logInPrincipal(
            self.request, loginsource.getPrincipalByLogin(email), email)

    @cachedproperty
    def sreg_response(self):
        return sreg.SRegResponse.fromSuccessResponse(self.openid_response)

    def _getEmailAddressAndFullName(self):
        # Here we assume the OP sent us the user's email address and
        # full name in the response. Note we can only do that because
        # we used a fixed OP (login.launchpad.net) that includes the
        # user's email address and full name in the response when
        # asked to.  Once we start using other OPs we won't be able to
        # make this assumption here as they might not include what we
        # want in the response.
        assert self.sreg_response is not None, (
            "OP didn't include an sreg extension in the response.")
        email_address = self.sreg_response.get('email')
        full_name = self.sreg_response.get('fullname')
        assert email_address is not None and full_name is not None, (
            "No email address or full name found in sreg response")
        return email_address, full_name

    def processPositiveAssertion(self):
        """Process an OpenID response containing a positive assertion.

        We'll get the person and account with the given OpenID
        identifier (creating one if necessary), and then login using
        that account.

        If the account is suspended, we stop and render an error page.

        We also update the 'last_write' key in the session if we've done any
        DB writes, to ensure subsequent requests use the master DB and see
        the changes we just did.
        """
        identifier = self.openid_response.identity_url.split('/')[-1]
        identifier = identifier.decode('ascii')
        should_update_last_write = False
        # Force the use of the master database to make sure a lagged slave
        # doesn't fool us into creating a Person/Account when one already
        # exists.
        person_set = getUtility(IPersonSet)
        email_address, full_name = self._getEmailAddressAndFullName()
        try:
            person, db_updated = person_set.getOrCreateByOpenIDIdentifier(
                identifier, email_address, full_name,
                comment='when logging in to Launchpad.',
                creation_rationale=(
                    PersonCreationRationale.OWNER_CREATED_LAUNCHPAD))
            should_update_last_write = db_updated
        except AccountSuspendedError:
            return self.suspended_account_template()

        with MasterDatabasePolicy():
            self.login(person.account)

        if should_update_last_write:
            # This is a GET request but we changed the database, so update
            # session_data['last_write'] to make sure further requests use
            # the master DB and thus see the changes we've just made.
            session_data = ISession(self.request)['lp.dbpolicy']
            session_data['last_write'] = datetime.utcnow()
        self._redirect()
        # No need to return anything as we redirect above.
        return None

    def render(self):
        if self.openid_response.status == SUCCESS:
            return self.processPositiveAssertion()

        if self.account is not None:
            # The authentication failed (or was canceled), but the user is
            # already logged in, so we just add a notification message and
            # redirect.
            self.request.response.addInfoNotification(
                _(u'Your authentication failed but you were already '
                   'logged into Launchpad.'))
            self._redirect()
            # No need to return anything as we redirect above.
            return None
        else:
            return OpenIDLoginErrorView(
                self.context, self.request, self.openid_response)()

    def __call__(self):
        retval = super(OpenIDCallbackView, self).__call__()
        # The consumer.complete() call in initialize() will create entries in
        # OpenIDConsumerNonce to prevent replay attacks, but since this will
        # be a GET request, the transaction would be rolled back, so we need
        # an explicit commit here.
        transaction.commit()
        return retval

    def _redirect(self):
        target = self.request.form.get('starting_url')
        if target is None:
            # If this was a POST, then the starting_url won't be in the form
            # values, but in the query parameters instead.
            target = self.request.query_string_params.get('starting_url')
            if target is None:
                target = self.request.getApplicationURL()
            else:
                target = target[0]
        self.request.response.redirect(target, temporary_if_possible=True)


class OpenIDLoginErrorView(LaunchpadView):

    page_title = 'Error logging in'
    template = ViewPageTemplateFile("templates/login-error.pt")

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


class AlreadyLoggedInView(LaunchpadView):

    page_title = 'Already logged in'
    template = ViewPageTemplateFile("templates/login-already.pt")


def logInPrincipal(request, principal, email):
    """Log the principal in. Password validation must be done in callsites."""
    # Force a fresh session, per Bug #828638. Any changes to any
    # existing session made this request will be lost, but that should
    # not be a problem as authentication must be done before
    # authorization and authorization before we do any actual work.
    client_id_manager = getUtility(IClientIdManager)
    new_client_id = client_id_manager.generateUniqueId()
    client_id_manager.setRequestId(request, new_client_id)
    session = ISession(request)
    authdata = session['launchpad.authenticateduser']
    assert principal.id is not None, 'principal.id is None!'
    request.setPrincipal(principal)
    authdata['accountid'] = principal.id
    authdata['logintime'] = datetime.utcnow()
    authdata['login'] = email
    notify(CookieAuthLoggedInEvent(request, email))


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
        openid_root = config.launchpad.openid_provider_root
        target = '%s+logout?%s' % (
            config.codehosting.secure_codebrowse_root,
            urllib.urlencode(dict(next_to='%s+logout' % (openid_root, ))))
        self.request.response.redirect(target)
        return ''


class FeedsUnauthorizedView(UnauthorizedView):
    """All users of feeds are anonymous, so don't redirect to login."""

    def __call__(self):
        assert IUnauthenticatedPrincipal.providedBy(self.request.principal), (
            "Feeds user should always be anonymous.")
        self.request.response.setStatus(403)  # Forbidden
        return self.forbidden_page()
