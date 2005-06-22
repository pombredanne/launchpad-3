# Copyright 2004 Canonical Ltd.  All rights reserved.

import psycopg

from zope.interface import implements

# XXX: canonical.authserver.adbapi is backport of a new version of adbapi; it
#      was supposed to fix the database reconnection issues, but didn't.
#      Probably it should be removed, in favour of canonical.database.reconnect.
#        - Andrew Bennetts, 2005-01-25
from twisted.enterprise import adbapi
#from canonical.authserver import adbapi

from canonical.launchpad.webapp.authentication import SSHADigestEncryptor
from canonical.database.sqlbase import quote
from canonical.lp import dbschema

from canonical.authserver.interfaces import IUserDetailsStorage
from canonical.authserver.interfaces import IUserDetailsStorageV2

from canonical.foaf import nickname


class UserDetailsStorageMixin(object):
    """Functions that are shared between DatabaseUserDetailsStorage and
    DatabaseUserDetailsStorageV2"""

    def _getEmailAddresses(self, transaction, personID):
        """Get the email addresses for a person"""
        transaction.execute(
            'SELECT EmailAddress.email FROM EmailAddress '
            'WHERE EmailAddress.person = %d '
            'ORDER BY EmailAddress.email'
            % (personID,)
        )
        return [row[0] for row in transaction.fetchall()]

    def _addEmailAddresses(self, transaction, emailAddresses, personID):
        """Add some email addresses to a person
       
        First email address is PREFERRED, others are VALIDATED
        """
        transaction.execute(
            "INSERT INTO EmailAddress (person, email, status) "
            "VALUES (%d, %s, %d)" % (
                personID, quote(emailAddresses[0]),
                dbschema.EmailAddressStatus.PREFERRED.value
                )
            )
        for emailAddress in emailAddresses[1:]:
            transaction.execute(
                "INSERT INTO EmailAddress (person, email, status) "
                "VALUES (%d, %s, %d)"
                % (personID, quote(emailAddress),
                   dbschema.EmailAddressStatus.VALIDATED.value)
            )

    def getSSHKeys(self, archiveName):
        ri = self.connectionPool.runInteraction
        return ri(self._getSSHKeysInteraction, archiveName)

    def _getSSHKeysInteraction(self, transaction, archiveName):
        # The PushMirrorAccess table explicitly says that a person may access a
        # particular push mirror.
        transaction.execute(
            "SELECT keytype, keytext "
            "FROM SSHKey "
            "JOIN PushMirrorAccess ON SSHKey.person = PushMirrorAccess.person "
            "WHERE PushMirrorAccess.name = %s"
            % (quote(archiveName),)
        )
        authorisedKeys = transaction.fetchall()
        
        # A person can also access any archive named after a validated email
        # address.
        if '--' in archiveName:
            email, suffix = archiveName.split('--', 1)
        else:
            email = archiveName

        transaction.execute(
            "SELECT keytype, keytext "
            "FROM SSHKey "
            "JOIN EmailAddress ON SSHKey.person = EmailAddress.person "
            "WHERE EmailAddress.email = %s "
            "AND EmailAddress.status in (%d, %d)"
            % (quote(email), dbschema.EmailAddressStatus.VALIDATED.value,
                dbschema.EmailAddressStatus.PREFERRED.value)
        )
        authorisedKeys.extend(transaction.fetchall())
        # Replace keytype with correct DBSchema items.
        authorisedKeys = [(dbschema.SSHKeyType.items[keytype].title, keytext)
                          for keytype, keytext in authorisedKeys]
        return authorisedKeys


