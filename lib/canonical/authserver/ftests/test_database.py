# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

"""Tests for lib/canonical/authserver/database.py"""

__metaclass__ = type

import unittest
import datetime

import pytz
import transaction
from zope.component import getUtility
from zope.interface.verify import verifyObject
from zope.security.management import getSecurityPolicy, setSecurityPolicy
from zope.security.simplepolicies import PermissiveSecurityPolicy

from canonical.database.sqlbase import cursor, sqlvalues

from canonical.launchpad.ftests import login, logout, ANONYMOUS
from canonical.launchpad.interfaces import (
    IBranchSet, IEmailAddressSet, IPersonSet, IWikiNameSet)
from canonical.launchpad.webapp.authentication import SSHADigestEncryptor
from canonical.launchpad.webapp.authorization import LaunchpadSecurityPolicy

from canonical.authserver.interfaces import (
    IBranchDetailsStorage, IHostedBranchStorage, IUserDetailsStorage,
    IUserDetailsStorageV2, READ_ONLY, WRITABLE)
from canonical.authserver.database import (
    DatabaseUserDetailsStorage, DatabaseUserDetailsStorageV2,
    DatabaseBranchDetailsStorage)
from canonical.lp import dbschema

from canonical.launchpad.ftests.harness import LaunchpadTestCase

from canonical.testing.layers import LaunchpadScriptLayer


UTC = pytz.timezone('UTC')


class TestDatabaseSetup(LaunchpadTestCase):

    def setUp(self):
        super(TestDatabaseSetup, self).setUp()
        self.connection = self.connect()
        self.cursor = self.connection.cursor()

    def tearDown(self):
        self.cursor.close()
        self.connection.close()
        super(TestDatabaseSetup, self).tearDown()


