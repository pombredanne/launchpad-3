# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Servers used in the authserver tests."""

__metaclass__ = type
__all__ = ['make_xmlrpc_resource', 'TwistedServer']

import xmlrpclib

from bzrlib.transport import Server
from canonical.authserver.client import (
    InMemoryBlockingProxy, InMemoryTwistedProxy)

from twisted.application import strports
from twisted.web import server, resource, xmlrpc


def make_xmlrpc_resource(xmlrpc_object, methods_to_publish):
    """Turn a regular object into a Twisted XML-RPC resource.

    Also, cheats a bit and stores the parameters on the returned resource
    as 'original' and 'methods_to_publish'.
    """
    xmlrpc_resource = xmlrpc.XMLRPC()
    for method_name in methods_to_publish:
        method = getattr(xmlrpc_object, method_name)
        setattr(xmlrpc_resource, 'xmlrpc_%s' % method_name, method)
    xmlrpc_resource.original = xmlrpc_object
    xmlrpc_resource.published_methods = list(methods_to_publish)
    return xmlrpc_resource


class InMemoryServer(Server):
    """An in-memory server that serves an XML-RPC resource."""

    def __init__(self, xmlrpc_resource):
        super(InMemoryServer, self).__init__()
        self.xmlrpc_resource = xmlrpc_resource

    def setUp(self):
        pass

    def get_url(self):
        return None

    def tearDown(self):
        pass

    def getBlockingProxy(self):
        xmlrpc_object = self.xmlrpc_resource.original
        published_methods = self.xmlrpc_resource.published_methods
        return InMemoryBlockingProxy(xmlrpc_object, published_methods)

    def getTwistedProxy(self):
        return InMemoryTwistedProxy(self.xmlrpc_resource)


class TwistedServer(Server):
    """A test HTTP server that serves an XML-RPC resource.

    Use `getBlockingProxy` to get a real proxy (i.e. an
    `xmlrpclib.ServerProxy`) that points to the resource.
    """

    def __init__(self, xmlrpc_resource):
        super(TwistedServer, self).__init__()
        self.xmlrpc_resource = xmlrpc_resource
        self._service = None

    def setUp(self):
        root = resource.Resource()
        root.putChild('xmlrpc', self.xmlrpc_resource)
        site = server.Site(root)
        self._service = strports.service('tcp:0', site)
        self._service.startService()

    def get_url(self):
        return 'http://localhost:%s/xmlrpc' % (
            self._service._port.getHost().port)

    def tearDown(self):
        self._service.stopService()

    def getBlockingProxy(self):
        return xmlrpclib.ServerProxy(self.get_url())

    def getTwistedProxy(self):
        return xmlrpc.Proxy(self.get_url())