class DatabaseUserDetailsStorage(UserDetailsStorageMixin):
    """Launchpad-database backed implementation of IUserDetailsStorage"""
    # Note that loginID always refers to any name you can login with (an email
    # address, or a nickname, or a numeric ID), whereas personID always refers
    # to the numeric ID, which is the value found in Person.id in the database.
    implements(IUserDetailsStorage)
    
    def __init__(self, connectionPool):
        """Constructor.
        
        :param connectionPool: A twisted.enterprise.adbapi.ConnectionPool
        """
        self.connectionPool = connectionPool
        self.encryptor = SSHADigestEncryptor()
    
    def getUser(self, loginID):
        ri = self.connectionPool.runInteraction
        return ri(self._getUserInteraction, loginID)

    def _getUserInteraction(self, transaction, loginID):
        row = self._getPerson(transaction, loginID)
        try:
            personID, displayname, passwordDigest, salt = row
        except TypeError:
            # No-one found
            return {}
        
        emailaddresses = self._getEmailAddresses(transaction, personID)

        return {
            'id': personID,
            'displayname': displayname,
            'emailaddresses': emailaddresses,
            'salt': salt,
        }

    def authUser(self, loginID, sshaDigestedPassword):
        ri = self.connectionPool.runInteraction
        return ri(self._authUserInteraction, loginID,
                  sshaDigestedPassword.encode('base64'))
        
    def _authUserInteraction(self, transaction, loginID, sshaDigestedPassword):
        row = self._getPerson(transaction, loginID)
        try:
            personID, displayname, passwordDigest, salt = row
        except TypeError:
            # No-one found
            return {}

        if passwordDigest is None:
            # The user has no password, which means they can't login.
            return {}
        
        if passwordDigest.rstrip() != sshaDigestedPassword.rstrip():
            # Wrong password
            return {}
        
        emailaddresses = self._getEmailAddresses(transaction, personID)

        return {
            'id': personID,
            'displayname': displayname,
            'emailaddresses': emailaddresses,
            'salt': salt,
        }

    def createUser(self, preferredEmail, sshaDigestedPassword, displayname,
                   emailAddresses):
        """Create a user.

        :param preferredEmail: Preferred email address for this user.

        :param emailAddresses: Other email addresses for this user.
        
        This method should only be called if the email addresses have all
        been validated, or if emailAddresses is an empty list and the
        password only known by the controller of the preferredEmail address.
        """
        ri = self.connectionPool.runInteraction
        emailAddresses = (
                [preferredEmail]
                + [e for e in emailAddresses if e != preferredEmail]
                )
        deferred = ri(self._createUserInteraction,
                      sshaDigestedPassword.encode('base64'),
                      displayname, emailAddresses)
        deferred.addErrback(self._eb_createUser)
        return deferred

    def _eb_createUser(self, failure):
        failure.trap(psycopg.DatabaseError)
        # Return any empty dict to signal failure
        # FIXME: we should distinguish between transient failure (e.g. DB
        #        temporarily down or timing out) and actual errors (i.e. the
        #        data is somehow invalid due to violating a constraint)?
        return {}

    def _createUserInteraction(self, transaction, sshaDigestedPassword,
                               displayname, emailAddresses):
        # Note that any psycopg.DatabaseErrors that occur will be translated
        # into a return value of {} by the _eb_createUser errback.
        # TODO: Catch bad types, e.g. unicode, and raise appropriate exceptions

        # Get the ID of the new person
        transaction.execute(
            "SELECT NEXTVAL('person_id_seq'); "
        )

        # No try/except IndexError here, because this shouldn't be able to fail!
        personID = transaction.fetchone()[0]

        # Create the Person
        name = nickname.generate_nick(emailAddresses[0], lambda nick:
                self._getPerson(transaction, nick))
        transaction.execute(
            "INSERT INTO Person (id, name, displayname, password) "
            "VALUES (%d, %s, %s, %s)"
            % (personID, quote(name), quote(displayname).encode('utf-8'),
               quote(sshaDigestedPassword))
        )

        self._addEmailAddresses(transaction, emailAddresses, personID)

        return {
            'id': personID,
            'displayname': displayname,
            'emailaddresses': list(emailAddresses),
            'salt': saltFromDigest(sshaDigestedPassword),
        }
                
    def changePassword(self, loginID, sshaDigestedPassword,
                       newSshaDigestedPassword):
        ri = self.connectionPool.runInteraction
        return ri(self._changePasswordInteraction, loginID,
                  sshaDigestedPassword.encode('base64'),
                  newSshaDigestedPassword.encode('base64'))

    def _changePasswordInteraction(self, transaction, loginID,
                                   sshaDigestedPassword,
                                   newSshaDigestedPassword):
        userDict = self._authUserInteraction(transaction, loginID,
                                             sshaDigestedPassword)
        if not userDict:
            return {}

        personID = userDict['id']
        
        transaction.execute(
            "UPDATE Person "
            "SET password = %s "
            "WHERE Person.id = %d "
            % (quote(str(newSshaDigestedPassword)), personID)
        )
        
        userDict['salt'] = saltFromDigest(newSshaDigestedPassword)
        return userDict

    def _getPerson(self, transaction, loginID):
        query = (
            "SELECT Person.id, Person.displayname, Person.password "
            "FROM Person "
        )
        transaction.execute(
            query +
            "INNER JOIN EmailAddress ON EmailAddress.person = Person.id "
            "WHERE lower(EmailAddress.email) = %s"
            % (quote(str(loginID).lower()),)
        )
        
        row = transaction.fetchone()
        if row is None:
            # Fallback: try looking up by id, rather than by email
            try:
                personID = int(loginID)
            except ValueError:
                pass
            else:
                transaction.execute(
                    query +
                    "WHERE Person.id = %d" % (personID,)
                )
                row = transaction.fetchone()
        if row is None:
            # Fallback #2: try treating loginID as a nickname
            transaction.execute(
                query +
                "WHERE Person.name = %s" 
                % (quote(str(loginID)),)
            )
            row = transaction.fetchone()
        if row is None:
            # Fallback #3: give up!
            return None

        row = list(row)
        passwordDigest = row[2]
        if passwordDigest:
            salt = saltFromDigest(passwordDigest)
        else:
            salt = ''

        return row + [salt]

    def _getEmailAddresses(self, transaction, personID):
        transaction.execute(
            'SELECT EmailAddress.email FROM EmailAddress '
            'WHERE EmailAddress.person = %d '
            'ORDER BY EmailAddress.email'
            % (personID,)
        )
        return [row[0] for row in transaction.fetchall()]

