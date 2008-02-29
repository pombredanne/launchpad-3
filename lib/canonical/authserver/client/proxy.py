# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Proxies that connect to XML-RPC servers."""

__metaclass__ = type
__all__ = [
    'get_blocking_proxy',
    'get_twisted_proxy',
    'InMemoryBlockingProxy',
    'InMemoryTwistedProxy',
    ]

import xmlrpclib

from canonical.authserver.database import DatabaseUserDetailsStorageV2
from canonical.authserver.interfaces import (
    IHostedBranchStorage, IUserDetailsStorageV2)
from canonical.authserver.xmlrpc import UserDetailsResourceV2

from twisted.internet import defer
from twisted.web.xmlrpc import Proxy

from zope.interface.interface import Method


def get_twisted_proxy(url):
    """Return a Twisted XML-RPC proxy for `url`.

    :param url: The URL of an XML-RPC service. Sometimes this can be a
        'fake:///' URL. See the module docstring for details.
    :return: An object that behaves like a `twisted.web.xmlrpc.Proxy`.
    """
    if url == 'fake:///user-details-2':
        storage = DatabaseUserDetailsStorageV2(None)
        xmlrpc = UserDetailsResourceV2(storage)
        return InMemoryTwistedProxy(xmlrpc)
    return Proxy(url)


def get_blocking_proxy(url):
    """Return an XML-RPC proxy for `url`.

    :param url: The URL of an XML-RPC service. Sometimes this can be a
        'fake:///' URL. See the module docstring for details.
    :return: An object that behaves like an `xmlrpclib.ServerProxy`.
    """
    if url == 'fake:///user-details-2':
        method_names = (
            list(get_method_names_in_interface(IUserDetailsStorageV2))
            + list(get_method_names_in_interface(IHostedBranchStorage)))
        storage = DatabaseUserDetailsStorageV2(None)
        return InMemoryBlockingProxy(storage, method_names)
    return xmlrpclib.ServerProxy(url)


def get_method_names_in_interface(interface):
    """Generate a sequence of the method names defined on `interface`.

    :param interface: A Zope `Interface`.
    :return: A generator that yields the names of the methods on the
        interface. No ordering is defined.
    """
    for attribute_name in interface:
        if isinstance(interface[attribute_name], Method):
            yield attribute_name


class InMemoryBlockingProxy:
    """ServerProxy work-a-like that calls methods directly."""

    def __init__(self, xmlrpc_object, method_names):
        self._xmlrpc_object = xmlrpc_object
        self._method_names = method_names

    def _faultMaker(self, code, string):
        """Return a callable that raises a Fault when called."""
        def raise_fault(*args):
            raise xmlrpclib.Fault(code, string)
        return raise_fault

    def _checkMarshalling(self, function):
        """Decorate function to check it for marshallability.

        Checks the arguments and return values for whether or not they can
        be passed via XML-RPC. Mostly, this means checking for None.
        """
        def call_method(*args):
            xmlrpclib.dumps(args)
            result = function(*args)
            try:
                xmlrpclib.dumps((result,))
            except TypeError:
                raise xmlrpclib.Fault(
                    8002, "can't serialize output (%r)" % (result,))
            return result
        return call_method

    def __getattr__(self, name):
        if name not in self._method_names:
            return self._faultMaker(8001, 'function %s not found' % (name,))
        return self._checkMarshalling(getattr(self._xmlrpc_object, name))


class InMemoryTwistedProxy:
    """Twisted `Proxy` work-a-like that calls methods directly."""

    def __init__(self, xmlrpc_object):
        self.xmlrpc_object = xmlrpc_object

    def _checkArgumentsMarshallable(self, args):
        """Raise a `TypeError` if `args` are not marhallable."""
        xmlrpclib.dumps(args)

    def _checkReturnValueMarshallable(self, result):
        """Raise a fault if `result` is not marshallable.

        Mostly, this is used to check if `result` is not `None`. This method
        can be used as a Twisted callback.

        :param result: The return value to check.
        :return: `result`, unmodified.
        """
        try:
            xmlrpclib.dumps((result,))
        except TypeError:
            raise xmlrpclib.Fault(
                8002, "can't serialize output (%r)" % (result,))
        return result

    def callRemote(self, method_name, *args):
        """Call `method_name` on the XML-RPC resource.

        :param method_name: The name of a method to call. `callRemote` will
            call the method called 'xmlrpc_' + method_name on the underlying
            resource.
        :param args: The arguments to pass to the method.
        :return: A `Deferred` that fires with the return value of the
            underlying method. If the method raises an error, or a fault, or
            there is an XML-RPC protocol violation, the `Deferred` will
            errback.
        """
        self._checkArgumentsMarshallable(args)
        try:
            method = getattr(self.xmlrpc_object, 'xmlrpc_%s' % (method_name,))
        except AttributeError:
            return defer.fail(xmlrpclib.Fault(
                8001, "Method %r does not exist" % (method_name,)))
        deferred = defer.maybeDeferred(method, *args)
        return deferred.addCallback(self._checkReturnValueMarshallable)
