# Copyright 2007 Canonical Ltd.  All rights reserved.

"""OpenID server."""

__metaclass__ = type
__all__ = []

import re
from tempfile import mkdtemp
from time import time
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.session.interfaces import ISession
from zope.component import getUtility
from zope.interface import Interface, Attribute, implements
from zope.security.interfaces import Unauthorized
from zope.security.proxy import isinstance as zisinstance

from openid.server.server import (
    ProtocolError,
    Server,
    ENCODE_URL,
    CheckIDRequest,
    )
from openid.server.trustroot import TrustRoot
# XXX: Temporary - switch to SQL -- StuartBishop 20070214
from openid.store.filestore import FileOpenIDStore

from canonical.launchpad.interfaces import ILaunchBag, UnexpectedFormData
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.vhosts import allvhosts
from canonical.uuid import generate_uuid


SESSION_PKG_KEY = 'openid'


class IOpenIdView(Interface):
    openid_request = Attribute("OpenIDRequest")
    trust_root = Attribute("TrustRoot")


class OpenIdView(LaunchpadView):
    implements(IOpenIdView)

    openid_server = Server(FileOpenIDStore(mkdtemp('openid')))

    openid_request = None
    trust_root = None

    default_template = ViewPageTemplateFile("../templates/openid-index.pt")
    decide_template = ViewPageTemplateFile("../templates/openid-decide.pt")
    invalid_identity_template = ViewPageTemplateFile(
            "../templates/openid-invalid-identity.pt"
            )

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
            elif self.request.form.get('action_allow_once'):
                return self.renderOpenIdResponse(self.allowOnce())
            else:
                raise UnexpectedFormData("Invalid action")

        # Not a form submission, so extract the OpenIDRequest from the request.
        try:
            # NB: Will be None if there are no parameters in the request.
            self.openid_request = self.openid_server.decodeRequest(
                self.request.form
                )
        except ProtocolError, exception:
            return self.renderProtocolError(exception)

        # Not an OpenID request, so display a message explaining what this
        # is to nosy users.
        if self.openid_request is None:
            return self.default_template()

        if self.openid_request.mode in ['checkid_immediate', 'checkid_setup']:
            self.login = self.extractName(self.openid_request.identity)
            if self.login is None:
                # Failed to extract the username from the identity, which
                # means this is not a valid Launchpad identity.
                # Display an error message to the user and let them
                # continue.
                me = getUtility(ILaunchBag).user
                if me is None:
                    self.login = 'username'
                else:
                    self.login = me.name
                return self.invalid_identity_template()

            if self.isAuthorized():
                # User has previously allowed auth to this site, or we
                # wish to force auth to be allowed to this site
                openid_response = self.openid_request.answer(True)

            elif self.openid_request.immediate:
                # An immediate request has come through, but we can't
                # approve it without asking the user. So report fail to
                # the consumer.
                openid_response = self.openid_request.answer(
                        False, allvhosts.configs['openid'].rooturl
                        )
            else:
                # We have an interactive id check request (checkid_setup).
                # Render a page allowing the user to choose how to proceed.
                return self.showDecidePage()

        else:
            openid_response = self.openid_server.handleRequest(
                    self.openid_request
                    )

        return self.renderOpenIdResponse(openid_response)

    def renderOpenIdResponse(self, openid_response):
        webresponse = self.openid_server.encodeResponse(openid_response)

        response = self.request.response
        response.setStatus(webresponse.code)
        for header, value in webresponse.headers.items():
            response.setHeader(header, value)
        return webresponse.body

    def extractName(self, identity):
        """Return the Person.name from the OpenID identitifier.
        
        Returns None if the identity was not a valid Launchpad OpenID
        identifier.

        >>> view = OpenIdView(None, None)
        >>> view.extractName('foo')
        >>> view.extractName('http://example.com/~sabdfl')
        >>> view.extractName('http://launchpad.dev/~sabdfl')
        'sabdfl'
        >>> view.extractName('https://launchpad.dev/~sabdfl')
        'sabdfl'
        """
        rooturl = allvhosts.configs['mainsite'].rooturl
        if rooturl.startswith('http:'):
            url_match_string = 'https?' + re.escape(rooturl[4:])
        elif rooturl.startswith('https:'):
            url_match_string = 'https?' + re.escape(rooturl[5:])
        else:
            raise AssertionError("Invalid root url %s" % rooturl)

        # Note that we accept
        match = re.search(r'^\s*%s~(\w+)\s*$' % url_match_string, identity)

        if match is None:
            return None
        else:
            return match.group(1)

    def showDecidePage(self):
        """Render the 'do you want to authenticate' page.

        An OpenID consumer has redirected the user here to be authenticated.
        We need to explain what they are doing here and ask them if they
        want to allow Launchpad to authenticate them with the OpenID consumer.
        """
        self.trust_root = TrustRoot.parse(self.openid_request.trust_root)
        if self.trust_root is None:
            raise UnexpectedFormData("Invalid trust root")
        # To ensure that the user has seen this page and it was actually the
        # user that clicks the 'Accept' button, we generate a token and
        # use it to store the openid_request in the session. The token
        # is passed through by the form, but it is only meaningful if
        # it was used to store information in the actual users session,
        # rather than the session of a malicious connection attempting a
        # man-in-the-middle attack.
        token = '%s' % generate_uuid()
        session = self.getSession()
        # We also store the time with the openid_request so we can clear
        # out old requests after some time, say 1 hour.
        now = time()
        self._sweep(now, session)
        # Store token with a distinct prefix to ensure malicious requests
        # can't trick our code into retrieving something that isn't a token.
        session['token_' + token] = (now, self.openid_request)
        self.token = token
        return self.decide_template(foo='foobar')

    def _sweep(self, now, session):
        """Clean our Session of tokens older than 1 hour."""
        to_delete = []
        for key, value in session.items():
            timestamp, session = value
            if timestamp < now - 3600:
                to_delete.append(key)
        for key in to_delete:
            del session[key]

    def isAuthenticated(self):
        """Returns True if we are logged in as the owner of the identity."""
        me = getUtility(ILaunchBag).user
        # Not authenticated if the user is not logged in
        if me is None:
            return False

        # Not authenticated if we are logged in as someone other than
        # the identity's owner
        return me.name == self.login

    def isAuthorized(self):
        if not self.isAuthenticated():
            return False

        # XXX: Implement this
        trust_root = self.openid_request.trust_root

        return False

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

    def allowOnce(self):
        """Handle "Allow Once" selection from the decide page.

        Returns an OpenIDResponse.
        """
        # If the user is not authenticated as the user owning the
        # identifier, bounce them to the login page.
        self.login = self.extractName(self.openid_request.identity)
        if not self.isAuthenticated():
            raise Unauthorized(
                    "You are not yet authorized to use this OpenID identifier."
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

    def renderProtocolError(self, exception):
        # XXX: Is this tested? -- StuartBishop 20070226
        response = self.request.response
        if exception.whichEncoding() == ENCODE_URL:
            url = excecption.encodeToURL()
            response.redirect(url)
        else:
            response.setStatus(200)
        response.setHeader('Content-Type', 'text/plain;charset=utf-8')
        return exception.encodeToKVForm()

