# Copyright 2004 Canonical Ltd.  All rights reserved.

from zope.interface import Interface

class IUserDetailsStorage(Interface):
    
    def getUser(loginID):
        """Get a user

        :param loginID: A login ID (i.e. email address) or person ID from a user
            dict.
        
        :returns: user dict if loginID exists, otherwise empty dict
        """

    def authUser(loginID, sshaDigestedPassword):
        """Authenticate a user
        
        :returns: user dict if authenticated, otherwise empty dict
        """

    def createUser(loginID, sshaDigestedPassword, displayName, emailAddresses):
        """Create a user
        
        :returns: user dict, or TBD if there is an error such as a database
            constraint being violated.
        """


