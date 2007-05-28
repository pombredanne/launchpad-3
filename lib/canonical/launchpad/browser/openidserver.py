# Copyright 2007 Canonical Ltd.  All rights reserved.

"""OpenID server."""

__metaclass__ = type
__all__ = []

from datetime import datetime, timedelta
import re
from tempfile import mkdtemp
import textwrap
import threading
from time import time

import pytz

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.session.interfaces import ISession, IClientIdManager
from zope.component import getUtility
from zope.interface import implements, Interface
from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.security.interfaces import Unauthorized
from zope.security.proxy import isinstance as zisinstance

from openid.server.server import (
    ProtocolError,
    Server,
    ENCODE_URL,
    CheckIDRequest,
    )
from openid.server.trustroot import TrustRoot
from openid import oidutil

from canonical.launchpad.interfaces import (
        IEmailAddressSet, ILaunchBag, IOpenIdAuthorizationSet,
        ILaunchpadOpenIdStoreFactory, IPersonSet, UnexpectedFormData,
        )
from canonical.launchpad.webapp import LaunchpadView, canonical_url
from canonical.launchpad.webapp.publisher import (
        stepthrough, Navigation, RedirectionView,
        )
from canonical.launchpad.webapp.vhosts import allvhosts
from canonical.uuid import generate_uuid


SESSION_PKG_KEY = 'OpenID'

# Shut up noisy OpenID library
def null_log(message, level=0):
    pass
oidutil.log = null_log


class IOpenIdView(Interface):
    """Marker interface"""
    pass

