# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Tests for lib/canonical/authserver/database.py"""

__metaclass__ = type

import unittest

from zope.interface.verify import verifyObject

from canonical.database.sqlbase import sqlvalues

from canonical.launchpad.webapp.authentication import SSHADigestEncryptor

from canonical.authserver.interfaces import (
    IBranchDetailsStorage, IHostedBranchStorage, IUserDetailsStorage,
    IUserDetailsStorageV2)
from canonical.authserver.database import (
    DatabaseUserDetailsStorage, DatabaseUserDetailsStorageV2,
    DatabaseBranchDetailsStorage)
from canonical.lp import dbschema

from canonical.launchpad.ftests.harness import LaunchpadTestCase


class TestDatabaseSetup(LaunchpadTestCase):
    def setUp(self):
        super(TestDatabaseSetup, self).setUp()
        self.connection = self.connect()
        self.cursor = self.connection.cursor()

    def tearDown(self):
        self.cursor.close()
        self.connection.close()
        super(TestDatabaseSetup, self).tearDown()


class DatabaseStorageTestCase(TestDatabaseSetup):

    def test_verifyInterface(self):
        self.failUnless(verifyObject(IUserDetailsStorage,
                                     DatabaseUserDetailsStorage(None)))
        self.failUnless(verifyObject(IUserDetailsStorageV2,
                                     DatabaseUserDetailsStorageV2(None)))
        self.failUnless(verifyObject(IHostedBranchStorage,
                                     DatabaseUserDetailsStorageV2(None)))

    def test_getUser(self):
        # Getting a user should return a valid dictionary of details

        # Note: we access _getUserInteraction directly to avoid mucking around
        # with setting up a ConnectionPool
        storage = DatabaseUserDetailsStorage(None)
        userDict = storage._getUserInteraction(self.cursor, 'mark@hbd.com')
        self.assertEqual('Mark Shuttleworth', userDict['displayname'])
        self.assertEqual(['mark@hbd.com'], userDict['emailaddresses'])
        self.assertEqual('MarkShuttleworth', userDict['wikiname'])
        self.failUnless(userDict.has_key('salt'))

        # Getting by ID should give the same result as getting by email
        userDict2 = storage._getUserInteraction(self.cursor, userDict['id'])
        self.assertEqual(userDict, userDict2)

        # Getting by nickname should also give the same result
        userDict3 = storage._getUserInteraction(self.cursor, 'sabdfl')
        self.assertEqual(userDict, userDict3)

    def test_getUserMissing(self):
        # Getting a non-existent user should return {}
        storage = DatabaseUserDetailsStorage(None)
        userDict = storage._getUserInteraction(self.cursor, 'noone@fake.email')
        self.assertEqual({}, userDict)

        # Ditto for getting a non-existent user by id :)
        userDict = storage._getUserInteraction(self.cursor, 9999)
        self.assertEqual({}, userDict)

    def test_getUserMultipleAddresses(self):
        # Getting a user with multiple addresses should return all the
        # confirmed addresses.
        storage = DatabaseUserDetailsStorage(None)
        userDict = storage._getUserInteraction(self.cursor,
                                               'stuart.bishop@canonical.com')
        self.assertEqual('Stuart Bishop', userDict['displayname'])
        self.assertEqual(['stuart.bishop@canonical.com',
                          'stuart@stuartbishop.net'],
                         userDict['emailaddresses'])

    def test_noUnconfirmedAddresses(self):
        # Unconfirmed addresses should not be returned, so if we add a NEW
        # address, it won't change the result.
        storage = DatabaseUserDetailsStorage(None)
        userDict = storage._getUserInteraction(self.cursor,
                                               'stuart.bishop@canonical.com')
        self.cursor.execute('''
            INSERT INTO EmailAddress (email, person, status)
            VALUES ('sb@example.com', %d, %d)
            ''' % (userDict['id'], dbschema.EmailAddressStatus.NEW.value))
        userDict2 = storage._getUserInteraction(self.cursor,
                                                'stuart.bishop@canonical.com')
        self.assertEqual(userDict, userDict2)
        
    def test_preferredEmailFirst(self):
        # If there's a PREFERRED address, it should be first in the
        # emailaddresses list.  Let's make stuart@stuartbishop.net PREFERRED
        # rather than stuart.bishop@canonical.com.
        storage = DatabaseUserDetailsStorage(None)
        self.cursor.execute('''
            UPDATE EmailAddress SET status = %d
            WHERE email = 'stuart.bishop@canonical.com'
            ''' % (dbschema.EmailAddressStatus.VALIDATED.value,))
        self.cursor.execute('''
            UPDATE EmailAddress SET status = %d
            WHERE email = 'stuart@stuartbishop.net'
            ''' % (dbschema.EmailAddressStatus.PREFERRED.value,))
        userDict = storage._getUserInteraction(self.cursor,
                                               'stuart.bishop@canonical.com')
        self.assertEqual(['stuart@stuartbishop.net',
                          'stuart.bishop@canonical.com'],
                         userDict['emailaddresses'])

    def test_authUserNoUser(self):
        # Authing a user that doesn't exist should return {}
        storage = DatabaseUserDetailsStorage(None)
        ssha = SSHADigestEncryptor().encrypt('supersecret!')
        userDict = storage._authUserInteraction(self.cursor, 'noone@fake.email',
                                                ssha)
        self.assertEqual({}, userDict)

    def test_authUserNullPassword(self):
        # Authing a user with a NULL password should always return {}
        storage = DatabaseUserDetailsStorage(None)
        ssha = SSHADigestEncryptor().encrypt('supersecret!')
        # The 'admins' user in the sample data has no password, so we use that.
        userDict = storage._authUserInteraction(self.cursor, 'admins', ssha)
        self.assertEqual({}, userDict)

    def test_authUserUnconfirmedEmail(self):
        # Unconfirmed email addresses cannot be used to log in.
        storage = DatabaseUserDetailsStorage(None)
        ssha = SSHADigestEncryptor().encrypt('supersecret!')
        self.cursor.execute('''
            UPDATE Person SET password = '%s'
            WHERE id = (SELECT person FROM EmailAddress WHERE email =
                        'justdave@bugzilla.org')'''
            % (ssha,))
        userDict = storage._authUserInteraction(self.cursor,
                                                'justdave@bugzilla.org', ssha)
        self.assertEqual({}, userDict)

    def test_nameInV2UserDict(self):
        # V2 user dicts should have a 'name' field.
        storage = DatabaseUserDetailsStorageV2(None)
        userDict = storage._getUserInteraction(self.cursor, 'mark@hbd.com')
        self.assertEqual('sabdfl', userDict['name'])

    def test_fetchProductID(self):
        storage = DatabaseUserDetailsStorageV2(None)
        productID = storage._fetchProductIDInteraction(self.cursor, 'firefox')
        self.assertEqual(4, productID)
    
        # Invalid product names are signalled by a return value of ''
        productID = storage._fetchProductIDInteraction(self.cursor, 'xxxxx')
        self.assertEqual('', productID)

    def test_getBranchesForUser(self):
        # Although user 12 has lots of branches in the sample data, they only
        # have one push branch: a branch named "pushed" on the "gnome-terminal"
        # product.
        storage = DatabaseUserDetailsStorageV2(None)
        branches = storage._getBranchesForUserInteraction(self.cursor, 12)
        self.assertEqual(1, len(branches))
        gnomeTermProduct = branches[0]
        gnomeTermID, gnomeTermName, gnomeTermBranches = gnomeTermProduct
        self.assertEqual(6, gnomeTermID)
        self.assertEqual('gnome-terminal', gnomeTermName)
        self.assertEqual([(25, 'pushed')], gnomeTermBranches)

    def test_getBranchesForUserNullProduct(self):
        # getBranchesForUser returns branches for hosted branches with no
        # product.

        # First, insert a push branch (url is NULL) with a NULL product.
        self.cursor.execute("""
            INSERT INTO Branch
                (owner, product, name, title, summary, author, url)
            VALUES
                (12, NULL, 'foo-branch', NULL, NULL, 12, NULL)
            """)

        storage = DatabaseUserDetailsStorageV2(None)
        branchInfo = storage._getBranchesForUserInteraction(self.cursor, 12)
        self.assertEqual(2, len(branchInfo))

        gnomeTermProduct, junkProduct = branchInfo
        # Results could come back in either order, so swap if necessary.
        if gnomeTermProduct[0] is None:
            gnomeTermProduct, junkProduct = junkProduct, gnomeTermProduct
        
        # Check that the details and branches for the junk product are correct:
        # empty ID and name for the product, with a single branch named
        # 'foo-branch'.
        junkID, junkName, junkBranches = junkProduct
        self.assertEqual('', junkID)
        self.assertEqual('', junkName)
        self.assertEqual(1, len(junkBranches))
        fooBranchID, fooBranchName = junkBranches[0]
        self.assertEqual('foo-branch', fooBranchName)
    
    def test_createBranch(self):
        storage = DatabaseUserDetailsStorageV2(None)
        branchID = storage._createBranchInteraction(self.cursor, 12, 6, 'foo')
        # Assert branchID now appears in database.  Note that title and summary
        # should be NULL, and author should be set to the owner.
        self.cursor.execute("""
            SELECT owner, product, name, title, summary, author FROM Branch
            WHERE id = %d"""
            % branchID)
        self.assertEqual((12, 6, 'foo', None, None, 12), self.cursor.fetchone())

        # Create a branch with NULL product too:
        branchID = storage._createBranchInteraction(self.cursor, 1, None, 'foo')
        self.cursor.execute("""
            SELECT owner, product, name, title, summary, author FROM Branch
            WHERE id = %d"""
            % branchID)
        self.assertEqual((1, None, 'foo', None, None, 1),
                         self.cursor.fetchone())
        

