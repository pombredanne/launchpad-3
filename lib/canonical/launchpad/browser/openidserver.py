# Copyright 2007 Canonical Ltd.  All rights reserved.

"""OpenID server."""

__metaclass__ = type
__all__ = []

from tempfile import mkdtemp

from openid.server.server import ProtocolError, Server, ENCODE_URL
# XXX: Temporary - switch to SQL -- StuartBishop 20070214
from openid.store.filestore import FileOpenIDStore

from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.vhosts import allvhosts


class OpenIdView(LaunchpadView):

    openid_server = Server(FileOpenIDStore(mkdtemp('openid')))

    def render(self):
        try:
            openid_request = self.openid_server.decodeRequest(self.request.form)
        except ProtocolError, exception:
            return self.renderProtocolError(exception)

        # Not an OpenID request, so display a message explaining what this
        # is to nosy users.
        if openid_request is None:
            return self.template()

        if openid_request.mode in ['checkid_immediate', 'checkid_setup']:
            if self.isAuthorized(
                openid_request.identity, openid_request.trust_root):
                openid_response = openid_request.answer(True)
            elif openid_request.immediate:
                openid_response = openid_request.answer(
                        False, allvhosts.configs['openid'].rooturl
                        )
            else:
                self.showDecidePage(openid_request)
                return
        else:
            openid_response = self.openid_server.handleRequest(openid_request)

        webresponse = self.openid_server.encodeResponse(openid_response)

        response = self.request.response
        response.setStatus(webresponse.code)
        for header, value in webresponse.headers.items():
            response.setHeader(header, value)
        return webresponse.body

    def isAuthorized(self, identity, trust_root):
        return False

    def renderProtocolError(self, exception):
        response = self.request.response
        if exception.whichEncoding() == ENCODE_URL:
            url = excecption.encodeToURL()
            response.redirect(url)
        else:
            response.setStatus(200)
        response.setHeader('Content-Type', 'text/plain;charset=utf-8')
        return exception.encodeToKVForm()

