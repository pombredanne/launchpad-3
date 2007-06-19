# Copyright 2007 Canonical Ltd.  All rights reserved.

"""OpenID server."""

__metaclass__ = type
__all__ = [
    'OpenIdMixin',
    ]

import cgi
from datetime import datetime
from time import time

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.session.interfaces import ISession, IClientIdManager
from zope.component import getUtility
from zope.event import notify
from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.security.proxy import isinstance as zisinstance

from openid.server.server import CheckIDRequest, ENCODE_URL, Server
from openid.server.trustroot import TrustRoot
from openid import oidutil

from canonical.config import config
from canonical.launchpad import _
from canonical.lp.dbschema import LoginTokenType
from canonical.launchpad.interfaces import (
    ILaunchpadOpenIdStoreFactory, ILoginServiceAuthorizeForm,
    ILoginServiceLoginForm, ILoginTokenSet, IOpenIdApplication,
    IOpenIdAuthorizationSet, IPersonSet, NotFoundError, UnexpectedFormData)
from canonical.launchpad.interfaces.validation import valid_password
from canonical.launchpad.validators.email import valid_email
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, LaunchpadFormView, LaunchpadView)
from canonical.launchpad.webapp.interfaces import (
    IPlacelessLoginSource, LoggedOutEvent)
from canonical.launchpad.webapp.login import logInPerson
from canonical.launchpad.webapp.publisher import (
    Navigation, RedirectionView, stepthrough, stepto)
from canonical.launchpad.webapp.vhosts import allvhosts
from canonical.uuid import generate_uuid
from canonical.widgets.itemswidgets import LaunchpadRadioWidget


OPENID_REQUEST_TIMEOUT = 3600
SESSION_PKG_KEY = 'OpenID'
IDENTIFIER_SELECT_URI = 'http://specs.openid.net/auth/2.0/identifier_select'


# Shut up noisy OpenID library
def null_log(message, level=0):
    pass
oidutil.log = null_log


class OpenIdMixin:

    openid_request = None

    def __init__(self, context, request):
        super(OpenIdMixin, self).__init__(context, request)
        store_factory = getUtility(ILaunchpadOpenIdStoreFactory)
        self.openid_server = Server(store_factory())
        self.server_url = allvhosts.configs['openid'].rooturl + '+openid'
        self.identity_url_prefix = allvhosts.configs['openid'].rooturl + '+id/'

    @property
    def user_identity_url(self):
        return self.identity_url_prefix + self.user.openid_identifier

    def isIdentityOwner(self):
        """Return True if the user can authenticate as the given identifier."""
        assert self.user is not None, "user should be logged in by now."
        return self.openid_request.identity in (
            IDENTIFIER_SELECT_URI, self.user_identity_url)

    def getSession(self):
        return ISession(self.request)[SESSION_PKG_KEY]

    @staticmethod
    def _sweep(now, session):
        """Clean our Session of nonces older than 1 hour.

        The session argument is edited in place to remove the expired items:
          >>> now = 10000
          >>> session = {
          ...     'x': (9999, 'foo'),
          ...     'y': (11000, 'bar'),
          ...     'z': (100, 'baz')
          ...     }
          >>> OpenIdMixin._sweep(now, session)
          >>> for key in sorted(session):
          ...     print key, session[key]
          x (9999, 'foo')
          y (11000, 'bar')
        """
        to_delete = []
        for key, value in session.items():
            timestamp = value[0]
            if timestamp < now - OPENID_REQUEST_TIMEOUT:
                to_delete.append(key)
        for key in to_delete:
            del session[key]

    def restoreRequestFromSession(self, key):
        """Get the OpenIDRequest from our session using the given key."""
        session = self.getSession()
        try:
            timestamp, self.openid_request = session[key]
        except KeyError:
            raise UnexpectedFormData("Invalid or expired nonce")

        assert zisinstance(self.openid_request, CheckIDRequest), (
            'Invalid OpenIDRequest in session')

    def saveRequestInSession(self, key):
        """Save the OpenIDRequest in our session using the given key."""
        session = self.getSession()
        # We also store the time with the openid_request so we can clear
        # out old requests after some time, say 1 hour.
        now = time()
        self._sweep(now, session)
        # Store nonce with a distinct prefix to ensure malicious requests
        # can't trick our code into retrieving something that isn't a nonce.
        session[key] = (now, self.openid_request)

    def trashRequestInSession(self, key):
        """Remove the OpenIdRequest from the session using the given key."""
        session = self.getSession()
        try:
            del session[key]
        except KeyError:
            pass

    def renderOpenIdResponse(self, openid_response):
        webresponse = self.openid_server.encodeResponse(openid_response)
        response = self.request.response
        response.setStatus(webresponse.code)
        for header, value in webresponse.headers.items():
            response.setHeader(header, value)
        return webresponse.body

    def createPositiveResponse(self):
        """Create a positive assertion OpenIDResponse.

        This method should be called to create the response to
        successful checkid requests.

        If the trust root for the request is in openid_sreg_trustroots,
        then additional user information is included with the
        response.
        """
        assert self.user is not None, (
            'Must be logged in for positive OpenID response')
        assert self.openid_request is not None, (
            'No OpenID request to respond to.')

        if not self.isIdentityOwner():
            return self.createFailedResponse()

        response = self.openid_request.answer(True)

        # If we are in identifier select mode, then we need to
        # override the claimed identifier.  For regular checks it does
        # not hurt, so we set it here unconditionally.
        response.addField(None, 'identity', self.user_identity_url)

        # If this is a trust root we know about and trust, send some
        # user details.
        if (self.openid_request.trust_root in
            config.launchpad.openid_sreg_trustroots):
            response.addField('sreg', 'email',
                              self.user.preferredemail.email, signed=True)
            response.addField('sreg', 'fullname',
                              self.user.displayname, signed=True)
            response.addField('sreg', 'nickname',
                              self.user.name, signed=True)
            response.addField('sreg', 'timezone',
                              self.user.timezone, signed=True)
        return response

    def createFailedResponse(self):
        """Create a failed assertion OpenIDResponse.

        This method should be called to create the response to
        unsuccessful checkid requests.
        """
        assert self.openid_request is not None, (
            'No OpenID request to respond to.')
        response = self.openid_request.answer(False, self.server_url)
        return response


