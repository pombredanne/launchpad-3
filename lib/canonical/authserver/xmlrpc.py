# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

from twisted.web import xmlrpc

from canonical.config import config


class LoggingResource(xmlrpc.XMLRPC):
    """Includes the original stack trace in unexpected Faults."""

    def _ebRender(self, failure):
        fault = xmlrpc.XMLRPC._ebRender(self, failure)
        if (config.authserver.include_traceback_in_fault
            and fault.faultCode == self.FAILURE):
            return xmlrpc.Fault(
                self.FAILURE,
                'Original traceback:\n' + failure.getTraceback())
        else:
            return fault


class UserDetailsResource(LoggingResource):

    def __init__(self, storage, debug=False):
        LoggingResource.__init__(self)
        self.storage = storage
        self.debug = debug

    def xmlrpc_getUser(self, loginID):
        """Get a user

        :returns: user dict if loginID exists, otherwise empty dict
        """
        if self.debug:
            print 'getUser(%r)' % (loginID,)
        return self.storage.getUser(loginID)

    def xmlrpc_authUser(self, loginID, sshaDigestedPassword):
        """Authenticate a user

        :returns: user dict if authenticated, otherwise empty dict
        """
        if self.debug:
            print 'authUser(%r, %r)' % (loginID, sshaDigestedPassword)
        return self.storage.authUser(loginID,
                                     sshaDigestedPassword.decode('base64'))


class UserDetailsResourceV2(LoggingResource):
    """A new (and simpler) version of the user details XML-RPC API."""

    def __init__(self, storage, debug=False):
        LoggingResource.__init__(self)
        self.storage = storage
        self.debug = debug

    def xmlrpc_getUser(self, loginID):
        """Get a user

        :returns: user dict if loginID exists, otherwise empty dict
        """
        if self.debug:
            print 'getUser(%r)' % (loginID,)
        return self.storage.getUser(loginID)

    def xmlrpc_authUser(self, loginID, password):
        """Authenticate a user

        :returns: user dict if authenticated, otherwise empty dict
        """
        if self.debug:
            print 'authUser(%r, %r)' % (loginID, password)
        return self.storage.authUser(loginID, password)
