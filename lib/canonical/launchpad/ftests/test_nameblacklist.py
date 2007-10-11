# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test the person_sort_key stored procedure."""

__metaclass__ = type

import unittest

from canonical.launchpad.ftests.harness import (
    LaunchpadTestCase, LaunchpadTestSetup)
from canonical.database.sqlbase import sqlvalues
from canonical.foaf.nickname import is_blacklisted

class TestNameBlacklist(LaunchpadTestCase):
    def setUp(self):
        LaunchpadTestCase.setUp(self)
        self.con = self.connect()
        self.cur = self.con.cursor()

        # Create a couple of blacklist entres
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
        """Tear down the test and reset the database."""
        self.con.close()
        LaunchpadTestSetup().force_dirty_database()
        LaunchpadTestCase.tearDown(self)

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

    def test_is_blacklisted(self):
        # is_blacklisted is a method in canonical.foaf.nickname
        # which corresponds to is_blacklisted_name in this test
        # except that it also allows unicode strings
        self.failUnless(is_blacklisted("foo", self.cur) == 1)
        self.failUnless(is_blacklisted(u"foo", self.cur) == 1)
        self.failUnless(is_blacklisted("bar", self.cur) == 0)
        self.failUnless(is_blacklisted(u"bar", self.cur) == 0)

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


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestNameBlacklist))
    return suite


if __name__ == '__main__':
    unittest.main()
