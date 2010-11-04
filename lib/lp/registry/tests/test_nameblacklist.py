# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the person_sort_key stored procedure."""

__metaclass__ = type

from lp.testing import TestCase

from zope.component import getUtility
from zope.interface.verify import verifyObject


from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.ftests import login
from canonical.testing.layers import ZopelessDatabaseLayer
from lp.registry.interfaces.nameblacklist import (
    INameBlackList,
    INameBlackListSet,
    )
from lp.testing.sampledata import ADMIN_EMAIL


class TestNameBlacklist(TestCase):
    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestNameBlacklist, self).setUp()
        self.con = self.layer.connect()
        self.cur = self.con.cursor()

        # Create a couple of blacklist entries
        self.cur.execute("""
            INSERT INTO NameBlacklist(id, regexp) VALUES (-200, '^foo')
            """)
        self.cur.execute("""
            INSERT INTO NameBlacklist(id, regexp) VALUES (-100, 'foo')
            """)
        self.cur.execute("""
            INSERT INTO NameBlacklist(id, regexp) VALUES (-50, 'v e r b o s e')
            """)

    def tearDown(self):
        super(TestNameBlacklist, self).tearDown()
        self.con.close()

    def name_blacklist_match(self, name):
        '''Return the result of the name_blacklist_match stored procedure.'''
        self.cur.execute("SELECT name_blacklist_match(%(name)s)", vars())
        return self.cur.fetchone()[0]

    def is_blacklisted_name(self, name):
        '''Call the is_blacklisted_name stored procedure and return the result
        '''
        self.cur.execute("SELECT is_blacklisted_name(%(name)s)", vars())
        blacklisted = self.cur.fetchone()[0]
        self.failIf(blacklisted is None, 'is_blacklisted_name returned NULL')
        return bool(blacklisted)

    def test_name_blacklist_match(self):

        # A name that is not blacklisted returns NULL/None
        self.failUnless(self.name_blacklist_match("bar") is None)

        # A name that is blacklisted returns the id of the row in the
        # NameBlacklist table that matched. Rows are tried in order, and the
        # first match is returned.
        self.failUnlessEqual(self.name_blacklist_match("foobar"), -200)
        self.failUnlessEqual(self.name_blacklist_match("barfoo"), -100)

    def test_name_blacklist_match_cache(self):
        # If the blacklist is changed in the DB, these changes are noticed.
        # This test is needed because the stored procedure keeps a cache
        # of the compiled regular expressions.
        self.failUnlessEqual(self.name_blacklist_match("foobar"), -200)
        self.cur.execute(
                "UPDATE NameBlacklist SET regexp='nomatch' where id=-200"
                )
        self.failUnlessEqual(self.name_blacklist_match("foobar"), -100)
        self.cur.execute(
                "UPDATE NameBlacklist SET regexp='nomatch2' where id=-100"
                )
        self.failUnless(self.name_blacklist_match("foobar") is None)

    def test_is_blacklisted_name(self):
        # is_blacklisted_name() is just a wrapper around name_blacklist_match
        # that is friendlier to use in a boolean context.
        self.failUnless(self.is_blacklisted_name("bar") is False)
        self.failUnless(self.is_blacklisted_name("foo") is True)
        self.cur.execute("UPDATE NameBlacklist SET regexp='bar' || regexp")
        self.failUnless(self.is_blacklisted_name("foo") is False)

    def test_case_insensitive(self):
        self.failUnless(self.is_blacklisted_name("Foo") is True)

    def test_verbose(self):
        # Testing the VERBOSE flag is used when compiling the regexp
        self.failUnless(self.is_blacklisted_name("verbose") is True)


class TestNameBlackListSet(TestCase):

    layer = ZopelessDatabaseLayer

    def test_create_with_one_arg(self):
        login(ADMIN_EMAIL)
        nameblacklist_set = getUtility(INameBlackListSet)
        nameblacklist = nameblacklist_set.create(u'foo')
        self.assertTrue(verifyObject(INameBlackList, nameblacklist))
        self.assertEquals(u'foo', nameblacklist.regexp)
        self.assertIs(None, nameblacklist.comment)

    def test_create_with_two_args(self):
        login(ADMIN_EMAIL)
        nameblacklist_set = getUtility(INameBlackListSet)
        nameblacklist = nameblacklist_set.create(u'foo', u'bar')
        self.assertTrue(verifyObject(INameBlackList, nameblacklist))
        self.assertEquals(u'foo', nameblacklist.regexp)
        self.assertEquals(u'bar', nameblacklist.comment)

    def test_get(self):
        login(ADMIN_EMAIL)
        nameblacklist_set = getUtility(INameBlackListSet)
        nameblacklist = nameblacklist_set.create(u'foo', u'bar')
        store = IStore(nameblacklist)
        store.flush()
        retrieved = nameblacklist_set.get(nameblacklist.id)
        self.assertEquals(nameblacklist, retrieved)
