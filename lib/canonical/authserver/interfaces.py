# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Interfaces for the Authserver.

Some terminology:
    :id: a numeric ID for a person.
    :loginID: any one of an email address, a nickname, or a numeric id for a
        person.
    :user dict: a dictionary of information about a person.  Refer to the
        interface docstrings for their contents.
"""

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

    def createUser(preferredEmail, sshaDigestedPassword, displayname,
            emailAddresses):
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

    def getSSHKeys(archiveName):
        """Retrieve SSH public keys for a given push mirror archive
        
        :param archive: an archive name.
        :returns: list of 2-tuples of (key type, key text).  This list will be
            empty if the user has no keys or does not exist.
        """


class IUserDetailsStorageV2(Interface):
    """A storage for details about users.

    Many of the methods defined here return *user dicts*.  A user dict is a
    dictionary containing:
        :id:             person id (integer, doesn't change ever)
        :displayname:    full name, for display
        :emailaddresses: list of email addresses

    Differences from version 1 (IUserDetailsStorage):
        - no salts in user dicts
        - no SSHA digests, just cleartext passwords
    """

    def getUser(loginID):
        """Get a user

        :param loginID: A login ID (an email address, nickname, or numeric
            person ID from a user dict).
        
        :returns: user dict if loginID exists, otherwise empty dict
        """

    def authUser(loginID, password):
        """Authenticate a user
        
        :param loginID: A login ID, same as for getUser.
        :param password: A password, in clear text.
        :returns: user dict if authenticated, otherwise empty dict
        """

    def createUser(preferredEmail, password, displayname, emailAddresses):
        """Create a user
        
        :param loginID: A login ID, same as for getUser.
        :param password: A password, in clear text.
        :param displayname: full name, for display.
        :param emailAddresses: list of email addresses.  The loginID may appear
            in this list as well; it doesn't matter either way.
            
        :returns: user dict, or TBD if there is an error such as a database
            constraint being violated.
        """

    def changePassword(loginID, oldPassword, newPassword):
        """Change a password

        :param loginID: A login ID, same as for getUser.
        :param sshaDigestedPassword: The current password.
        :param newSshaDigestedPassword: The password to change to.
        """

    def getSSHKeys(archiveName):
        """Retrieve SSH public keys for a given push mirror archive
        
        :param archive: an archive name.
        :returns: list of 2-tuples of (key type, key text).  This list will be
            empty if the user has no keys or does not exist.
        """


