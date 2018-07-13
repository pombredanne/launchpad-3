# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for the XML-RPC authentication server."""

__metaclass__ = type
__all__ = [
    'IAuthServer',
    'IAuthServerApplication',
    ]


from zope.interface import Interface

from lp.services.webapp.interfaces import ILaunchpadApplication


class IAuthServer(Interface):
    """A storage for details about users."""

    def getUserAndSSHKeys(name):
        """Get details about a person, including their SSH keys.

        :param name: The username to look up.
        :returns: A dictionary {id: person-id, username: person-name, keys:
            [(key-type, key-text)]}, or NoSuchPersonWithName if there is no
            person with the given name.
        """

    def verifyMacaroon(macaroon_raw, context):
        """Verify that `macaroon_raw` grants access to `context`.

        :param macaroon_raw: A serialised macaroon.
        :param context: The context to check.  Note that this is passed over
            XML-RPC, so it should be plain data (e.g. an ID) rather than a
            database object.
        :return: True if the macaroon grants access to `context`, otherwise
            an `Unauthorized` fault.
        """


class IAuthServerApplication(ILaunchpadApplication):
    """Launchpad legacy AuthServer application root."""
