# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from datetime import datetime, timedelta
from pytz import timezone
import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces import ILanguageSet
from canonical.launchpad.testing.factory import LaunchpadObjectFactory
from canonical.testing import LaunchpadZopelessLayer


class TestTranslationEmptyMessages(unittest.TestCase):
    """Test behaviour of empty translation messages."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Set up context to test in."""
        # Pretend we have a product being translated to Serbian.
        # This is where we are going to be importing translations to.
        factory = LaunchpadObjectFactory()
        self.factory = factory
        self.productseries = factory.makeProductSeries()
        self.productseries.product.official_rosetta = True
        self.potemplate = factory.makePOTemplate(self.productseries)
        self.serbian = getUtility(ILanguageSet).getLanguageByCode('sr')
        self.pofile_sr = factory.makePOFile('sr', potemplate=self.potemplate)
        self.now = datetime.now(timezone('UTC'))

    def test_NoEmptyImporedTranslation(self):
        # When an empty translation comes from import, it is
        # ignored when there's NO previous is_imported translation.
        potmsgset = self.factory.makePOTMsgSet(self.potemplate)
        translation = potmsgset.updateTranslation(self.pofile_sr, self.pofile_sr.owner,
            [u""], is_imported=True, lock_timestamp=None)
        import sys
        print >>sys.stderr, "\nTRANSLATION: %s" % translation.translations
        self.assertEquals(translation, None,
                          "Importing an empty translation should not create "
                          "a new record in the database.")

    def test_DeactivatingCurrentTranslation(self):
        # Deactivating replace existing is_current translation,
        # stores an empty translation in the database.
        potmsgset = self.factory.makePOTMsgSet(self.potemplate)
        translation = potmsgset.updateTranslation(self.pofile_sr, self.pofile_sr.owner,
            ["active translation"], is_imported=False, lock_timestamp=None)
        deactivation = potmsgset.updateTranslation(self.pofile_sr, self.pofile_sr.owner,
            [u""], is_imported=False, lock_timestamp=self.now)
        current_message = potmsgset.getCurrentTranslationMessage(self.serbian)
        self.assertEquals(deactivation, current_message,
                          "Storing empty translation should deactivate current "
                          "translation message.")

    def test_DeactivatingImportedTranslation(self):
        # When an empty translation comes from import, it is
        # ignored when there IS a previous is_imported translation,
        # and previous translation is marked as not being is_imported anymore.
        potmsgset = self.factory.makePOTMsgSet(self.potemplate)
        translation = potmsgset.updateTranslation(self.pofile_sr, self.pofile_sr.owner,
            ["imported translation"], is_imported=True, lock_timestamp=None)
        old_imported_message = potmsgset.getImportedTranslationMessage(self.serbian)
        deactivation = potmsgset.updateTranslation(self.pofile_sr, self.pofile_sr.owner,
            [""], is_imported=True, lock_timestamp=self.now)
        imported_message = potmsgset.getImportedTranslationMessage(self.serbian)
        current_message = potmsgset.getCurrentTranslationMessage(self.serbian)
        self.assertEquals(deactivation, None,
                          "Empty is_imported message should not be imported.")
        self.assertEquals(imported_message, None,
                          "Existing is_imported message should be unset.")
        self.assertEquals(current_message, old_imported_message,
                          "Old is_imported message should remain is_current.")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
