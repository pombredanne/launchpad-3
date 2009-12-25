from z3c.ptcompat import ViewPageTemplateFile

from lp.services.openid.browser.openiddiscovery import (
    XRDSContentNegotiationMixin)

from canonical.launchpad.webapp import LaunchpadView


class FakeOpenIDIndexView(XRDSContentNegotiationMixin, LaunchpadView):
    template = ViewPageTemplateFile(
        "../templates/null.pt")
    xrds_template = ViewPageTemplateFile(
        "../templates/openidapplication-xrds.pt")

    @property
    def openid_server_url(self):
        """The OpenID Server endpoint URL for Launchpad."""
        return 'https://launchpad.dev/testopenid/+openid-auth'


class FakeOpenIDAuthView(LaunchpadView):
    server_url = 'https://launchpad.dev/testopenid'

    def render(self):
        from openid.server.server import Server
        from openid.store.memstore import MemoryStore
        self.openid_server = Server(MemoryStore(), self.server_url)
        self.openid_request = self.openid_server.decodeRequest(
            self.openid_parameters)
        assert self.openid_request is not None
        openid_response = self.createPositiveResponse()
        return self.renderOpenIDResponse(openid_response)

    @property
    def openid_parameters(self):
        """A dictionary of OpenID query parameters from request."""
        query = {}
        for key, value in self.request.form.items():
            if key.startswith('openid.'):
                query[key.encode('US-ASCII')] = value.encode('US-ASCII')
        return query

    def renderOpenIDResponse(self, openid_response):
        webresponse = self.openid_server.encodeResponse(openid_response)
        response = self.request.response
        response.setStatus(webresponse.code)
        for header, value in webresponse.headers.items():
            response.setHeader(header, value)
        return webresponse.body

    def createPositiveResponse(self):
        """Create a positive assertion OpenIDResponse."""
        assert self.openid_request is not None, (
            'No OpenID request to respond to.')
        return self.openid_request.answer(
            True, identity='https://openid.launchpad.dev/+id/mark_oid')
