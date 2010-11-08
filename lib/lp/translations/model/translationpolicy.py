# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Translation access and sharing policy."""

__metaclass__ = type
__all__ = [
    'TranslationPolicyMixin',
    ]

from storm.expr import (
    And,
    LeftJoin,
    )
from zope.component import getUtility

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.interfaces.lpstorm import IStore
from lp.registry.model.person import Person
from lp.translations.interfaces.translationsperson import ITranslationsPerson
from lp.translations.model.translationgroup import TranslationGroup
from lp.translations.model.translator import Translator


class TranslationPolicyMixin:
    """Implementation mixin for `ITranslationPolicy`."""

    def getInheritedTranslationPolicy(self):
        """Get any `ITranslationPolicy` objects that this one inherits.

        To be overridden by the implementing class.  A `Product` may
        inherit a policy from a `ProjectGroup` it's in.
        """
        return None

    def isTranslationsOwner(self, person):
        """Is `person` one of the owners of these translations?

        To be overridden by the implementing class if it grants special
        translation rights to certain people.
        """
        return False

    def _hasSpecialTranslationPrivileges(self, person):
        """Does this person have special translation editing rights here?"""
        celebs = getUtility(ILaunchpadCelebrities)
        return (
            person.inTeam(celebs.admin) or
            person.inTeam(celebs.rosetta_experts) or
            self.isTranslationsOwner(person))

    def _canTranslate(self, person):
        """Is `person` in a position to translate?

        Someone who has declined the translations relicensing agreement
        is not.  Someone who hasn't decided on the agreement yet is, but
        may be redirected to a form to sign first.
        """
        translations_person = ITranslationsPerson(person)
        agreement = translations_person.translations_relicensing_agreement
        return agreement is not False

    def getTranslationGroups(self):
        """See `ITranslationPolicy`."""
        inherited = self.getInheritedTranslationPolicy()
        if inherited is None:
            groups = []
        else:
            groups = inherited.getTranslationGroups()
        my_group = self.translationgroup
        if my_group is not None and my_group not in groups:
            groups.append(my_group)
        return groups

    def _getTranslator(self, translationgroup, language, store):
        """Retrieve one (TranslationGroup, Translator, Person) tuple."""
        translator_join = LeftJoin(Translator, And(
            Translator.translationgroupID == TranslationGroup.id,
            Translator.languageID == language.id))
        person_join = LeftJoin(
            Person, Person.id == Translator.translatorID)

        source = store.using(TranslationGroup, translator_join, person_join)
        return source.find(
            (TranslationGroup, Translator, Person),
            TranslationGroup.id == translationgroup.id).one()

    def getTranslators(self, language, store=None):
        """See `ITranslationPolicy`."""
        if store is None:
            store = IStore(TranslationGroup)
        return [
            self._getTranslator(group, language, store)
            for group in self.getTranslationGroups()]

    def getEffectiveTranslationPermission(self):
        """See `ITranslationPolicy`."""
        inherited = self.getInheritedTranslationPolicy()
        if inherited is None:
            return self.translationpermission
        else:
            return max([
                self.translationpermission,
                inherited.getEffectiveTranslationPermission()])