class OpenIdView(OpenIdMixin, LaunchpadView):
    """An OpenID Provider endpoint for Launchpad.

    This class implemnts an OpenID endpoint using the python-openid
    library.  In addition to the normal modes of operation, it also
    implements the OpenID 2.0 identifier select mode.
    """

    default_template = ViewPageTemplateFile("../templates/openid-index.pt")
    invalid_identity_template = ViewPageTemplateFile(
        "../templates/openid-invalid-identity.pt")

    def render(self):
        """Handle all OpenId requests and form submissions

        Returns the page contents after setting all relevant headers in
        self.request.response
        """
        args = {}
        for key, value in self.request.form.items():
            if key.startswith('openid.'):
                args[key.encode('US-ASCII')] = value.encode('US-ASCII')
        # NB: Will be None if there are no parameters in the request.
        self.openid_request = self.openid_server.decodeRequest(args)

        # Not an OpenID request, so display a message explaining what this
        # is to nosy users.
        if self.openid_request is None:
            return self.default_template()

        # Handle checkid_immediate requests.
        if self.openid_request.mode == 'checkid_immediate':
            if self.isAuthorized():
                openid_response = self.createPositiveResponse()
            else:
                openid_response = self.createFailedResponse()

        # Handle checkid_setup requests.
        elif self.openid_request.mode == 'checkid_setup':
            # If we can not possibly handle this identity URL, show an
            # error page telling the user.
            if not self.canHandleIdentity():
                return self.invalid_identity_template()

            if self.user is None:
                return self.showLoginPage()
            if not self.isIdentityOwner():
                openid_response = self.createFailedResponse()
            elif self.isAuthorized():
                # User is logged in and the site is authorized.
                openid_response = self.createPositiveResponse()
            else:
                # We have an interactive id check request (checkid_setup).
                # Render a page allowing the user to choose how to proceed.
                return self.showDecidePage()

        else:
            openid_response = self.openid_server.handleRequest(
                    self.openid_request)

        # If the above code has not already returned or raised an exception,
        # openid_respose is filled out ready for the openid library to render.
        return self.renderOpenIdResponse(openid_response)

    def storeOpenIdRequestInSession(self):
        # To ensure that the user has seen this page and it was actually the
        # user that clicks the 'Accept' button, we generate a nonce and
        # use it to store the openid_request in the session. The nonce
        # is passed through by the form, but it is only meaningful if
        # it was used to store information in the actual users session,
        # rather than the session of a malicious connection attempting a
        # man-in-the-middle attack.
        nonce = generate_uuid()
        self.saveRequestInSession('nonce' + nonce)
        self.nonce = nonce

    def showLoginPage(self):
        """Render the login dialog.

        This should be done if the user has not yet authenticated to
        Launchpad.
        """
        self.storeOpenIdRequestInSession()
        return LoginServiceLoginView(
            self.context, self.request, self.nonce)()

    def showDecidePage(self):
        """Render the 'do you want to authenticate' page.

        An OpenID consumer has redirected the user here to be authenticated.
        We need to explain what they are doing here and ask them if they
        want to allow Launchpad to authenticate them with the OpenID consumer.
        """
        self.storeOpenIdRequestInSession()
        return LoginServiceAuthorizeView(
            self.context, self.request, self.nonce)()

    def canHandleIdentity(self):
        """Returns True if the identity URL is supported by the server."""
        identity = self.openid_request.identity
        return (identity == IDENTIFIER_SELECT_URI or
                identity.startswith(self.identity_url_prefix))

    def isAuthorized(self):
        """Check if the identity is authorized for the trust_root"""
        # Can't be authorized if we are not logged in, or logged in as a
        # user other than the identity owner.
        if self.user is None or not self.isIdentityOwner():
            return False

        client_id = getUtility(IClientIdManager).getClientId(self.request)
        auth_set = getUtility(IOpenIdAuthorizationSet)

        return auth_set.isAuthorized(
                self.user, self.openid_request.trust_root, client_id)


