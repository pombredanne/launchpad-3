#!/usr/bin/python
# Copyright 2006 Canonical Ltd.  All rights reserved.

from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET


class DistributionMirrorTestHTTPServer(Resource):
    """An HTTP server used to test the DistributionMirror probe script.

    This server will behave in a different way depending on the path that is
    accessed. These are the possible paths and how the server behaves for each
    of them:

    :valid-mirror: Respond with a '200 OK' status.

    :timeout: Do not respond, causing the client to keep waiting.

    :error: Respond with a '500 Internal Server Error' status.

    :redirect-to-valid-mirror: Respond with a '302 Found' status, redirecting
                               to http://localhost:11375/valid-mirror.

    :redirect-infinite-loop: Respond with a '302 Found' status, redirecting
                             to http://localhost:11375/redirect-infinite-loop/N
                             where N is an integer starting at 1 and increased
                             by 1 every time we redirect.

    :redirect-unknown-url-scheme: Respond with a '302 Found' status, redirecting
                                  to ftp://localhost/foo.

    Any other path will cause the server to respond with a '404 Not Found'
    status.
    """

    redirect_count = 0

    def getChild(self, name, request):
        if name == 'valid-mirror':
            leaf = DistributionMirrorTestHTTPServer()
            leaf.isLeaf = True
            return leaf
        elif name == 'timeout':
            return NeverFinishResource()
        elif name == 'error':
            return FiveHundredResource()
        elif name == 'redirect-to-valid-mirror':
            return RedirectingResource('http://localhost:11375/valid-mirror')
        elif 'redirect-infinite-loop' in name:
            self.redirect_count += 1
            return RedirectingResource(
                'http://localhost:11375/redirect-infinite-loop/%d'
                % self.redirect_count)
        elif name == 'redirect-unknown-url-scheme':
            return RedirectingResource('ftp://localhost/foo')
        else:
            return Resource.getChild(self, name, request)

    def render_GET(self, request):
        return "Hi"


class RedirectingResource(Resource):

    def __init__(self, redirection_url):
        self.redirection_url = redirection_url
        Resource.__init__(self)

    def render_GET(self, request):
        request.redirect(self.redirection_url)
        request.write('Get Lost')


class NeverFinishResource(Resource):
    def render_GET(self, request):
        return NOT_DONE_YET


class FiveHundredResource(Resource):
    def render_GET(self, request):
        request.setResponseCode(500)
        request.write('ASPLODE!!!')
        return NOT_DONE_YET
