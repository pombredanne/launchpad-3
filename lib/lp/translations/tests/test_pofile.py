# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0102

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
from textwrap import dedent

import pytz
from zope.component import (
    getAdapter,
    getUtility,
    )
from zope.interface.verify import verifyObject
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )
from lp.app.enums import ServiceUsage
from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.pofile import IPOFileSet
from lp.translations.interfaces.translatablemessage import (
    ITranslatableMessage,
    )
from lp.translations.interfaces.translationcommonformat import (
    ITranslationFileData,
    )
from lp.translations.interfaces.translationgroup import TranslationPermission
from lp.translations.interfaces.translationmessage import (
    TranslationValidationStatus,
    )
from lp.translations.interfaces.translationsperson import ITranslationsPerson


def set_relicensing(person, choice):
    """Set `person`'s choice for the translations relicensing agreement.

    :param person: A `Person`.
    :param choice: The person's tri-state boolean choice on the
        relicensing agreement.  None means undecided, which is the
        default initial choice for any person.
    """
    ITranslationsPerson(person).translations_relicensing_agreement = choice


class TestTranslationSharedPOFile(TestCaseWithFactory):
    """Test behaviour of PO files with shared POTMsgSets."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        # Create a product with two series and a shared POTemplate
        # in different series ('devel' and 'stable').
        super(TestTranslationSharedPOFile, self).setUp()
        self.foo = self.factory.makeProduct(
            name='foo',
            translations_usage=ServiceUsage.LAUNCHPAD)
        self.foo_devel = self.factory.makeProductSeries(
            name='devel', product=self.foo)
        self.foo_stable = self.factory.makeProductSeries(
            name='stable', product=self.foo)

        # POTemplate is 'shared' if it has the same name ('messages').
        self.devel_potemplate = self.factory.makePOTemplate(
            productseries=self.foo_devel, name="messages")
        self.stable_potemplate = self.factory.makePOTemplate(self.foo_stable,
                                                        name="messages")

        # We'll use two PO files, one for each series.
        self.devel_sr_pofile = self.factory.makePOFile(
            'sr', self.devel_potemplate)
        self.stable_sr_pofile = self.factory.makePOFile(
            'sr', self.stable_potemplate)

        # Create a single POTMsgSet that is used across all tests,
        # and add it to only one of the POTemplates.
        self.potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate)
        self.potmsgset.setSequence(self.devel_potemplate, 1)

    def test_POFile_canonical_url(self):
        # Test the canonical_url of the POFile.
        self.assertEqual(
            'http://translations.launchpad.dev/foo/devel/+pots/messages/sr',
            canonical_url(self.devel_sr_pofile))
        self.assertEqual(
            ('http://translations.launchpad.dev/'
            'foo/devel/+pots/messages/sr/+details'),
            canonical_url(self.devel_sr_pofile, view_name="+details"))

    def test_findPOTMsgSetsContaining(self):
        # Test that search works correctly.

        # Searching for English strings.
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate,
                                               u"Some wild text")
        potmsgset.setSequence(self.devel_potemplate, 2)

        found_potmsgsets = list(
            self.devel_sr_pofile.findPOTMsgSetsContaining(u"wild"))
        self.assertEquals(found_potmsgsets, [potmsgset])

        # Just linking an existing POTMsgSet into another POTemplate
        # will make it be returned in searches.
        potmsgset.setSequence(self.stable_potemplate, 2)
        found_potmsgsets = list(
            self.stable_sr_pofile.findPOTMsgSetsContaining(u"wild"))
        self.assertEquals(found_potmsgsets, [potmsgset])

        # Searching for singular in plural messages works as well.
        plural_potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate,
                                                      u"Some singular text",
                                                      u"Some plural text")
        plural_potmsgset.setSequence(self.devel_potemplate, 3)

        found_potmsgsets = list(
            self.devel_sr_pofile.findPOTMsgSetsContaining(u"singular"))
        self.assertEquals(found_potmsgsets, [plural_potmsgset])

        # And searching for plural text returns only the matching plural
        # message.
        found_potmsgsets = list(
            self.devel_sr_pofile.findPOTMsgSetsContaining(u"plural"))
        self.assertEquals(found_potmsgsets, [plural_potmsgset])

        # Search translations as well.
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"One translation message"])
        found_potmsgsets = list(
            self.devel_sr_pofile.findPOTMsgSetsContaining(u"translation"))
        self.assertEquals(found_potmsgsets, [potmsgset])

        # Search matches all plural forms.
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=plural_potmsgset,
            translations=[u"One translation message",
                          u"Plural translation message",
                          u"Third translation message"])
        found_potmsgsets = list(
            self.devel_sr_pofile.findPOTMsgSetsContaining(
                u"Plural translation"))
        self.assertEquals(found_potmsgsets, [plural_potmsgset])

        # Search works case insensitively for English strings.
        found_potmsgsets = list(
            self.devel_sr_pofile.findPOTMsgSetsContaining(u"WiLd"))
        self.assertEquals(found_potmsgsets, [potmsgset])
        # ...English plural forms.
        found_potmsgsets = list(
            self.devel_sr_pofile.findPOTMsgSetsContaining(u"PLurAl"))
        self.assertEquals(found_potmsgsets, [plural_potmsgset])
        # ...translations.
        found_potmsgsets = list(
            self.devel_sr_pofile.findPOTMsgSetsContaining(u"tRANSlaTIon"))
        self.assertEquals(found_potmsgsets, [potmsgset, plural_potmsgset])
        # ...and translated plurals.
        found_potmsgsets = list(
            self.devel_sr_pofile.findPOTMsgSetsContaining(u"THIRD"))
        self.assertEquals(found_potmsgsets, [plural_potmsgset])

    def test_getTranslationsFilteredBy(self):
        # Test that filtering by submitters works.

        potmsgset = self.potmsgset

        # A person to be submitting all translations.
        submitter = self.factory.makePerson()

        # When there are no translations, empty list is returned.
        found_translations = list(
            self.devel_sr_pofile.getTranslationsFilteredBy(submitter))
        self.assertEquals(found_translations, [])

        # If 'submitter' provides a translation, it's returned in a list.
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"Translation message"],
            translator=submitter)
        found_translations = list(
            self.devel_sr_pofile.getTranslationsFilteredBy(submitter))
        self.assertEquals(found_translations, [translation])

        # If somebody else provides a translation, it's not added to the
        # list of submitter's translations.
        someone_else = self.factory.makePerson()
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"Another translation"],
            translator=someone_else)
        found_translations = list(
            self.devel_sr_pofile.getTranslationsFilteredBy(submitter))
        self.assertEquals(found_translations, [translation])

        # Adding a translation for same POTMsgSet, but to a different
        # POFile (different language) will not add the translation
        # to the list of submitter's translations for *former* POFile.
        serbian_latin = self.factory.makeLanguage(
            'sr@latin', 'Serbian Latin')

        self.devel_sr_latin_pofile = self.factory.makePOFile(
            'sr@latin', potemplate=self.devel_potemplate)
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_latin_pofile, potmsgset=potmsgset,
            translations=[u"Yet another translation"],
            translator=submitter)
        found_translations = list(
            self.devel_sr_pofile.getTranslationsFilteredBy(submitter))
        self.assertEquals(found_translations, [translation])

        # If a POTMsgSet is shared between two templates, a
        # translation is listed on both.
        potmsgset.setSequence(self.stable_potemplate, 1)
        found_translations = list(
            self.stable_sr_pofile.getTranslationsFilteredBy(submitter))
        self.assertEquals(found_translations, [translation])
        found_translations = list(
            self.devel_sr_pofile.getTranslationsFilteredBy(submitter))
        self.assertEquals(found_translations, [translation])

    def test_getPOTMsgSetTranslated_NoShared(self):
        # Test listing of translated POTMsgSets when there is no shared
        # translation for the POTMsgSet.

        # When there is no diverged translation either, nothing is returned.
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(found_translations, [])

        # When a diverged translation is added, the potmsgset is returned.
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Translation"])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(found_translations, [self.potmsgset])

        # If diverged translation is empty, POTMsgSet is not listed.
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u""])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(found_translations, [])

    def test_getPOTMsgSetTranslated_Shared(self):
        # Test listing of translated POTMsgSets when there is a shared
        # translation for the POTMsgSet as well.

        # We create a shared translation first.
        self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Shared translation"])

        # When there is no diverged translation, shared one is returned.
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(found_translations, [self.potmsgset])

        # When an empty diverged translation is added, nothing is listed.
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u""])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(found_translations, [])

        # If diverged translation is non-empty, POTMsgSet is listed.
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Translation"])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(found_translations, [self.potmsgset])

    def test_getPOTMsgSetTranslated_EmptyShared(self):
        # Test listing of translated POTMsgSets when there is an
        # empty shared translation for the POTMsgSet as well.

        # We create an empty shared translation first.
        self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u""])

        # When there is no diverged translation, shared one is returned,
        # but since it's empty, there are no results.
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(found_translations, [])

        # When an empty diverged translation is added, nothing is listed.
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u""])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(found_translations, [])

        # If diverged translation is non-empty, POTMsgSet is listed.
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Translation"])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(found_translations, [self.potmsgset])

    def test_getPOTMsgSetTranslated_Multiple(self):
        # Test listing of translated POTMsgSets if there is more than one
        # translated message.

        # Add a diverged translation on the included POTMsgSet...
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Diverged translation"])

        # and a shared translation on newly added POTMsgSet...
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate,
                                               u"Translated text")
        potmsgset.setSequence(self.devel_potemplate, 2)

        self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"Shared translation"])

        # Both POTMsgSets are listed.
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(found_translations, [self.potmsgset, potmsgset])

    def test_getPOTMsgSetUntranslated_NoShared(self):
        # Test listing of translated POTMsgSets when there is no shared
        # translation for the POTMsgSet.

        # When there is no diverged translation either, nothing is returned.
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(found_translations, [self.potmsgset])

        # When a diverged translation is added, the potmsgset is returned.
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Translation"])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(found_translations, [])

        # If diverged translation is empty, POTMsgSet is not listed.
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u""])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(found_translations, [self.potmsgset])

    def test_getPOTMsgSetUntranslated_Shared(self):
        # Test listing of translated POTMsgSets when there is a shared
        # translation for the POTMsgSet as well.

        # We create a shared translation first.
        self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Shared translation"])

        # When there is no diverged translation, shared one is returned.
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(found_translations, [])

        # When an empty diverged translation is added, nothing is listed.
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u""])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(found_translations, [self.potmsgset])

        # If diverged translation is non-empty, POTMsgSet is listed.
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Translation"])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(found_translations, [])

    def test_getPOTMsgSetUntranslated_EmptyShared(self):
        # Test listing of translated POTMsgSets when there is an
        # empty shared translation for the POTMsgSet as well.

        # We create an empty shared translation first.
        self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u""])

        # When there is no diverged translation, shared one is returned,
        # but since it's empty, there are no results.
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(found_translations, [self.potmsgset])

        # When an empty diverged translation is added, nothing is listed.
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u""])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(found_translations, [self.potmsgset])

        # If diverged translation is non-empty, POTMsgSet is listed.
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Translation"])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(found_translations, [])

    def test_getPOTMsgSetUntranslated_Multiple(self):
        # Test listing of untranslated POTMsgSets if there is more than one
        # untranslated message.

        # Add an empty translation to the included POTMsgSet...
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u""])

        # ...and a new untranslated POTMsgSet.
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate,
                                               u"Translated text")
        potmsgset.setSequence(self.devel_potemplate, 2)

        # Both POTMsgSets are listed.
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(found_translations, [self.potmsgset, potmsgset])

    def test_getPOTMsgSetWithNewSuggestions(self):
        # Test listing of POTMsgSets with unreviewed suggestions.

        # When there are no suggestions, nothing is returned.
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetWithNewSuggestions())
        self.assertEquals(found_translations, [])

        # When a suggestion is added, the potmsgset is returned.
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Suggestion"], suggestion=True)
        self.assertEquals(translation.is_current, False)

        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetWithNewSuggestions())
        self.assertEquals(found_translations, [self.potmsgset])

    def test_getPOTMsgSetWithNewSuggestions_Shared(self):
        # Test listing of suggestions for POTMsgSets with a shared
        # translation.

        # A POTMsgSet has a shared, current translation created 5 days ago.
        date_created = datetime.now(pytz.UTC)-timedelta(5)
        translation = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Translation"], date_updated=date_created)
        self.assertEquals(translation.is_current, True)

        # When there are no suggestions, nothing is returned.
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetWithNewSuggestions())
        self.assertEquals(found_translations, [])

        # When a suggestion is added one day after, the potmsgset is returned.
        suggestion_date = date_created + timedelta(1)
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Suggestion"], suggestion=True,
            date_updated=suggestion_date)
        self.assertEquals(translation.is_current, False)

        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetWithNewSuggestions())
        self.assertEquals(found_translations, [self.potmsgset])

        # Setting a suggestion as current makes it have no unreviewed
        # suggestions.
        translation.is_current = True
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetWithNewSuggestions())
        self.assertEquals(found_translations, [])

        # And adding another suggestion 2 days later, the potmsgset is
        # again returned.
        suggestion_date += timedelta(2)
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"New suggestion"], suggestion=True,
            date_updated=suggestion_date)
        self.assertEquals(translation.is_current, False)

        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetWithNewSuggestions())
        self.assertEquals(found_translations, [self.potmsgset])

    def test_getPOTMsgSetWithNewSuggestions_Diverged(self):
        # Test listing of suggestions for POTMsgSets with a shared
        # translation and a later diverged one.

        # First we create a shared translation (5 days old), a diverged
        # translation 1 day later.
        # Then we make sure that getting unreviewed messages works when:
        #  * A suggestion is added 1 day after (shows as unreviewed).
        #  * A new diverged translation is added another day later (nothing).
        #  * A new suggestion is added after another day (shows).
        #  * Suggestion is made active (nothing).

        # A POTMsgSet has a shared, current translation created 5 days ago.
        date_created = datetime.now(pytz.UTC)-timedelta(5)
        self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Shared translation"], date_updated=date_created)

        # And we also have a diverged translation created a day after shared
        # current translation.
        diverged_date = date_created + timedelta(1)
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Old translation"], date_updated=diverged_date)

        # There is also a suggestion against the shared translation
        # created 2 days after the shared translation.
        suggestion_date = date_created + timedelta(2)
        translation = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Shared suggestion"], suggestion=True,
            date_updated=suggestion_date)
        self.assertEquals(translation.is_current, False)

        # Shared suggestion is shown since diverged_date < suggestion_date.
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetWithNewSuggestions())
        self.assertEquals(found_translations, [self.potmsgset])

        # When a diverged translation is done after the shared suggestion,
        # there are no unreviewed suggestions.
        diverged_date = suggestion_date + timedelta(1)
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Translation"], date_updated=diverged_date)
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetWithNewSuggestions())
        self.assertEquals(found_translations, [])

        # When a suggestion is added one day after, the potmsgset is returned.
        suggestion_date = diverged_date + timedelta(1)
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Suggestion"], suggestion=True,
            date_updated=suggestion_date)
        self.assertEquals(translation.is_current, False)

        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetWithNewSuggestions())
        self.assertEquals(found_translations, [self.potmsgset])

        # Setting a suggestion as current makes it have no unreviewed
        # suggestions.
        translation.is_current = True
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetWithNewSuggestions())
        self.assertEquals(found_translations, [])

    def test_getPOTMsgSetWithNewSuggestions_Multiple(self):
        # Test that multiple unreviewed POTMsgSets are returned.

        # One POTMsgSet has no translations, but only a suggestion.
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"New suggestion"], suggestion=True)

        # Another POTMsgSet has both a translation and a suggestion.
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate,
                                               u"Translated text")
        potmsgset.setSequence(self.devel_potemplate, 2)
        date_created = datetime.now(pytz.UTC) - timedelta(5)
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Translation"], date_updated=date_created)
        suggestion_date = date_created + timedelta(1)
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"New suggestion"], suggestion=True,
            date_updated=suggestion_date)

        # Both POTMsgSets are listed.
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetWithNewSuggestions())
        self.assertEquals(found_translations, [self.potmsgset, potmsgset])

    def test_getPOTMsgSetWithNewSuggestions_distinct(self):
        # Provide two suggestions on a single message and make sure
        # a POTMsgSet is returned only once.
        self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile,
            potmsgset=self.potmsgset,
            translations=["A suggestion"],
            suggestion=True)
        self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile,
            potmsgset=self.potmsgset,
            translations=["Another suggestion"],
            suggestion=True)

        potmsgsets = list(
            self.devel_sr_pofile.getPOTMsgSetWithNewSuggestions())
        self.assertEquals(potmsgsets,
                          [self.potmsgset])
        self.assertEquals(
            self.devel_sr_pofile.getPOTMsgSetWithNewSuggestions().count(),
            1)

    def test_getPOTMsgSetWithNewSuggestions_empty(self):
        # Test listing of POTMsgSets with empty strings as suggestions.

        # When an empty suggestion is added, the potmsgset is NOT returned.
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u""], suggestion=True)
        self.assertEquals(False, translation.is_current)

        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetWithNewSuggestions())
        self.assertEquals([], found_translations)

    def test_getPOTMsgSetChangedInLaunchpad(self):
        # Test listing of POTMsgSets which contain changes from imports.

        # If there are no translations, nothing is listed.
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetChangedInLaunchpad())
        self.assertEquals(found_translations, [])

        # Adding a non-imported current translation doesn't change anything.
        translation = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Non-imported translation"])
        self.assertEquals(translation.is_imported, False)
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetChangedInLaunchpad())
        self.assertEquals(found_translations, [])

        # Adding an imported translation which is also current indicates
        # that there are no changes.
        translation = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Imported translation"], is_imported=True)
        self.assertEquals(translation.is_imported, True)
        self.assertEquals(translation.is_current, True)
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetChangedInLaunchpad())
        self.assertEquals(found_translations, [])

        # However, changing current translation to a non-imported one
        # makes this a changed in LP translation.
        translation = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Changed translation"], is_imported=False)
        self.assertEquals(translation.is_imported, False)
        self.assertEquals(translation.is_current, True)
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetChangedInLaunchpad())
        self.assertEquals(found_translations, [self.potmsgset])

        # Adding a diverged, non-imported translation, still lists
        # it as a changed translation.
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Diverged translation"], is_imported=False)
        self.assertEquals(translation.is_imported, False)
        self.assertEquals(translation.is_current, True)
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetChangedInLaunchpad())
        self.assertEquals(found_translations, [self.potmsgset])

        # But adding a diverged current and imported translation means
        # that it's not changed anymore.
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Diverged imported"], is_imported=True,
            force_diverged=True)
        self.assertEquals(translation.is_imported, True)
        self.assertEquals(translation.is_current, True)
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetChangedInLaunchpad())
        self.assertEquals(found_translations, [])

        # Changing from a diverged, imported translation is correctly
        # detected.
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Diverged changed"], is_imported=False)
        self.assertEquals(translation.is_imported, False)
        self.assertEquals(translation.is_current, True)
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetChangedInLaunchpad())
        self.assertEquals(found_translations, [self.potmsgset])

    def test_getPOTMsgSetChangedInLaunchpad_diverged_imported(self):
        # If there is a diverged imported (but non-current) message
        # and a shared current message, it should not be listed as changed.
        # Even though that is generally incorrect, this is a situation
        # we can't come to with new code and is a residue of old data
        # (see bug #455680 for details).

        # To hit the bug, we need:
        # 1) Shared imported and current translation.
        # 2) Diverged, imported, non-current message.
        shared = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Shared imported current"], is_imported=True)
        diverged = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Diverged imported non-current"],
            is_imported=True, force_diverged=True)
        # As we can't come to this situation using existing code,
        # we modify the is_current flag directly.
        diverged.is_current = False

        self.assertEquals(shared.is_imported, True)
        self.assertEquals(shared.is_current, True)
        self.assertIs(shared.potemplate, None)
        self.assertEquals(diverged.is_imported, True)
        self.assertEquals(diverged.is_current, False)
        self.assertEquals(diverged.potemplate, self.devel_potemplate)

        # Such POTMsgSet is not considered changed in this PO file.
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetChangedInLaunchpad())
        self.assertEquals(found_translations, [])

    def test_getPOTMsgSetChangedInLaunchpad_SharedDiverged(self):
        # Test listing of changed in LP for shared/diverged messages.

        # Adding an imported translation which is also current indicates
        # that there are no changes.
        translation = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Imported translation"], is_imported=True)
        self.assertEquals(translation.is_imported, True)
        self.assertEquals(translation.is_current, True)
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetChangedInLaunchpad())
        self.assertEquals(found_translations, [])

        # Adding a diverged, non-imported translation makes it appear
        # as changed.
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Changed translation"], is_imported=False)
        self.assertEquals(translation.is_imported, False)
        self.assertEquals(translation.is_current, True)
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetChangedInLaunchpad())
        self.assertEquals(found_translations, [self.potmsgset])

    def test_getPOTMsgSetWithErrors(self):
        # Test listing of POTMsgSets with errors in translations.
        translation = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Imported translation"], is_imported=True)
        removeSecurityProxy(translation).validation_status = (
            TranslationValidationStatus.UNKNOWNERROR)
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetWithErrors())
        self.assertEquals(found_translations, [self.potmsgset])

    def test_updateStatistics(self):
        # Test that updating statistics keeps working.

        # We are constructing a POFile with:
        #  - 2 untranslated message
        #  - 2 unreviewed suggestions (for translated and untranslated each)
        #  - 2 imported translations, out of which 1 is changed in LP
        #  - 1 LP-provided translation
        # For a total of 6 messages, 4 translated (1 from import,
        # 3 only in LP, where 1 is changed from imported).

        # First POTMsgSet (self.potmsgset) is untranslated.

        # Second POTMsgSet is untranslated, but with a suggestion.
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate)
        potmsgset.setSequence(self.devel_potemplate, 2)
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"Unreviewed suggestion"], suggestion=True)

        # Third POTMsgSet is translated, and with a suggestion.
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate)
        potmsgset.setSequence(self.devel_potemplate, 3)
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"Translation"], suggestion=False,
            date_updated=datetime.now(pytz.UTC)-timedelta(1))
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"Another suggestion"], suggestion=True)

        # Fourth POTMsgSet is translated in import.
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate)
        potmsgset.setSequence(self.devel_potemplate, 4)
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"Imported translation"], is_imported=True)

        # Fifth POTMsgSet is translated in import, but changed in LP.
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate)
        potmsgset.setSequence(self.devel_potemplate, 5)
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"Imported translation"], is_imported=True)
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"LP translation"], is_imported=False)

        # Sixth POTMsgSet is translated in LP only.
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate)
        potmsgset.setSequence(self.devel_potemplate, 6)
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"New translation"], is_imported=False)

        removeSecurityProxy(self.devel_potemplate).messagecount = (
            self.devel_potemplate.getPOTMsgSetsCount())

        # Returns current, updates, rosetta, unreviewed counts.
        stats = self.devel_sr_pofile.updateStatistics()
        self.assertEquals(stats, (1, 1, 3, 2))

        self.assertEquals(self.devel_sr_pofile.messageCount(), 6)
        self.assertEquals(self.devel_sr_pofile.translatedCount(), 4)
        self.assertEquals(self.devel_sr_pofile.untranslatedCount(), 2)
        self.assertEquals(self.devel_sr_pofile.currentCount(), 1)
        self.assertEquals(self.devel_sr_pofile.rosettaCount(), 3)
        self.assertEquals(self.devel_sr_pofile.updatesCount(), 1)
        self.assertEquals(self.devel_sr_pofile.unreviewedCount(), 2)

    def test_TranslationFileData_adapter(self):
        # Test that exporting works correctly with shared and diverged
        # messages.
        self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile,
            potmsgset=self.potmsgset,
            translations=["Shared translation"])

        # Get the adapter and extract only English singular and
        # first translation form from all messages.
        translation_file_data = getAdapter(
            self.devel_sr_pofile, ITranslationFileData, 'all_messages')
        exported_messages = [
            (msg.singular_text, msg.translations[0])
            for msg in translation_file_data.messages]
        self.assertEquals(exported_messages,
                          [(self.potmsgset.singular_text,
                            "Shared translation")])

        # When we add a diverged translation, only that is exported.
        self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile,
            potmsgset=self.potmsgset,
            translations=["Diverged translation"],
            force_diverged=True)

        # Get the adapter and extract only English singular and
        # first translation form from all messages.
        translation_file_data = getAdapter(
            self.devel_sr_pofile, ITranslationFileData, 'all_messages')
        exported_messages = [
            (msg.singular_text, msg.translations[0])
            for msg in translation_file_data.messages]
        # Only the diverged translation is exported.
        self.assertEquals(exported_messages,
                          [(self.potmsgset.singular_text,
                            "Diverged translation")])


class TestSharedPOFileCreation(TestCaseWithFactory):
    """Test that POFiles are created in shared POTemplates."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        # Create a product with two series and a shared POTemplate
        # in different series ('devel' and 'stable').
        super(TestSharedPOFileCreation, self).setUp()
        self.foo = self.factory.makeProduct(
            translations_usage=ServiceUsage.LAUNCHPAD)
        self.foo_devel = self.factory.makeProductSeries(
            name='devel', product=self.foo)
        self.foo_stable = self.factory.makeProductSeries(
            name='stable', product=self.foo)

    def test_pofile_creation_shared(self):
        # When a pofile is created in a POTemplate it is also created in
        # all shared templates.
        # POTemplate is 'shared' if it has the same name ('messages').
        devel_potemplate = self.factory.makePOTemplate(
            productseries=self.foo_devel, name="messages")
        stable_potemplate = self.factory.makePOTemplate(
            productseries=self.foo_stable, name="messages")

        self.assertEqual(None, stable_potemplate.getPOFileByLang('eo'))
        pofile_devel = devel_potemplate.newPOFile('eo')
        pofile_stable = stable_potemplate.getPOFileByLang('eo')
        self.assertNotEqual(None, pofile_stable)
        self.assertEqual(pofile_devel.language.code,
                         pofile_stable.language.code)

    def test_pofile_creation_not_shared(self):
        # When a pofile is created in a POTemplate it is not created in
        # other templates that are not shared.
        potemplate_devel_1 = self.factory.makePOTemplate(
            productseries=self.foo_devel, name="template-1")
        potemplate_stable_2 = self.factory.makePOTemplate(
            productseries=self.foo_stable, name="template-2")

        self.assertEqual(None, potemplate_devel_1.getPOFileByLang('eo'))
        potemplate_devel_1.newPOFile('eo')
        self.assertEqual(None, potemplate_stable_2.getPOFileByLang('eo'))

    def test_potemplate_creation(self):
        # When a potemplate is created it receives a copy of all pofiles in
        # all shared potemplates.
        foo_other = self.factory.makeProductSeries(
            name='other', product=self.foo)
        self.factory.makePOTemplate(
            productseries=foo_other, name="messages")
        devel_potemplate = self.factory.makePOTemplate(
            productseries=self.foo_devel, name="messages")
        # These will automatically be shared across all sharing templates.
        # They will also be created in the 'other' series.
        devel_potemplate.newPOFile('eo')
        devel_potemplate.newPOFile('de')

        stable_potemplate = self.factory.makePOTemplate(
            productseries=self.foo_stable, name="messages")

        self.assertEqual(2, len(list(stable_potemplate.pofiles)))
        self.assertNotEqual(None, stable_potemplate.getPOFileByLang('eo'))
        self.assertNotEqual(None, stable_potemplate.getPOFileByLang('de'))