# Information about known trust roots
# XXX: 2007-06-14 jamesh
# Include more information about the trust roots, such as an icon.  We
# should really maintain this data elsewhere, but this should be fine
# for phase 1 of the implementation.
KNOWN_TRUST_ROOTS = {
    'http://localhost.localdomain:8001/':
        dict(title="OpenID Consumer Example"),
    'http://pdl-dev.co.uk':
        dict(title="PDL Demo OSCommerce shop"),
    'http://www.mmania.biz':
        dict(title="Demo Canonical Shop"),
    'http://www.mmania.biz/ubuntu/':
        dict(title="Demo Canonical Shop"),
    #'https://shop.ubuntu.com/':
    #    dict(title="Ubuntu Shop"),
    #'https://shipit.ubuntu.com/':
    #    dict(title="Ubuntu Shipit"),
    #'https://shipit.kubuntu.org/':
    #    dict(title="Kubuntu Shipit"),
    #'https://shipit.edubuntu.org/':
    #    dict(title="Edubuntu Shipit"),
    #'https://wiki.ubuntu.com/':
    #    dict(title="Ubuntu Wiki"),
    }


class LoginServiceBaseView(OpenIdMixin, LaunchpadFormView):
    """Common functionality for the OpenID login and authorize forms."""

    def __init__(self, context, request, nonce=None):
        super(LoginServiceBaseView, self).__init__(context, request)
        self.nonce = nonce

    @property
    def initial_values(self):
        return {'nonce': self.nonce}

    def setUpWidgets(self):
        """Set up the widgets, and grab the OpenID request from the session."""
        super(LoginServiceBaseView, self).setUpWidgets()

        # Restore the OpenID request.
        widget = self.widgets['nonce']
        if widget.hasValidInput():
            self.nonce = widget.getInputValue()
        if self.nonce is None:
            raise UnexpectedFormData("No OpenID request.")
        self.restoreRequestFromSession('nonce' + self.nonce)

    def trashRequest(self):
        """Remove the OpenID request from the session."""
        self.trashRequestInSession('nonce' + self.nonce)

    @property
    def relying_party_title(self):
        """Return a display name for the relying party.

        The relying party is looked up in the list of known RPs by its
        trust root to find its title.

        If the relying party is not known, its trust root URL is returned.
        """
        assert self.openid_request is not None, (
            'Could not find the OpenID request')
        rp_info = KNOWN_TRUST_ROOTS.get(self.openid_request.trust_root)
        if rp_info is not None:
            return rp_info['title']
        else:
            return self.openid_request.trust_root

    def isSaneTrustRoot(self):
        """Return True if the RP's trust root looks sane."""
        assert self.openid_request is not None, (
            'Could not find the OpenID request')
        trust_root = TrustRoot.parse(self.openid_request.trust_root)
        return trust_root.isSane()