class ExtraUserDatabaseStorageTestCase(TestDatabaseSetup):
    # Tests that do some database writes (but makes sure to roll them back)
    def setUp(self):
        TestDatabaseSetup.setUp(self)
        # This is the salt for Mark's password in the sample data.
        self.salt = '\xf4;\x15a\xe4W\x1f'

    def _getTime(self, row_id):
        self.cursor.execute("""
            SELECT mirror_request_time FROM Branch
            WHERE id = %d""" % row_id)
        [mirror_request_time] = self.cursor.fetchone()
        return mirror_request_time

    def test_initialMirrorRequest(self):
        # The default 'mirror_request_time' for a newly created hosted branch
        # should be None.
        storage = DatabaseUserDetailsStorageV2(None)
        branchID = storage._createBranchInteraction(self.cursor, 1, None,
                                                    'foo')
        self.assertEqual(self._getTime(branchID), None)

    def test_requestMirror(self):
        # requestMirror should set the mirror_request_time field to be the
        # current time.
        hosted_branch_id = 25
        # make sure the sample data is sane
        self.assertEqual(self._getTime(hosted_branch_id), None)

        storage = DatabaseUserDetailsStorageV2(None)
        storage._requestMirrorInteraction(self.cursor, hosted_branch_id)
        self.cursor.execute("SELECT CURRENT_TIMESTAMP AT TIME ZONE 'UTC'")
        [current_db_time] = self.cursor.fetchone()
        self.assertEqual(current_db_time, self._getTime(hosted_branch_id))

    def test_authUser(self):
        # Authenticating a user with the right password should work
        storage = DatabaseUserDetailsStorage(None)
        ssha = SSHADigestEncryptor().encrypt('test', self.salt)
        userDict = storage._authUserInteraction(self.cursor, 'mark@hbd.com',
                                                ssha)
        self.assertNotEqual({}, userDict)

        # In fact, it should return the same dict as getUser
        goodDict = storage._getUserInteraction(self.cursor, 'mark@hbd.com')
        self.assertEqual(goodDict, userDict)

        # Unicode email addresses are handled too.
        self.cursor.execute(
            "INSERT INTO EmailAddress (person, email, status) "
            "VALUES ("
            "  1, "
            "  '%s', "
            "  2)"  # 2 == Validated
            % (u'm\xe3rk@hbd.com'.encode('utf-8'),)
        )
        userDict = storage._authUserInteraction(self.cursor, u'm\xe3rk@hbd.com',
                                                ssha)
        goodDict = storage._getUserInteraction(self.cursor, u'm\xe3rk@hbd.com')
        self.assertEqual(goodDict, userDict)

    def test_authUserByNickname(self):
        # Authing a user by their nickname should work, just like an email
        # address in test_authUser.
        storage = DatabaseUserDetailsStorage(None)
        ssha = SSHADigestEncryptor().encrypt('test', self.salt)
        userDict = storage._authUserInteraction(self.cursor, 'sabdfl', ssha)
        self.assertNotEqual({}, userDict)

        # In fact, it should return the same dict as getUser
        goodDict = storage._getUserInteraction(self.cursor, 'sabdfl')
        self.assertEqual(goodDict, userDict)
        
        # And it should be the same as returned by looking them up by email
        # address.
        goodDict = storage._getUserInteraction(self.cursor, 'mark@hbd.com')
        self.assertEqual(goodDict, userDict)

    def test_authUserByNicknameNoEmailAddr(self):
        # Just like test_authUserByNickname, but for a user with no email
        # address.  The result should be the same.
        self.cursor.execute(
            "DELETE FROM EmailAddress WHERE person = 1;"
        )
        storage = DatabaseUserDetailsStorage(None)
        ssha = SSHADigestEncryptor().encrypt('test', self.salt)
        userDict = storage._authUserInteraction(self.cursor, 'sabdfl', ssha)
        self.assertNotEqual({}, userDict)

        # In fact, it should return the same dict as getUser
        goodDict = storage._getUserInteraction(self.cursor, 'sabdfl')
        self.assertEqual(goodDict, userDict)

    def test_authUserBadPassword(self):
        # Authing a real user with the wrong password should return {}
        storage = DatabaseUserDetailsStorage(None)
        ssha = SSHADigestEncryptor().encrypt('wrong', self.salt)
        userDict = storage._authUserInteraction(self.cursor, 'mark@hbd.com',
                                                ssha)
        self.assertEqual({}, userDict)

    def test_getSSHKeys(self):
        # FIXME: there should probably be some SSH keys in the sample data,
        #        so that this test wouldn't need to add some.

        # Add test SSH keys
        self.cursor.execute(
            "INSERT INTO SSHKey (person, keytype, keytext, comment) "
            "VALUES ("
            "  1, "
            "  %d,"
            "  'garbage123',"
            "  'mark@hbd.com')"
            % (dbschema.SSHKeyType.DSA.value, )
        )

        # Add test push mirror access
        self.cursor.execute(
            "INSERT INTO PushMirrorAccess (name, person) "
            "VALUES ("
            "  'marks-archive@example.com',"
            "  1) "
        )

        # Fred's SSH key should have access to freds-archive@example.com
        storage = DatabaseUserDetailsStorage(None)
        keys = storage._getSSHKeysInteraction(self.cursor,
                                              'marks-archive@example.com')
        self.assertEqual([('DSA', 'garbage123')], keys)

        # Fred's SSH key should also have access to an archive with his email
        # address
        keys = storage._getSSHKeysInteraction(self.cursor, 'mark@hbd.com')
        self.assertEqual([('DSA', 'garbage123')], keys)

        # Fred's SSH key should also have access to an archive whose name
        # starts with his email address + '--'.
        keys = storage._getSSHKeysInteraction(self.cursor,
                                              'mark@hbd.com--2005')
        self.assertEqual([('DSA', 'garbage123')], keys)

        # No-one should have access to wilma@hbd.com
        keys = storage._getSSHKeysInteraction(self.cursor, 'wilma@hbd.com')
        self.assertEqual([], keys)

        # Mark should not have access to wilma@hbd.com--2005, even if he has the
        # email address wilma@hbd.com--2005.mark.is.a.hacker.com
        self.cursor.execute(
            "INSERT INTO EmailAddress (person, email, status) "
            "VALUES ("
            "  1, "
            "  'wilma@hbd.com--2005.mark.is.a.hacker.com',"
            "  2)"  # 2 == Validated
        )
        keys = storage._getSSHKeysInteraction(
            self.cursor, 'wilma@mark@hbd.com--2005.mark.is.a.hacker.com'
        )
        self.assertEqual([], keys)
        keys = storage._getSSHKeysInteraction(
            self.cursor, 'wilma@mark@hbd.com--2005.mark.is.a.hacker.com--2005'
        )
        self.assertEqual([], keys)

        # Fred should not have access to archives named after an unvalidated
        # email address of his
        self.cursor.execute(
            "INSERT INTO EmailAddress (person, email, status) "
            "VALUES ("
            "  1, "
            "  'mark@hotmail',"
            "  1)"  # 1 == New (unvalidated)
        )
        keys = storage._getSSHKeysInteraction(self.cursor, 'mark@hotmail')
        self.assertEqual([], keys)

    def test_getUserNoWikiname(self):
        # Ensure that the authserver copes gracefully with users with:
        #    a) no wikinames at all
        #    b) no wikiname for http://www.ubuntulinux.com/wiki/
        # (even though in the long run we want to make sure these situations can
        # never happen, until then the authserver should be robust).
        
        # First, make sure that the sample user has no wikiname.
        self.cursor.execute("""
            DELETE FROM WikiName
            WHERE id = (SELECT id FROM Person
                        WHERE displayname = 'Sample Person')
            """)

        # Get the user dict for Sample Person (test@canonical.com).
        storage = DatabaseUserDetailsStorageV2(None)
        userDict = storage._getUserInteraction(self.cursor,
                                               'test@canonical.com')

        # The user dict has results, even though the wikiname is empty
        self.assertNotEqual({}, userDict)
        self.assertEqual('', userDict['wikiname'])
        self.assertEqual(12, userDict['id'])

        # Now lets add a wikiname, but for a different wiki.
        self.cursor.execute(
            "INSERT INTO WikiName (person, wiki, wikiname) "
            "VALUES (12, 'http://foowiki/', 'SamplePerson')"
        )

        # The authserver should return exactly the same results.
        userDict2 = storage._getUserInteraction(self.cursor,
                                                'test@canonical.com')
        self.assertEqual(userDict, userDict2)
        
    def testTeamDict(self):
        # The user dict from a V2 storage should include a 'teams' element with
        # a list of team dicts, one for each team the user is in, including
        # the user.

        # Get a user dict
        storage = DatabaseUserDetailsStorageV2(None)
        userDict = storage._getUserInteraction(self.cursor, 'mark@hbd.com')

        # Sort the teams by id, they may be returned in any order.
        teams = sorted(userDict['teams'], key=lambda teamDict: teamDict['id'])

        # Mark should be in his own team, Ubuntu Team, Launchpad Administrators
        # and testing Spanish team.
        self.assertEqual(
            [{'displayname': u'Mark Shuttleworth', 'id': 1, 'name': u'sabdfl'},
             {'displayname': u'Ubuntu Team', 'id': 17, 'name': u'ubuntu-team'},
             {'displayname': u'Launchpad Administrators',
              'id': 25, 'name': u'admins'},
             {'displayname': u'testing Spanish team',
              'id': 53, 'name': u'testing-spanish-team'},
             {'displayname': u'Mirror Administrators', 
              'id': 59, 'name': u'ubuntu-mirror-admins'},
             {'displayname': u'Registry Administrators', 'id': 60,
              'name': u'registry'},
            ], teams)

        # The dict returned by authUser should be identical.
        userDict2 = storage._authUserInteraction(self.cursor,
                                                 'mark@hbd.com', 'test')
        self.assertEqual(userDict, userDict2)

    def test_authUserUnconfirmedEmail(self):
        # Unconfirmed email addresses cannot be used to log in.
        storage = DatabaseUserDetailsStorageV2(None)
        ssha = SSHADigestEncryptor().encrypt('supersecret!')
        self.cursor.execute('''
            UPDATE Person SET password = '%s'
            WHERE id = (SELECT person FROM EmailAddress
                        WHERE email = 'justdave@bugzilla.org')'''
            % (ssha,))
        userDict = storage._authUserInteraction(
            self.cursor, 'justdave@bugzilla.org', 'supersecret!')
        self.assertEqual({}, userDict)


