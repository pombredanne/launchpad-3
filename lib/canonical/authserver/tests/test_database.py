# Copyright 2006-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0141

"""Tests for lib/canonical/authserver/database.py"""

__metaclass__ = type

import unittest

import pytz
import transaction

from zope.component import getUtility
from zope.interface.verify import verifyObject
from zope.security.management import getSecurityPolicy, setSecurityPolicy

from bzrlib.tests import TestCase

from canonical.database.sqlbase import cursor, sqlvalues

from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.database.person import Person
from canonical.launchpad.interfaces.authserver import IAuthServer
from canonical.launchpad.interfaces.emailaddress import (
    EmailAddressStatus, IEmailAddressSet)
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.webapp.authentication import SSHADigestEncryptor
from canonical.launchpad.webapp.authorization import LaunchpadSecurityPolicy
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, MASTER_FLAVOR)

from canonical.authserver.interfaces import IUserDetailsStorage
from canonical.authserver.database import (
    DatabaseUserDetailsStorage, DatabaseUserDetailsStorageV2,
    read_only_transaction)

from canonical.testing.layers import LaunchpadScriptLayer


UTC = pytz.timezone('UTC')


class DatabaseTest(TestCase):
    """Base class for authserver database tests.

    Runs the tests in using the web database adapter and the stricter Launchpad
    security model. Provides a `cursor` instance variable for ad-hoc queries.
    """

    layer = LaunchpadScriptLayer

    def setUp(self):
        LaunchpadScriptLayer.switchDbConfig('authserver')
        super(DatabaseTest, self).setUp()
        self._old_policy = getSecurityPolicy()
        setSecurityPolicy(LaunchpadSecurityPolicy)
        self.cursor = cursor()

    def tearDown(self):
        setSecurityPolicy(self._old_policy)
        super(DatabaseTest, self).tearDown()


