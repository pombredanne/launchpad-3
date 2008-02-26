# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Twisted client code."""

__metaclass__ = type
__all__ = ['InMemoryTwistedProxy', 'TwistedAuthServer']

import xmlrpclib

from twisted.internet import defer
from twisted.web.xmlrpc import Proxy


def get_twisted_proxy(url):
    return Proxy(url)


def get_blocking_proxy(url):
    return xmlrpclib.ServerProxy(url)


class InMemoryTwistedProxy:

    def __init__(self, xmlrpc_object):
        self.xmlrpc_object = xmlrpc_object

    def _checkArgumentsMarshallable(self, args):
        """Raise a `TypeError` if `args` are not marhallable."""
        xmlrpclib.dumps(args)

    def _checkReturnValueMarshallable(self, result):
        try:
            xmlrpclib.dumps((result,))
        except TypeError:
            raise xmlrpclib.Fault(
                8002, "can't serialize output (%r)" % (result,))
        return result

    def callRemote(self, method_name, *args):
        self._checkArgumentsMarshallable(args)
        try:
            method = getattr(self.xmlrpc_object, 'xmlrpc_%s' % (method_name,))
        except AttributeError:
            return defer.fail(xmlrpclib.Fault(
                8001, "Method %r does not exist" % (method_name,)))
        deferred = defer.maybeDeferred(method, *args)
        return deferred.addCallback(self._checkReturnValueMarshallable)


class TwistedAuthServer:
    """Twisted client for the authserver.

    This almost implements canonical.authserver.interfaces.IUserDetailsStorage,
    except everything returns Deferreds.  Refer to IUserDetailsStorage for docs.
    """

    def __init__(self, url):
        self.proxy = get_twisted_proxy(url)

    def getUser(self, loginID):
        return self.proxy.callRemote('getUser', loginID)

    def authUser(self, loginID, sshaDigestedPassword):
        return self.proxy.callRemote(
            'authUser', loginID, sshaDigestedPassword)

    def changePassword(self, loginID, sshaDigestedPassword,
                       newSshaDigestedPassword):
        return self.proxy.callRemote('changePassword', loginID,
                                     sshaDigestedPassword,
                                     newSshaDigestedPassword)

    def getSSHKeys(self, archiveName):
        return self.proxy.callRemote('getSSHKeys', archiveName)

    def getBranchesForUser(self, personID):
        return self.proxy.callRemote('getBranchesForUser', personID)

    def fetchProductID(self, productName):
        d = self.proxy.callRemote('fetchProductID', productName)
        d.addCallback(self._cb_fetchProductID)
        return d

    def _cb_fetchProductID(self, productID):
        if productID == '':
            productID = None
        return productID

    def createBranch(self, loginID, personName, productName, branchName):
        return self.proxy.callRemote(
            'createBranch', loginID, personName, productName, branchName)

    def requestMirror(self, loginID, branchID):
        return self.proxy.callRemote('requestMirror', loginID, branchID)

