#!/usr/bin/python
# Copyright 2006 Canonical Ltd.  All rights reserved.

from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET


class DistributionMirrorTestHTTPServer(Resource):
    """An HTTP server used to test the DistributionMirror probe script.

    This server will return a '200 OK' status if the path requested starts
    with 'valid-mirror'. If the path starts with 'timeout', then the server
    will go to sleep and will never return. If the path starts with 'error',
    then it returns a '500 Internal Server Error'. If the path starts with 
    anything other than 'valid-mirror' or 'timeout', then a '404 Not Found'
    status is returned.
    """

    def getChild(self, name, request):
        if name == 'valid-mirror':
            leaf = DistributionMirrorTestHTTPServer()
            leaf.isLeaf = True
            return leaf
        elif name == 'timeout':
            return NeverFinishResource()
        elif name == 'error':
            return FiveHundredResource()
        elif name == 'redirectme':
            return RedirectingResource()
        else:
            return Resource.getChild(self, name, request)

    def render_GET(self, request):
        return "Hi"


class RedirectingResource(Resource):
    def render_GET(self, request):
        request.redirect('http://localhost:11375/valid-mirror')
        request.write('Get Lost')


class NeverFinishResource(Resource):
    def render_GET(self, request):
        return NOT_DONE_YET


class FiveHundredResource(Resource):
    def render_GET(self, request):
        request.setResponseCode(500)
        request.write('ASPLODE!!!')
        return NOT_DONE_YET