class LoginServiceAuthorizeView(LoginServiceBaseView):

    schema = ILoginServiceAuthorizeForm
    template = ViewPageTemplateFile(
        "../templates/loginservice-authorize.pt")

    @action('Sign In', name='auth')
    def auth_action(self, action, data):
        self.trashRequest()
        return self.renderOpenIdResponse(self.createPositiveResponse())

    @action("I Don't Want To Sign In", name='deny')
    def deny_action(self, action, data):
        self.trashRequest()
        return self.renderOpenIdResponse(self.createFailedResponse())

    @action("No, I'm Someone Else", name='logout')
    # XXX 20070618 mpt: "I'm" should use a typographical apostrophe
    # XXX 20070618 mpt: "Someone Else" should be "Not" then the person's name
    def logout_action(self, action, data):
        # Log the user out and render the login page again.
        session = ISession(self.request)
        authdata = session['launchpad.authenticateduser']
        previous_login = authdata.get('personid')
        assert previous_login is not None, "User is not logged in."
        authdata['personid'] = None
        authdata['logintime'] = datetime.utcnow()
        notify(LoggedOutEvent(self.request))
        # Display the unauthenticated form
        return LoginServiceLoginView(
            self.context, self.request, self.nonce)()


class LoginServiceLoginView(LoginServiceBaseView):

    schema = ILoginServiceLoginForm
    template = ViewPageTemplateFile("../templates/loginservice-login.pt")
    custom_widget('action', LaunchpadRadioWidget)

    email_sent_template = ViewPageTemplateFile(
        "../templates/loginservice-email-sent.pt")

    @property
    def initial_values(self):
        values = super(LoginServiceLoginView, self).initial_values
        values['action'] = 'login'
        return values

    def validate(self, data):
        email = data.get('email')
        action = data.get('action')
        password = data.get('password')
        person = getUtility(IPersonSet).getByEmail(email)
        if email is None or not valid_email(email):
            self.addError('Please enter a valid email address.')
            return

        if action == 'login':
            self.validateEmailAndPassword(email, password)
        elif action == 'resetpassword':
            if person is None:
                self.addError(_(
                    "Your account details have not been found. Please "
                    "check your subscription email address and try again."))
            elif person.isTeam():
                self.addError(_(
                    "The email address <strong>%s</strong> can not be used "
                    "to log in as it belongs to a team." % email))
        elif action == 'createaccount':
            if person is not None and person.is_valid_person:
                self.addError(_(
                    "Sorry, someone has already registered the %s email "
                    "address.  If this is you and you've forgotten your "
                    "password, just choose the 'I've forgotten my "
                    "password' option below and we'll allow you to "
                    "change it." % cgi.escape(email)))
            else:
                # This is either an email address we've never seen or it's
                # associated with an unvalidated profile, so we just move
                # on with the registration process as if we had never seen it.
                pass
        else:
            raise UnexpectedFormData("Unknown action")

    def validateEmailAndPassword(self, email, password):
        """Check that the email address and password are valid for login."""
        loginsource = getUtility(IPlacelessLoginSource)
        principal = loginsource.getPrincipalByLogin(email)
        if principal is not None and principal.validate(password):
            person = getUtility(IPersonSet).getByEmail(email)
            if person.preferredemail is None:
                self.addError(_(
                    "The email address '%s' has not yet been confirmed. We "
                    "sent an email to that address with instructions on how "
                    "to confirm that it belongs to you." % email))
                self.token = getUtility(ILoginTokenSet).new(
                    person, email, email, LoginTokenType.VALIDATEEMAIL)
                self.token.sendEmailValidationRequest(
                    self.request.getApplicationURL())
                self.saveRequestInSession('token' + self.token.token)

            if not person.is_valid_person:
                # Normally invalid accounts will have a NULL password
                # so this will be rarely seen, if ever. An account with no
                # valid email addresses might end up in this situation,
                # such as having them flagged as OLD by a email bounce
                # processor or manual changes by the DBA.
                self.addError(_("This account cannot be used."))
        else:
            self.addError(_("Incorrect password for the provided "
                            "email address."))

    @action('Continue', name='continue')
    def continue_action(self, action, data):
        email = data['email']
        action = data['action']
        self.trashRequest()
        if action == 'login':
            password = data['password']
            loginsource = getUtility(IPlacelessLoginSource)
            principal = loginsource.getPrincipalByLogin(email)
            logInPerson(self.request, principal, email)
            return self.renderOpenIdResponse(self.createPositiveResponse())
        elif action == 'resetpassword':
            return self.process_password_recovery(email)
        elif action == 'createaccount':
            return self.process_registration(email)
        else:
            raise UnexpectedFormData("Unknown action.")

    def process_registration(self, email):
        logintokenset = getUtility(ILoginTokenSet)
        self.token = logintokenset.new(
            requester=None, requesteremail=None, email=email,
            tokentype=LoginTokenType.NEWACCOUNT)
        self.token.sendNewUserNeutralEmail()
        self.saveRequestInSession('token' + self.token.token)
        self.email_heading = 'Registration mail sent'
        self.email_reason = 'to confirm your address.'
        return self.email_sent_template()

    def process_password_recovery(self, email):
        person = getUtility(IPersonSet).getByEmail(email)
        logintokenset = getUtility(ILoginTokenSet)
        self.token = logintokenset.new(
            person, email, email, LoginTokenType.PASSWORDRECOVERY)
        self.token.sendPasswordResetNeutralEmail()
        self.saveRequestInSession('token' + self.token.token)
        self.email_heading = 'Forgotten your password?'
        self.email_reason = 'with instructions on resetting your password.'
        return self.email_sent_template()


