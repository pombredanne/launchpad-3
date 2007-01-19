# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DatabaseUserDetailsStorage',
    'DatabaseUserDetailsStorageV2',
    'DatabaseBranchDetailsStorage',
    ]

import os

from zope.interface import implements

from canonical.launchpad.webapp import urlappend
from canonical.launchpad.webapp.authentication import SSHADigestEncryptor
from canonical.launchpad.scripts.supermirror_rewritemap import split_branch_id
from canonical.launchpad.interfaces import UBUNTU_WIKI_URL
from canonical.database.sqlbase import sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.lp import dbschema
from canonical.config import config

from canonical.authserver.interfaces import (
    IUserDetailsStorage, IUserDetailsStorageV2, IBranchDetailsStorage)


def utf8(x):
    if isinstance(x, unicode):
        x = x.encode('utf-8')
    return x


class UserDetailsStorageMixin:
    """Functions that are shared between DatabaseUserDetailsStorage and
    DatabaseUserDetailsStorageV2"""

    def _getEmailAddresses(self, transaction, personID):
        """Get the email addresses for a person"""
        transaction.execute(utf8('''
            SELECT EmailAddress.email FROM EmailAddress
            WHERE EmailAddress.person = %s
            AND EmailAddress.status IN (%s, %s)
            ORDER BY (EmailAddress.status = %s) DESC, EmailAddress.email'''
            % sqlvalues(personID, dbschema.EmailAddressStatus.PREFERRED,
                        dbschema.EmailAddressStatus.VALIDATED,
                        dbschema.EmailAddressStatus.PREFERRED))
        )
        return [row[0] for row in transaction.fetchall()]

    def getSSHKeys(self, archiveName):
        ri = self.connectionPool.runInteraction
        return ri(self._getSSHKeysInteraction, archiveName)

    def _getSSHKeysInteraction(self, transaction, loginID):
        """The interaction for getSSHKeys."""
        if '@' in loginID:
            # Bazaar 1.x logins.  Deprecated.
            archiveName = loginID
            # The PushMirrorAccess table explicitly says that a person may
            # access a particular push mirror.
            transaction.execute(utf8('''
                SELECT keytype, keytext
                FROM SSHKey
                JOIN PushMirrorAccess ON SSHKey.person = PushMirrorAccess.person
                WHERE PushMirrorAccess.name = %s'''
                % sqlvalues(archiveName))
            )
            authorisedKeys = transaction.fetchall()
            
            # A person can also access any archive named after a validated email
            # address.
            if '--' in archiveName:
                email, suffix = archiveName.split('--', 1)
            else:
                email = archiveName

            transaction.execute(utf8('''
                SELECT keytype, keytext
                FROM SSHKey
                JOIN EmailAddress ON SSHKey.person = EmailAddress.person
                WHERE EmailAddress.email = %s
                AND EmailAddress.status in (%s, %s)'''
                % sqlvalues(email, dbschema.EmailAddressStatus.VALIDATED,
                            dbschema.EmailAddressStatus.PREFERRED))
            )
            authorisedKeys.extend(transaction.fetchall())
        else:
            transaction.execute(utf8('''
                SELECT keytype, keytext
                FROM SSHKey
                JOIN Person ON SSHKey.person = Person.id
                WHERE Person.name = %s'''
                % sqlvalues(loginID))
            )
            authorisedKeys = transaction.fetchall()

        # Replace keytype with correct DBSchema items.
        authorisedKeys = [(dbschema.SSHKeyType.items[keytype].title, keytext)
                          for keytype, keytext in authorisedKeys]
        return authorisedKeys

    def _getPerson(self, transaction, loginID):
        # We go through some contortions with assembling the SQL to ensure that
        # the OUTER JOIN happens after the INNER JOIN.  This should allow
        # postgres to optimise the query as much as possible (approx 10x faster
        # according to my tests with EXPLAIN on the production database).
        select = '''
            SELECT Person.id, Person.displayname, Person.name, Person.password,
                   Wikiname.wikiname
            FROM Person '''

        wikiJoin = ('''
            LEFT OUTER JOIN Wikiname ON Wikiname.person = Person.id
            AND Wikiname.wiki = %s '''
            % sqlvalues(UBUNTU_WIKI_URL))

        # First, try to look the person up by using loginID as an email
        # address
        try:
            if not isinstance(loginID, unicode):
                # Refuse to guess encoding, so we decode as 'ascii'
                loginID = str(loginID).decode('ascii')
        except UnicodeDecodeError:
            row = None
        else:
            transaction.execute(utf8(
                select +
                "INNER JOIN EmailAddress ON EmailAddress.person = Person.id " +
                wikiJoin +
                ("WHERE lower(EmailAddress.email) = %s "
                 "AND EmailAddress.status IN (%s, %s) "
                % sqlvalues(loginID.lower(),
                            dbschema.EmailAddressStatus.PREFERRED,
                            dbschema.EmailAddressStatus.VALIDATED)))
            )

            row = transaction.fetchone()

        if row is None:
            # Fallback: try looking up by id, rather than by email
            try:
                personID = int(loginID)
            except ValueError:
                pass
            else:
                transaction.execute(utf8(
                    select + wikiJoin +
                    ("WHERE Person.id = %s " % sqlvalues(personID)))
                )
                row = transaction.fetchone()
        if row is None:
            # Fallback #2: try treating loginID as a nickname
            transaction.execute(utf8(
                select + wikiJoin +
                ("WHERE Person.name = %s " % sqlvalues(loginID)))
            )
            row = transaction.fetchone()
        if row is None:
            # Fallback #3: give up!
            return None

        row = list(row)
        assert isinstance(row[1], unicode)

        passwordDigest = row[3]
        if passwordDigest:
            salt = saltFromDigest(passwordDigest)
        else:
            salt = ''

        return row + [salt]


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
        """The interaction for getUser."""
        row = self._getPerson(transaction, loginID)
        try:
            personID, displayname, name, passwordDigest, wikiname, salt = row
        except TypeError:
            # No-one found
            return {}
        
        emailaddresses = self._getEmailAddresses(transaction, personID)

        if wikiname is None:
            # None/nil isn't standard XML-RPC
            wikiname = ''

        return {
            'id': personID,
            'displayname': displayname,
            'emailaddresses': emailaddresses,
            'wikiname': wikiname,
            'salt': salt,
        }

    def authUser(self, loginID, sshaDigestedPassword):
        ri = self.connectionPool.runInteraction
        return ri(self._authUserInteraction, loginID,
                  sshaDigestedPassword.encode('base64'))
        
    def _authUserInteraction(self, transaction, loginID, sshaDigestedPassword):
        """The interaction for authUser."""
        row = self._getPerson(transaction, loginID)
        try:
            personID, displayname, name, passwordDigest, wikiname, salt = row
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

        if wikiname is None:
            # None/nil isn't standard XML-RPC
            wikiname = ''

        return {
            'id': personID,
            'displayname': displayname,
            'emailaddresses': emailaddresses,
            'wikiname': wikiname,
            'salt': salt,
        }


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

    def _getTeams(self, transaction, personID):
        """Get list of teams a person is in.

        Returns a list of team dicts (see IUserDetailsStorageV2).
        """
        transaction.execute(utf8('''
            SELECT TeamParticipation.team, Person.name, Person.displayname
            FROM TeamParticipation
            INNER JOIN Person ON TeamParticipation.team = Person.id
            WHERE TeamParticipation.person = %s
            '''
            % sqlvalues(personID))
        )
        return [{'id': row[0], 'name': row[1], 'displayname': row[2]}
                for row in transaction.fetchall()]
    
    def getUser(self, loginID):
        ri = self.connectionPool.runInteraction
        return ri(self._getUserInteraction, loginID)

    def _getUserInteraction(self, transaction, loginID):
        """The interaction for getUser."""
        row = self._getPerson(transaction, loginID)
        try:
            personID, displayname, name, passwordDigest, wikiname = row
        except TypeError:
            # No-one found
            return {}
        
        emailaddresses = self._getEmailAddresses(transaction, personID)

        if wikiname is None:
            # None/nil isn't standard XML-RPC
            wikiname = ''

        return {
            'id': personID,
            'displayname': displayname,
            'name': name,
            'emailaddresses': emailaddresses,
            'wikiname': wikiname,
            'teams': self._getTeams(transaction, personID),
        }

    def _getPerson(self, transaction, loginID):
        """Look up a person by loginID.

        The loginID will be first tried as an email address, then as a numeric
        ID, then finally as a nickname.

        :returns: a tuple of (person ID, display name, password, wikiname) or
            None if not found.
        """
        row = UserDetailsStorageMixin._getPerson(self, transaction, loginID)
        if row is None:
            return None
        else:
            # Remove the salt from the result; the v2 API doesn't include it.
            return row[:-1]

    def authUser(self, loginID, password):
        ri = self.connectionPool.runInteraction
        return ri(self._authUserInteraction, loginID, password)
        
    def _authUserInteraction(self, transaction, loginID, password):
        """The interaction for authUser."""
        row = self._getPerson(transaction, loginID)
        try:
            personID, displayname, name, passwordDigest, wikiname = row
        except TypeError:
            # No-one found
            return {}

        if not self.encryptor.validate(password, passwordDigest):
            # Wrong password
            return {}
        
        emailaddresses = self._getEmailAddresses(transaction, personID)

        if wikiname is None:
            # None/nil isn't standard XML-RPC
            wikiname = ''

        return {
            'id': personID,
            'name': name,
            'displayname': displayname,
            'emailaddresses': emailaddresses,
            'wikiname': wikiname,
            'teams': self._getTeams(transaction, personID),
        }

    def getBranchesForUser(self, personID):
        ri = self.connectionPool.runInteraction
        return ri(self._getBranchesForUserInteraction, personID)

    def _getBranchesForUserInteraction(self, transaction, personID):
        """The interaction for getBranchesForUser."""
        transaction.execute(utf8('''
            SELECT Product.id, Product.name, Branch.id, Branch.name
            FROM Product RIGHT OUTER JOIN Branch ON Branch.product = Product.id
            WHERE Branch.owner = %s AND Branch.url IS NULL
            ORDER BY Product.id
            '''
            % sqlvalues(personID))
        )
        branches = []
        prevProductID = 'x'  # can never be equal to a real integer ID.
        rows = transaction.fetchall()
        for productID, productName, branchID, branchName in rows:
            if productID != prevProductID:
                prevProductID = productID
                currentBranches = []
                if productID is None:
                    assert productName is None
                    # Replace Nones with '', because standards-compliant XML-RPC
                    # can't handle None :(
                    productID, productName = '', ''
                branches.append((productID, productName, currentBranches))
            currentBranches.append((branchID, branchName))
        return branches

    def fetchProductID(self, productName):
        ri = self.connectionPool.runInteraction
        return ri(self._fetchProductIDInteraction, productName)

    def _fetchProductIDInteraction(self, transaction, productName):
        """The interaction for fetchProductID."""
        transaction.execute(utf8('''
            SELECT id FROM Product WHERE name = %s'''
            % sqlvalues(productName))
        )
        row = transaction.fetchone()
        if row is None:
            # No product by that name in the DB.
            productID = ''
        else:
            (productID,) = row
        return productID

    def createBranch(self, personID, productID, branchName):
        ri = self.connectionPool.runInteraction
        return ri(self._createBranchInteraction, personID, productID,
                  branchName)

    def _createBranchInteraction(self, transaction, personID, productID,
                                 branchName):
        """The interaction for createBranch."""
        # Convert psuedo-None to real None (damn XML-RPC!)
        if productID == '':
            productID = None

        # Get the ID of the new branch
        transaction.execute(
            "SELECT NEXTVAL('branch_id_seq'); "
        )
        branchID = transaction.fetchone()[0]

        transaction.execute(utf8('''
            INSERT INTO Branch (id, owner, product, name, author)
            VALUES (%s, %s, %s, %s, %s)'''
            % sqlvalues(branchID, personID, productID, branchName, personID))
        )
        return branchID


