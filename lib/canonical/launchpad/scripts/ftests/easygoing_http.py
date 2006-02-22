#!/usr/bin/python
# Copyright 2006 Canonical Ltd.  All rights reserved.

from twisted.web import server
from twisted.web.resource import Resource
from twisted.internet import reactor


class EasyGoingHTTPServer(Resource):
    """I'm just an HTTP server that will always give you a '200 OK' answer
    if the first path element on the request is 'valid-mirror'.

    Otherwise you'll get a 404.
    """

    def getChild(self, name, request):
        if name == 'valid-mirror':
            leaf = EasyGoingHTTPServer()
            leaf.isLeaf = True
            return leaf
        else:
            return Resource.getChild(self, name, request)

    def render_GET(self, request):
        return "Hi"


if __name__ == "__main__":
    easygoing = EasyGoingHTTPServer()
    site = server.Site(easygoing)
    reactor.listenTCP(11375, site)
    reactor.run()

