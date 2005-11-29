# Note: these test cases requires the Launchpad sample data.  Run
#   make launchpad_test
# in $launchpad_root/database/schema.

import unittest

import psycopg

from zope.interface.verify import verifyObject

from twisted.enterprise import adbapi

from canonical.launchpad.webapp.authentication import SSHADigestEncryptor

from canonical.authserver.database import (
    DatabaseUserDetailsStorage, DatabaseUserDetailsStorageV2,
    IUserDetailsStorage)
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


class ExtraUserDatabaseStorageTestCase(TestDatabaseSetup):
    # Tests that do some database writes (but makes sure to roll them back)
    def setUp(self):
        TestDatabaseSetup.setUp(self)
        # This is the salt for Mark's password in the sample data.
        self.salt = '\xf4;\x15a\xe4W\x1f'

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

    def test_createUser(self):
        # Creating a user should return a user dict with that user's details
        storage = DatabaseUserDetailsStorage(None)
        ssha = SSHADigestEncryptor().encrypt('supersecret!')
        displayname = 'Testy the Test User'
        emailaddresses = ['test1@test.test', 'test2@test.test']
        # This test needs a real Transaction, because it calls rollback
        trans = adbapi.Transaction(None, self.connection)
        userDict = storage._createUserInteraction(
            trans, ssha, displayname, emailaddresses
        )
        self.assertNotEqual({}, userDict)
        self.assertEqual(displayname, userDict['displayname'])
        self.assertEqual(emailaddresses, userDict['emailaddresses'])
        self.assertEqual('TestyTheTestUser', userDict['wikiname'])

    def test_createUserUnicode(self):
        # Creating a user should return a user dict with that user's details
        storage = DatabaseUserDetailsStorage(None)
        ssha = SSHADigestEncryptor().encrypt('supersecret!')
        # Name with an e acute, and an apostrophe too.
        displayname = u'Test\xc3\xa9 the Test\' User'
        emailaddresses = ['test1@test.test', 'test2@test.test']
        # This test needs a real Transaction, because it calls rollback
        trans = adbapi.Transaction(None, self.connection)
        userDict = storage._createUserInteraction(
            trans, ssha, displayname, emailaddresses
        )
        self.assertNotEqual({}, userDict)
        self.assertEqual(displayname, userDict['displayname'])
        self.assertEqual(emailaddresses, userDict['emailaddresses'])

        # Check that the nickname was correctly generated (and that getUser
        # returns the same values that createUser returned)
        userDict2 = storage._getUserInteraction(self.cursor, 'test1')
        self.assertEqual(userDict, userDict2)

    # FIXME: behaviour of this case isn't defined yet
    ##def test_createUserFailure(self):
    ##    # Creating a user with a loginID that already exists should fail

    def test_changePassword(self):
        storage = DatabaseUserDetailsStorage(None)
        # Changing a password should return a user dict with that user's details
        ssha = SSHADigestEncryptor().encrypt('test', self.salt)
        newSsha = SSHADigestEncryptor().encrypt('testing123')
        userDict = storage._changePasswordInteraction(self.cursor,
                                                      'mark@hbd.com', ssha,
                                                      newSsha)
        self.assertNotEqual({}, userDict)

        # In fact, it should return the same dict as getUser
        goodDict = storage._getUserInteraction(self.cursor, 'mark@hbd.com')
        self.assertEqual(goodDict, userDict)

        # And we should be able to authenticate with the new password...
        authDict = storage._authUserInteraction(self.cursor, 'mark@hbd.com',
                                                newSsha)
        self.assertEqual(goodDict, authDict)

        # ...but not the old
        authDict = storage._authUserInteraction(self.cursor, 'mark@hbd.com',
                                                ssha)
        self.assertEqual({}, authDict)

    def test_changePasswordFailure(self):
        storage = DatabaseUserDetailsStorage(None)
        # Changing a password without giving the right current pw should fail
        # (i.e. return {})
        ssha = SSHADigestEncryptor().encrypt('WRONG', self.salt)
        newSsha = SSHADigestEncryptor().encrypt('testing123')
        userDict = storage._changePasswordInteraction(self.cursor,
                                                      'mark@hbd.com', ssha,
                                                      newSsha)
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
             {'displayname': u'Ubuntu Team', 'id': 17, 'name': u'name17'},
             {'displayname': u'Launchpad Administrators',
              'id': 25,
              'name': u'admins'},
             {'displayname': u'testing Spanish team',
              'id': 53,
              'name': u'testing-spanish-team'},],
            teams
        )

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


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DatabaseStorageTestCase))
    suite.addTest(unittest.makeSuite(ExtraUserDatabaseStorageTestCase))
    return suite

