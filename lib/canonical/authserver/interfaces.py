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

        :param loginID: A login ID (an email address, nickname, or numeric
            person ID from a user dict).
        
        :returns: user dict if loginID exists, otherwise empty dict
        """

    def authUser(loginID, sshaDigestedPassword):
        """Authenticate a user
        
        :param loginID: A login ID, same as for getUser.
        :returns: user dict if authenticated, otherwise empty dict
        """

    def createUser(loginID, sshaDigestedPassword, displayname, emailAddresses):
        """Create a user
        
        :param loginID: A login ID, same as for getUser.
        :param sshaDigestedPassword: SSHA digest of the password.
        :param displayname: full name, for display.
        :param emailAddresses: list of email addresses.  The loginID may appear
            in this list as well; it doesn't matter either way.
            
        :returns: user dict, or TBD if there is an error such as a database
            constraint being violated.
        """

    def changePassword(loginID, sshaDigestedPassword, newSshaDigestedPassword):
        """Change a password

        :param loginID: A login ID, same as for getUser.
        :param sshaDigestedPassword: SSHA digest of the current password.
        :param newSshaDigestedPassword: SSHA digest of the new password.
        """

    def getSSHKeys(loginID):
        """Retrieve SSH public keys for a given user
        
        :param loginID: a login ID.
        :returns: list of 2-tuples of (key type, key text).  This list will be
            empty if the user has no keys or does not exist.
        """