class TestTranslationCredits(TestCaseWithFactory):
    """Test generation of translation credits."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestTranslationCredits, self).setUp()
        self.pofile = self.factory.makePOFile('sr')
        self.potemplate = self.pofile.potemplate

        self.potmsgset = self.factory.makePOTMsgSet(
            potemplate=self.potemplate, sequence=1)
        self.credits_potmsgset = self.factory.makePOTMsgSet(
            potemplate=self.potemplate, singular=u'translator-credits')

    def compose_launchpad_credits_text(self, imported_credits_text):
        return u"%s\n\nLaunchpad Contributions:\n  %s" % (
                imported_credits_text,
                "\n  ".join(["%s %s" % (person.displayname,
                                        canonical_url(person))
                             for person in self.pofile.contributors]))

    def test_prepareTranslationCredits_extending(self):
        # This test ensures that continuous updates to the translation credits
        # don't result in duplicate entries.
        # Only the 'translator-credits' message is covered right now.
        person = self.factory.makePerson()

        imported_credits_text = u"Imported Contributor <name@project.org>"

        # Import a translation credits message to 'translator-credits'.
        self.factory.makeTranslationMessage(
            pofile=self.pofile,
            potmsgset=self.credits_potmsgset,
            translations=[imported_credits_text],
            is_imported=True)

        # `person` updates the translation using Launchpad.
        self.factory.makeTranslationMessage(
            pofile=self.pofile,
            potmsgset=self.potmsgset,
            translator=person)

        # The first translation credits export.
        credits_text = self.pofile.prepareTranslationCredits(
            self.credits_potmsgset)
        self.assertEquals(
            self.compose_launchpad_credits_text(imported_credits_text),
            credits_text)

        # Now, re-import this generated message.
        self.factory.makeTranslationMessage(
            pofile=self.pofile,
            potmsgset=self.credits_potmsgset,
            translations=[credits_text],
            is_imported=True)

        credits_text = self.pofile.prepareTranslationCredits(
            self.credits_potmsgset)
        self.assertEquals(
            self.compose_launchpad_credits_text(imported_credits_text),
            credits_text)


class TestTranslationPOFilePOTMsgSetOrdering(TestCaseWithFactory):
    """Test ordering of POTMsgSets as returned by PO file methods."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        # Create a product with two series and a shared POTemplate
        # in different series ('devel' and 'stable').
        super(TestTranslationPOFilePOTMsgSetOrdering, self).setUp()
        self.foo = self.factory.makeProduct(
            translations_usage=ServiceUsage.LAUNCHPAD)
        self.foo_devel = self.factory.makeProductSeries(
            name='devel', product=self.foo)
        self.foo_stable = self.factory.makeProductSeries(
            name='stable', product=self.foo)

        # POTemplate is 'shared' if it has the same name ('messages').
        self.devel_potemplate = self.factory.makePOTemplate(
            productseries=self.foo_devel, name="messages")
        self.stable_potemplate = self.factory.makePOTemplate(self.foo_stable,
                                                             name="messages")

        # We'll use two PO files, one for each series.
        self.devel_sr_pofile = self.factory.makePOFile(
            'sr', self.devel_potemplate)
        self.stable_sr_pofile = self.factory.makePOFile(
            'sr', self.stable_potemplate)

        # Create two POTMsgSets that can be used to test in what order
        # are they returned.  Add them only to devel_potemplate sequentially.
        self.potmsgset1 = self.factory.makePOTMsgSet(self.devel_potemplate)
        self.potmsgset1.setSequence(self.devel_potemplate, 1)
        self.potmsgset2 = self.factory.makePOTMsgSet(self.devel_potemplate)
        self.potmsgset2.setSequence(self.devel_potemplate, 2)

    def test_getPOTMsgSetTranslated_ordering(self):
        # Translate both POTMsgSets in devel_sr_pofile, so
        # they are returned with getPOTMsgSetTranslated() call.
        self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile,
            potmsgset=self.potmsgset1,
            translations=["Shared translation"])
        self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile,
            potmsgset=self.potmsgset2,
            translations=["Another shared translation"])

        translated_potmsgsets = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(translated_potmsgsets,
                          [self.potmsgset1, self.potmsgset2])

        # Insert these two POTMsgSets into self.stable_potemplate in reverse
        # order.
        self.potmsgset2.setSequence(self.stable_potemplate, 1)
        self.potmsgset1.setSequence(self.stable_potemplate, 2)

        # And they are returned in the new order as desired.
        translated_potmsgsets = list(
            self.stable_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(translated_potmsgsets,
                          [self.potmsgset2, self.potmsgset1])

        # Order is unchanged for the previous template.
        translated_potmsgsets = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(translated_potmsgsets,
                          [self.potmsgset1, self.potmsgset2])

    def test_getPOTMsgSetUntranslated_ordering(self):
        # Both POTMsgSets in devel_sr_pofile are untranslated.
        untranslated_potmsgsets = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(untranslated_potmsgsets,
                          [self.potmsgset1, self.potmsgset2])

        # Insert these two POTMsgSets into self.stable_potemplate in reverse
        # order.
        self.potmsgset2.setSequence(self.stable_potemplate, 1)
        self.potmsgset1.setSequence(self.stable_potemplate, 2)

        # And they are returned in the new order as desired.
        untranslated_potmsgsets = list(
            self.stable_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(untranslated_potmsgsets,
                          [self.potmsgset2, self.potmsgset1])

        # Order is unchanged for the previous template.
        untranslated_potmsgsets = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(untranslated_potmsgsets,
                          [self.potmsgset1, self.potmsgset2])

    def test_getPOTMsgSetChangedInLaunchpad_ordering(self):
        # Suggest a translation on both POTMsgSets in devel_sr_pofile,
        # so they are returned with getPOTMsgSetWithNewSuggestions() call.
        self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile,
            potmsgset=self.potmsgset1,
            translations=["Imported"],
            is_imported=True)
        self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile,
            potmsgset=self.potmsgset1,
            translations=["Changed"],
            is_imported=False)
        self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile,
            potmsgset=self.potmsgset2,
            translations=["Another imported"],
            is_imported=True)
        self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile,
            potmsgset=self.potmsgset2,
            translations=["Another changed"],
            is_imported=False)

        potmsgsets = list(
            self.devel_sr_pofile.getPOTMsgSetChangedInLaunchpad())
        self.assertEquals(potmsgsets,
                          [self.potmsgset1, self.potmsgset2])

        # Insert these two POTMsgSets into self.stable_potemplate in reverse
        # order.
        self.potmsgset2.setSequence(self.stable_potemplate, 1)
        self.potmsgset1.setSequence(self.stable_potemplate, 2)

        # And they are returned in the new order as desired.
        potmsgsets = list(
            self.stable_sr_pofile.getPOTMsgSetChangedInLaunchpad())
        self.assertEquals(potmsgsets,
                          [self.potmsgset2, self.potmsgset1])

        # Order is unchanged for the previous template.
        potmsgsets = list(
            self.devel_sr_pofile.getPOTMsgSetChangedInLaunchpad())
        self.assertEquals(potmsgsets,
                          [self.potmsgset1, self.potmsgset2])

    def test_getPOTMsgSetWithErrors_ordering(self):
        # Suggest a translation on both POTMsgSets in devel_sr_pofile,
        # so they are returned with getPOTMsgSetWithNewSuggestions() call.
        imported1 = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile,
            potmsgset=self.potmsgset1,
            translations=["Imported"],
            is_imported=True)
        removeSecurityProxy(imported1).validation_status = (
            TranslationValidationStatus.UNKNOWNERROR)
        imported2 = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile,
            potmsgset=self.potmsgset2,
            translations=["Another imported"],
            is_imported=True)
        removeSecurityProxy(imported2).validation_status = (
            TranslationValidationStatus.UNKNOWNERROR)

        potmsgsets = list(
            self.devel_sr_pofile.getPOTMsgSetWithErrors())
        self.assertEquals(potmsgsets,
                          [self.potmsgset1, self.potmsgset2])

        # Insert these two POTMsgSets into self.stable_potemplate in reverse
        # order.
        self.potmsgset2.setSequence(self.stable_potemplate, 1)
        self.potmsgset1.setSequence(self.stable_potemplate, 2)

        # And they are returned in the new order as desired.
        potmsgsets = list(
            self.stable_sr_pofile.getPOTMsgSetWithErrors())
        self.assertEquals(potmsgsets,
                          [self.potmsgset2, self.potmsgset1])

        # Order is unchanged for the previous template.
        potmsgsets = list(
            self.devel_sr_pofile.getPOTMsgSetWithErrors())
        self.assertEquals(potmsgsets,
                          [self.potmsgset1, self.potmsgset2])

    def test_getPOTMsgSets_ordering(self):
        # Both POTMsgSets in devel_potemplate are untranslated.
        potmsgsets = list(
            self.devel_potemplate.getPOTMsgSets())
        self.assertEquals(potmsgsets,
                          [self.potmsgset1, self.potmsgset2])

        # Insert these two POTMsgSets into self.stable_potemplate in reverse
        # order.
        self.potmsgset2.setSequence(self.stable_potemplate, 1)
        self.potmsgset1.setSequence(self.stable_potemplate, 2)

        # And they are returned in the new order as desired.
        potmsgsets = list(
            self.stable_potemplate.getPOTMsgSets())
        self.assertEquals(potmsgsets,
                          [self.potmsgset2, self.potmsgset1])

        # Order is unchanged for the previous template.
        potmsgsets = list(
            self.devel_potemplate.getPOTMsgSets())
        self.assertEquals(potmsgsets,
                          [self.potmsgset1, self.potmsgset2])

    def test_findPOTMsgSetsContaining_ordering(self):
        # As per bug 388473 findPOTMsgSetsContaining still used the old
        # potmsgset.sequence for ordering. Check that this is fixed.
        # This test will go away when potmsgset.sequence goes away.

        # Give the method something to search for.
        self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile,
            potmsgset=self.potmsgset1,
            translations=["Shared translation"])
        self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile,
            potmsgset=self.potmsgset2,
            translations=["Another shared translation"])

        # Mess with potmsgset.sequence.
        removeSecurityProxy(self.potmsgset1).sequence = 2
        removeSecurityProxy(self.potmsgset2).sequence = 1

        potmsgsets = list(
            self.devel_sr_pofile.findPOTMsgSetsContaining("translation"))

        # Order ignores potmsgset.sequence.
        self.assertEquals([self.potmsgset1, self.potmsgset2],
                          potmsgsets)