class DatabaseBranchDetailsStorage:
    """Launchpad-database backed implementation of IUserDetailsStorage"""

    implements(IBranchDetailsStorage)
    
    def __init__(self, connectionPool):
        """Constructor.
        
        :param connectionPool: A twisted.enterprise.adbapi.ConnectionPool
        """
        self.connectionPool = connectionPool

    def getBranchPullQueue(self):
        ri = self.connectionPool.runInteraction
        return ri(self._getBranchPullQueueInteraction)

    def _getBranchPullQueueInteraction(self, transaction):
        """The interaction for getBranchPullQueue."""
        # XXX Andrew Bennetts 2006-06-14: 
        # 'vcs-imports' should not be hard-coded in this function.  Instead this
        # ought to use getUtility(LaunchpadCelebrities), but the authserver
        # currently does not setup sqlobject etc.  Even nicer would be if the
        # Branch table had an enum column for the branch type.

        # XXX Andrew Bennetts 2006-06-15:
        # This query special cases hosted branches (url is NULL AND Person.name
        # <> 'vcs-imports') so that they are always in the queue, regardless of
        # last_mirror_attempt.  This is a band-aid fix for bug #48813, but we'll
        # need to do something more scalable eventually.

        # NOTE: The import-branch case is separated by testing
        # ProductSeries.id, but the 'vcs-imports' test is still relevant to
        # prevent obsolete vcs-imports branches that are no longer associated
        # to a ProductSeries from being mirrored every time.
        # -- DavidAllouche 2006-12-22
        transaction.execute(utf8("""
            SELECT Branch.id, Branch.url, Person.name
            FROM Branch INNER JOIN Person ON Branch.owner = Person.id
            LEFT OUTER JOIN ProductSeries
                ON ProductSeries.import_branch = Branch.id
            WHERE (ProductSeries.id is NULL AND (
                      last_mirror_attempt is NULL
                      OR (%(utc_now)s - last_mirror_attempt > '1 day')
                      OR (url is NULL AND Person.name <> 'vcs-imports')))
                   OR (ProductSeries.id IS NOT NULL AND (
                      (datelastsynced IS NOT NULL
                          AND last_mirror_attempt IS NULL)
                       OR (datelastsynced > last_mirror_attempt)
                       OR (datelastsynced IS NULL
                          AND (%(utc_now)s - last_mirror_attempt > '1 day'))))
            ORDER BY last_mirror_attempt IS NOT NULL, last_mirror_attempt
            """ % {'utc_now': UTC_NOW}))
        result = []
        for (branch_id, url, owner_name) in transaction.fetchall():
            if url is not None:
                # This is a pull branch, hosted externally.
                pull_url = url
            elif owner_name == 'vcs-imports':
                # This is an import branch, imported into bzr from
                # another RCS system such as CVS.
                prefix = config.launchpad.bzr_imports_root_url
                pull_url = urlappend(prefix, '%08x' % branch_id)
            else:
                # This is a push branch, hosted on the supermirror
                # (pushed there by users via SFTP).
                prefix = config.supermirrorsftp.branches_root
                pull_url = os.path.join(prefix, split_branch_id(branch_id))
            result.append((branch_id, pull_url))
        return result

    def startMirroring(self, branchID):
        """See IBranchDetailsStorage"""
        ri = self.connectionPool.runInteraction
        return ri(self._startMirroringInteraction, branchID)

    def _startMirroringInteraction(self, transaction, branchID):
        """The interaction for startMirroring."""
        transaction.execute(utf8("""
            UPDATE Branch
              SET last_mirror_attempt = CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
              WHERE id = %d""" % (branchID,)))
        # how many rows were updated?
        assert transaction.rowcount in [0, 1]
        return transaction.rowcount == 1

    def mirrorComplete(self, branchID, lastRevisionID):
        """See IBranchDetailsStorage"""
        ri = self.connectionPool.runInteraction
        return ri(self._mirrorCompleteInteraction, branchID, lastRevisionID)
    
    def _mirrorCompleteInteraction(self, transaction, branchID,
                                   lastRevisionID):
        """The interaction for mirrorComplete."""
        transaction.execute(utf8("""
            UPDATE Branch
              SET last_mirrored = last_mirror_attempt, mirror_failures = 0,
                  mirror_status_message = NULL, last_mirrored_id = %s
              WHERE id = %s""" % sqlvalues(lastRevisionID, branchID)))
        # how many rows were updated?
        assert transaction.rowcount in [0, 1]
        return transaction.rowcount == 1

    def mirrorFailed(self, branchID, reason):
        """See IBranchDetailsStorage"""
        ri = self.connectionPool.runInteraction
        return ri(self._mirrorFailedInteraction, branchID, reason)
    
    def _mirrorFailedInteraction(self, transaction, branchID, reason):
        """The interaction for mirrorFailed."""
        transaction.execute(utf8("""
            UPDATE Branch
              SET mirror_failures = mirror_failures + 1,
                  mirror_status_message = %s
              WHERE id = %s""" % sqlvalues(reason, branchID)))
        # how many rows were updated?
        assert transaction.rowcount in [0, 1]
        return transaction.rowcount == 1

