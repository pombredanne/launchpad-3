# Copyright 2007 Canonical Ltd., all rights reserved.

"""Legacy Auth-Server XML-RPC API ."""

__metaclass__ = type

__all__ = [
    'AuthServerAPIView',
    ]

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import IAuthServer, IPersonSet
from canonical.launchpad.webapp import LaunchpadXMLRPCView
from canonical.launchpad.xmlrpc import faults


class AuthServerAPIView(LaunchpadXMLRPCView):
    """The XMLRPC API provided by the old AuthServer and used by the wikis."""
    implements(IAuthServer)

    def getUser(self, login_id):
        """See `IAuthServer`."""
        return self._getPersonDict(self._getPerson(login_id))

    def getSSHKeys(self, login_id):
        """See `IAuthServer`."""
        person = self._getPerson(login_id)
        if person is None:
            return []
        return [(key.keytype.title, key.keytext) for key in person.sshkeys]

    def _getPerson(self, login_id):
        """Look up a person by login_id.

        The login_id will be first tried as an email address, then as a
        numeric ID, then finally as a nickname.

        :returns: a `Person` or None if not found.
        """
        try:
            if not isinstance(login_id, unicode):
                # Refuse to guess encoding, so we decode as 'ascii'
                login_id = str(login_id).decode('ascii')
        except UnicodeDecodeError:
            return None

        person_set = getUtility(IPersonSet)

        # Try as email first.
        person = person_set.getByEmail(login_id)

        # If email didn't work, try as id.
        if person is None:
            try:
                person_id = int(login_id)
            except ValueError:
                pass
            else:
                person = person_set.get(person_id)

        # If id didn't work, try as nick-name.
        if person is None:
            person = person_set.getByName(login_id)

        return person

    def _getPersonDict(self, person):
        """Return a dict representing 'person' to be returned over XML-RPC.

        See `IUserDetailsStorage`.
        """
        if person is None:
            return {}

        return {
            'id': person.id,
            'name': person.name,
        }

    def getUserAndSSHKeys(self, name):
        """See `IAuthServer.getUserAndSSHKeys`."""
        person = getUtility(IPersonSet).getByName(name)
        if person is None:
            return faults.NoSuchPersonWithName(name)
        return {
            'id': person.id,
            'name': person.name,
            'keys': [(key.keytype.title, key.keytext)
                     for key in person.sshkeys],
            }