class TestPOFileSet(TestCaseWithFactory):
    """Test PO file set methods."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        # Create a POFileSet to work with.
        super(TestPOFileSet, self).setUp()
        self.pofileset = getUtility(IPOFileSet)

    def test_POFileSet_getPOFilesTouchedSince_none(self):
        # Make sure getPOFilesTouchedSince returns nothing
        # when there are no touched PO files.
        now = datetime.now(pytz.UTC)
        pofiles = self.pofileset.getPOFilesTouchedSince(now)
        self.assertContentEqual([], pofiles)

        week_ago = now - timedelta(7)
        pofiles = self.pofileset.getPOFilesTouchedSince(week_ago)
        self.assertContentEqual([], pofiles)

        # Even when a POFile is touched, but earlier than
        # what we are looking for, nothing is returned.
        pofile = self.factory.makePOFile('sr')
        pofile.date_changed = week_ago
        pofiles = self.pofileset.getPOFilesTouchedSince(now)
        self.assertContentEqual([], pofiles)

    def test_POFileSet_getPOFilesTouchedSince_unshared(self):
        # Make sure actual touched POFiles are returned by
        # getPOFilesTouchedSince.
        now = datetime.now(pytz.UTC)
        yesterday = now - timedelta(1)

        new_pofile = self.factory.makePOFile('sr')
        new_pofile.date_changed = now
        pofiles = self.pofileset.getPOFilesTouchedSince(yesterday)
        self.assertContentEqual([new_pofile], pofiles)

        # An older file means is not returned.
        week_ago = now - timedelta(7)
        old_pofile = self.factory.makePOFile('sr')
        old_pofile.date_changed = week_ago
        pofiles = self.pofileset.getPOFilesTouchedSince(yesterday)
        self.assertContentEqual([new_pofile], pofiles)

        # Unless we extend the time period we ask for.
        pofiles = self.pofileset.getPOFilesTouchedSince(week_ago)
        self.assertContentEqual([new_pofile, old_pofile], pofiles)

    def test_POFileSet_getPOFilesTouchedSince_shared_in_product(self):
        # Make sure actual touched POFiles and POFiles that are sharing
        # with them in the same product are all returned by
        # getPOFilesTouchedSince.

        # We create a product with two series, and attach
        # a POTemplate and Serbian POFile to each, making
        # sure they share translations (potemplates have the same name).
        product = self.factory.makeProduct(
            translations_usage=ServiceUsage.LAUNCHPAD)
        series1 = self.factory.makeProductSeries(product=product,
                                                 name='one')
        series2 = self.factory.makeProductSeries(product=product,
                                                 name='two')
        potemplate1 = self.factory.makePOTemplate(name='shared',
                                                  productseries=series1)
        pofile1 = self.factory.makePOFile('sr', potemplate=potemplate1)
        potemplate2 = self.factory.makePOTemplate(name='shared',
                                                  productseries=series2)
        pofile2 = potemplate2.getPOFileByLang('sr')

        now = datetime.now(pytz.UTC)
        yesterday = now - timedelta(1)
        pofiles = self.pofileset.getPOFilesTouchedSince(yesterday)
        self.assertContentEqual([pofile1, pofile2], pofiles)

        # Even if one of the sharing POFiles is older, it's still returned.
        week_ago = now - timedelta(7)
        pofile2.date_changed = week_ago
        pofiles = self.pofileset.getPOFilesTouchedSince(yesterday)
        self.assertContentEqual([pofile1, pofile2], pofiles)

        # A POFile in a different language is not returned.
        pofile3 = self.factory.makePOFile('de', potemplate=potemplate2)
        pofile3.date_changed = week_ago
        pofiles = self.pofileset.getPOFilesTouchedSince(yesterday)
        self.assertContentEqual([pofile1, pofile2], pofiles)

    def test_POFileSet_getPOFilesTouchedSince_smaller_ids(self):
        # Make sure that all relevant POFiles are returned,
        # even the sharing ones with smaller IDs.
        # This is a test for bug #414832 which caused sharing POFiles
        # of the touched POFile not to be returned if they had
        # IDs smaller than the touched POFile.
        product = self.factory.makeProduct(
            translations_usage=ServiceUsage.LAUNCHPAD)
        series1 = self.factory.makeProductSeries(product=product,
                                                 name='one')
        series2 = self.factory.makeProductSeries(product=product,
                                                 name='two')
        potemplate1 = self.factory.makePOTemplate(name='shared',
                                                  productseries=series1)
        pofile1 = self.factory.makePOFile('sr', potemplate=potemplate1)
        potemplate2 = self.factory.makePOTemplate(name='shared',
                                                  productseries=series2)
        pofile2 = potemplate2.getPOFileByLang('sr')
        now = datetime.now(pytz.UTC)
        yesterday = now - timedelta(1)
        week_ago = now - timedelta(7)
        pofile1.date_changed = week_ago

        # Let's make sure the condition from the bug holds,
        # since pofile2 is created implicitely with the makePOTemplate call.
        self.assertTrue(pofile1.id < pofile2.id)
        pofiles = self.pofileset.getPOFilesTouchedSince(yesterday)
        self.assertContentEqual([pofile1, pofile2], pofiles)

    def test_POFileSet_getPOFilesTouchedSince_shared_in_distribution(self):
        # Make sure actual touched POFiles and POFiles that are sharing
        # with them in the same distribution/sourcepackage are all returned
        # by getPOFilesTouchedSince.

        # We create a distribution with two series with the same
        # sourcepackage in both, and attach a POTemplate and Serbian
        # POFile to each, making sure they share translations
        # (potemplates have the same name).
        distro = self.factory.makeDistribution()
        distro.translations_usage = ServiceUsage.LAUNCHPAD
        series1 = self.factory.makeDistroRelease(distribution=distro,
                                                 name='one')
        sourcepackagename = self.factory.makeSourcePackageName()
        potemplate1 = self.factory.makePOTemplate(
            name='shared', distroseries=series1,
            sourcepackagename=sourcepackagename)
        pofile1 = self.factory.makePOFile('sr', potemplate=potemplate1)

        series2 = self.factory.makeDistroRelease(distribution=distro,
                                                 name='two')
        potemplate2 = self.factory.makePOTemplate(
            name='shared', distroseries=series2,
            sourcepackagename=sourcepackagename)
        pofile2 = potemplate2.getPOFileByLang('sr')

        # Now the test actually starts.
        now = datetime.now(pytz.UTC)
        yesterday = now - timedelta(1)
        pofiles = self.pofileset.getPOFilesTouchedSince(yesterday)
        self.assertContentEqual([pofile1, pofile2], pofiles)

        # Even if one of the sharing POFiles is older, it's still returned.
        week_ago = now - timedelta(7)
        pofile2.date_changed = week_ago
        pofiles = self.pofileset.getPOFilesTouchedSince(yesterday)
        self.assertContentEqual([pofile1, pofile2], pofiles)

        # A POFile in a different language is not returned.
        pofile3 = self.factory.makePOFile('de', potemplate=potemplate2)
        pofile3.date_changed = week_ago
        pofiles = self.pofileset.getPOFilesTouchedSince(yesterday)
        self.assertContentEqual([pofile1, pofile2], pofiles)

    def test_POFileSet_getPOFilesTouchedSince_external_pofiles(self):
        # Make sure POFiles which are in different products
        # are not returned even though they have the same potemplate name.
        series1 = self.factory.makeProductSeries(name='one')
        series1.product.translations_usage = ServiceUsage.LAUNCHPAD
        series2 = self.factory.makeProductSeries(name='two')
        series1.product.translations_usage = ServiceUsage.LAUNCHPAD
        self.assertNotEqual(series1.product, series2.product)

        potemplate1 = self.factory.makePOTemplate(name='shared',
                                                  productseries=series1)
        pofile1 = self.factory.makePOFile('sr', potemplate=potemplate1)

        potemplate2 = self.factory.makePOTemplate(name='shared',
                                                  productseries=series2)
        pofile2 = self.factory.makePOFile('sr', potemplate=potemplate2)

        # Now the test actually starts.
        now = datetime.now(pytz.UTC)
        yesterday = now - timedelta(1)
        week_ago = now - timedelta(7)

        # Second POFile has been modified earlier than yesterday,
        # and is attached to a different product, even if the template
        # name is the same.  It's not returned.
        pofile2.date_changed = week_ago
        pofiles = self.pofileset.getPOFilesTouchedSince(yesterday)
        self.assertContentEqual([pofile1], pofiles)

    def test_getPOFilesWithTranslationCredits(self):
        # Initially, we only get data from the sampledata.
        sampledata_pofiles = list(
            self.pofileset.getPOFilesWithTranslationCredits())
        total = len(sampledata_pofiles)
        self.assertEquals(3, total)

        def list_of_tuples_into_list(list_of_tuples):
            return [item[0] for item in list_of_tuples]

        # All POFiles with translation credits messages are
        # returned along with relevant POTMsgSets.
        potemplate1 = self.factory.makePOTemplate()
        self.factory.makePOTMsgSet(
            potemplate1, singular=u'translator-credits', sequence=1)

        sr_pofile = self.factory.makePOFile('sr', potemplate=potemplate1)
        self.assertIn(sr_pofile,
                      list_of_tuples_into_list(
                          self.pofileset.getPOFilesWithTranslationCredits()))
        self.assertEquals(
            total + 1,
            self.pofileset.getPOFilesWithTranslationCredits().count())

        # If there's another POFile on this template, it's returned as well.
        de_pofile = self.factory.makePOFile('de', potemplate=potemplate1)
        self.assertIn(de_pofile,
                      list_of_tuples_into_list(
                          self.pofileset.getPOFilesWithTranslationCredits()))

        # If another POTemplate has a translation credits message, it's
        # returned as well.
        potemplate2 = self.factory.makePOTemplate()
        self.factory.makePOTMsgSet(
            potemplate2, singular=u'Your names',
            context=u'NAME OF TRANSLATORS', sequence=1)
        sr_kde_pofile = self.factory.makePOFile('sr', potemplate=potemplate2)
        self.assertIn(sr_kde_pofile,
                      list_of_tuples_into_list(
                          self.pofileset.getPOFilesWithTranslationCredits()))

        # And let's confirm that the full listing contains all of the
        # above.
        all_pofiles = list_of_tuples_into_list(sampledata_pofiles)
        all_pofiles.extend([sr_pofile, de_pofile, sr_kde_pofile])
        self.assertContentEqual(
            all_pofiles,
            list_of_tuples_into_list(
                self.pofileset.getPOFilesWithTranslationCredits()))

    def test_getPOFilesWithTranslationCredits_untranslated(self):
        # We need absolute DB access to be able to remove a translation
        # message.
        LaunchpadZopelessLayer.switchDbUser('postgres')

        # Initially, we only get data from the sampledata, all of which
        # are untranslated.
        sampledata_pofiles = list(
            self.pofileset.getPOFilesWithTranslationCredits(
                untranslated=True))
        total = len(sampledata_pofiles)
        self.assertEquals(3, total)

        # All POFiles with translation credits messages are
        # returned along with relevant POTMsgSets.
        potemplate1 = self.factory.makePOTemplate()
        credits_potmsgset = self.factory.makePOTMsgSet(
            potemplate1, singular=u'translator-credits', sequence=1)

        sr_pofile = self.factory.makePOFile('sr', potemplate=potemplate1)
        pofiles_with_credits = (
            self.pofileset.getPOFilesWithTranslationCredits(
                untranslated=True))
        self.assertNotIn((sr_pofile, credits_potmsgset),
                         list(pofiles_with_credits))
        self.assertEquals(
            total,
            pofiles_with_credits.count())

        # Removing a translation for this message, removes it
        # from a result set when untranslated=True is passed in.
        message = credits_potmsgset.getSharedTranslationMessage(
            sr_pofile.language)
        message.destroySelf()
        pofiles_with_credits = (
            self.pofileset.getPOFilesWithTranslationCredits(
                untranslated=True))
        self.assertIn((sr_pofile, credits_potmsgset),
                      list(pofiles_with_credits))
        self.assertEquals(
            total + 1,
            pofiles_with_credits.count())

    def test_getPOFilesByPathAndOrigin_path_mismatch(self):
        # getPOFilesByPathAndOrigin matches on POFile path.
        template = self.factory.makePOTemplate()
        template.newPOFile('ta')

        not_found = self.pofileset.getPOFilesByPathAndOrigin(
            'tu.po', distroseries=template.distroseries,
            sourcepackagename=template.sourcepackagename,
            productseries=template.productseries)

        self.assertContentEqual([], not_found)

    def test_getPOFilesByPathAndOrigin_productseries_none(self):
        # getPOFilesByPathAndOrigin returns an empty result set if a
        # ProductSeries search matches no POFiles.
        productseries = self.factory.makeProductSeries()

        # Look for zh.po, which does not exist.
        not_found = self.pofileset.getPOFilesByPathAndOrigin(
            'zh.po', productseries=productseries)

        self.assertContentEqual([], not_found)

    def test_getPOFilesByPathAndOrigin_productseries(self):
        # getPOFilesByPathAndOrigin finds a POFile for a productseries.
        productseries = self.factory.makeProductSeries()
        template = self.factory.makePOTemplate(productseries=productseries)
        pofile = template.newPOFile('nl')
        removeSecurityProxy(pofile).path = 'nl.po'

        found = self.pofileset.getPOFilesByPathAndOrigin(
            'nl.po', productseries=productseries)

        self.assertContentEqual([pofile], found)

    def test_getPOFilesByPathAndOrigin_sourcepackage_none(self):
        # getPOFilesByPathAndOrigin returns an empty result set if a
        # source-package search matches no POFiles.
        package = self.factory.makeSourcePackage()

        # Look for no.po, which does not exist.
        not_found = self.pofileset.getPOFilesByPathAndOrigin(
            'no.po', distroseries=package.distroseries,
            sourcepackagename=package.sourcepackagename)

        self.assertContentEqual([], not_found)

    def test_getPOFilesByPathAndOrigin_sourcepackage(self):
        # getPOFilesByPathAndOrigin finds a POFile for a source package
        # name.
        package = self.factory.makeSourcePackage()
        template = self.factory.makePOTemplate(
            distroseries=package.distroseries,
            sourcepackagename=package.sourcepackagename)
        pofile = template.newPOFile('kk')
        removeSecurityProxy(pofile).path = 'kk.po'

        found = self.pofileset.getPOFilesByPathAndOrigin(
            'kk.po', distroseries=package.distroseries,
            sourcepackagename=package.sourcepackagename)

        self.assertContentEqual([pofile], found)

    def test_getPOFilesByPathAndOrigin_from_sourcepackage_none(self):
        # getPOFilesByPathAndOrigin returns an empty result set if a
        # from-source-package search matches no POFiles.
        upload_package = self.factory.makeSourcePackage()

        # Look for la.po, which does not exist.
        not_found = self.pofileset.getPOFilesByPathAndOrigin(
            'la.po', distroseries=upload_package.distroseries,
            sourcepackagename=upload_package.sourcepackagename)

        self.assertContentEqual([], not_found)

    def test_getPOFilesByPathAndOrigin_from_sourcepackage(self):
        # getPOFilesByPathAndOrigin finds a POFile for the source
        # package it was uploaded for (which may not be the same as the
        # source package it's actually in).
        upload_package = self.factory.makeSourcePackage()
        distroseries = upload_package.distroseries
        target_package = self.factory.makeSourcePackage(
            distroseries=distroseries)
        template = self.factory.makePOTemplate(
            distroseries=distroseries,
            sourcepackagename=target_package.sourcepackagename)
        removeSecurityProxy(template).from_sourcepackagename = (
            upload_package.sourcepackagename)
        pofile = template.newPOFile('ka')
        removeSecurityProxy(pofile).path = 'ka.po'
        removeSecurityProxy(pofile).from_sourcepackagename = (
            upload_package.sourcepackagename)

        found = self.pofileset.getPOFilesByPathAndOrigin(
            'ka.po', distroseries=distroseries,
            sourcepackagename=upload_package.sourcepackagename)

        self.assertContentEqual([pofile], found)


class TestPOFileStatistics(TestCaseWithFactory):
    """Test PO files statistics calculation."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        # Create a POFile to calculate statistics on.
        super(TestPOFileStatistics, self).setUp()
        self.pofile = self.factory.makePOFile('sr')
        self.potemplate = self.pofile.potemplate

        # Create a single POTMsgSet that is used across all tests,
        # and add it to only one of the POTemplates.
        self.potmsgset = self.factory.makePOTMsgSet(self.potemplate,
                                                    sequence=1)

    def test_POFile_updateStatistics_currentCount(self):
        # Make sure count of translations which are active both
        # in import and in Launchpad is correct.
        self.pofile.updateStatistics()
        self.assertEquals(self.pofile.currentCount(), 0)

        # Adding an imported translation increases currentCount().
        self.factory.makeTranslationMessage(
            pofile=self.pofile,
            potmsgset=self.potmsgset,
            translations=["Imported current"],
            is_imported=True)
        self.pofile.updateStatistics()
        self.assertEquals(self.pofile.currentCount(), 1)

        # Adding a suggestion (i.e. unused translation)
        # will not change the current count when there's
        # already an imported message.
        self.factory.makeTranslationMessage(
            pofile=self.pofile,
            potmsgset=self.potmsgset,
            translations=["A suggestion"],
            suggestion=True)
        self.pofile.updateStatistics()
        self.assertEquals(self.pofile.currentCount(), 1)

    def test_POFile_updateStatistics_newCount(self):
        # Make sure count of translations which are provided
        # only in Launchpad (and not in imports) is correct.
        self.pofile.updateStatistics()
        self.assertEquals(self.pofile.newCount(), 0)

        # Adding a current translation for an untranslated
        # message increases the count of new translations in LP.
        self.factory.makeTranslationMessage(
            pofile=self.pofile,
            potmsgset=self.potmsgset,
            translations=["Current"])
        self.pofile.updateStatistics()
        self.assertEquals(self.pofile.newCount(), 1)

    def test_POFile_updateStatistics_newCount_reimporting(self):
        # If we get an 'imported' translation for what
        # we already have as 'new', it's not considered 'new'
        # anymore since it has been synced.
        self.factory.makeTranslationMessage(
            pofile=self.pofile,
            potmsgset=self.potmsgset,
            translations=["Current"])
        # Reimport it but with is_imported=True.
        self.factory.makeTranslationMessage(
            pofile=self.pofile,
            potmsgset=self.potmsgset,
            translations=["Current"],
            is_imported=True)

        self.pofile.updateStatistics()
        self.assertEquals(self.pofile.newCount(), 0)

    def test_POFile_updateStatistics_newCount_changed(self):
        # If we change an 'imported' translation through
        # Launchpad, it's still not considered 'new',
        # but an 'update' instead.
        self.factory.makeTranslationMessage(
            pofile=self.pofile,
            potmsgset=self.potmsgset,
            translations=["Imported"],
            is_imported=True)
        self.factory.makeTranslationMessage(
            pofile=self.pofile,
            potmsgset=self.potmsgset,
            translations=["Changed"])
        self.pofile.updateStatistics()
        self.assertEquals(self.pofile.newCount(), 0)
        self.assertEquals(self.pofile.updatesCount(), 1)


