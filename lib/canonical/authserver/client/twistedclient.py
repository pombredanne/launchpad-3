# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Twisted client code."""

__metaclass__ = type
__all__ = [
    'get_blocking_proxy', 'get_twisted_proxy', 'InMemoryTwistedProxy',
    'TwistedAuthServer']

import xmlrpclib

from canonical.authserver.database import DatabaseUserDetailsStorageV2
from canonical.authserver.interfaces import (
    IHostedBranchStorage, IUserDetailsStorageV2)
from canonical.authserver.xmlrpc import UserDetailsResourceV2

from twisted.internet import defer
from twisted.web.xmlrpc import Proxy

from zope.interface.interface import Method


def _make_connection_pool():
    """Construct a ConnectionPool from the database settings in the
    Launchpad config.
    """
    from canonical.config import config
    from twisted.enterprise.adbapi import ConnectionPool
    if config.dbhost is None:
        dbhost = ''
    else:
        dbhost = 'host=' + config.dbhost
    ConnectionPool.min = ConnectionPool.max = 1
    dbpool = ConnectionPool(
        'psycopg', 'dbname=%s %s user=%s' % (
            config.dbname, dbhost, config.authserver.dbuser),
        cp_reconnect=True)
    return dbpool


def get_twisted_proxy(url):
    if url == 'fake:///user-details-2':
        return InMemoryTwistedProxy(
            UserDetailsResourceV2(
                DatabaseUserDetailsStorageV2(_make_connection_pool())))
    return Proxy(url)


def get_blocking_proxy(url):
    return xmlrpclib.ServerProxy(url)


def get_method_names_in_interface(interface):
    for attribute_name in interface:
        if isinstance(interface[attribute_name], Method):
            yield attribute_name


class InMemoryTwistedProxy:

    debug = False

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
        if self.debug:
            def debug(value, message):
                print '%s%r -> %r (%s)' % (method_name, args, value, message)
                return value
            deferred.addCallback(debug, 'SUCCESS')
            deferred.addErrback(debug, 'FAILURE')
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

