# Copyright 2008, 2009 Canonical Ltd.  All rights reserved.

"""Interface for the XML-RPC authentication server."""

__metaclass__ = type
__all__ = [
    'IAuthServer'
    ]


from zope.interface import Interface


class IAuthServer(Interface):
    """A storage for details about users."""

    def getUserAndSSHKeys(name):
        """Get details about a person, including their SSH keys.

        :param name: The username to look up.
        :returns: A dictionary {id: person-id, username: person-name, keys:
            [(key-type, key-text)]}, or NoSuchPersonWithName if there is no
            person with the given name.
        """