class DatabaseStorageTestCase(unittest.TestCase):

    layer = LaunchpadScriptLayer

    def setUp(self):
        LaunchpadScriptLayer.switchDbConfig('authserver')
        super(DatabaseStorageTestCase, self).setUp()
        self.cursor = cursor()

    def tearDown(self):
        self.cursor.close()
        super(DatabaseStorageTestCase, self).tearDown()

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
        userDict = storage._getUserInteraction('mark@hbd.com')
        self.assertEqual('Mark Shuttleworth', userDict['displayname'])
        self.assertEqual(['mark@hbd.com'], userDict['emailaddresses'])
        self.assertEqual('MarkShuttleworth', userDict['wikiname'])
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
        self.assertEqual(['stuart.bishop@canonical.com',
                          'stuart@stuartbishop.net'],
                         userDict['emailaddresses'])

    def test_noUnconfirmedAddresses(self):
        # Unconfirmed addresses should not be returned, so if we add a NEW
        # address, it won't change the result.
        storage = DatabaseUserDetailsStorage(None)
        userDict = storage._getUserInteraction('stuart.bishop@canonical.com')
        self.cursor.execute('''
            INSERT INTO EmailAddress (email, person, status)
            VALUES ('sb@example.com', %d, %d)
            ''' % (userDict['id'], dbschema.EmailAddressStatus.NEW.value))
        userDict2 = storage._getUserInteraction('stuart.bishop@canonical.com')
        self.assertEqual(userDict, userDict2)

    def test_preferredEmailFirst(self):
        # If there's a PREFERRED address, it should be first in the
        # emailaddresses list.  Let's make stuart@stuartbishop.net PREFERRED
        # rather than stuart.bishop@canonical.com.
        transaction.begin()
        email_set = getUtility(IEmailAddressSet)

        email = email_set.getByEmail('stuart.bishop@canonical.com')
        email.status = dbschema.EmailAddressStatus.VALIDATED
        email.syncUpdate()

        email = email_set.getByEmail('stuart@stuartbishop.net')
        email.status = dbschema.EmailAddressStatus.PREFERRED
        email.syncUpdate()
        transaction.commit()

        storage = DatabaseUserDetailsStorage(None)
        userDict = storage._getUserInteraction('stuart.bishop@canonical.com')
        self.assertEqual(
            ['stuart@stuartbishop.net', 'stuart.bishop@canonical.com'],
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
        # The 'admins' user in the sample data has no password, so we use that.
        userDict = storage._authUserInteraction('admins', ssha)
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
        userDict = storage._authUserInteraction('justdave@bugzilla.org', ssha)
        self.assertEqual({}, userDict)

    def test_nameInV2UserDict(self):
        # V2 user dicts should have a 'name' field.
        storage = DatabaseUserDetailsStorageV2(None)
        userDict = storage._getUserInteraction('mark@hbd.com')
        self.assertEqual('sabdfl', userDict['name'])


class NewDatabaseStorageTestCase(unittest.TestCase):
    # Tests that call database methods that use the new-style database
    # connection infrastructure.

    layer = LaunchpadScriptLayer

    def setUp(self):
        LaunchpadScriptLayer.switchDbConfig('authserver')
        super(NewDatabaseStorageTestCase, self).setUp()
        self._old_policy = getSecurityPolicy()
        setSecurityPolicy(LaunchpadSecurityPolicy)

    def tearDown(self):
        setSecurityPolicy(self._old_policy)
        super(NewDatabaseStorageTestCase, self).tearDown()

    def _getTime(self, row_id):
        cur = cursor()
        cur.execute("""
            SELECT mirror_request_time FROM Branch
            WHERE id = %d""" % row_id)
        [mirror_request_time] = cur.fetchone()
        return mirror_request_time

    def isBranchInPullQueue(self, branch_id):
        """Whether the branch with this id is present in the pull queue."""
        storage = DatabaseBranchDetailsStorage(None)
        results = storage._getBranchPullQueueInteraction()
        return branch_id in (
            result_branch_id
            for result_branch_id, result_pull_url, unique_name in results)

    def test_createBranch(self):
        storage = DatabaseUserDetailsStorageV2(None)
        branchID = storage._createBranchInteraction(
            12, 'name12', 'firefox', 'foo')
        # Assert branchID now appears in database.  Note that title and summary
        # should be NULL, and author should be set to the owner.
        cur = cursor()
        cur.execute("""
            SELECT Person.name, Product.name, Branch.name, Branch.title,
                Branch.summary, Branch.author
            FROM Branch, Person, Product
            WHERE Branch.id = %d
            AND Person.id = Branch.owner
            AND Product.id = Branch.product
            """
            % branchID)
        self.assertEqual(
            ['name12', 'firefox', 'foo', None, None, 12], cur.fetchone())

    def test_createBranch_junk(self):
        # Create a branch with NULL product too:
        storage = DatabaseUserDetailsStorageV2(None)
        branchID = storage._createBranchInteraction(
            1, 'sabdfl', '+junk', 'foo')
        cur = cursor()
        cur.execute("""
            SELECT Person.name, Branch.product, Branch.name, Branch.title,
                Branch.summary, Branch.author
            FROM Branch, Person
            WHERE Branch.id = %d
            AND Person.id = Branch.owner
            """
            % branchID)
        self.assertEqual(
            ['sabdfl', None, 'foo', None, None, 1], cur.fetchone())

    def test_fetchProductID(self):
        storage = DatabaseUserDetailsStorageV2(None)
        productID = storage._fetchProductIDInteraction('firefox')
        self.assertEqual(4, productID)

        # Invalid product names are signalled by a return value of ''
        productID = storage._fetchProductIDInteraction('xxxxx')
        self.assertEqual('', productID)

    def test_getBranchesForUser(self):
        # getBranchesForUser returns all of the hosted branches that a user may
        # write to. The branches are grouped by product, and are specified by
        # name and id. The name and id of the products are also included.
        storage = DatabaseUserDetailsStorageV2(None)
        fetched_branches = storage._getBranchesForUserInteraction(12)

        # Flatten the structured return value of getBranchesForUser so that we
        # can easily compare it to the data from our SQLObject methods.
        flattened = []
        for user_id, branches_by_product in fetched_branches:
            for (product_id, product_name), branches in branches_by_product:
                for branch_id, branch_name in branches:
                    flattened.append(
                        (user_id, product_id, product_name, branch_id,
                         branch_name))

        # Get the hosted branches for user 12 from SQLObject classes.
        login(ANONYMOUS)
        try:
            person = getUtility(IPersonSet).get(12)
            login(person.preferredemail.email)
            expected_branches = getUtility(
                IBranchSet).getHostedBranchesForPerson(person)
            expected_branches = [
                (branch.owner.id, branch.product.id, branch.product.name,
                 branch.id, branch.name)
                for branch in expected_branches]
        finally:
            logout()

        self.assertEqual(set(expected_branches), set(flattened))

    def test_getBranchesForUserNullProduct(self):
        # getBranchesForUser returns branches for hosted branches with no
        # product.
        login(ANONYMOUS)
        try:
            person = getUtility(IPersonSet).get(12)
            login_email = person.preferredemail.email
        finally:
            logout()

        transaction.begin()
        login(login_email)
        try:
            branch = getUtility(IBranchSet).new(
                dbschema.BranchType.HOSTED, 'foo-branch', person, person,
                None, None, None)
        finally:
            logout()
            transaction.commit()

        storage = DatabaseUserDetailsStorageV2(None)
        branchInfo = storage._getBranchesForUserInteraction(12)

        for person_id, by_product in branchInfo:
            if person_id == 12:
                for (product_id, product_name), branches in by_product:
                    if product_id == '':
                        self.assertEqual('', product_name)
                        self.assertEqual(1, len(branches))
                        branch_id, branch_name = branches[0]
                        self.assertEqual('foo-branch', branch_name)
                        break
                else:
                    self.fail("Couldn't find +junk branch")
                break
        else:
            self.fail("Couldn't find user 12")

    def test_getBranchInformation_owned(self):
        # When we get the branch information for one of our own branches (i.e.
        # owned by us or by a team we are on), we get the database id of the
        # branch, and a flag saying that we can write to that branch.
        store = DatabaseUserDetailsStorageV2(None)
        branch_id, permissions = store._getBranchInformationInteraction(
            12, 'name12', 'gnome-terminal', 'pushed')
        self.assertEqual(25, branch_id)
        self.assertEqual(WRITABLE, permissions)

    def test_getBranchInformation_nonexistent(self):
        # When we get the branch information for a non-existent branch, we get
        # a tuple of two empty strings (the empty string being an approximation
        # of 'None').
        store = DatabaseUserDetailsStorageV2(None)
        branch_id, permissions = store._getBranchInformationInteraction(
            12, 'name12', 'gnome-terminal', 'doesnt-exist')
        self.assertEqual('', branch_id)
        self.assertEqual('', permissions)

    def test_getBranchInformation_unowned(self):
        # When we get the branch information for a branch that we don't own, we
        # get the database id and a flag saying that we can only read that
        # branch.
        store = DatabaseUserDetailsStorageV2(None)
        branch_id, permissions = store._getBranchInformationInteraction(
            12, 'sabdfl', 'firefox', 'release-0.8')
        self.assertEqual(13, branch_id)
        self.assertEqual(READ_ONLY, permissions)

    def test_getBranchInformation_private(self):
        # When we get the branch information for a private branch that is
        # hidden to us, it is an if the branch doesn't exist at all.
        store = DatabaseUserDetailsStorageV2(None)
        # salgado is a member of landscape-developers.
        store._createBranchInteraction(
            'salgado', 'landscape-developers', 'landscape',
            'some-branch')
        # ddaa is not an admin, not a Landscape developer.
        branch_id, permissions = store._getBranchInformationInteraction(
            'ddaa', 'landscape-developers', 'landscape', 'some-branch')
        self.assertEqual('', branch_id)
        self.assertEqual('', permissions)

    def test_initialMirrorRequest(self):
        # The default 'mirror_request_time' for a newly created hosted branch
        # should be None.
        storage = DatabaseUserDetailsStorageV2(None)
        branchID = storage._createBranchInteraction(
            1, 'sabdfl', '+junk', 'foo')
        self.assertEqual(self._getTime(branchID), None)

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

        cur = cursor()
        cur.execute("""
            SELECT keytext FROM SSHKey
            JOIN Person ON (SSHKey.person = Person.id)
            WHERE Person.name = 'sabdfl'
            """)
        [expected_keytext] = cur.fetchone()

        storage = DatabaseUserDetailsStorage(None)
        [(keytype, keytext)] = storage._getSSHKeysInteraction('sabdfl')
        self.assertEqual('DSA', keytype)
        self.assertEqual(expected_keytext, keytext)

    def test_getUserNoWikiname(self):
        # Ensure that the authserver copes gracefully with users with:
        #    a) no wikinames at all
        #    b) no wikiname for http://www.ubuntulinux.com/wiki/
        # (even though in the long run we want to make sure these situations can
        # never happen, until then the authserver should be robust).

        # First, make sure that the sample user has no wikiname.
        transaction.begin()
        person = getUtility(IPersonSet).getByEmail('test@canonical.com')
        wiki_names = getUtility(IWikiNameSet).getAllWikisByPerson(person)
        for wiki_name in wiki_names:
            wiki_name.destroySelf()
        transaction.commit()

        # Get the user dict for Sample Person (test@canonical.com).
        storage = DatabaseUserDetailsStorageV2(None)
        userDict = storage._getUserInteraction('test@canonical.com')

        # The user dict has results, even though the wikiname is empty
        self.assertNotEqual({}, userDict)
        self.assertEqual('', userDict['wikiname'])
        self.assertEqual(12, userDict['id'])

        # Now lets add a wikiname, but for a different wiki.
        transaction.begin()
        login(ANONYMOUS)
        person = getUtility(IPersonSet).getByEmail('test@canonical.com')
        getUtility(IWikiNameSet).new(person, 'http://foowiki/', 'SamplePerson')
        logout()
        transaction.commit()

        # The authserver should return exactly the same results.
        userDict2 = storage._getUserInteraction('test@canonical.com')
        self.assertEqual(userDict, userDict2)

    def test_requestMirror(self):
        # requestMirror should set the mirror_request_time field to be the
        # current time.
        hosted_branch_id = 25
        # make sure the sample data is sane
        self.assertEqual(self._getTime(hosted_branch_id), None)

        cur = cursor()
        cur.execute("SELECT CURRENT_TIMESTAMP AT TIME ZONE 'UTC'")
        [current_db_time] = cur.fetchone()

        storage = DatabaseUserDetailsStorageV2(None)
        storage._requestMirrorInteraction(hosted_branch_id)

        self.assertTrue(current_db_time < self._getTime(hosted_branch_id),
                        "Branch mirror_request_time not updated.")

    def test_mirrorComplete_resets_mirror_request(self):
        # After successfully mirroring a branch, mirror_request_time should be
        # set to NULL.

        # Request that 25 (a hosted branch) be mirrored. This sets
        # mirror_request_time.
        storage = DatabaseUserDetailsStorageV2(None)
        storage._requestMirrorInteraction(25)

        # Simulate successfully mirroring branch 25
        storage = DatabaseBranchDetailsStorage(None)
        cur = cursor()
        storage._startMirroringInteraction(25)
        storage._mirrorCompleteInteraction(25, 'rev-1')

        self.assertEqual(None, self._getTime(25))

    def test_mirrorFailed_resets_mirror_request(self):
        # After failing to mirror a branch, mirror_request_time for that branch
        # should be set to NULL.

        # Request that 25 (a hosted branch) be mirrored. This sets
        # mirror_request_time.
        storage = DatabaseUserDetailsStorageV2(None)
        storage._requestMirrorInteraction(25)

        # Simulate successfully mirroring branch 25
        storage = DatabaseBranchDetailsStorage(None)
        cur = cursor()
        storage._startMirroringInteraction(25)
        storage._mirrorFailedInteraction(25, 'failed')

        self.assertEqual(None, self._getTime(25))

    def test_requested_hosted_branches(self):
        # Hosted branches that HAVE had a mirror requested should be in
        # the branch queue

        # Mark 25 (a hosted branch) as recently mirrored.
        storage = DatabaseBranchDetailsStorage(None)
        cur = cursor()
        storage._startMirroringInteraction(25)
        storage._mirrorCompleteInteraction(25, 'rev-1')

        # Request a mirror
        storage = DatabaseUserDetailsStorageV2(None)
        storage._requestMirrorInteraction(25)

        self.failUnless(self.isBranchInPullQueue(25), "Should be in queue")


class ExtraUserDatabaseStorageTestCase(TestDatabaseSetup):
    # Tests that do some database writes (but makes sure to roll them back)

    layer = LaunchpadScriptLayer

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
        self.cursor.execute(
            "INSERT INTO EmailAddress (person, email, status) "
            "VALUES ("
            "  1, "
            "  '%s', "
            "  2)"  # 2 == Validated
            % (u'm\xe3rk@hbd.com'.encode('utf-8'),)
        )
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
        self.cursor.execute(
            "DELETE FROM EmailAddress WHERE person = 1;"
        )
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

    def testTeamDict(self):
        # The user dict from a V2 storage should include a 'teams' element with
        # a list of team dicts, one for each team the user is in, including
        # the user.

        # Get a user dict
        storage = DatabaseUserDetailsStorageV2(None)
        userDict = storage._getUserInteraction('mark@hbd.com')

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
        userDict2 = storage._authUserInteraction('mark@hbd.com', 'test')
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
            'justdave@bugzilla.org', 'supersecret!')
        self.assertEqual({}, userDict)