class OpenIdApplicationNavigation(Navigation):
    usedfor = IOpenIdApplication

    @stepthrough('+id')
    def traverse_id(self, name):
        person = getUtility(IPersonSet).getByOpenIdIdentifier(name)
        if person is not None and person.is_openid_enabled:
            return OpenIdIdentityView(person, self.request)
        else:
            return None

    @stepto('token')
    def token(self):
        # We need to traverse the 'token' namespace in order to allow people
        # to create new accounts and reset their passwords. This can't clash
        # with a person's name because it's a blacklisted name.
        return getUtility(ILoginTokenSet)

    def traverse(self, name):
        # Provide a permanent OpenID identity for use by the Ubuntu shop
        # or other services that cannot cope with name changes.
        person = getUtility(IPersonSet).getByName(name)
        if person is not None and person.is_openid_enabled:
            target = '%s+id/%s' % (
                    allvhosts.configs['openid'].rooturl,
                    person.openid_identifier)
            return RedirectionView(target, self.request, 303)
        else:
            raise NotFoundError(name)


class ProtocolErrorView(LaunchpadView):
    """Render a ProtocolError raised by the openid library."""
    def render(self):
        response = self.request.response
        if self.context.whichEncoding() == ENCODE_URL:
            url = self.context.encodeToURL()
            response.redirect(url)
        else:
            response.setStatus(200)
        response.setHeader('Content-Type', 'text/plain;charset=utf-8')
        return self.context.encodeToKVForm()


class OpenIdIdentityView:
    """Render the OpenID identity page."""

    implements(IBrowserPublisher)

    identity_template = ViewPageTemplateFile("../templates/openid-identity.pt")

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        # Setup variables to pass to the template
        self.server_url = allvhosts.configs['openid'].rooturl + '+openid'
        self.identity_url = '%s+id/%s' % (
                self.server_url, self.context.openid_identifier)
        self.person_url = canonical_url(self.context, rootsite='mainsite')
        self.meta_refresh_content = "1; URL=%s" % self.person_url

        return self.identity_template()

    def browserDefault(self, request):
        return self, ()

