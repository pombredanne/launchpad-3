# Copyright 2004 Canonical Ltd.  All rights reserved.

import psycopg

from zope.interface import implements

from twisted.enterprise import adbapi

from canonical.lp.placelessauth.encryption import SSHADigestEncryptor
from canonical.lp import dbschema

from canonical.authserver.interfaces import IUserDetailsStorage

class DatabaseUserDetailsStorage(object):
    """Launchpad-database backed implementation of IUserDetailsStorage"""
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
        return ri(self._authUserInteraction, loginID, sshaDigestedPassword)
        
    def _authUserInteraction(self, transaction, loginID, sshaDigestedPassword):
        row = self._getPerson(transaction, loginID)
        try:
            personID, displayname, passwordDigest, salt = row
        except TypeError:
            # No-one found
            return {}

        if passwordDigest != sshaDigestedPassword:
            # Wrong password
            return {}
        
        emailaddresses = self._getEmailAddresses(transaction, personID)

        return {
            'id': personID,
            'displayname': displayname,
            'emailaddresses': emailaddresses,
            'salt': salt,
        }

    def createUser(self, loginID, sshaDigestedPassword, displayName,
                   emailAddresses):
        ri = self.connectionPool.runInteraction
        deferred = ri(self._createUserInteraction, transaction, sshaDigestedPassword,
                      displayName, emailAddresses)
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
                               displayName, emailAddresses):
        # Note that any psycopg.DatabaseErrors that occur will be translated
        # into a return value of {} by the _eb_createUser errback.

        # Create the Person
        transaction.execute(
            "INSERT INTO Person (displayname, password) "
            "VALUES ('%s', '%s')"
            % (displayName.replace("'", "''"),
              sshaDigestedPassword.replace("'", "''"))
        )

        # Get the ID of the new person
        transaction.execute(
            "SELECT Person.id "
            "FROM Person "
            "WHERE Person.displayname = '%s' "
            "AND Person.password = '%s'"
            % (displayName.replace("'", "''"),
              sshaDigestedPassword.replace("'", "''"))
        )

        # No try/except IndexError here, because this shouldn't be able to fail!
        personID = transaction.fetchone()[0]

        # Add the email addresses
        for emailAddress in emailAddresses:
            transaction.execute(
                "INSERT INTO EmailAddress (person, email, status) "
                "VALUES ('%d', '%s', %d)"
                % (personID,
                   emailAddress.replace("'", "''"),
                   dbschema.EmailAddressStatus.NEW)
            )

        return {
            'id': personID,
            'displayname': displayName,
            'emailaddresses': list(emailAddresses)
        }
                
    def _getPerson(self, transaction, loginID):
        transaction.execute(
            "SELECT Person.id, Person.displayname, Person.password "
            "FROM Person "
            "WHERE EmailAddress.email = '%s' "
            "AND EmailAddress.person = Person.id"
            % (str(loginID).replace("'", "''"),)
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
                    "SELECT Person.id, Person.displayname, Person.password "
                    "FROM Person "
                    "WHERE Person.id = '%d'" % (personID,)
                )
                row = transaction.fetchone()
            if row is None:
                return row

        row = list(row)
        passwordDigest = row[2]
        if passwordDigest:
            salt = passwordDigest.decode('base64')[20:]
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

