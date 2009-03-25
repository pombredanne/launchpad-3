# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interface for the XML-RPC authentication server."""

__metaclass__ = type
__all__ = [
    'IAuthServer'
    ]


from zope.interface import Interface


class IAuthServer(Interface):
    """A storage for details about users.

    A user dict is a dictionary containing:

        :id:   person id (integer, doesn't change ever)
        :name: person nickname
    """

    def getUser(loginID):
        """Get a user

        :param loginID: A login ID (an email address, nickname, or numeric
            person ID from a user dict).

        :returns: user dict if loginID exists, otherwise empty dict
        """

    def getSSHKeys(loginID):
        """Retrieve SSH public keys for a given push mirror archive

        :param loginID: A login ID (an email address, nickname, or numeric
            person ID from a user dict).
        :returns: list of 2-tuples of (key type, key text).  This list will be
            empty if the user has no keys or does not exist.
        """