class BranchDetailsDatabaseStorageInterfaceTestCase(TestDatabaseSetup):

    def test_verifyInterface(self):
        self.failUnless(verifyObject(IBranchDetailsStorage,
                                     DatabaseBranchDetailsStorage(None)))


class NewBranchDetailsDatabaseStorageTestCase(unittest.TestCase):

    layer = LaunchpadScriptLayer

    def setUp(self):
        super(NewBranchDetailsDatabaseStorageTestCase, self).setUp()
        LaunchpadScriptLayer.switchDbConfig('authserver')
        self.storage = DatabaseBranchDetailsStorage(None)
        self.cursor = cursor()
        self._old_policy = getSecurityPolicy()
        setSecurityPolicy(LaunchpadSecurityPolicy)

    def tearDown(self):
        setSecurityPolicy(self._old_policy)
        super(NewBranchDetailsDatabaseStorageTestCase, self).tearDown()

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
        results = self.storage._getBranchPullQueueInteraction()
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
        cur = cursor()
        assert int(value is None) + int(now_minus is None) == 1
        if now_minus is not None:
            value = ("CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - interval '%s'"
                     % now_minus)
        cur.execute(
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
        cur = cursor()
        cur.execute(
            "UPDATE Branch SET last_mirror_attempt = (%s) WHERE id = %d"
            % (value, branch_id))

    def test_startMirroring(self):
        # verify that the last mirror time is None before hand.
        self.cursor.execute("""
            SELECT last_mirror_attempt, last_mirrored
                FROM branch WHERE id = 1""")
        row = self.cursor.fetchone()
        self.assertEqual(row[0], None)
        self.assertEqual(row[1], None)

        success = self.storage._startMirroringInteraction(1)
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

        success = self.storage._startMirroringInteraction(-11)
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

        success = self.storage._startMirroringInteraction(1)
        self.assertEqual(success, True)
        success = self.storage._mirrorFailedInteraction(1, "failed")
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

        success = self.storage._startMirroringInteraction(1)
        self.assertEqual(success, True)
        success = self.storage._mirrorCompleteInteraction(1, 'rev-1')
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

    def test_mirrorComplete_resets_failure_count(self):
        # this increments the failure count ...
        self.test_mirrorFailed()

        success = self.storage._startMirroringInteraction(1)
        self.assertEqual(success, True)
        success = self.storage._mirrorCompleteInteraction(1, 'rev-1')
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
        self.storage._startMirroringInteraction(25)
        self.storage._mirrorCompleteInteraction(25, 'rev-1')

        self.failIf(self.isBranchInPullQueue(25),
                    "Shouldn't be in queue until mirror requested")

    def test_mirror_stale_hosted_branches(self):
        # Hosted branches which haven't been mirrored for a whole day should be
        # mirrored even if they haven't asked for it.

        # Branch 25 is a hosted branch, hasn't been mirrored for over 1 day
        # and has not had a mirror requested
        self.failUnless(self.isBranchInPullQueue(25))

        # Mark 25 as recently mirrored.
        self.storage._startMirroringInteraction(25)
        self.storage._mirrorCompleteInteraction(25, 'rev-1')

        # 25 should only be in the pull queue if a mirror has been requested
        self.failIf(self.isBranchInPullQueue(25),
                    "hosted branch no longer in pull list")

    def test_recordSuccess(self):
        # recordSuccess must insert the given data into BranchActivity.
        started = datetime.datetime(2007, 07, 05, 19, 32, 1, tzinfo=UTC)
        completed = datetime.datetime(2007, 07, 05, 19, 34, 24, tzinfo=UTC)
        started_tuple = tuple(started.utctimetuple())
        completed_tuple = tuple(completed.utctimetuple())
        success = self.storage._recordSuccessInteraction(
            'test-recordsuccess', 'vostok', started_tuple, completed_tuple)
        self.assertEqual(success, True, '_recordSuccessInteraction failed')

        self.cursor.execute("""
            SELECT name, hostname, date_started, date_completed
                FROM ScriptActivity where name = 'test-recordsuccess'""")
        row = self.cursor.fetchone()
        self.assertEqual(row[0], 'test-recordsuccess')
        self.assertEqual(row[1], 'vostok')
        self.assertEqual(row[2], started.replace(tzinfo=None))
        self.assertEqual(row[3], completed.replace(tzinfo=None))

    def test_getBranchPullQueue(self):
        # Set up the database so the vcs-import branch will appear in the queue.
        transaction.begin()
        self.setSeriesDateLastSynced(3, now_minus='1 second')
        self.setBranchLastMirrorAttempt(14, now_minus='1 day')
        transaction.commit()

        results = self.storage._getBranchPullQueueInteraction()

        # The first item in the row is the id.
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
        transaction.begin()
        self.setSeriesDateLastSynced(3, now_minus='1 second')
        self.setBranchLastMirrorAttempt(14, now_minus='1 day')
        transaction.commit()

        results = self.storage._getBranchPullQueueInteraction()

        # The first item in the row is the id.
        results_dict = dict((row[0], row) for row in results)

        # branch 3 is a branch without a product.
        branch_id, url, unique_name = results_dict[3]
        self.assertEqual(unique_name, 'spiv/+junk/trunk')

    def test_getBranchPullQueueOrdering(self):
        # Test that rows where last_mirror_attempt IS NULL are listed first, and
        # then that rows are ordered so that older last_mirror_attempts are
        # listed earlier.

        transaction.begin()
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
        transaction.commit()

        # Call getBranchPullQueue
        results = self.storage._getBranchPullQueueInteraction()

        # Get the branch IDs from the results for the branches we modified:
        branches = [row[0] for row in results if row[0] in range(16, 26)]

        # All 10 branches should be in the list in order of descending
        # ID due to the last_mirror_attempt values.
        self.assertEqual(list(reversed(branches)), range(16, 26))

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
        transaction.begin()
        self.setSeriesDateLastSynced(3, 'NULL')
        self.setBranchLastMirrorAttempt(14, 'NULL')
        transaction.commit()

        # Since the import was never successful, the branch should not be in
        # the pull queue.
        self.failIf(self.isBranchInPullQueue(14),
            "incomplete import branch in pull queue.")

        # Mark ProductSeries 3 as just synced, and branch 14 as never mirrored.
        self.setSeriesDateLastSynced(3, now_minus='1 second')
        self.setBranchLastMirrorAttempt(14, 'NULL')
        transaction.commit()

        # We have a new import! We must mirror it as soon as possible.
        self.failUnless(self.isBranchInPullQueue(14),
            "new import branch not in pull queue.")

        # Mark ProductSeries 3 as synced, and branch 14 as more recently
        # mirrored. Use a last_mirror_attempt older than a day to make sure
        # that we are no exercising the 'one mirror per day' logic.
        self.setSeriesDateLastSynced(3, now_minus='1 day 15 minutes')
        self.setBranchLastMirrorAttempt(14, now_minus='1 day 10 minutes')
        transaction.commit()

        # Since the the import was not successfully synced since the last
        # mirror, we do not have anything new to mirror.
        self.failIf(self.isBranchInPullQueue(14),
            "not recently synced import branch in pull queue.")

        # Mark ProductSeries 3 as synced recently, and branch 13 as last
        # mirrored before this sync.
        self.setSeriesDateLastSynced(3, now_minus='1 second')
        self.setBranchLastMirrorAttempt(14, now_minus='1 day')
        transaction.commit()

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
        transaction.commit()
        self.failUnless(self.isBranchInPullQueue(14),
            "import branch last mirrored >1 day ago not in pull queue.")

        # Set a NULL datelastsynced in ProductSeries 3, and mark Branch 14 as
        # mirrored recently.
        self.setSeriesDateLastSynced(3, 'NULL')
        self.setBranchLastMirrorAttempt(14, now_minus='5 minutes')
        transaction.commit()
        self.failIf(self.isBranchInPullQueue(14),
            "import branch mirrored <1 day ago in pull queue.")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

