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
        # We start with fresh shared PO templates.
        self.devel_potemplate.expireAllMessages()
        self.stable_potemplate.expireAllMessages()

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
        pass

    def test_getPOTMsgSetTranslated(self):
        """Test listing of translated POTMsgSets."
        pass

    def test_getPOTMsgSetUntranslated(self):
        """Test listing of untranslated POTMsgSets."
        pass

    def test_getPOTMsgSetWithNewSuggestions(self):
        """Test listing of POTMsgSets with unreviewed suggestions."
        pass

    def test_getPOTMsgSetChangedInLaunchpad(self):
        """Test listing of POTMsgSets which contain changes from imports."
        pass

    def test_getPOTMsgSetWithErrors(self):
        """Test listing of POTMsgSets with errors in translations."
        pass

    def test_hasMessageID(self):
        """Test that finding messages by English string works."""
        pass

    def test_updateStatistics(self):
        """Test that updating statistics keeps working."""
        pass


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
