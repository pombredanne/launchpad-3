# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from datetime import datetime, timedelta
from pytz import timezone
import unittest

import transaction

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.database.translationtemplateitem import (
    TranslationTemplateItem)
from canonical.launchpad.interfaces import (
    ILanguageSet, TranslationFileFormat)
from canonical.launchpad.testing.factory import LaunchpadObjectFactory
from canonical.testing import LaunchpadZopelessLayer


class TestTranslationSharedPOTemplate(unittest.TestCase):
    """Test behaviour of "shared" PO templates."""

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
        """Test that search works correctly."""

        # Searching for English strings.
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate,
                                               u"Some wild text")
        potmsgset.setSequence(self.devel_potemplate, 1)

        found_potmsgsets = list(
            self.devel_sr_pofile.findPOTMsgSetsContaining(u"wild"))
        self.assertEquals(found_potmsgsets, [potmsgset])

        # Just linking an existing POTMsgSet into another POTemplate
        # will make it be returned in searches.
        potmsgset.setSequence(self.stable_potemplate, 1)
        found_potmsgsets = list(
            self.stable_sr_pofile.findPOTMsgSetsContaining(u"wild"))
        self.assertEquals(found_potmsgsets, [potmsgset])

        # Searching for singular in plural messages works as well.
        plural_potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate,
                                                      u"Some singular text",
                                                      u"Some plural text")
        plural_potmsgset.setSequence(self.devel_potemplate, 1)

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
        """Test that filtering by submitters works."""

        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate,
                                               u"Cheesy text")
        potmsgset.setSequence(self.devel_potemplate, 1)

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
        """Test listing of translated POTMsgSets when there is no shared
        translation for the POTMsgSet."""

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
        """Test listing of translated POTMsgSets when there is a shared
        translation for the POTMsgSet as well."""

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
        """Test listing of translated POTMsgSets when there is an
        empty shared translation for the POTMsgSet as well."""

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
        """Test listing of translated POTMsgSets if there is more than one
        translated message."""

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


    def test_getPOTMsgSetUntranslated(self):
        """Test listing of untranslated POTMsgSets."""
        pass

    def test_getPOTMsgSetWithNewSuggestions(self):
        """Test listing of POTMsgSets with unreviewed suggestions."""
        pass

    def test_getPOTMsgSetChangedInLaunchpad(self):
        """Test listing of POTMsgSets which contain changes from imports."""
        pass

    def test_getPOTMsgSetWithErrors(self):
        """Test listing of POTMsgSets with errors in translations."""
        pass

    def test_hasMessageID(self):
        """Test that finding messages by English string works."""
        pass

    def test_updateStatistics(self):
        """Test that updating statistics keeps working."""
        pass


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
