# Copyright 2004 Canonical Ltd.  All rights reserved.

import psycopg

from zope.interface import implements

#from twisted.enterprise import adbapi
from canonical.authserver import adbapi

from canonical.launchpad.webapp.authentication import SSHADigestEncryptor
from canonical.lp import dbschema

from canonical.authserver.interfaces import IUserDetailsStorage

from canonical.foaf import nickname

class DatabaseUserDetailsStorage(object):
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

    def createUser(self, loginID, sshaDigestedPassword, displayname,
                   emailAddresses):
        ri = self.connectionPool.runInteraction
        if loginID not in emailAddresses:
            emailAddresses = emailAddresses + [loginID]
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

        # Create the Person
        displaynameOrig = displayname
        name = nickname.generate_nick(emailAddresses[0], lambda nick:
                self._getPerson(transaction, nick))
        displayname = displayname.replace("'", "''").encode('utf-8')
        pw = sshaDigestedPassword.replace("'", "''")
        sql = ("""\
            INSERT INTO Person (name, displayname, password)  VALUES ('%s', '%s', '%s')"""
            % (name, displayname, pw))

        transaction.execute(sql)

        # Get the ID of the new person
        transaction.execute(
            "SELECT Person.id "
            "FROM Person "
            "WHERE Person.displayname = '%s' "
            "AND Person.password = '%s'"
            % (displayname, pw)
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
            'displayname': displaynameOrig,
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
            "SET password = '%s' "
            "WHERE Person.id = %d "
            % (str(newSshaDigestedPassword).replace("'", "''"),
               personID)
        )
        
        userDict['salt'] = saltFromDigest(newSshaDigestedPassword)
        return userDict

    def _getPerson(self, transaction, loginID):
        query = (
            "SELECT Person.id, Person.displayname, Person.password "
            "FROM Person "
            "INNER JOIN EmailAddress ON EmailAddress.person = Person.id "
        )
        transaction.execute(
            query + 
            "WHERE lower(EmailAddress.email) = '%s' "
            % (str(loginID).lower().replace("'", "''"),)
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
                "WHERE Person.name = '%s'" 
                % (str(loginID).replace("'", "''"),)
            )
            row = transaction.fetchone()
        if row is None:
            # Fallback #3: give up
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
            "WHERE PushMirrorAccess.name = '%s'"
            % (archiveName.replace("'", "''"),)
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
            "WHERE EmailAddress.email = '%s' "
            "AND EmailAddress.status in (2, 4)"
            % (email.replace("'", "''"),)
        )
        authorisedKeys.extend(transaction.fetchall())
        
        return authorisedKeys


def saltFromDigest(digest):
    """Extract the salt from a SSHA digest.

    :param digest: base64-encoded digest
    """
    return digest.encode('us-ascii').decode('base64')[20:].encode('base64')

