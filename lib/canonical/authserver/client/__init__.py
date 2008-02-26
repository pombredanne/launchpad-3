# Copyright 2004 Canonical Ltd.  All rights reserved.

"""Client APIs for the authserver.

While the authserver is just XML-RPC, there is still some boilerplate that can
be reduced by putting common code in this package.
"""

# TODO:
#   - refactor authserver client code in shipit to live here
#   - Twisted XML-RPC client stuff for supermirror SFTP server.

__all__ = [
    'InMemoryBlockingProxy',
    'InMemoryTwistedProxy']

import xmlrpclib

from canonical.authserver.client.twistedclient import InMemoryTwistedProxy


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
