# Copyright 2004 Canonical Ltd.  All rights reserved.

from zope.interface import Interface

class IUserDetailsStorage(Interface):
    """A storage for details about users.

    Many of the methods defined here return *user dicts*.  A user dict is a
    dictionary containing:
        :id:             person id (integer, doesn't change ever)
        :displayname:    full name, for display
        :emailaddresses: list of email addresses
        :salt:           salt of a SSHA digest, base64-encoded.
    """

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

    def createUser(loginID, sshaDigestedPassword, displayname, emailAddresses):
        """Create a user
        
        :returns: user dict, or TBD if there is an error such as a database
            constraint being violated.
        """

    def changePassword(loginID, sshaDigestedPassword, newSshaDigestedPassword):
        """Change a password

        :param sshaDigestedPassword: SSHA digest of the current password.
        :param newSshaDigestedPassword: SSHA digest of the new password.
        """