def saltFromDigest(digest):
    """Extract the salt from a SSHA digest.

    :param digest: base64-encoded digest
    """
    if isinstance(digest, unicode):
        # Make sure digest is a str, because unicode objects don't have a
        # decode method in python 2.3.  Base64 should always be representable in
        # ASCII.
        digest = digest.encode('ascii')
    return digest.decode('base64')[20:].encode('base64')


class DatabaseUserDetailsStorageV2(UserDetailsStorageMixin):
    """Launchpad-database backed implementation of IUserDetailsStorageV2"""
    implements(IUserDetailsStorageV2)
    
    def __init__(self, connectionPool):
        """Constructor.
        
        :param connectionPool: A twisted.enterprise.adbapi.ConnectionPool
        """
        self.connectionPool = connectionPool
        self.encryptor = SSHADigestEncryptor()
    
    def getUser(self, loginID):
        ri = self.connectionPool.runInteraction
        return ri(self._getUserInteraction, loginID)

    def _getUserInteraction(self, transaction, loginID):
        row = self._getPerson(transaction, loginID)
        try:
            personID, displayname, passwordDigest = row
        except TypeError:
            # No-one found
            return {}
        
        emailaddresses = self._getEmailAddresses(transaction, personID)

        return {
            'id': personID,
            'displayname': displayname,
            'emailaddresses': emailaddresses,
        }

    def _getPerson(self, transaction, loginID):
        """Look up a person by loginID.

        The loginID will be first tried as an email address, then as a numeric
        ID, then finally as a nickname.

        :returns: a tuple of (person ID, display name, password) or None if not
            found.
        """
        query = (
            "SELECT Person.id, Person.displayname, Person.password "
            "FROM Person "
            "INNER JOIN EmailAddress ON EmailAddress.person = Person.id "
        )

        # First, try to look the person up by using loginID as an email 
        # address
        transaction.execute(
            query + 
            "WHERE lower(EmailAddress.email) = %s "
            % (quote(str(loginID).lower()),)
        )
        
        row = transaction.fetchone()
        if row is None:
            # Fallback: try looking up by id, rather than by email
            try:
                personID = int(loginID)
            except ValueError:
                pass
            else:
                transaction.execute(
                    query +
                    "WHERE Person.id = '%d'" % (personID,)
                )
                row = transaction.fetchone()
        if row is None:
            # Fallback #2: try treating loginID as a nickname
            transaction.execute(
                query +
                "WHERE Person.name = %s" 
                % (quote(str(loginID)),)
            )
            row = transaction.fetchone()
        if row is None:
            # Fallback #3: give up
            return None

        row = list(row)
        assert isinstance(row[1], unicode)

        return row

    def authUser(self, loginID, password):
        ri = self.connectionPool.runInteraction
        return ri(self._authUserInteraction, loginID, password)
        
    def _authUserInteraction(self, transaction, loginID, password):
        row = self._getPerson(transaction, loginID)
        try:
            personID, displayname, passwordDigest = row
        except TypeError:
            # No-one found
            return {}

        if not self.encryptor.validate(password, passwordDigest):
            # Wrong password
            return {}
        
        emailaddresses = self._getEmailAddresses(transaction, personID)

        return {
            'id': personID,
            'displayname': displayname,
            'emailaddresses': emailaddresses,
        }

    def createUser(self, preferredEmail, password, displayname, emailAddresses):
        ri = self.connectionPool.runInteraction
        emailAddresses = (
                [preferredEmail]
                + [e for e in emailAddresses if e != preferredEmail]
                )
        deferred = ri(self._createUserInteraction,
                      password, displayname, emailAddresses)
        deferred.addErrback(self._eb_createUser)
        return deferred

    def _eb_createUser(self, failure):
        failure.trap(psycopg.DatabaseError)
        # Return any empty dict to signal failure
        # FIXME: should we distinguish between transient failure (e.g. DB
        #        temporarily down or timing out) and actual errors (i.e. the
        #        data is somehow invalid due to violating a constraint)?
        return {}

    def _createUserInteraction(self, transaction, password, displayname,
                               emailAddresses):
        # Note that any psycopg.DatabaseErrors that are raised will be translated
        # into a return value of {} by the _eb_createUser errback.

        # TODO: Catch bad types, e.g. unicode, and raise appropriate exceptions

        # Get the ID of the new person
        transaction.execute(
            "SELECT NEXTVAL('person_id_seq'); "
        )

        # No try/except IndexError here, because this shouldn't be able to fail!
        personID = transaction.fetchone()[0]

        # Create the Person
        name = nickname.generate_nick(emailAddresses[0], lambda nick:
                self._getPerson(transaction, nick))
        passwordDigest = self.encryptor.encrypt(password)
        transaction.execute(
            "INSERT INTO Person (id, name, displayname, password) "
            "VALUES (%d, %s, %s, %s)"
            % (personID, quote(name), quote(displayname).encode('utf-8'),
               quote(passwordDigest))
        )

        self._addEmailAddresses(transaction, emailAddresses, personID)

        return {
            'id': personID,
            'displayname': displayname,
            'emailaddresses': list(emailAddresses),
        }
                
    def changePassword(self, loginID, oldPassword, newPassword):
        ri = self.connectionPool.runInteraction
        return ri(self._changePasswordInteraction, loginID,
                  oldPassword, newPassword)

    def _changePasswordInteraction(self, transaction, loginID,
                                   oldPassword, newPassword):
        # First authenticate with the old password
        userDict = self._authUserInteraction(transaction, loginID, oldPassword)
        if not userDict:
            return {}

        personID = userDict['id']
        newPasswordDigest = self.encryptor.encrypt(newPassword)
        
        transaction.execute(
            "UPDATE Person "
            "SET password = '%s' "
            "WHERE Person.id = %d "
            % (newPasswordDigest, personID)
        )
        
        return userDict