class TestPOFile(TestCaseWithFactory):
    """Test PO file methods."""

    layer = ZopelessDatabaseLayer

    # The sequence number 0 is put at the beginning of the data to verify that
    # it really gets sorted to the end.
    TEST_MESSAGES = [
        {'msgid':'computer', 'string':'komputilo', 'sequence':0},
        {'msgid':'mouse', 'string':'muso', 'sequence':0},
        {'msgid':'Good morning', 'string':'Bonan matenon', 'sequence':2},
        {'msgid':'Thank you', 'string':'Dankon', 'sequence':1},
        ]
    EXPECTED_SEQUENCE = [1, 2, 0, 0]

    def setUp(self):
        # Create a POFile to calculate statistics on.
        super(TestPOFile, self).setUp()
        self.pofile = self.factory.makePOFile('eo')
        self.potemplate = self.pofile.potemplate

    def test_makeTranslatableMessage(self):
        # TranslatableMessages can be created from the PO file
        potmsgset = self.factory.makePOTMsgSet(self.potemplate, sequence=1)
        message = self.pofile.makeTranslatableMessage(potmsgset)
        verifyObject(ITranslatableMessage, message)

    def _createMessageSet(self, testmsg):
        # Create a message set from the test data.
        pomsgset = self.factory.makePOTMsgSet(
            self.potemplate, testmsg['msgid'], sequence=testmsg['sequence'])
        pomsgset.updateTranslation(
            self.pofile, self.pofile.owner,
            {0: testmsg['string'], },
            True, None, force_edition_rights=True)

    def test_getTranslationRows_sequence(self):
        # Test for correct sorting of obsolete messages (where sequence=0).
        [self._createMessageSet(msg) for msg in self.TEST_MESSAGES]
        for rownum, row in enumerate(
            self.pofile.getTranslationRows()):
            self.failUnlessEqual(
                row.sequence, self.EXPECTED_SEQUENCE[rownum],
                "getTranslationRows does not sort obsolete messages "
                "(sequence=0) to the end of the file.")


