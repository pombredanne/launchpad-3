# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0102

__metaclass__ = type

from datetime import datetime, timedelta
import pytz
import unittest

from zope.component import getAdapter
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces import TranslationValidationStatus
from canonical.launchpad.interfaces.translationcommonformat import (
    ITranslationFileData)
from lp.testing import TestCaseWithFactory
from lp.testing.factory import LaunchpadObjectFactory
from canonical.testing import LaunchpadZopelessLayer


class TestTranslationSharedPOFile(unittest.TestCase):
    """Test behaviour of PO files with shared POTMsgSets."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Set up context to test in."""
        # Create a product with two series and a shared POTemplate
        # in different series ('devel' and 'stable').
        factory = LaunchpadObjectFactory()
        self.factory = factory
        self.foo = factory.makeProduct()
        self.foo_devel = factory.makeProductSeries(
            name='devel', product=self.foo)
        self.foo_stable = factory.makeProductSeries(
            name='stable', product=self.foo)
        self.foo.official_rosetta = True

        # POTemplate is 'shared' if it has the same name ('messages').
        self.devel_potemplate = factory.makePOTemplate(
            productseries=self.foo_devel, name="messages")
        self.stable_potemplate = factory.makePOTemplate(self.foo_stable,
                                                        name="messages")

        # We'll use two PO files, one for each series.
        self.devel_sr_pofile = factory.makePOFile(
            'sr', self.devel_potemplate)
        self.stable_sr_pofile = factory.makePOFile(
            'sr', self.stable_potemplate)

        # Create a single POTMsgSet that is used across all tests,
        # and add it to only one of the POTemplates.
        self.potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate)
        self.potmsgset.setSequence(self.devel_potemplate, 1)

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
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"One translation message"])
        found_potmsgsets = list(
            self.devel_sr_pofile.findPOTMsgSetsContaining(u"translation"))
        self.assertEquals(found_potmsgsets, [potmsgset])

        # Search matches all plural forms.
        plural_translation = self.factory.makeTranslationMessage(
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
        other_translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"Another translation"],
            translator=someone_else)
        found_translations = list(
            self.devel_sr_pofile.getTranslationsFilteredBy(submitter))
        self.assertEquals(found_translations, [translation])

        # Adding a translation for same POTMsgSet, but to a different
        # POFile (i.e. language or variant) will not add the translation
        # to the list of submitter's translations for *former* POFile.
        self.devel_sr_latin_pofile = self.factory.makePOFile(
            'sr', variant=u'latin', potemplate=self.devel_potemplate)
        latin_translation = self.factory.makeTranslationMessage(
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
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Translation"])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(found_translations, [self.potmsgset])

        # If diverged translation is empty, POTMsgSet is not listed.
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u""])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(found_translations, [])

    def test_getPOTMsgSetTranslated_Shared(self):
        # Test listing of translated POTMsgSets when there is a shared
        # translation for the POTMsgSet as well.

        # We create a shared translation first.
        shared_translation = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Shared translation"])

        # When there is no diverged translation, shared one is returned.
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(found_translations, [self.potmsgset])

        # When an empty diverged translation is added, nothing is listed.
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u""])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(found_translations, [])

        # If diverged translation is non-empty, POTMsgSet is listed.
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Translation"])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(found_translations, [self.potmsgset])

    def test_getPOTMsgSetTranslated_EmptyShared(self):
        # Test listing of translated POTMsgSets when there is an
        # empty shared translation for the POTMsgSet as well.

        # We create an empty shared translation first.
        shared_translation = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u""])

        # When there is no diverged translation, shared one is returned,
        # but since it's empty, there are no results.
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(found_translations, [])

        # When an empty diverged translation is added, nothing is listed.
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u""])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(found_translations, [])

        # If diverged translation is non-empty, POTMsgSet is listed.
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Translation"])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetTranslated())
        self.assertEquals(found_translations, [self.potmsgset])

    def test_getPOTMsgSetTranslated_Multiple(self):
        # Test listing of translated POTMsgSets if there is more than one
        # translated message.

        # Add a diverged translation on the included POTMsgSet...
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Diverged translation"])

        # and a shared translation on newly added POTMsgSet...
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate,
                                               u"Translated text")
        potmsgset.setSequence(self.devel_potemplate, 2)

        shared_translation = self.factory.makeSharedTranslationMessage(
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
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Translation"])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(found_translations, [])

        # If diverged translation is empty, POTMsgSet is not listed.
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u""])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(found_translations, [self.potmsgset])

    def test_getPOTMsgSetUntranslated_Shared(self):
        # Test listing of translated POTMsgSets when there is a shared
        # translation for the POTMsgSet as well.

        # We create a shared translation first.
        shared_translation = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Shared translation"])

        # When there is no diverged translation, shared one is returned.
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(found_translations, [])

        # When an empty diverged translation is added, nothing is listed.
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u""])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(found_translations, [self.potmsgset])

        # If diverged translation is non-empty, POTMsgSet is listed.
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Translation"])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(found_translations, [])

    def test_getPOTMsgSetUntranslated_EmptyShared(self):
        # Test listing of translated POTMsgSets when there is an
        # empty shared translation for the POTMsgSet as well.

        # We create an empty shared translation first.
        shared_translation = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u""])

        # When there is no diverged translation, shared one is returned,
        # but since it's empty, there are no results.
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(found_translations, [self.potmsgset])

        # When an empty diverged translation is added, nothing is listed.
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u""])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(found_translations, [self.potmsgset])

        # If diverged translation is non-empty, POTMsgSet is listed.
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Translation"])
        found_translations = list(
            self.devel_sr_pofile.getPOTMsgSetUntranslated())
        self.assertEquals(found_translations, [])

    def test_getPOTMsgSetUntranslated_Multiple(self):
        # Test listing of untranslated POTMsgSets if there is more than one
        # untranslated message.

        # Add an empty translation to the included POTMsgSet...
        translation = self.factory.makeTranslationMessage(
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
        translation = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Shared translation"], date_updated=date_created)

        # And we also have a diverged translation created a day after shared
        # current translation.
        diverged_date = date_created + timedelta(1)
        translation = self.factory.makeTranslationMessage(
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
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"New suggestion"], suggestion=True)

        # Another POTMsgSet has both a translation and a suggestion.
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate,
                                               u"Translated text")
        potmsgset.setSequence(self.devel_potemplate, 2)
        date_created = datetime.now(pytz.UTC) - timedelta(5)
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=self.potmsgset,
            translations=[u"Translation"], date_updated=date_created)
        suggestion_date = date_created + timedelta(1)
        translation = self.factory.makeTranslationMessage(
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
        translation1 = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile,
            potmsgset=self.potmsgset,
            translations=["A suggestion"],
            suggestion=True)
        translation2 = self.factory.makeSharedTranslationMessage(
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
        old_translation = translation
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
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"Unreviewed suggestion"], suggestion=True)

        # Third POTMsgSet is translated, and with a suggestion.
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate)
        potmsgset.setSequence(self.devel_potemplate, 3)
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"Translation"], suggestion=False,
            date_updated=datetime.now(pytz.UTC)-timedelta(1))
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"Another suggestion"], suggestion=True)

        # Fourth POTMsgSet is translated in import.
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate)
        potmsgset.setSequence(self.devel_potemplate, 4)
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"Imported translation"], is_imported=True)

        # Fifth POTMsgSet is translated in import, but changed in LP.
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate)
        potmsgset.setSequence(self.devel_potemplate, 5)
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"Imported translation"], is_imported=True)
        translation = self.factory.makeTranslationMessage(
            pofile=self.devel_sr_pofile, potmsgset=potmsgset,
            translations=[u"LP translation"], is_imported=False)

        # Sixth POTMsgSet is translated in LP only.
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate)
        potmsgset.setSequence(self.devel_potemplate, 6)
        translation = self.factory.makeTranslationMessage(
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
        shared_translation = self.factory.makeSharedTranslationMessage(
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
        diverged_translation = self.factory.makeTranslationMessage(
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


class TestTranslationPOFilePOTMsgSetOrdering(TestCaseWithFactory):
    """Test ordering of POTMsgSets as returned by PO file methods."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Set up context to test in."""
        # Create a product with two series and a shared POTemplate
        # in different series ('devel' and 'stable').
        TestCaseWithFactory.setUp(self)
        self.foo = self.factory.makeProduct()
        self.foo_devel = self.factory.makeProductSeries(
            name='devel', product=self.foo)
        self.foo_stable = self.factory.makeProductSeries(
            name='stable', product=self.foo)
        self.foo.official_rosetta = True

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
        translation1 = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile,
            potmsgset=self.potmsgset1,
            translations=["Shared translation"])
        translation2 = self.factory.makeSharedTranslationMessage(
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
        imported1 = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile,
            potmsgset=self.potmsgset1,
            translations=["Imported"],
            is_imported=True)
        translation1 = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile,
            potmsgset=self.potmsgset1,
            translations=["Changed"],
            is_imported=False)
        imported2 = self.factory.makeSharedTranslationMessage(
            pofile=self.devel_sr_pofile,
            potmsgset=self.potmsgset2,
            translations=["Another imported"],
            is_imported=True)
        translation2 = self.factory.makeSharedTranslationMessage(
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



class TestPOFileStatistics(TestCaseWithFactory):
    """Test PO files statistics calculation."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Set up context to test in."""
        # Create a POFile to calculate statistics on.
        TestCaseWithFactory.setUp(self)
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
        imported = self.factory.makeTranslationMessage(
            pofile=self.pofile,
            potmsgset=self.potmsgset,
            translations=["Imported current"],
            is_imported=True)
        self.pofile.updateStatistics()
        self.assertEquals(self.pofile.currentCount(), 1)

        # Adding a suggestion (i.e. unused translation)
        # will not change the current count when there's
        # already an imported message.
        suggestion = self.factory.makeTranslationMessage(
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
        current = self.factory.makeTranslationMessage(
            pofile=self.pofile,
            potmsgset=self.potmsgset,
            translations=["Current"])
        self.pofile.updateStatistics()
        self.assertEquals(self.pofile.newCount(), 1)

    def test_POFile_updateStatistics_newCount_reimporting(self):
        # If we get an 'imported' translation for what
        # we already have as 'new', it's not considered 'new'
        # anymore since it has been synced.
        current = self.factory.makeTranslationMessage(
            pofile=self.pofile,
            potmsgset=self.potmsgset,
            translations=["Current"])
        # Reimport it but with is_imported=True.
        imported = self.factory.makeTranslationMessage(
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
        imported = self.factory.makeTranslationMessage(
            pofile=self.pofile,
            potmsgset=self.potmsgset,
            translations=["Imported"],
            is_imported=True)
        update = self.factory.makeTranslationMessage(
            pofile=self.pofile,
            potmsgset=self.potmsgset,
            translations=["Changed"])
        self.pofile.updateStatistics()
        self.assertEquals(self.pofile.newCount(), 0)
        self.assertEquals(self.pofile.updatesCount(), 1)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
