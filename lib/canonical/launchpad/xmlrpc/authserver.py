# Copyright 2007 Canonical Ltd., all rights reserved.

"""Legacy Auth-Server XML-RPC API ."""

__metaclass__ = type

__all__ = [
    'AuthServerAPIView',
    ]

from zope.component import getUtility
from zope.interface import implements

from canonical.authserver.interfaces import IUserDetailsStorageV2
from canonical.launchpad.interfaces import IPersonSet
from canonical.launchpad.webapp import LaunchpadXMLRPCView
from canonical.launchpad.webapp.authentication import SSHADigestEncryptor


class AuthServerAPIView(LaunchpadXMLRPCView):
    """The XMLRPC API provided by the old AuthServer and used by the wikis."""
    implements(IUserDetailsStorageV2)

    def getUser(self, loginID):
        """See `IUserDetailsStorageV2`."""
        return self._getPersonDict(self._getPerson(loginID))

    def authUser(self, loginID, password):
        """See `IUserDetailsStorageV2`."""

        person = self._getPerson(loginID)
        if person is None:
            return {}

        if not SSHADigestEncryptor().validate(password, person.password):
            # Wrong password
            return {}

        return self._getPersonDict(person)

    def getSSHKeys(self, loginID):
        """See `IUserDetailsStorageV2`."""
        person = self._getPerson(loginID)
        if person is None:
            return []
        return [(key.keytype.title, key.keytext) for key in person.sshkeys]

    def _getPerson(self, loginID):
        """Look up a person by loginID.

        The loginID will be first tried as an email address, then as a numeric
        ID, then finally as a nickname.

        :returns: a `Person` or None if not found.
        """
        try:
            if not isinstance(loginID, unicode):
                # Refuse to guess encoding, so we decode as 'ascii'
                loginID = str(loginID).decode('ascii')
        except UnicodeDecodeError:
            return None

        person_set = getUtility(IPersonSet)

        # Try as email first.
        person = person_set.getByEmail(loginID)

        # If email didn't work, try as id.
        if person is None:
            try:
                person_id = int(loginID)
            except ValueError:
                pass
            else:
                person = person_set.get(person_id)

        # If id didn't work, try as nick-name.
        if person is None:
            person = person_set.getByName(loginID)

        return person

    def _getTeams(self, person):
        """Get list of teams a person is in.

        Returns a list of team dicts (see IUserDetailsStorageV2).
        """
        teams = [
            dict(id=person.id, name=person.name,
                 displayname=person.displayname)]

        return teams + [
            dict(id=team.id, name=team.name, displayname=team.displayname)
            for team in person.teams_participated_in]

    def _getPersonDict(self, person):
        """Return a dict representing 'person' to be returned over XML-RPC.

        See `IUserDetailsStorage`.
        """
        if person is None:
            return {}

        wikiname = getattr(person.ubuntuwiki, 'wikiname', '')
        return {
            'id': person.id,
            'displayname': person.displayname,
            'emailaddresses': self._getEmailAddresses(person),
            'wikiname': wikiname,
            'name': person.name,
            'teams': self._getTeams(person),
        }

    def _getEmailAddresses(self, person):
        """Get the email addresses for a person"""
        emails = [person.preferredemail] + list(person.validatedemails)
        return (
            [person.preferredemail.email] +
            [email.email for email in person.validatedemails])

