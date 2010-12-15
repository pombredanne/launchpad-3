# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import datetime

from pytz import timezone
from zope.component import getUtility

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.app.enums import ServiceUsage
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing import TestCaseWithFactory


class TestTranslationEmptyMessages(TestCaseWithFactory):
    """Test behaviour of empty translation messages."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Set up context to test in."""
        # Pretend we have a product being translated to Serbian.
        # This is where we are going to be importing translations to.
        super(TestTranslationEmptyMessages, self).setUp()
        product = self.factory.makeProduct(
            translations_usage=ServiceUsage.LAUNCHPAD)
        self.productseries = self.factory.makeProductSeries(product=product)
        self.potemplate = self.factory.makePOTemplate(self.productseries)
        self.serbian = getUtility(ILanguageSet).getLanguageByCode('sr')
        self.pofile_sr = self.factory.makePOFile(
            'sr',
            potemplate=self.potemplate)
        self.now = datetime.now(timezone('UTC'))

    def test_NoEmptyImporedTranslation(self):
        # When an empty translation comes from import, it is
        # ignored when there's NO previous is_current_upstream translation.
        potmsgset = self.factory.makePOTMsgSet(self.potemplate)
        translation = potmsgset.updateTranslation(
            self.pofile_sr, self.pofile_sr.owner, [""],
            is_current_upstream=True, lock_timestamp=None)

        # Importing an empty translation should not create a new record
        # in the database.
        self.assertEquals(translation, None)

    def test_DeactivatingCurrentTranslation(self):
        # Deactivating replace existing is_current_ubuntu translation,
        # stores an empty translation in the database.
        potmsgset = self.factory.makePOTMsgSet(self.potemplate)
        translation = potmsgset.updateTranslation(
            self.pofile_sr, self.pofile_sr.owner, ["active translation"],
            is_current_upstream=False, lock_timestamp=None)
        deactivation = potmsgset.updateTranslation(
            self.pofile_sr, self.pofile_sr.owner, [u""],
            is_current_upstream=False, lock_timestamp=self.now)
        ubuntu_message = potmsgset.getCurrentTranslationMessage(
            self.potemplate, self.serbian)

        # Storing an empty translation should deactivate the current
        # translation message.
        self.assertEquals(deactivation, ubuntu_message)

    def test_DeactivatingImportedTranslation(self):
        # When an empty translation comes from import, it is
        # ignored when there IS a previous is_current_upstream translation,
        # and previous translation is marked as not being
        # is_current_upstream anymore.
        potmsgset = self.factory.makePOTMsgSet(self.potemplate)
        translation = potmsgset.updateTranslation(
            self.pofile_sr, self.pofile_sr.owner, ["upstream translation"],
            is_current_upstream=True, lock_timestamp=None)
        deactivation = potmsgset.updateTranslation(
            self.pofile_sr, self.pofile_sr.owner, [""],
            is_current_upstream=True, lock_timestamp=self.now)
        upstream_message = potmsgset.getImportedTranslationMessage(
            self.potemplate, self.serbian)
        ubuntu_message = potmsgset.getCurrentTranslationMessage(
            self.potemplate, self.serbian)

        # Empty is_current_upstream message should not be imported.
        self.assertEquals(deactivation, None)
        # Existing is_current_upstream message should be unset.
        self.assertEquals(upstream_message, None)
        # Old is_current_upstream message is not is_current_ubuntu either.
        self.assertEquals(ubuntu_message, None)

    def test_DeactivatingImportedNotCurrentTranslation(self):
        # When an empty translation comes from import, and there is a
        # previous is_current_upstream translation and another
        # is_current_ubuntu translation, only is_current_upstream
        # translation is unset.
        potmsgset = self.factory.makePOTMsgSet(self.potemplate)
        upstream_message = potmsgset.updateTranslation(
            self.pofile_sr, self.pofile_sr.owner, ["upstream translation"],
            is_current_upstream=True, lock_timestamp=None)
        launchpad_message = potmsgset.updateTranslation(
            self.pofile_sr, self.pofile_sr.owner, ["launchpad translation"],
            is_current_upstream=False, lock_timestamp=self.now)
        deactivation = potmsgset.updateTranslation(
            self.pofile_sr, self.pofile_sr.owner, [""],
            is_current_upstream=True, lock_timestamp=self.now)
        new_upstream_message = potmsgset.getImportedTranslationMessage(
            self.potemplate, self.serbian)
        ubuntu_message = potmsgset.getCurrentTranslationMessage(
            self.potemplate, self.serbian)

        # Current message should not be changed.
        self.assertEquals(launchpad_message, ubuntu_message)
        # Existing is_current_upstream message should be unset.
        self.assertEquals(new_upstream_message, None)
