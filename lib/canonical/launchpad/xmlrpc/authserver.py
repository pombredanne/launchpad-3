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
from canonical.launchpad.webapp.authentication import SSHADigestEncryptor


class AuthServerAPIView(LaunchpadXMLRPCView):
    """The XMLRPC API provided by the old AuthServer and used by the wikis."""
    implements(IAuthServer)

    def getUser(self, loginID):
        """See `IAuthServer`."""
        return self._getPersonDict(self._getPerson(loginID))

    def authUser(self, loginID, password):
        """See `IAuthServer`."""

        person = self._getPerson(loginID)
        if person is None:
            return {}

        if not SSHADigestEncryptor().validate(password, person.password):
            # Wrong password
            return {}

        return self._getPersonDict(person)

    def getSSHKeys(self, loginID):
        """See `IAuthServer`."""
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

        Returns a list of team dicts (see IAuthServer).
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

        return {
            'id': person.id,
            'displayname': person.displayname,
            'emailaddresses': self._getEmailAddresses(person),
            'name': person.name,
            'teams': self._getTeams(person),
        }

    def _getEmailAddresses(self, person):
        """Get the email addresses for a person"""
        emails = [person.preferredemail] + list(person.validatedemails)
        # Bypass zope's security because IEmailAddress.email is not public.
        from zope.security.proxy import removeSecurityProxy
        return [removeSecurityProxy(email).email for email in emails]
