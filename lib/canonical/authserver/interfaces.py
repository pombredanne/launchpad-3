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
    'IUserDetailsStorageV2',
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


class IUserDetailsStorageV2(Interface):
    """A storage for details about users.

    Published at `http://$authserver_host/v2`.

    Many of the methods defined here return *user dicts*.  A user dict is a
    dictionary containing:
        :id:             person id (integer, doesn't change ever)
        :displayname:    full name, for display
        :emailaddresses: list of email addresses, preferred email first, the
                         rest alphabetically sorted.
        :teams:          a list of team dicts for each team the user is a member
                         of (including the user themself).

    A *team dict* contains:
        :id:            team id (integer, doesn't change ever)
        :name:          nickname for the team
        :displayname:   full name of the team, for display

    Differences from version 1 (IUserDetailsStorage):
        - no salts in user dicts
        - no SSHA digests, just cleartext passwords
        - teams in user dicts.
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

    def getSSHKeys(archiveName):
        """Retrieve SSH public keys for a given push mirror archive

        :param archive: an archive name.
        :returns: list of 2-tuples of (key type, key text).  This list will be
            empty if the user has no keys or does not exist.
        """
