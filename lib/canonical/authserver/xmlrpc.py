# Copyright 2004 Canonical Ltd.  All rights reserved.

from twisted.web import xmlrpc

class UserDetailsResource(xmlrpc.XMLRPC):

    def __init__(self, storage, debug=False):
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
                                     sshaDigestedPassword.decode('hex'))

    def xmlrpc_createUser(self, loginID, sshaDigestedPassword, displayName,
                          emailAddresses):
        """Create a user
        
        :returns: user dict, or TBD if there is an error such as a database
            constraint being violated.
        """
        if self.debug:
            print ("createUser(%r, %r, %r, %r)"
                   % (loginID, sshaDigestedPassword, displayName,
                      emailAddresses))
        return self.storage.createUser(loginID,
                                       sshaDigestedPassword.decode('hex'), 
                                       displayName, emailAddresses)

