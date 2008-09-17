# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DatabaseUserDetailsStorage',
    'DatabaseUserDetailsStorageV2',
    ]

import pytz

import transaction

from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces import IPersonSet
from canonical.launchpad.interfaces.authserver import IAuthServer
from canonical.launchpad.ftests import login, logout, ANONYMOUS
from canonical.launchpad.webapp.authentication import SSHADigestEncryptor
from canonical.database.sqlbase import (
    clear_current_connection_cache, reset_store)

from canonical.authserver.interfaces import IUserDetailsStorage


from twisted.internet.threads import deferToThread
from twisted.python.util import mergeFunctionMetadata


UTC = pytz.timezone('UTC')


def read_only_transaction(function):
    """Wrap 'function' in a transaction and Zope session."""
    @reset_store
    def transacted(*args, **kwargs):
        transaction.begin()
        clear_current_connection_cache()
        login(ANONYMOUS)
        try:
            return function(*args, **kwargs)
        finally:
            logout()
            transaction.abort()
    return mergeFunctionMetadata(function, transacted)


class UserDetailsStorageMixin:
    """Functions that are shared between DatabaseUserDetailsStorage and
    DatabaseUserDetailsStorageV2"""

    def _getEmailAddresses(self, person):
        """Get the email addresses for a person"""
        emails = [person.preferredemail] + list(person.validatedemails)
        # Bypass zope's security because IEmailAddress.email is not public.
        return [removeSecurityProxy(email).email for email in emails]

    def getSSHKeys(self, loginID):
        """See `IUserDetailsStorage`."""
        return deferToThread(self._getSSHKeysInteraction, loginID)

    @read_only_transaction
    def _getSSHKeysInteraction(self, loginID):
        """The synchronous implementation of `getSSHKeys`.

        See `IUserDetailsStorage`.
        """
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

    def _getPersonDict(self, person):
        """Return a dict representing 'person' to be returned over XML-RPC.

        See `IUserDetailsStorage`.
        """
        if person is None:
            return {}

        if person.password:
            salt = saltFromDigest(person.password)
        else:
            salt = ''

        return {
            'id': person.id,
            'displayname': person.displayname,
            'emailaddresses': self._getEmailAddresses(person),
            'salt': salt,
        }

    def getUser(self, loginID):
        """See `IUserDetailsStorage`."""
        return deferToThread(self._getUserInteraction, loginID)

    @read_only_transaction
    def _getUserInteraction(self, loginID):
        """The interaction for getUser."""
        return self._getPersonDict(self._getPerson(loginID))


class DatabaseUserDetailsStorage(UserDetailsStorageMixin):
    """Launchpad-database backed implementation of IUserDetailsStorage"""
    # Note that loginID always refers to any name you can login with (an email
    # address, or a nickname, or a numeric ID), whereas personID always refers
    # to the numeric ID, which is the value found in Person.id in the
    # database.
    implements(IUserDetailsStorage)

    def __init__(self, connectionPool):
        """Constructor.

        :param connectionPool: A twisted.enterprise.adbapi.ConnectionPool
        """
        self.connectionPool = connectionPool
        self.encryptor = SSHADigestEncryptor()

    def authUser(self, loginID, sshaDigestedPassword):
        """See `IUserDetailsStorage`."""
        return deferToThread(
            self._authUserInteraction, loginID,
            sshaDigestedPassword.encode('base64'))

    @read_only_transaction
    def _authUserInteraction(self, loginID, sshaDigestedPassword):
        """Synchronous implementation of `authUser`.

        See `IUserDetailsStorage`.
        """
        person = self._getPerson(loginID)

        if person is None:
            return {}

        if person.password is None:
            # The user has no password, which means they can't login.
            return {}

        if person.password.rstrip() != sshaDigestedPassword.rstrip():
            # Wrong password
            return {}

        return self._getPersonDict(person)


def saltFromDigest(digest):
    """Extract the salt from a SSHA digest.

    :param digest: base64-encoded digest
    """
    if isinstance(digest, unicode):
        # Make sure digest is a str, because unicode objects don't have a
        # decode method in python 2.3. Base64 should always be representable
        # in ASCII.
        digest = digest.encode('ascii')
    return digest.decode('base64')[20:].encode('base64')


class DatabaseUserDetailsStorageV2(UserDetailsStorageMixin):
    """Launchpad-database backed implementation of IAuthServer"""
    implements(IAuthServer)

    def __init__(self, connectionPool):
        """Constructor.

        :param connectionPool: A twisted.enterprise.adbapi.ConnectionPool
        """
        self.connectionPool = connectionPool
        self.encryptor = SSHADigestEncryptor()

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
        person_dict = UserDetailsStorageMixin._getPersonDict(self, person)
        if person_dict == {}:
            return {}
        del person_dict['salt']
        person_dict['name'] = person.name
        person_dict['teams'] = self._getTeams(person)
        return person_dict

    def authUser(self, loginID, password):
        """See `IAuthServer`."""
        return deferToThread(self._authUserInteraction, loginID, password)

    @read_only_transaction
    def _authUserInteraction(self, loginID, password):
        """Synchronous implementation of `authUser`.

        See `IAuthServer`.
        """
        person = self._getPerson(loginID)
        if person is None:
            return {}

        if not self.encryptor.validate(password, person.password):
            # Wrong password
            return {}

        return self._getPersonDict(person)
