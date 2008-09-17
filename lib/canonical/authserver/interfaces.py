# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0213
"""XML-RPC interfaces for the Authserver.

The interfaces here are purely for documentation purposes.  They describe the
XML-RPC methods published by this server.

Some terminology:
    :id: a numeric ID for a person.
    :loginID: any one of an email address, a nickname, or a numeric id for a
        person.
    :user dict: a dictionary of information about a person.  Refer to the
        interface docstrings for their contents.
"""

__all__ = [
    'IUserDetailsStorage',
    ]


from zope.interface import Interface


class IUserDetailsStorage(Interface):
    """A storage for details about users.

    Published at `http://$authserver_host/`. (i.e. the root)

    Many of the methods defined here return *user dicts*.  A user dict is a
    dictionary containing:
        :id:             person id (integer, doesn't change ever)
        :displayname:    full name, for display
        :emailaddresses: list of email addresses, preferred email first, the
                         rest alphabetically sorted.
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
