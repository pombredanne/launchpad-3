# Copyright 2004 Canonical Ltd.  All rights reserved.

from twisted.web import xmlrpc

class UserDetailsResource(xmlrpc.XMLRPC):
    
    def __init__(self, storage):
        self.storage = storage

    def xmlrpc_getUser(self, loginID):
        """Get a user
        
        :returns: user dict if loginID exists, otherwise empty dict
        """
        return self.storage.getUser(loginID)

    def xmlrpc_authUser(self, loginID, sshaDigestedPassword):
        """Authenticate a user
        
        :returns: user dict if authenticated, otherwise empty dict
        """
        return self.storage.authUser(loginID,
                                     sshaDigestedPassword.decode('hex'))

    def xmlrpc_createUser(self, loginID, sshaDigestedPassword, displayName,
                          emailAddresses):
        """Create a user
        
        :returns: user dict, or TBD if there is an error such as a database
            constraint being violated.
        """
        return self.storage.createUser(loginID,
                                       sshaDigestedPassword.decode('hex'), 
                                       displayName, emailAddresses)