class OpenIdView(LaunchpadView):
    implements(IOpenIdView)

    def publishTraverse(self, request, name):
        # XXX: Argh! Navigation doesn't seem to be hooked into view traversal
        # -- StuartBishop 20070428
        nav = OpenIdViewNavigation(self, request)
        return nav.publishTraverse(request, name)

    openid_request = None

    default_template = ViewPageTemplateFile("../templates/openid-index.pt")
    decide_template = ViewPageTemplateFile("../templates/openid-decide.pt")
    invalid_identity_template = ViewPageTemplateFile(
            "../templates/openid-invalid-identity.pt"
            )

    def __init__(self, context, request):
        LaunchpadView.__init__(self, context, request)
        store_factory = getUtility(ILaunchpadOpenIdStoreFactory)
        self.openid_server = Server(store_factory())

    def render(self):
        """Handle all OpenId requests and form submissions

        Returns the page contents after setting all relevant headers in
        self.request.response
        """
        # Detect submission of the decide page
        if self.request.form.has_key('token'):
            self.restoreSessionOpenIdRequest()
            if self.request.form.get('action_deny'):
                return self.renderOpenIdResponse(self.deny())
            elif self.request.form.get('action_allow'):
                return self.renderOpenIdResponse(self.allow())
            else:
                raise UnexpectedFormData("Invalid action")

        # Not a form submission, so extract the OpenIDRequest from the request.
        # Convert our Unicode arguments Z3 gives us back to ASCII so
        # the error messages the OpenID library gives us are nicer (it
        # relies on repr())
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
            self.login = self.getPersonNameByIdentity(
                    self.openid_request.identity
                    )
            if self.isAuthorized():
                openid_response = self.openid_request.answer(True)
            else:
                openid_response = self.openid_request.answer(
                    False, allvhosts.configs['openid'].rooturl
                    )
        # Handle checkid_setup requests.
        elif self.openid_request.mode == 'checkid_setup':
            # Determine the account we are trying to authenticate with.
            # The consumer might have sent us an identity URL we can
            # extract the identifier from, or maybe sent us a token
            # indicating we need to calculate the identity.
            if (self.openid_request.identity ==
                    'http://specs.openid.net/auth/2.0/identifier_select'):
                # Magic identity indicating that we need to determine it.
                if self.user is None:
                    raise Unauthorized("You must be logged in to continue")
                self.login = self.user.name
                self.openid_request.identity = '%s+openid/+id/%s' % (
                        allvhosts.configs['openid'].rooturl,
                        self.user.openid_identifier
                        )

            else:
                # Consumer sent us an identity URL
                self.login = self.getPersonNameByIdentity(
                        self.openid_request.identity
                        )
                if self.login is None:
                    if self.user is None:
                        self.login = 'username'
                    else:
                        self.login = self.user.name
                    return self.invalid_identity_template()

            if not self.isAuthenticated():
                # Interactive request, but user is not yet logged on.
                # Trigger authentication.
                raise Unauthorized(
                        "You are not authorized to use this OpenID identifier."
                        )

            elif self.isAuthorized():
                # User is logged in and the site is authorized.
                openid_response = self.openid_request.answer(True)

            else:
                # We have an interactive id check request (checkid_setup).
                # Render a page allowing the user to choose how to proceed.
                return self.showDecidePage()

        else:
            openid_response = self.openid_server.handleRequest(
                    self.openid_request
                    )

        # If the above code has not already returned or raised an exception,
        # openid_respose is filled out ready for the openid library to render.
        return self.renderOpenIdResponse(openid_response)

    def renderOpenIdResponse(self, openid_response):
        webresponse = self.openid_server.encodeResponse(openid_response)

        response = self.request.response
        response.setStatus(webresponse.code)
        for header, value in webresponse.headers.items():
            response.setHeader(header, value)
        return webresponse.body

    def getPersonByIdentity(self, identity):
        """Return the Person from the OpenID identitifier.
        
        Returns None if the identity was not a valid Launchpad OpenID
        identifier. This includes checks that the name belongs to a valid
        person and is not a team.

        >>> view = OpenIdView(None, None)
        >>> view.getPersonByIdentity('foo')
        >>> view.getPersonByIdentity('https://launchpad.dev/~admins')
        >>> view.getPersonByIdentity('http://example.com/~sabdfl')
        >>> view.getPersonByIdentity('http://launchpad.dev/~sabdfl').name
        u'sabdfl'
        >>> view.getPersonByIdentity('https://launchpad.dev/~sabdfl').name
        u'sabdfl'
        >>> view.getPersonByIdentity('https://launchpad.dev/%7Esabdfl').name
        u'sabdfl'
        >>> view.getPersonByIdentity('https://launchpad.dev/~sabdfl/').name
        u'sabdfl'
        >>> view.getPersonByIdentity(
        ...     'https://openid.launchpad.dev/+openid/+id/temp1').name
        u'sabdfl'
        >>> view.getPersonByIdentity(
        ...     'http://openid.launchpad.dev/+openid/+id/temp1').name
        u'sabdfl'
        """
        root_url = allvhosts.configs['mainsite'].rooturl
        if root_url.startswith('http:'):
            url_match_string = 'https?' + re.escape(root_url[4:])
        else:
            url_match_string = 'https?' + re.escape(root_url[5:])

        # Note that we accept both http and https urls.
        match = re.search(
                r'^\s*%s(?:~|%%7E)(\w+)/?\s*$' % url_match_string, identity
                )

        person_set = getUtility(IPersonSet)

        if match is not None:
            person = person_set.getByName(match.group(1))

        else:
            openid_url = allvhosts.configs['openid'].rooturl
            if openid_url.startswith('http:'):
                url_match_string = 'https?' + re.escape(openid_url[4:])
            else:
                url_match_string = 'https?' + re.escape(openid_url[5:])

            url_match_string += re.escape('+openid/+id/')

            match = re.search(
                    r'^\s*%s(\w+)/?\s*$' % url_match_string, identity
                    )

            if match is None:
                return None

            person = person_set.getByOpenIdIdentifier(match.group(1))

        if person is None:
            return None

        if not person.is_openid_enabled:
            return None

        return person

    def getPersonNameByIdentity(self, identity):
        """Return the Person.name for the given Identity URL, or None.

        >>> view = OpenIdView(None, None)
        >>> view.getPersonNameByIdentity('foo')
        >>> view.getPersonNameByIdentity('https://launchpad.dev/~admins')
        >>> view.getPersonNameByIdentity('http://example.com/~sabdfl')
        >>> view.getPersonNameByIdentity('http://launchpad.dev/~sabdfl')
        u'sabdfl'
        """
        person = self.getPersonByIdentity(identity)
        if person is None:
            return None
        else:
            return person.name

    @property
    def trust_root(self):
        try:
            return TrustRoot.parse(self.openid_request.trust_root)
        except AttributeError:
            return None

    def showDecidePage(self):
        """Render the 'do you want to authenticate' page.

        An OpenID consumer has redirected the user here to be authenticated.
        We need to explain what they are doing here and ask them if they
        want to allow Launchpad to authenticate them with the OpenID consumer.
        """
        if self.trust_root is None:
            raise UnexpectedFormData("Invalid trust root")
        # To ensure that the user has seen this page and it was actually the
        # user that clicks the 'Accept' button, we generate a token and
        # use it to store the openid_request in the session. The token
        # is passed through by the form, but it is only meaningful if
        # it was used to store information in the actual users session,
        # rather than the session of a malicious connection attempting a
        # man-in-the-middle attack.
        token = generate_uuid()
        session = self.getSession()
        # We also store the time with the openid_request so we can clear
        # out old requests after some time, say 1 hour.
        now = time()
        self._sweep(now, session)
        # Store token with a distinct prefix to ensure malicious requests
        # can't trick our code into retrieving something that isn't a token.
        session['token_' + token] = (now, self.openid_request)
        self.token = token
        return self.decide_template()

    def _sweep(self, now, session):
        """Clean our Session of tokens older than 1 hour."""
        to_delete = []
        for key, value in session.items():
            timestamp = value[0]
            if timestamp < now - 3600:
                to_delete.append(key)
        for key in to_delete:
            del session[key]

    def isAuthenticated(self):
        """Returns True if we are logged in as the owner of the identity."""
        # Not authenticated if the user is not logged in
        if self.user is None:
            return False

        # Not authenticated if we are logged in as someone other than
        # the identity's owner
        return self.user.name == self.login

    def isAuthorized(self):
        """Check if the identity is authorized for the trust_root"""
        # Can't be authorized if we are logged in, or logged in as a
        # user other than the identity owner.
        if not self.isAuthenticated():
            return False

        client_id = getUtility(IClientIdManager).getClientId(self.request)

        auth_set = getUtility(IOpenIdAuthorizationSet)
        return auth_set.isAuthorized(
                self.user,
                self.openid_request.trust_root,
                client_id
                )

    def restoreSessionOpenIdRequest(self):
        """Get the OpenIDRequest from our session using the token in the
        request.
        """
        try:
            token = self.request.form['token']
        except LookupError:
            raise UnexpectedFormData("No token in request")
        session = self.getSession()
        try:
            timestamp, self.openid_request = session['token_' + token]
        except LookupError:
            raise UnexpectedFormData("Invalid or expired token")

        assert zisinstance(self.openid_request, CheckIDRequest), \
                'Invalid OpenIDRequest in session'

    def trashSessionOpenIdRequest(self):
        """Remove the OpenIdRequest from the session using the token in the
        request.
        """
        try:
            token = self.request.form['token']
        except LookupError:
            raise UnexpectedFormData("No token in request")
        session = self.getSession()
        try:
            del session['token_' + token]
        except LookupError:
            pass

    def allow(self):
        """Handle "Allow" selection from the decide page.

        Returns an OpenIDResponse.
        """
        # If the user is not authenticated as the user owning the
        # identifier, bounce them to the login page.
        self.login = self.getPersonNameByIdentity(
                self.openid_request.identity
                )
        if not self.isAuthenticated():
            raise Unauthorized(
                    "You are not yet authorized to use this OpenID identifier."
                    )
        duration = self.request.form['allow_duration']

        if duration != 'once':
            # Sticky authorization - calculate expiry and store authorization
            # for future use.
            if duration == 'forever':
                expires = None
            else:
                try:
                    duration = int(duration)
                except ValueError:
                    raise UnexpectedFormData
                expires = (
                        datetime.utcnow().replace(tzinfo=pytz.UTC)
                        + timedelta(seconds=duration)
                        )

            auth_set = getUtility(IOpenIdAuthorizationSet)
            auth_set.authorize(
                    self.user, self.openid_request.trust_root, expires
                    )

        return self.openid_request.answer(True)

    def deny(self):
        """Handle "Deny" choice from the decide page.

        Returns a negative OpenIDResponse and removes the OpenIDRequest from
        the session immediately.
        """
        try:
            return self.openid_request.answer(False)
        finally:
            self.trashSessionOpenIdRequest()

    def getSession(self):
        return ISession(self.request)[SESSION_PKG_KEY]