class UserDetailsStorageTest(DatabaseTest):

    def setUp(self):
        super(UserDetailsStorageTest, self).setUp()
        self.salt = '\xf4;\x15a\xe4W\x1f'

    def test_verifyInterface(self):
        self.failUnless(verifyObject(IUserDetailsStorage,
                                     DatabaseUserDetailsStorage(None)))
        self.failUnless(
            verifyObject(IAuthServer, DatabaseUserDetailsStorageV2(None)))

    def test_getUser(self):
        # Getting a user should return a valid dictionary of details
        storage = DatabaseUserDetailsStorage(None)
        userDict = storage._getUserInteraction('mark@hbd.com')
        self.assertEqual('Mark Shuttleworth', userDict['displayname'])
        self.assertEqual(['mark@hbd.com'], userDict['emailaddresses'])
        self.failUnless(userDict.has_key('salt'))

        # Getting by ID should give the same result as getting by email
        userDict2 = storage._getUserInteraction(userDict['id'])
        self.assertEqual(userDict, userDict2)

        # Getting by nickname should also give the same result
        userDict3 = storage._getUserInteraction('sabdfl')
        self.assertEqual(userDict, userDict3)

    def test_getUserMissing(self):
        # Getting a non-existent user should return {}
        storage = DatabaseUserDetailsStorage(None)
        userDict = storage._getUserInteraction('noone@fake.email')
        self.assertEqual({}, userDict)

        # Ditto for getting a non-existent user by id :)
        userDict = storage._getUserInteraction(9999)
        self.assertEqual({}, userDict)

    def test_getUserMultipleAddresses(self):
        # Getting a user with multiple addresses should return all the
        # confirmed addresses.
        storage = DatabaseUserDetailsStorage(None)
        userDict = storage._getUserInteraction('stuart.bishop@canonical.com')
        self.assertEqual('Stuart Bishop', userDict['displayname'])
        self.assertEqual(
            set(['stuart.bishop@canonical.com', 'stuart@stuartbishop.net']),
            set(userDict['emailaddresses']))

    def test_noUnconfirmedAddresses(self):
        # Unconfirmed addresses should not be returned, so if we add a NEW
        # address, it won't change the result.
        storage = DatabaseUserDetailsStorage(None)
        userDict = storage._getUserInteraction('stuart.bishop@canonical.com')

        transaction.begin()
        login(ANONYMOUS)
        stub = getUtility(IPersonSet).getByName('stub')
        email_set = getUtility(IEmailAddressSet)
        email = email_set.new('sb@example.com', stub, EmailAddressStatus.NEW)
        logout()
        transaction.commit()

        userDict2 = storage._getUserInteraction('stuart.bishop@canonical.com')
        self.assertEqual(userDict, userDict2)

    def test_preferredEmailFirst(self):
        # If there's a PREFERRED address, it should be first in the
        # emailaddresses list.  Let's make stuart@stuartbishop.net PREFERRED
        # rather than stuart.bishop@canonical.com.
        transaction.begin()
        email_set = getUtility(IEmailAddressSet)

        email = email_set.getByEmail('stuart.bishop@canonical.com')
        email.status = EmailAddressStatus.VALIDATED
        email.syncUpdate()

        email = email_set.getByEmail('stuart@stuartbishop.net')
        email.status = EmailAddressStatus.PREFERRED
        email.syncUpdate()
        transaction.commit()

        storage = DatabaseUserDetailsStorage(None)
        userDict = storage._getUserInteraction('stuart.bishop@canonical.com')
        self.assertEqual(
            ['stuart@stuartbishop.net', 'stuart.bishop@canonical.com'],
            userDict['emailaddresses'])

    def test_emailAlphabeticallySorted(self):
        # Although the preferred email address is first in the emailaddresses
        # list, the rest are alphabetically sorted.
        transaction.begin()
        stub = getUtility(IPersonSet).getByName('stub')
        email_set = getUtility(IEmailAddressSet)
        # Use a silly email address that is going to appear before all others
        # in alphabetical sorting.
        email = email_set.new(
            '_stub@canonical.com', stub, EmailAddressStatus.VALIDATED)
        transaction.commit()

        storage = DatabaseUserDetailsStorage(None)
        userDict = storage._getUserInteraction('stub')
        self.assertEqual(
            ['stuart.bishop@canonical.com', '_stub@canonical.com',
             'stuart@stuartbishop.net'],
            userDict['emailaddresses'])

    def test_authUserNoUser(self):
        # Authing a user that doesn't exist should return {}
        storage = DatabaseUserDetailsStorage(None)
        ssha = SSHADigestEncryptor().encrypt('supersecret!')
        userDict = storage._authUserInteraction('noone@fake.email', ssha)
        self.assertEqual({}, userDict)

    def test_authUserNullPassword(self):
        # Authing a user with a NULL password should always return {}
        storage = DatabaseUserDetailsStorage(None)
        ssha = SSHADigestEncryptor().encrypt('supersecret!')
        # The 'admins' user in the sample data has no password, so we use
        # that.
        userDict = storage._authUserInteraction('admins', ssha)
        self.assertEqual({}, userDict)

    def test_authUserUnconfirmedEmail(self):
        # Unconfirmed email addresses cannot be used to log in.
        storage = DatabaseUserDetailsStorage(None)
        ssha = SSHADigestEncryptor().encrypt('supersecret!')
        self.cursor.execute("""
            INSERT INTO AccountPassword (account, password)
            VALUES (
                (SELECT account FROM EmailAddress
                WHERE email='matsubara@async.com.br'), %s
                )
            """ % sqlvalues(ssha))
        userDict = storage._authUserInteraction('matsubara@async.com.br', ssha)
        self.assertEqual({}, userDict)

    def test_authUser(self):
        # Authenticating a user with the right password should work
        storage = DatabaseUserDetailsStorage(None)
        ssha = SSHADigestEncryptor().encrypt('test', self.salt)
        userDict = storage._authUserInteraction('mark@hbd.com', ssha)
        self.assertNotEqual({}, userDict)

        # In fact, it should return the same dict as getUser
        goodDict = storage._getUserInteraction('mark@hbd.com')
        self.assertEqual(goodDict, userDict)

        # Unicode email addresses are handled too.
        cur = cursor()
        cur.execute(
            "INSERT INTO EmailAddress (person, email, status) "
            "VALUES (1, %s, 2)"  # 2 == Validated
            % sqlvalues(u'm\xe3rk@hbd.com'))
        transaction.commit()
        userDict = storage._authUserInteraction(u'm\xe3rk@hbd.com', ssha)
        goodDict = storage._getUserInteraction(u'm\xe3rk@hbd.com')
        self.assertEqual(goodDict, userDict)

    def test_authUserByNickname(self):
        # Authing a user by their nickname should work, just like an email
        # address in test_authUser.
        storage = DatabaseUserDetailsStorage(None)
        ssha = SSHADigestEncryptor().encrypt('test', self.salt)
        userDict = storage._authUserInteraction('sabdfl', ssha)
        self.assertNotEqual({}, userDict)

        # In fact, it should return the same dict as getUser
        goodDict = storage._getUserInteraction('sabdfl')
        self.assertEqual(goodDict, userDict)

        # And it should be the same as returned by looking them up by email
        # address.
        goodDict = storage._getUserInteraction('mark@hbd.com')
        self.assertEqual(goodDict, userDict)

    def test_authUserByNicknameNoEmailAddr(self):
        # Just like test_authUserByNickname, but for a user with no email
        # address.  The result should be the same.

        # The authserver isn't allowed to delete email addresses.
        LaunchpadScriptLayer.switchDbConfig('launchpad')
        self.cursor = cursor()
        self.cursor.execute(
            "DELETE FROM EmailAddress WHERE person = 1;"
        )
        LaunchpadScriptLayer.switchDbConfig('authserver')

        storage = DatabaseUserDetailsStorage(None)
        ssha = SSHADigestEncryptor().encrypt('test', self.salt)
        userDict = storage._authUserInteraction('sabdfl', ssha)
        self.assertNotEqual({}, userDict)

        # In fact, it should return the same dict as getUser
        goodDict = storage._getUserInteraction('sabdfl')
        self.assertEqual(goodDict, userDict)

    def test_authUserBadPassword(self):
        # Authing a real user with the wrong password should return {}
        storage = DatabaseUserDetailsStorage(None)
        ssha = SSHADigestEncryptor().encrypt('wrong', self.salt)
        userDict = storage._authUserInteraction('mark@hbd.com', ssha)
        self.assertEqual({}, userDict)

    def test_getSSHKeys_empty(self):
        # getSSHKeys returns an empty list for users without SSH keys.
        storage = DatabaseUserDetailsStorage(None)
        keys = storage._getSSHKeysInteraction('no-priv')
        self.assertEqual([], keys)

    def test_getSSHKeys_no_such_user(self):
        storage = DatabaseUserDetailsStorage(None)
        keys = storage._getSSHKeysInteraction('no-such-user')
        self.assertEqual([], keys)

    def test_getSSHKeys(self):
        # getSSHKeys returns a list of keytype, keytext tuples for users with
        # SSH keys.

        self.cursor.execute("""
            SELECT keytext FROM SSHKey
            JOIN Person ON (SSHKey.person = Person.id)
            WHERE Person.name = 'sabdfl'
            """)
        expected_keytext = self.cursor.fetchone()[0]

        storage = DatabaseUserDetailsStorage(None)
        keytype, keytext = storage._getSSHKeysInteraction('sabdfl')[0]
        self.assertEqual('DSA', keytype)
        self.assertEqual(expected_keytext, keytext)


