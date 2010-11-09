# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the person_sort_key stored procedure."""

__metaclass__ = type


from lp.testing import (
    ANONYMOUS,
    login,
    login_person,
    TestCaseWithFactory,
    )

from zope.component import getUtility
from zope.interface.verify import verifyObject

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    ZopelessDatabaseLayer,
    )
from canonical.launchpad.webapp.authorization import check_permission

from lp.registry.interfaces.nameblacklist import (
    INameBlacklist,
    INameBlacklistSet,
    )
from lp.testing.sampledata import ADMIN_EMAIL


class TestNameBlacklist(TestCaseWithFactory):
    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestNameBlacklist, self).setUp()
        self.name_blacklist_set = getUtility(INameBlacklistSet)
        self.caret_foo_exp = self.name_blacklist_set.create(u'^foo')
        self.foo_exp = self.name_blacklist_set.create(u'foo')
        self.verbose_exp = self.name_blacklist_set.create(u'v e r b o s e')
        self.store = IStore(self.foo_exp)
        self.store.flush()

    def name_blacklist_match(self, name):
        '''Return the result of the name_blacklist_match stored procedure.'''
        result = self.store.execute(
            "SELECT name_blacklist_match(%s)", (name,))
        return result.get_one()[0]

    def is_blacklisted_name(self, name):
        '''Call the is_blacklisted_name stored procedure and return the result
        '''
        result = self.store.execute(
            "SELECT is_blacklisted_name(%s)", (name,))
        blacklisted = result.get_one()[0]
        self.failIf(blacklisted is None, 'is_blacklisted_name returned NULL')
        return bool(blacklisted)

    def test_name_blacklist_match(self):

        # A name that is not blacklisted returns NULL/None
        self.failUnless(self.name_blacklist_match("bar") is None)

        # A name that is blacklisted returns the id of the row in the
        # NameBlacklist table that matched. Rows are tried in order, and the
        # first match is returned.
        self.failUnlessEqual(
            self.name_blacklist_match("foobar"),
            self.caret_foo_exp.id)
        self.failUnlessEqual(
            self.name_blacklist_match("barfoo"),
            self.foo_exp.id)

    def test_name_blacklist_match_cache(self):
        # If the blacklist is changed in the DB, these changes are noticed.
        # This test is needed because the stored procedure keeps a cache
        # of the compiled regular expressions.
        self.failUnlessEqual(
            self.name_blacklist_match("foobar"),
            self.caret_foo_exp.id)
        self.caret_foo_exp.regexp = u'nomatch'
        self.failUnlessEqual(
            self.name_blacklist_match("foobar"),
            self.foo_exp.id)
        self.foo_exp.regexp = u'nomatch2'
        self.failUnless(self.name_blacklist_match("foobar") is None)

    def test_is_blacklisted_name(self):
        # is_blacklisted_name() is just a wrapper around name_blacklist_match
        # that is friendlier to use in a boolean context.
        self.failUnless(self.is_blacklisted_name("bar") is False)
        self.failUnless(self.is_blacklisted_name("foo") is True)
        self.caret_foo_exp.regexp = u'bar'
        self.foo_exp.regexp = u'bar2'
        self.failUnless(self.is_blacklisted_name("foo") is False)

    def test_case_insensitive(self):
        self.failUnless(self.is_blacklisted_name("Foo") is True)

    def test_verbose(self):
        # Testing the VERBOSE flag is used when compiling the regexp
        self.failUnless(self.is_blacklisted_name("verbose") is True)


class TestNameBlacklistSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestNameBlacklistSet, self).setUp()
        registry_experts = getUtility(ILaunchpadCelebrities).registry_experts
        registry_expert = self.factory.makePerson()
        login(ADMIN_EMAIL)
        registry_experts.addMember(registry_expert, registry_expert)
        login_person(registry_expert)
        self.name_blacklist_set = getUtility(INameBlacklistSet)

    def test_create_with_one_arg(self):
        # Test NameBlacklistSet.create(regexp).
        name_blacklist = self.name_blacklist_set.create(u'foo')
        self.assertTrue(verifyObject(INameBlacklist, name_blacklist))
        self.assertEquals(u'foo', name_blacklist.regexp)
        self.assertIs(None, name_blacklist.comment)

    def test_create_with_two_args(self):
        # Test NameBlacklistSet.create(regexp, comment).
        name_blacklist = self.name_blacklist_set.create(u'foo', u'bar')
        self.assertTrue(verifyObject(INameBlacklist, name_blacklist))
        self.assertEquals(u'foo', name_blacklist.regexp)
        self.assertEquals(u'bar', name_blacklist.comment)

    def test_get(self):
        # Test NameBlacklistSet.get().
        name_blacklist = self.name_blacklist_set.create(u'foo', u'bar')
        store = IStore(name_blacklist)
        store.flush()
        retrieved = self.name_blacklist_set.get(name_blacklist.id)
        self.assertEquals(name_blacklist, retrieved)

    def test_getAll(self):
        # Test NameBlacklistSet.getAll().
        result = [
            (item.regexp, item.comment)
            for item in self.name_blacklist_set.getAll()]
        expected = [
            ('^admin', None),
            ('blacklist', 'For testing purposes'),
            ]
        self.assertEqual(expected, result)

    def test_NameBlacklistSet_permissions(self):
        # Verify that non-registry-experts do not have permission to
        # access the NameBlacklistSet.
        self.assertTrue(
            check_permission('launchpad.View', self.name_blacklist_set))
        self.assertTrue(
            check_permission('launchpad.Edit', self.name_blacklist_set))
        login(ANONYMOUS)
        self.assertFalse(
            check_permission('launchpad.View', self.name_blacklist_set))
        self.assertFalse(
            check_permission('launchpad.Edit', self.name_blacklist_set))

    def test_NameBlacklist_permissions(self):
        # Verify that non-registry-experts do not have permission to
        # access the NameBlacklist.
        name_blacklist = self.name_blacklist_set.create(u'foo')
        self.assertTrue(check_permission('launchpad.View', name_blacklist))
        self.assertTrue(check_permission('launchpad.Edit', name_blacklist))
        login(ANONYMOUS)
        self.assertFalse(check_permission('launchpad.View', name_blacklist))
        self.assertFalse(check_permission('launchpad.Edit', name_blacklist))