class OpenIdViewNavigation(Navigation):
    usedfor = IOpenIdView

    @stepthrough('+email')
    def traverse_email(self, name):
        # Allow traversal to email addresses, redirecting to the
        # user's permanent OpenID URL.
        email = getUtility(IEmailAddressSet).getByEmail(name)
        if email is not None:
            person = getUtility(IPersonSet).get(email.personID)
            target = '%s+openid/+id/%s' % (
                    allvhosts.configs['openid'].rooturl,
                    person.openid_identifier
                    )
            return RedirectionView(target, self.request, 303)
        else:
            return None

    @stepthrough('+id')
    def traverse_id(self, name):
        person = getUtility(IPersonSet).getByOpenIdIdentifier(name)
        if person is not None:
            return MinimalOpenIdIdentityView(self.request, person)
        else:
            return None
    
    def traverse(self, name):
        # Provide a permanent OpenID identity for use by the Ubuntu shop
        # or other services that cannot cope with name changes.
        try:
            person_id = int(name)
        except ValueError:
            pass
        else:
            person = getUtility(IPersonSet).get(person_id)
            if person is not None:
                return MinimalOpenIdIdentityView(self.request, person)

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


class MinimalOpenIdIdentityView:
    """Render a minimal OpenID idenntity page."""
    implements(IBrowserPublisher)

    def __init__(self, request, context):
        self.request = request
        self.context = context

    def __call__(self):
        # XXX: No idea how to make this next line work. Hardcode for now
        # -- StuartBishop 20070528
        #person_url = canonical_url(self.context, rootsite='openid')
        openid_identifier = self.context.openid_identifier
        server_url = allvhosts.configs['openid'].rooturl
        person_url = '%s+openid/+id/%s' % (server_url, openid_identifier)
        return textwrap.dedent("""\
                <html>
                <head>
                <link rel="openid.server" href="%(server_url)s">
                </head>
                <body>
                <h1>OpenID Identity URL %(openid_identifier)s</h1>
                </body>
                </html>
                """ % vars())

    def browserDefault(self, request):
        return self, ()

