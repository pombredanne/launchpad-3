# Copyright 2008 Canonical Ltd.  All rights reserved.

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
    ILanguageSet, POTMsgSetInIncompatibleTemplatesError,
    TranslationFileFormat)
from canonical.launchpad.testing.factory import LaunchpadObjectFactory
from canonical.testing import LaunchpadZopelessLayer


class TestTranslationSharedPOTMsgSets(unittest.TestCase):
    """Test discovery of translation suggestions."""

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

        # Create a single POTMsgSet that is used across all tests,
        # and add it to only one of the POTemplates.
        self.potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate)
        self.potmsgset.setSequence(self.devel_potemplate, 1)

    def test_TranslationTemplateItem(self):
        self.potmsgset.setSequence(self.stable_potemplate, 1)

        devel_potmsgsets = list(self.devel_potemplate.getPOTMsgSets())
        stable_potmsgsets = list(self.stable_potemplate.getPOTMsgSets())

        self.assertEquals(devel_potmsgsets, [self.potmsgset])
        self.assertEquals(devel_potmsgsets, stable_potmsgsets)

    def test_POTMsgSetInIncompatiblePOTemplates(self):
        # Make sure a POTMsgSet cannot be used in two POTemplates with
        # different incompatible source_file_format (like XPI and PO).
        self.devel_potemplate.source_file_format = TranslationFileFormat.PO
        self.stable_potemplate.source_file_format = TranslationFileFormat.XPI

        potmsgset = self.potmsgset

        self.assertRaises(POTMsgSetInIncompatibleTemplatesError,
                          potmsgset.setSequence, self.stable_potemplate, 1)

        # If the two file formats are compatible, it works.
        self.stable_potemplate.source_file_format = (
            TranslationFileFormat.KDEPO)
        potmsgset.setSequence(self.stable_potemplate, 1)

        devel_potmsgsets = list(self.devel_potemplate.getPOTMsgSets())
        stable_potmsgsets = list(self.stable_potemplate.getPOTMsgSets())
        self.assertEquals(devel_potmsgsets, stable_potmsgsets)

        # We hack the POTemplate manually to make data inconsistent
        # in database.
        self.stable_potemplate.source_file_format = TranslationFileFormat.XPI
        transaction.commit()

        # We remove the security proxy to be able to get a callable for
        # properties like `uses_english_msgids` and `singular_text`.
        naked_potmsgset = removeSecurityProxy(potmsgset)

        self.assertRaises(POTMsgSetInIncompatibleTemplatesError,
                          naked_potmsgset.__getattribute__,
                          "uses_english_msgids")

        self.assertRaises(POTMsgSetInIncompatibleTemplatesError,
                          naked_potmsgset.__getattribute__, "singular_text")

        # Revert source_file_format to the default one.
        self.stable_potemplate.source_file_format = TranslationFileFormat.PO


    def test_POTMsgSetUsesEnglishMsgids(self):
        """Test that `uses_english_msgids` property works correctly."""

        # Gettext PO format uses English strings as msgids.
        self.devel_potemplate.source_file_format = TranslationFileFormat.PO
        transaction.commit()
        self.assertEquals(self.potmsgset.uses_english_msgids, True)

        # Mozilla XPI format doesn't use English strings as msgids.
        self.devel_potemplate.source_file_format = TranslationFileFormat.XPI
        transaction.commit()
        self.assertEquals(self.potmsgset.uses_english_msgids, False)

        # Revert the source_file_format to what other tests might expect.
        self.devel_potemplate.source_file_format = TranslationFileFormat.PO


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