class TestTransactionDecorators(DatabaseTest):
    """Tests for the transaction decorators used by the authserver."""

    def setUp(self):
        super(TestTransactionDecorators, self).setUp()
        self.store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        self.no_priv = self.store.find(Person, name='no-priv').one()

    def test_read_only_transaction_reset_store(self):
        """Make sure that the store is reset after the transaction."""
        @read_only_transaction
        def no_op():
            pass
        no_op()
        self.failIf(
            self.no_priv is self.store.find(Person, name='no-priv').one(),
            "Store wasn't reset properly.")


class UserDetailsStorageV2Test(DatabaseTest):
    """Test the implementation of `IAuthServer`."""

    def test_teamDict(self):
        # The user dict from a V2 storage should include a 'teams' element
        # with a list of team dicts, one for each team the user is in,
        # including the user.

        # Get a user dict
        storage = DatabaseUserDetailsStorageV2(None)
        userDict = storage._getUserInteraction('mark@hbd.com')

        # Sort the teams by id, they may be returned in any order.
        teams = sorted(userDict['teams'], key=lambda teamDict: teamDict['id'])

        # Mark should be in his own team, Ubuntu Team, Launchpad
        # Administrators and testing Spanish team, and other teams of which
        # Launchpad Administrators is a member or owner.
        self.assertEqual(
            [{'displayname': u'Mark Shuttleworth',
              'id': 1, 'name': u'sabdfl'},
             {'displayname': u'Ubuntu Team',
              'id': 17, 'name': u'ubuntu-team'},
             {'displayname': u'Launchpad Administrators',
              'id': 25, 'name': u'admins'},
             {'displayname': u'testing Spanish team',
              'id': 53, 'name': u'testing-spanish-team'},
             {'displayname': u'Mirror Administrators',
              'id': 59, 'name': u'ubuntu-mirror-admins'},
             {'displayname': u'Registry Administrators', 'id': 60,
              'name': u'registry'},
             {'displayname': u'Mailing List Experts',
              'name': u'mailing-list-experts', 'id': 243607},
            ], teams)

        # The dict returned by authUser should be identical.
        userDict2 = storage._authUserInteraction('mark@hbd.com', 'test')
        self.assertEqual(userDict, userDict2)

    def test_authUserUnconfirmedEmail(self):
        # Unconfirmed email addresses cannot be used to log in.
        storage = DatabaseUserDetailsStorageV2(None)
        ssha = SSHADigestEncryptor().encrypt('supersecret!')
        self.cursor.execute("""
            INSERT INTO AccountPassword (account, password)
            VALUES (
                (SELECT account FROM EmailAddress
                WHERE email = 'matsubara@async.com.br'), %s
                )
            """, (ssha,))
        userDict = storage._authUserInteraction(
            'matsubara@async.com.br', 'supersecret!')
        self.assertEqual({}, userDict)

    def test_nameInV2UserDict(self):
        # V2 user dicts should have a 'name' field.
        storage = DatabaseUserDetailsStorageV2(None)
        userDict = storage._getUserInteraction('mark@hbd.com')
        self.assertEqual('sabdfl', userDict['name'])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

