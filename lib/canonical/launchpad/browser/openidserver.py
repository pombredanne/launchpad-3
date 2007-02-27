# Copyright 2007 Canonical Ltd.  All rights reserved.

"""OpenID server."""

__metaclass__ = type
__all__ = []

from tempfile import mkdtemp
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.interface import Interface, Attribute, implements

from openid.server.server import ProtocolError, Server, ENCODE_URL
# XXX: Temporary - switch to SQL -- StuartBishop 20070214
from openid.store.filestore import FileOpenIDStore

from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.vhosts import allvhosts


class IOpenIdView(Interface):
    foo = Attribute('Foo')


class OpenIdView(LaunchpadView):
    implements(IOpenIdView)

    openid_server = Server(FileOpenIDStore(mkdtemp('openid')))

    default_template = ViewPageTemplateFile("../templates/openid-index.pt")
    decide_template = ViewPageTemplateFile("../templates/openid-decide.pt")

    def render(self):
        try:
            openid_request = self.openid_server.decodeRequest(self.request.form)
        except ProtocolError, exception:
            return self.renderProtocolError(exception)

        # Not an OpenID request, so display a message explaining what this
        # is to nosy users.
        if openid_request is None:
            return self.default_template()

        if openid_request.mode in ['checkid_immediate', 'checkid_setup']:
            if self.isAuthorized(
                openid_request.identity, openid_request.trust_root):
                openid_response = openid_request.answer(True)
            elif openid_request.immediate:
                openid_response = openid_request.answer(
                        False, allvhosts.configs['openid'].rooturl
                        )
            else:
                return self.showDecidePage(openid_request)
        else:
            openid_response = self.openid_server.handleRequest(openid_request)

        webresponse = self.openid_server.encodeResponse(openid_response)

        response = self.request.response
        response.setStatus(webresponse.code)
        for header, value in webresponse.headers.items():
            response.setHeader(header, value)
        return webresponse.body

    def showDecidePage(self, openid_request):
        """Render the 'do you want to authenticate' page.

        An OpenID consumer has redirected the user here to be authenticated.
        We need to explain what they are doing here and ask them if they
        want to allow Launchpad to authenticate them with the OpenID consumer.

        If the user is not authenticated with Launchpad, they will be
        presented with a login form. Otherwise, just "Login", and
        "Don't Login" buttons.
        """
        self.authenticated = False
        self.login = 'Fixme'
        return self.decide_template(foo='foobar')

    def isAuthorized(self, identity, trust_root):
        return False

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

