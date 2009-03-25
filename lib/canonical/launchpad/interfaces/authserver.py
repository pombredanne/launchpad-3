# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interface for the XML-RPC authentication server."""

__metaclass__ = type
__all__ = [
    'IAuthServer'
    ]


from zope.interface import Interface


class IAuthServer(Interface):
    """A storage for details about users.

    Many of the methods defined here return *user dicts*.  A user dict is a
    dictionary containing:
        :id:             person id (integer, doesn't change ever)
        :displayname:    full name, for display
        :emailaddresses: list of email addresses, preferred email first, the
                         rest alphabetically sorted.
        :teams:          a list of team dicts for each team the user is a
                         member of (including the user themself).

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

    def getSSHKeys(archiveName):
        """Retrieve SSH public keys for a given push mirror archive

        :param archive: an archive name.
        :returns: list of 2-tuples of (key type, key text).  This list will be
            empty if the user has no keys or does not exist.
        """