class BranchDetailsDatabaseStorageInterfaceTestCase(TestDatabaseSetup):

    def test_verifyInterface(self):
        self.failUnless(verifyObject(IBranchDetailsStorage,
                                     DatabaseBranchDetailsStorage(None)))


class BranchDetailsDatabaseStorageTestCase(TestDatabaseSetup):

    def setUp(self):
        TestDatabaseSetup.setUp(self)
        self.storage = DatabaseBranchDetailsStorage(None)

    def test_getBranchPullQueue(self):
        # Set up the database so the vcs-import branch will appear in the queue.
        self.setSeriesDateLastSynced(3, now_minus='1 second')
        self.setBranchLastMirrorAttempt(14, now_minus='1 day')
        self.connection.commit()

        results = self.storage._getBranchPullQueueInteraction(self.cursor)

        results_dict = dict((row[0], row) for row in results)
        # We verify that a selection of expected branches are included
        # in the results, each triggering a different pull_url algorithm.
        #   a vcs-imports branch:
        self.assertEqual(results_dict[14],
                         (14, 'http://escudero.ubuntu.com:680/0000000e',
                          u'vcs-imports/evolution/main'))
        #   a pull branch:
        self.assertEqual(results_dict[15],
                         (15, 'http://example.com/gnome-terminal/main',
                          u'name12/gnome-terminal/main'))
        #   a hosted SFTP push branch:
        self.assertEqual(results_dict[25],
                         (25, '/tmp/sftp-test/branches/00/00/00/19',
                          u'name12/gnome-terminal/pushed'))

    def test_getBranchPullQueueNoLinkedProduct(self):
        # If a branch doesn't have an associated product the unique name
        # returned should have +junk in the product segment. See
        # Branch.unique_name for precedent.
        self.setSeriesDateLastSynced(3, now_minus='1 second')
        self.setBranchLastMirrorAttempt(14, now_minus='1 day')
        self.connection.commit()

        results = self.storage._getBranchPullQueueInteraction(self.cursor)
        results_dict = dict((row[0], row) for row in results)

        # branch 3 is a branch without a product.
        branch_id, url, unique_name = results_dict[3]
        self.assertEqual(unique_name, 'spiv/+junk/trunk')

    def test_getBranchPullQueueOrdering(self):
        # Test that rows where last_mirror_attempt IS NULL are listed first, and
        # then that rows are ordered so that older last_mirror_attempts are
        # listed earlier.

        # Clear last_mirror_attempt on all rows
        self.cursor.execute("UPDATE Branch SET last_mirror_attempt = NULL")

        # Set last_mirror_attempt on 10 rows, with distinct values.
        for branchID in range(16, 26):
            # The higher the ID, the older the branch, so the earlier it should
            # appear in the queue.
            self.cursor.execute("""
                UPDATE Branch
                SET last_mirror_attempt = (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                                           - interval '%d days')
                WHERE id = %d"""
                % (branchID, branchID))

        # Call getBranchPullQueue
        results = self.storage._getBranchPullQueueInteraction(self.cursor)

        # Get the branch IDs from the results for the branches we modified:
        branches = [row[0] for row in results if row[0] in range(16, 26)]

        # All 10 branches should be in the list in order of descending
        # ID due to the last_mirror_attempt values.
        self.assertEqual(list(reversed(branches)), range(16, 26))

    def test_startMirroring(self):
        # verify that the last mirror time is None before hand.
        self.cursor.execute("""
            SELECT last_mirror_attempt, last_mirrored
                FROM branch WHERE id = 1""")
        row = self.cursor.fetchone()
        self.assertEqual(row[0], None)
        self.assertEqual(row[1], None)

        success = self.storage._startMirroringInteraction(self.cursor, 1)
        self.assertEqual(success, True)

        # verify that last_mirror_attempt is set
        self.cursor.execute("""
            SELECT last_mirror_attempt, last_mirrored
                FROM branch WHERE id = 1""")
        row = self.cursor.fetchone()
        self.assertNotEqual(row[0], None)
        self.assertEqual(row[1], None)

    def test_startMirroring_invalid_branch(self):
        # verify that no branch exists with id == -1
        self.cursor.execute("""
            SELECT id FROM branch WHERE id = -1""")
        self.assertEqual(self.cursor.rowcount, 0)

        success = self.storage._startMirroringInteraction(self.cursor, -11)
        self.assertEqual(success, False)

    def test_mirrorFailed(self):
        self.cursor.execute("""
            SELECT last_mirror_attempt, last_mirrored, mirror_failures,
                mirror_status_message
                FROM branch WHERE id = 1""")
        row = self.cursor.fetchone()
        self.assertEqual(row[0], None)
        self.assertEqual(row[1], None)
        self.assertEqual(row[2], 0)
        self.assertEqual(row[3], None)

        success = self.storage._startMirroringInteraction(self.cursor, 1)
        self.assertEqual(success, True)
        success = self.storage._mirrorFailedInteraction(
            self.cursor, 1, "failed")
        self.assertEqual(success, True)

        self.cursor.execute("""
            SELECT last_mirror_attempt, last_mirrored, mirror_failures,
                mirror_status_message
                FROM branch WHERE id = 1""")
        row = self.cursor.fetchone()
        self.assertNotEqual(row[0], None)
        self.assertEqual(row[1], None)
        self.assertEqual(row[2], 1)
        self.assertEqual(row[3], 'failed')

    def test_mirrorComplete(self):
        self.cursor.execute("""
            SELECT last_mirror_attempt, last_mirrored, mirror_failures
                FROM branch WHERE id = 1""")
        row = self.cursor.fetchone()
        self.assertEqual(row[0], None)
        self.assertEqual(row[1], None)
        self.assertEqual(row[2], 0)

        success = self.storage._startMirroringInteraction(self.cursor, 1)
        self.assertEqual(success, True)
        success = self.storage._mirrorCompleteInteraction(self.cursor, 1, 'rev-1')
        self.assertEqual(success, True)

        self.cursor.execute("""
            SELECT last_mirror_attempt, last_mirrored, mirror_failures,
                   last_mirrored_id
                FROM branch WHERE id = 1""")
        row = self.cursor.fetchone()
        self.assertNotEqual(row[0], None)
        self.assertEqual(row[0], row[1])
        self.assertEqual(row[2], 0)
        self.assertEqual(row[3], 'rev-1')

    def test_mirrorComplete_resets_mirror_request(self):
        # After successfully mirroring a branch, mirror_request_time should be
        # set to NULL.

        # Request that 25 (a hosted branch) be mirrored. This sets
        # mirror_request_time.
        storage = DatabaseUserDetailsStorageV2(None)
        storage._requestMirrorInteraction(self.cursor, 25)

        # Simulate successfully mirroring branch 25
        self.storage._startMirroringInteraction(self.cursor, 25)
        self.storage._mirrorCompleteInteraction(self.cursor, 25, 'rev-1')

        self.assertEqual(None, self.getMirrorRequestTime(25))

    def test_mirrorFailed_resets_mirror_request(self):
        # After failing to mirror a branch, mirror_request_time for that branch
        # should be set to NULL.

        # Request that 25 (a hosted branch) be mirrored. This sets
        # mirror_request_time.
        storage = DatabaseUserDetailsStorageV2(None)
        storage._requestMirrorInteraction(self.cursor, 25)

        # Simulate successfully mirroring branch 25
        self.storage._startMirroringInteraction(self.cursor, 25)
        self.storage._mirrorFailedInteraction(self.cursor, 25, 'failed')

        self.assertEqual(None, self.getMirrorRequestTime(25))

    def test_mirrorComplete_resets_failure_count(self):
        # this increments the failure count ...
        self.test_mirrorFailed()

        success = self.storage._startMirroringInteraction(self.cursor, 1)
        self.assertEqual(success, True)
        success = self.storage._mirrorCompleteInteraction(
            self.cursor, 1, 'rev-1')
        self.assertEqual(success, True)

        self.cursor.execute("""
            SELECT last_mirror_attempt, last_mirrored, mirror_failures
                FROM branch WHERE id = 1""")
        row = self.cursor.fetchone()
        self.assertNotEqual(row[0], None)
        self.assertEqual(row[0], row[1])
        self.assertEqual(row[2], 0)

    def test_unrequested_hosted_branches(self):
        # Hosted branches that haven't had a mirror requested should NOT be
        # included in the branch queue

        # Branch 25 is a hosted branch.
        # Double check that its mirror_request_time is NULL. The sample data
        # should guarantee this.
        self.assertEqual(None, self.getMirrorRequestTime(25))

        # Mark 25 as recently mirrored.
        self.storage._startMirroringInteraction(self.cursor, 25)
        self.storage._mirrorCompleteInteraction(self.cursor, 25, 'rev-1')

        self.failIf(self.isBranchInPullQueue(25),
                    "Shouldn't be in queue until mirror requested")

    def test_requested_hosted_branches(self):
        # Hosted branches that HAVE had a mirror requested should be in
        # the branch queue

        # Mark 25 (a hosted branch) as recently mirrored.
        self.storage._startMirroringInteraction(self.cursor, 25)
        self.storage._mirrorCompleteInteraction(self.cursor, 25, 'rev-1')

        # Request a mirror
        storage = DatabaseUserDetailsStorageV2(None)
        storage._requestMirrorInteraction(self.cursor, 25)

        self.failUnless(self.isBranchInPullQueue(25), "Should be in queue")

    def test_mirror_stale_hosted_branches(self):
        # Hosted branches which haven't been mirrored for a whole day should be
        # mirrored even if they haven't asked for it.

        # Branch 25 is a hosted branch, hasn't been mirrored for over 1 day
        # and has not had a mirror requested
        self.failUnless(self.isBranchInPullQueue(25))

        # Mark 25 as recently mirrored.
        self.storage._startMirroringInteraction(self.cursor, 25)
        self.storage._mirrorCompleteInteraction(self.cursor, 25, 'rev-1')

        # 25 should only be in the pull queue if a mirror has been requested
        self.failIf(self.isBranchInPullQueue(25),
                    "hosted branch no longer in pull list")

    def getMirrorRequestTime(self, branch_id):
        """Return the value of mirror_request_time for the branch with the
        given id.

        :param branch_id: The id of a row in the Branch table. An int.
        :return: A timestamp or None.
        """
        self.cursor.execute(
            "SELECT mirror_request_time FROM branch WHERE id = %s"
            % sqlvalues(branch_id))
        return self.cursor.fetchone()[0]

    def isBranchInPullQueue(self, branch_id):
        """Whether the branch with this id is present in the pull queue."""
        results = self.storage._getBranchPullQueueInteraction(self.cursor)
        return branch_id in (
            result_branch_id
            for result_branch_id, result_pull_url, unique_name in results)

    def setSeriesDateLastSynced(self, series_id, value=None, now_minus=None):
        """Helper to set the datelastsynced of a ProductSeries.

        :param series_id: Database id of the ProductSeries to update.
        :param value: SQL expression to set datelastsynced to.
        :param now_minus: shorthand to set a value before the current time.
        """
        # Exactly one of value or now_minus must be set.
        assert int(value is None) + int(now_minus is None) == 1
        if now_minus is not None:
            value = ("CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - interval '%s'"
                     % now_minus)
        self.cursor.execute(
            "UPDATE ProductSeries SET datelastsynced = (%s) WHERE id = %d"
            % (value, series_id))

    def setBranchLastMirrorAttempt(self, branch_id, value=None, now_minus=None):
        """Helper to set the last_mirror_attempt of a Branch.

        :param branch_id: Database id of the Branch to update.
        :param value: SQL expression to set last_mirror_attempt to.
        :param now_minus: shorthand to set a value before the current time.
        """
        # Exactly one of value or now_minus must be set.
        assert int(value is None) + int(now_minus is None) == 1
        if now_minus is not None:
            value = ("CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - interval '%s'"
                     % now_minus)
        self.cursor.execute(
            "UPDATE Branch SET last_mirror_attempt = (%s) WHERE id = %d"
            % (value, branch_id))

    def test_import_branches_only_listed_when_due(self):
        # Import branches (branches owned by vcs-imports) are only listed when
        # they are due for remirroring, i.e. when they have been successfully
        # synced since the last mirroring attempt.

        # Mirroring should normally never fail, but we still use the mirroring
        # attempt value so in case of an internal network failure, the system
        # does not get saturated with repeated failures to mirror import
        # branches.

        # Branch 14 is an imported branch.
        # It is attached to the import in ProductSeries 3.
        self.cursor.execute("""
            SELECT Person.name, ProductSeries.id FROM Branch
            JOIN Person ON Branch.owner = Person.id
            JOIN ProductSeries ON Branch.id = ProductSeries.import_branch
            WHERE Branch.id = 14""")
        rows = self.cursor.fetchall()
        self.assertEqual(1, len(rows))
        [[owner_name, series_id]] = rows
        self.assertEqual('vcs-imports', owner_name)
        self.assertEqual(3, series_id)

        # Mark ProductSeries 3 as never successfully synced, and branch 14 as
        # never mirrored.
        self.setSeriesDateLastSynced(3, 'NULL')
        self.setBranchLastMirrorAttempt(14, 'NULL')
        self.connection.commit()

        # Since the import was never successful, the branch should not be in
        # the pull queue.
        self.failIf(self.isBranchInPullQueue(14),
            "incomplete import branch in pull queue.")

        # Mark ProductSeries 3 as just synced, and branch 14 as never mirrored.
        self.setSeriesDateLastSynced(3, now_minus='1 second')
        self.setBranchLastMirrorAttempt(14, 'NULL')
        self.connection.commit()

        # We have a new import! We must mirror it as soon as possible.
        self.failUnless(self.isBranchInPullQueue(14),
            "new import branch not in pull queue.")

        # Mark ProductSeries 3 as synced, and branch 14 as more recently
        # mirrored. Use a last_mirror_attempt older than a day to make sure
        # that we are no exercising the 'one mirror per day' logic.
        self.setSeriesDateLastSynced(3, now_minus='1 day 15 minutes')
        self.setBranchLastMirrorAttempt(14, now_minus='1 day 10 minutes')
        self.connection.commit()

        # Since the the import was not successfully synced since the last
        # mirror, we do not have anything new to mirror.
        self.failIf(self.isBranchInPullQueue(14),
            "not recently synced import branch in pull queue.")

        # Mark ProductSeries 3 as synced recently, and branch 13 as last
        # mirrored before this sync.
        self.setSeriesDateLastSynced(3, now_minus='1 second')
        self.setBranchLastMirrorAttempt(14, now_minus='1 day')
        self.connection.commit()

        # The import was updated since the last mirror attempt. There might be
        # new revisions to mirror.
        self.failUnless(self.isBranchInPullQueue(14),
            "recently synced import branch not in pull queue.")

        # During the transition period where the branch puller is aware of
        # series.datelastynced, but importd does not yet record it, we will
        # have NULL datelastsynced, and non-null last_mirror_attempt for
        # existing imports. In those cases, we fall back to the old logic of
        # mirroring once a day.

        # Set a NULL datelastsynced in ProductSeries 3, and mark Branch 14 as
        # mirrored more than 1 day ago.
        self.setSeriesDateLastSynced(3, 'NULL')
        self.setBranchLastMirrorAttempt(14, now_minus='1 day 1 minute')
        self.connection.commit()
        self.failUnless(self.isBranchInPullQueue(14),
            "import branch last mirrored >1 day ago not in pull queue.")

        # Set a NULL datelastsynced in ProductSeries 3, and mark Branch 14 as
        # mirrored recently.
        self.setSeriesDateLastSynced(3, 'NULL')
        self.setBranchLastMirrorAttempt(14, now_minus='5 minutes')
        self.connection.commit()
        self.failIf(self.isBranchInPullQueue(14),
            "import branch mirrored <1 day ago in pull queue.")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

