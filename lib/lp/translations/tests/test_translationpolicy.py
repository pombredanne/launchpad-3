# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test `TranslationPolicyMixin`."""

__metaclass__ = type

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import ZopelessDatabaseLayer
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod
from lp.translations.interfaces.translationgroup import TranslationPermission
from lp.translations.interfaces.translationpolicy import ITranslationPolicy
from lp.translations.interfaces.translationsperson import ITranslationsPerson
from lp.translations.interfaces.translator import ITranslatorSet
from lp.translations.model.translationpolicy import TranslationPolicyMixin


class TranslationPolicyImplementation(TranslationPolicyMixin):
    implements(ITranslationPolicy)

    translationgroup = None

    translationpermission = TranslationPermission.OPEN


class TestTranslationPolicy(TestCaseWithFactory):
    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestTranslationPolicy, self).setUp()
        self.policy = TranslationPolicyImplementation()

    def _makeParentPolicy(self):
        """Create a policy that `self.policy` inherits from."""
        parent = TranslationPolicyImplementation()
        self.policy.getInheritedTranslationPolicy = FakeMethod(result=parent)
        return parent

    def _makeTranslationGroups(self, count):
        """Return a list of `count` freshly minted `TranslationGroup`s."""
        return [
            self.factory.makeTranslationGroup() for number in xrange(count)]

    def _makeTranslator(self, language, for_policy=None):
        """Create a translator for a policy object.

        Default is `self.policy`.  Creates a translation group if necessary.
        """
        if for_policy is None:
            for_policy = self.policy
        if for_policy.translationgroup is None:
            for_policy.translationgroup = self.factory.makeTranslationGroup()
        person = self.factory.makePerson()
        getUtility(ITranslatorSet).new(
            for_policy.translationgroup, language, person, None)
        return person

    def _setPermissions(self, child_permission, parent_permission):
        """Set `TranslationPermission`s for `self.policy` and its parent."""
        self.policy.translationpermission = child_permission
        self.policy.getInheritedTranslationPolicy().translationpermission = (
            parent_permission)

    def test_hasSpecialTranslationPrivileges_for_regular_joe(self):
        # A logged-in user has no special translationprivileges by
        # default.
        joe = self.factory.makePerson()
        self.assertFalse(self.policy._hasSpecialTranslationPrivileges(joe))

    def test_hasSpecialTranslationPrivileges_for_admin(self):
        # Admins have special translation privileges.
        admin = self.factory.makePerson()
        getUtility(ILaunchpadCelebrities).admin.addMember(admin, admin)
        self.assertTrue(self.policy._hasSpecialTranslationPrivileges(admin))

    def test_hasSpecialTranslationPrivileges_for_translations_owner(self):
        # A policy may define a "translations owner" who also gets
        # special translation privileges.
        self.policy.isTranslationsOwner = FakeMethod(result=True)
        owner = self.factory.makePerson()
        self.assertTrue(self.policy._hasSpecialTranslationPrivileges(owner))

    def test_canTranslate(self):
        # A user who has declined the licensing agreement can't
        # translate.  Someone who has agreed, or not made a decision
        # yet, can.
        user = self.factory.makePerson()
        translations_user = ITranslationsPerson(user)

        self.assertTrue(self.policy._canTranslate(user))

        translations_user.translations_relicensing_agreement = True
        self.assertTrue(self.policy._canTranslate(user))

        translations_user.translations_relicensing_agreement = False
        self.assertFalse(self.policy._canTranslate(user))

    def test_getTranslationGroups_returns_translation_group(self):
        # In the simple case, getTranslationGroup simply returns the
        # policy implementation's translation group.
        self.assertEqual([], self.policy.getTranslationGroups())
        self.policy.translationgroup = self.factory.makeTranslationGroup()
        self.assertEqual(
            [self.policy.translationgroup],
            self.policy.getTranslationGroups())

    def test_getTranslationGroups_enumerates_groups_inherited_first(self):
        parent = self._makeParentPolicy()
        groups = self._makeTranslationGroups(2)
        parent.translationgroup = groups[0]
        self.policy.translationgroup = groups[1]
        self.assertEqual(groups, self.policy.getTranslationGroups())

    def test_getTranslationGroups_inheritance_is_asymmetric(self):
        parent = self._makeParentPolicy()
        groups = self._makeTranslationGroups(2)
        parent.translationgroup = groups[0]
        self.policy.translationgroup = groups[1]
        self.assertEqual(groups[:1], parent.getTranslationGroups())

    def test_getTranslationGroups_eliminates_duplicates(self):
        parent = self._makeParentPolicy()
        groups = self._makeTranslationGroups(1)
        parent.translationgroup = groups[0]
        self.policy.translationgroup = groups[0]
        self.assertEqual(groups, self.policy.getTranslationGroups())

    def test_getTranslators_without_groups_returns_empty_list(self):
        language = self.factory.makeLanguage()
        self.assertEqual([], self.policy.getTranslators(language))

    def test_getTranslators_returns_group_even_without_translators(self):
        self.policy.translationgroup = self.factory.makeTranslationGroup()
        self.assertEqual(
            [(self.policy.translationgroup, None, None)],
            self.policy.getTranslators(self.factory.makeLanguage()))

    def test_getTranslators_returns_translator(self):
        language = self.factory.makeLanguage()
        language_translator = self._makeTranslator(language)
        translators = self.policy.getTranslators(language)
        self.assertEqual(1, len(translators))
        group, translator, person = translators[0]
        self.assertEqual(self.policy.translationgroup, group)
        self.assertEqual(
            self.policy.translationgroup, translator.translationgroup)
        self.assertEqual(person, translator.translator)
        self.assertEqual(language, translator.language)
        self.assertEqual(language_translator, person)

    def test_getEffectiveTranslationPermission_returns_permission(self):
        # In the basic case, getEffectiveTranslationPermission just
        # returns the policy's translation permission.
        self.policy.translationpermission = TranslationPermission.CLOSED
        self.assertEqual(
            self.policy.translationpermission,
            self.policy.getEffectiveTranslationPermission())

    def test_getEffectiveTranslationPermission_returns_maximum(self):
        # When combining permissions, getEffectiveTranslationPermission
        # returns the one with the highest numerical value.
        parent = self._makeParentPolicy()
        for child_permission in TranslationPermission.items:
            for parent_permission in TranslationPermission.items:
                self._setPermissions(child_permission, parent_permission)
                stricter = max(child_permission, parent_permission)
                self.assertEqual(
                    stricter, self.policy.getEffectiveTranslationPermission())

    def test_maximum_permission_is_strictest(self):
        # The TranslationPermissions are ordered from loosest to
        # strictest, so the maximum is always the strictest.
        self.assertEqual(TranslationPermission.STRUCTURED, max(
            TranslationPermission.OPEN, TranslationPermission.STRUCTURED))
        self.assertEqual(TranslationPermission.RESTRICTED, max(
            TranslationPermission.STRUCTURED,
            TranslationPermission.RESTRICTED))
        self.assertEqual(TranslationPermission.CLOSED, max(
            TranslationPermission.RESTRICTED,
            TranslationPermission.CLOSED))