class TestPOFileTranslationMessages(TestCaseWithFactory):
    """Test PO file getTranslationMessages method."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestPOFileTranslationMessages, self).setUp()
        self.pofile = self.factory.makePOFile('eo')
        self.potemplate = self.pofile.potemplate
        self.potmsgset = self.factory.makePOTMsgSet(
            self.potemplate, sequence=1)

    def test_getTranslationMessages_current_shared(self):
        # A shared message is included in this POFile's messages.
        message = self.factory.makeTranslationMessage(
            potmsgset=self.potmsgset, pofile=self.pofile, force_shared=True)

        self.assertEqual(
            [message], list(self.pofile.getTranslationMessages()))

    def test_getTranslationMessages_current_diverged(self):
        # A diverged message is included in this POFile's messages.
        message = self.factory.makeTranslationMessage(
            potmsgset=self.potmsgset, pofile=self.pofile, force_diverged=True)

        self.assertEqual(
            [message], list(self.pofile.getTranslationMessages()))

    def test_getTranslationMessages_suggestion(self):
        # A suggestion is included in this POFile's messages.
        message = self.factory.makeTranslationMessage(
            potmsgset=self.potmsgset, pofile=self.pofile)

        self.assertEqual(
            [message], list(self.pofile.getTranslationMessages()))

    def test_getTranslationMessages_obsolete(self):
        # A message on an obsolete POTMsgSEt is included in this
        # POFile's messages.
        potmsgset = self.factory.makePOTMsgSet(self.potemplate, sequence=0)
        message = self.factory.makeTranslationMessage(
            potmsgset=potmsgset, pofile=self.pofile, force_shared=True)

        self.assertEqual(
            [message], list(self.pofile.getTranslationMessages()))

    def test_getTranslationMessages_other_pofile(self):
        # A message from another POFiles is not included.
        other_pofile = self.factory.makePOFile('de')
        self.factory.makeTranslationMessage(
            potmsgset=self.potmsgset, pofile=other_pofile)

        self.assertEqual([], list(self.pofile.getTranslationMessages()))

    def test_getTranslationMessages_condition_matches(self):
        # A message matching the given condition is included.
        # Diverged messages are linked to a specific POTemplate.
        message = self.factory.makeTranslationMessage(
            potmsgset=self.potmsgset, pofile=self.pofile, force_diverged=True)

        self.assertContentEqual(
            [message],
            self.pofile.getTranslationMessages(
                "TranslationMessage.potemplate IS NOT NULL"))

    def test_getTranslationMessages_condition_matches_not(self):
        # A message not matching the given condition is excluded.
        # Shared messages are not linked to a POTemplate.
        self.factory.makeTranslationMessage(
            potmsgset=self.potmsgset, pofile=self.pofile, force_shared=True)

        self.assertContentEqual(
            [],
            self.pofile.getTranslationMessages(
                "TranslationMessage.potemplate IS NOT NULL"))

    def test_getTranslationMessages_condition_matches_in_other_pofile(self):
        # A message matching given condition but located in another POFile
        # is not included.
        other_pofile = self.factory.makePOFile('de')
        self.factory.makeTranslationMessage(
            potmsgset=self.potmsgset, pofile=other_pofile,
            force_diverged=True)

        self.assertContentEqual(
            [],
            self.pofile.getTranslationMessages(
                "TranslationMessage.potemplate IS NOT NULL"))

    def test_getTranslationMessages_diverged_elsewhere(self):
        # Diverged messages from sharing POTemplates are not included.
        # Create a sharing potemplate in another product series and share
        # potmsgset in both templates.
        other_series = self.factory.makeProductSeries(
            product=self.potemplate.productseries.product)
        other_template = self.factory.makePOTemplate(
            productseries=other_series, name=self.potemplate.name)
        other_pofile = other_template.getPOFileByLang(
            self.pofile.language.code)
        self.potmsgset.setSequence(other_template, 1)
        self.factory.makeTranslationMessage(
            potmsgset=self.potmsgset, pofile=other_pofile,
            force_diverged=True)

        self.assertEqual([], list(self.pofile.getTranslationMessages()))


class TestPOFileToTranslationFileDataAdapter(TestCaseWithFactory):
    """Test POFile being adapted to IPOFileToTranslationFileData."""

    layer = ZopelessDatabaseLayer

    header = dedent("""
        Project-Id-Version: foo
        Report-Msgid-Bugs-To:
        POT-Creation-Date: 2007-07-09 03:39+0100
        PO-Revision-Date: 2001-09-09 01:46+0000
        Last-Translator: Kubla Kahn <kk@pleasure-dome.com>
        Language-Team: Serbian <sr@li.org>
        MIME-Version: 1.0
        Content-Type: text/plain; charset=UTF-8
        Content-Transfer-Encoding: 8bit
        Plural-Forms: %s""")

    western_plural = "nplurals=2; plural=(n != 1)"
    other_2_plural = "nplurals=2; plural=(n > 0)"
    generic_plural = "nplurals=INTEGER; plural=EXPRESSION"
    serbian3_plural = ("nplurals=3; plural=(n%10==1 && n%100!=11 "
                      "? 0 : n%10>=2 && n%10<=4 && (n% 100<10 || n%100>=20) "
                      "? 1 : 2)")
    serbian4_plural = ("nplurals=4; plural=(n==1 ? 3 : (n%10==1 && n%100!=11 "
                      "? 0 : n%10>=2 && n%10<=4 && (n% 100<10 || n%100>=20) "
                      "? 1 : 2))")
    plural_template = "nplurals=%d; plural=%s"

    def _makePOFileWithPlural(self, language_code):
        pofile = removeSecurityProxy(self.factory.makePOFile(language_code))
        self.factory.makePOTMsgSet(
            pofile.potemplate, singular=u"Foo", plural=u"Bar", sequence=1)
        return pofile

    def test_header_pluralform_equal(self):
        # If the number of plural forms in the header is equal to that in the
        # language entry, use the data from the language entry.
        sr_pofile = self._makePOFileWithPlural('sr')
        sr_pofile.header = self.header % self.serbian3_plural

        translation_file_data = getAdapter(
            sr_pofile, ITranslationFileData, 'all_messages')
        self.assertEqual(3, translation_file_data.header.number_plural_forms)
        # The expression from the header starts with a "(", the language entry
        # does not.
        self.assertEqual(
            u"n%10==1 && n%100!=11",
            translation_file_data.header.plural_form_expression[:20])

    def test_header_pluralform_larger(self):
        # If the number of plural forms in the header is larger than in the
        # language entry, use the data from the header.
        sr_pofile = self._makePOFileWithPlural('sr')
        sr_pofile.header = self.header % self.serbian4_plural

        translation_file_data = getAdapter(
            sr_pofile, ITranslationFileData, 'all_messages')
        self.assertEqual(4, translation_file_data.header.number_plural_forms)
        self.assertEqual(
            u"(n==1 ? 3 : (n%10==1",
            translation_file_data.header.plural_form_expression[:20])

    def test_header_pluralform_larger_but_western(self):
        # If the plural form expression in the header is the standard western
        # expression, use the data from the language entry if present.
        # Use Japanese because it has only one plural form which is less
        # than the 2 the western style has.
        ja_pofile = self._makePOFileWithPlural('ja')
        # The expression comes in different forms.
        for expr in ('(n != 1)', '1 != n', 'n>1', '(1 < n)'):
            plural_info = self.plural_template % (2, expr)
            ja_pofile.header = self.header % plural_info

            translation_file_data = getAdapter(
                ja_pofile, ITranslationFileData, 'all_messages')
            nplurals_expected = 1
            nplurals = translation_file_data.header.number_plural_forms
            self.assertEqual(
                nplurals_expected, nplurals,
                "%d != %d for '%s'" % (nplurals_expected, nplurals, expr))
            # The plural form expression for Japanese (or any other language
            # with just one form) is simply '0'.
            self.assertEqual(
                u"0", translation_file_data.header.plural_form_expression)

    def test_header_pluralform_2_but_not_western(self):
        # If the plural form expression in the header reports two but is not
        # the standard western expression, use the data from the header.
        # Use Japanese because it has only one plural form which is less
        # than the 2 the western style has.
        ja_pofile = self._makePOFileWithPlural('ja')
        ja_pofile.header = self.header % self.other_2_plural

        translation_file_data = getAdapter(
            ja_pofile, ITranslationFileData, 'all_messages')
        self.assertEqual(2, translation_file_data.header.number_plural_forms)
        self.assertEqual(
            u"(n > 0)", translation_file_data.header.plural_form_expression)

    def test_header_pluralform_generic(self):
        # If the plural form expression in the header is a generic one (no
        # information), use the data from the language entry if present.
        ja_pofile = self._makePOFileWithPlural('ja')
        ja_pofile.header = self.header % self.generic_plural

        translation_file_data = getAdapter(
            ja_pofile, ITranslationFileData, 'all_messages')
        self.assertEqual(1, translation_file_data.header.number_plural_forms)
        self.assertEqual(
            u"0", translation_file_data.header.plural_form_expression)


class TestPOFilePermissions(TestCaseWithFactory):
    """Test `POFile` access privileges.

        :ivar pofile: A `POFile` for a `ProductSeries`.
    """
    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestPOFilePermissions, self).setUp()
        self.pofile = self.factory.makePOFile()

    def makeDistroPOFile(self):
        """Replace `self.pofile` with one for a `Distribution`."""
        template = self.factory.makePOTemplate(
            distroseries=self.factory.makeDistroSeries(),
            sourcepackagename=self.factory.makeSourcePackageName())
        self.pofile = self.factory.makePOFile(potemplate=template)

    def getTranslationPillar(self):
        """Return `self.pofile`'s `Product` or `Distribution`."""
        template = self.pofile.potemplate
        if template.productseries is not None:
            return template.productseries.product
        else:
            return template.distroseries.distribution

    def closeTranslations(self):
        """Set translation permissions for `self.pofile` to CLOSED.

        This is useful for showing that a particular person has rights
        to work on a translation despite it being generally closed to
        the public.
        """
        self.getTranslationPillar().translationpermission = (
            TranslationPermission.CLOSED)

    def test_makeDistroPOFile(self):
        # Test the makeDistroPOFile helper.
        self.assertEqual(
            self.pofile.potemplate.productseries.product,
            self.getTranslationPillar())
        self.makeDistroPOFile()
        self.assertEqual(
            self.pofile.potemplate.distroseries.distribution,
            self.getTranslationPillar())

    def test_closeTranslations_product(self):
        # Test the closeTranslations helper for Products.
        self.assertNotEqual(
            TranslationPermission.CLOSED,
            self.getTranslationPillar().translationpermission)
        self.closeTranslations()
        self.assertEqual(
            TranslationPermission.CLOSED,
            self.getTranslationPillar().translationpermission)

    def test_closeTranslations_distro(self):
        # Test the closeTranslations helper for Distributions.
        self.makeDistroPOFile()
        self.assertNotEqual(
            TranslationPermission.CLOSED,
            self.getTranslationPillar().translationpermission)
        self.closeTranslations()
        self.assertEqual(
            TranslationPermission.CLOSED,
            self.getTranslationPillar().translationpermission)

    def test_anonymous_cannot_submit(self):
        # Anonymous users cannot edit translations or enter suggestions.
        self.assertFalse(self.pofile.canEditTranslations(None))
        self.assertFalse(self.pofile.canAddSuggestions(None))

    def test_licensing_agreement_decliners_cannot_submit(self):
        # Users who decline the translations relicensing agreement can't
        # edit translations or enter suggestions.
        decliner = self.factory.makePerson()
        set_relicensing(decliner, False)
        self.assertFalse(self.pofile.canEditTranslations(decliner))
        self.assertFalse(self.pofile.canAddSuggestions(decliner))

    def test_licensing_agreement_accepters_can_submit(self):
        # Users who accept the translations relicensing agreement can
        # edit translations and enter suggestions as circumstances
        # allow.
        accepter = self.factory.makePerson()
        set_relicensing(accepter, True)
        self.assertTrue(self.pofile.canEditTranslations(accepter))
        self.assertTrue(self.pofile.canAddSuggestions(accepter))

    def test_admin_can_edit(self):
        # Administrators can edit all translations and make suggestions
        # anywhere.
        self.closeTranslations()
        admin = self.factory.makePerson()
        getUtility(ILaunchpadCelebrities).admin.addMember(admin, admin)
        self.assertTrue(self.pofile.canEditTranslations(admin))
        self.assertTrue(self.pofile.canAddSuggestions(admin))

    def test_translations_admin_can_edit(self):
        # Translations admins can edit all translations and make
        # suggestions anywhere.
        self.closeTranslations()
        translations_admin = self.factory.makePerson()
        getUtility(ILaunchpadCelebrities).rosetta_experts.addMember(
            translations_admin, translations_admin)
        self.assertTrue(self.pofile.canEditTranslations(translations_admin))
        self.assertTrue(self.pofile.canAddSuggestions(translations_admin))

    def test_product_owner_can_edit(self):
        # A Product owner can edit the Product's translations and enter
        # suggestions even when a regular user isn't allowed to.
        self.closeTranslations()
        product = self.getTranslationPillar()
        self.assertTrue(self.pofile.canEditTranslations(product.owner))
        self.assertTrue(self.pofile.canAddSuggestions(product.owner))

    def test_product_owner_can_edit_after_declining_agreement(self):
        # A Product owner can edit the Product's translations even after
        # declining the translations licensing agreement.
        product = self.getTranslationPillar()
        set_relicensing(product.owner, False)
        self.assertTrue(self.pofile.canEditTranslations(product.owner))

    def test_distro_owner_gets_no_privileges(self):
        # A Distribution owner gets no special privileges.
        self.makeDistroPOFile()
        self.closeTranslations()
        distro = self.getTranslationPillar()
        self.assertFalse(self.pofile.canEditTranslations(distro.owner))
        self.assertFalse(self.pofile.canAddSuggestions(distro.owner))

    def test_productseries_owner_gets_no_privileges(self):
        # A ProductSeries owner gets no special privileges.
        self.closeTranslations()
        productseries = self.pofile.potemplate.productseries
        productseries.owner = self.factory.makePerson()
        self.assertFalse(self.pofile.canEditTranslations(productseries.owner))
        self.assertFalse(self.pofile.canAddSuggestions(productseries.owner))

    def test_potemplate_owner_gets_no_privileges(self):
        # A POTemplate owner gets no special privileges.
        self.closeTranslations()
        template = self.pofile.potemplate
        template.owner = self.factory.makePerson()
        self.assertFalse(self.pofile.canEditTranslations(template.owner))
        self.assertFalse(self.pofile.canAddSuggestions(template.owner))

    def test_pofile_owner_can_edit(self):
        # A POFile owner currently has special edit privileges.
        self.closeTranslations()
        self.pofile.owner = self.factory.makePerson()
        self.assertTrue(self.pofile.canEditTranslations(self.pofile.owner))
        self.assertTrue(self.pofile.canAddSuggestions(self.pofile.owner))

    def test_product_translation_group_owner_gets_no_privileges(self):
        # A translation group owner manages the translation group
        # itself.  There are no special privileges.
        self.closeTranslations()
        group = self.factory.makeTranslationGroup()
        self.getTranslationPillar().translationgroup = group
        self.assertFalse(self.pofile.canEditTranslations(group.owner))
        self.assertFalse(self.pofile.canAddSuggestions(group.owner))

    def test_distro_translation_group_owner_gets_no_privileges(self):
        # Owners of Distribution translation groups get no special edit
        # privileges.
        self.makeDistroPOFile()
        self.closeTranslations()
        group = self.factory.makeTranslationGroup()
        self.getTranslationPillar().translationgroup = group
        self.assertFalse(self.pofile.canEditTranslations(group.owner))
        self.assertFalse(self.pofile.canAddSuggestions(group.owner))
