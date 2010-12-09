# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0102

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )

import pytz
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import ZopelessDatabaseLayer
from lp.app.enums import ServiceUsage
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.product import IProductSet
from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.potemplate import IPOTemplateSet
from lp.translations.interfaces.potmsgset import (
    POTMsgSetInIncompatibleTemplatesError,
    TranslationCreditsType,
    )
from lp.translations.interfaces.translationfileformat import (
    TranslationFileFormat,
    )
from lp.translations.interfaces.translationmessage import TranslationConflict
from lp.translations.model.translationmessage import DummyTranslationMessage


class TestTranslationSharedPOTMsgSets(TestCaseWithFactory):
    """Test discovery of translation suggestions."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        """Set up context to test in."""
        # Create a product with two series and a shared POTemplate
        # in different series ('devel' and 'stable').
        super(TestTranslationSharedPOTMsgSets, self).setUp()
        self.foo = self.factory.makeProduct(
            translations_usage=ServiceUsage.LAUNCHPAD)
        self.foo_devel = self.factory.makeProductSeries(
            name='devel', product=self.foo)
        self.foo_stable = self.factory.makeProductSeries(
            name='stable', product=self.foo)

        # POTemplate is 'shared' if it has the same name ('messages').
        self.devel_potemplate = self.factory.makePOTemplate(
            productseries=self.foo_devel, name="messages")
        self.stable_potemplate = self.factory.makePOTemplate(
            productseries=self.foo_stable, name="messages")

        # Create a single POTMsgSet that is used across all tests,
        # and add it to only one of the POTemplates.
        self.potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate)
        self.potmsgset.setSequence(self.devel_potemplate, 1)

    def _refreshSuggestiveTemplatesCache(self):
        """Refresh the `SuggestivePOTemplate` cache."""
        getUtility(IPOTemplateSet).populateSuggestivePOTemplatesCache()

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

    def test_POTMsgSetUsesEnglishMsgids(self):
        """Test that `uses_english_msgids` property works correctly."""

        # Gettext PO format uses English strings as msgids.
        self.devel_potemplate.source_file_format = TranslationFileFormat.PO
        transaction.commit()
        self.assertTrue(self.potmsgset.uses_english_msgids)

        # Mozilla XPI format doesn't use English strings as msgids.
        self.devel_potemplate.source_file_format = TranslationFileFormat.XPI
        transaction.commit()
        self.assertFalse(self.potmsgset.uses_english_msgids)

    def test_POTMsgSet_singular_text(self):
        """Test that `singular_text` property works correctly."""

        BASE_STRING = u"Base string"
        ENGLISH_STRING = u"English string"
        DIVERGED_ENGLISH_STRING = u"Diverged English string"

        # We create a POTMsgSet with a base English string.
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate,
                                               BASE_STRING)
        potmsgset.setSequence(self.devel_potemplate, 2)

        # Gettext PO format uses English strings as msgids.
        self.devel_potemplate.source_file_format = TranslationFileFormat.PO
        transaction.commit()
        self.assertEquals(potmsgset.singular_text, BASE_STRING)

        # Mozilla XPI format doesn't use English strings as msgids,
        # unless there is no English POFile object.
        self.devel_potemplate.source_file_format = TranslationFileFormat.XPI
        transaction.commit()
        self.assertEquals(potmsgset.singular_text, BASE_STRING)

        # POTMsgSet singular_text is read from a shared English translation.
        en_pofile = self.factory.makePOFile('en', self.devel_potemplate)
        translation = self.factory.makeSharedTranslationMessage(
            pofile=en_pofile, potmsgset=potmsgset,
            translations=[ENGLISH_STRING])
        self.assertEquals(potmsgset.singular_text, ENGLISH_STRING)

        # A diverged (translation.potemplate != None) English translation
        # is not used as a singular_text.
        translation = self.factory.makeTranslationMessage(
            pofile=en_pofile, potmsgset=potmsgset,
            translations=[DIVERGED_ENGLISH_STRING])
        translation.potemplate = self.devel_potemplate
        self.assertEquals(potmsgset.singular_text, ENGLISH_STRING)

    def test_getCurrentTranslationMessageOrDummy_returns_real_tm(self):
        pofile = self.factory.makePOFile('nl')
        message = self.factory.makeTranslationMessage(
            pofile=pofile, suggestion=False, is_imported=True)

        self.assertEqual(
            message,
            message.potmsgset.getCurrentTranslationMessageOrDummy(pofile))

    def test_getCurrentTranslationMessageOrDummy_returns_dummy_tm(self):
        pofile = self.factory.makePOFile('nl')
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)

        message = potmsgset.getCurrentTranslationMessageOrDummy(pofile)
        self.assertIsInstance(message, DummyTranslationMessage)

    def test_getCurrentTranslationMessage(self):
        """Test how shared and diverged current translation messages
        interact."""
        # Share a POTMsgSet in two templates, and get a Serbian POFile.
        self.potmsgset.setSequence(self.stable_potemplate, 1)
        sr_pofile = self.factory.makePOFile('sr', self.devel_potemplate)
        serbian = sr_pofile.language

        # A shared translation is current in both templates.
        shared_translation = self.factory.makeSharedTranslationMessage(
            pofile=sr_pofile, potmsgset=self.potmsgset)
        self.assertEquals(self.potmsgset.getCurrentTranslationMessage(
            self.devel_potemplate, serbian), shared_translation)
        self.assertEquals(self.potmsgset.getCurrentTranslationMessage(
            self.stable_potemplate, serbian), shared_translation)

        # Adding a diverged translation in one template makes that one
        # current in it.
        diverged_translation = self.factory.makeTranslationMessage(
            pofile=sr_pofile, potmsgset=self.potmsgset, force_diverged=True)
        self.assertEquals(self.potmsgset.getCurrentTranslationMessage(
            self.devel_potemplate, serbian), diverged_translation)
        self.assertEquals(self.potmsgset.getCurrentTranslationMessage(
            self.stable_potemplate, serbian), shared_translation)

    def test_getImportedTranslationMessage(self):
        """Test how shared and diverged current translation messages
        interact."""
        # Share a POTMsgSet in two templates, and get a Serbian POFile.
        self.potmsgset.setSequence(self.stable_potemplate, 1)
        sr_pofile = self.factory.makePOFile('sr', self.devel_potemplate)
        serbian = sr_pofile.language

        # A shared translation is imported in both templates.
        shared_translation = self.factory.makeSharedTranslationMessage(
            pofile=sr_pofile, potmsgset=self.potmsgset, is_imported=True)
        self.assertEquals(self.potmsgset.getImportedTranslationMessage(
            self.devel_potemplate, serbian), shared_translation)
        self.assertEquals(self.potmsgset.getImportedTranslationMessage(
            self.stable_potemplate, serbian), shared_translation)

        # Adding a diverged translation in one template makes that one
        # an imported translation there.
        diverged_translation = self.factory.makeTranslationMessage(
            pofile=sr_pofile, potmsgset=self.potmsgset, is_imported=True,
            force_diverged=True)
        self.assertEquals(self.potmsgset.getImportedTranslationMessage(
            self.devel_potemplate, serbian), diverged_translation)
        self.assertEquals(self.potmsgset.getImportedTranslationMessage(
            self.stable_potemplate, serbian), shared_translation)

    def test_getSharedTranslationMessage(self):
        """Test how shared and diverged current translation messages
        interact."""
        # Share a POTMsgSet in two templates, and get a Serbian POFile.
        sr_pofile = self.factory.makePOFile('sr', self.devel_potemplate)
        serbian = sr_pofile.language

        # A shared translation matches the current one.
        shared_translation = self.factory.makeSharedTranslationMessage(
            pofile=sr_pofile, potmsgset=self.potmsgset)
        self.assertEquals(
            self.potmsgset.getSharedTranslationMessage(serbian),
            shared_translation)

        # Adding a diverged translation doesn't break getSharedTM.
        diverged_translation = self.factory.makeTranslationMessage(
            pofile=sr_pofile, potmsgset=self.potmsgset, force_diverged=True)
        self.assertEquals(
            self.potmsgset.getSharedTranslationMessage(serbian),
            shared_translation)

    def test_getLocalTranslationMessages(self):
        """Test retrieval of local suggestions."""
        # Share a POTMsgSet in two templates, and get a Serbian POFile.
        self.potmsgset.setSequence(self.stable_potemplate, 1)
        sr_pofile = self.factory.makePOFile('sr', self.devel_potemplate)
        sr_stable_pofile = self.factory.makePOFile(
            'sr', self.stable_potemplate)
        serbian = sr_pofile.language

        # When there are no suggestions, empty list is returned.
        self.assertEquals(
            set(self.potmsgset.getLocalTranslationMessages(
                self.devel_potemplate, serbian)),
            set([]))

        # A shared suggestion is shown in both templates.
        shared_suggestion = self.factory.makeSharedTranslationMessage(
            pofile=sr_pofile, potmsgset=self.potmsgset, suggestion=True)
        self.assertEquals(
            set(self.potmsgset.getLocalTranslationMessages(
                self.devel_potemplate, serbian)),
            set([shared_suggestion]))
        self.assertEquals(
            set(self.potmsgset.getLocalTranslationMessages(
                self.stable_potemplate, serbian)),
            set([shared_suggestion]))

        # A suggestion on another PO file is still shown in both templates.
        another_suggestion = self.factory.makeSharedTranslationMessage(
            pofile=sr_stable_pofile, potmsgset=self.potmsgset,
            suggestion=True)
        self.assertEquals(
            set(self.potmsgset.getLocalTranslationMessages(
                self.devel_potemplate, serbian)),
            set([shared_suggestion, another_suggestion]))
        self.assertEquals(
            set(self.potmsgset.getLocalTranslationMessages(
                self.stable_potemplate, serbian)),
            set([shared_suggestion, another_suggestion]))

        # Setting one of the suggestions as current will leave
        # them both 'reviewed' and thus hidden.
        current_translation = self.factory.makeSharedTranslationMessage(
            pofile=sr_pofile, potmsgset=self.potmsgset, suggestion=False)
        self.assertEquals(
            set(self.potmsgset.getLocalTranslationMessages(
                self.devel_potemplate, serbian)),
            set([]))

    def test_getLocalTranslationMessages_empty_message(self):
        # An empty suggestion is never returned.
        self.potmsgset.setSequence(self.stable_potemplate, 1)
        pofile = self.factory.makePOFile('sr', self.stable_potemplate)
        empty_suggestion = self.factory.makeSharedTranslationMessage(
            pofile=pofile, potmsgset=self.potmsgset, suggestion=True,
            translations=[""])
        self.assertEquals(
            set([]),
            set(self.potmsgset.getLocalTranslationMessages(
                self.stable_potemplate, pofile.language)))

    def test_getExternallyUsedTranslationMessages(self):
        """Test retrieval of externally used translations."""

        # Create an external POTemplate with a POTMsgSet using
        # the same English string as the one in self.potmsgset.
        external_template = self.factory.makePOTemplate()
        product = external_template.productseries.product
        product.translations_usage = ServiceUsage.LAUNCHPAD
        external_potmsgset = self.factory.makePOTMsgSet(
            external_template,
            singular=self.potmsgset.singular_text)
        external_potmsgset.setSequence(external_template, 1)
        external_pofile = self.factory.makePOFile('sr', external_template)
        serbian = external_pofile.language
        self._refreshSuggestiveTemplatesCache()

        transaction.commit()

        # When there is no translation for the external POTMsgSet,
        # no externally used suggestions are returned.
        self.assertEquals(
            self.potmsgset.getExternallyUsedTranslationMessages(serbian),
            [])

        # If there are only suggestions on the external POTMsgSet,
        # no externally used suggestions are returned.
        external_suggestion = self.factory.makeSharedTranslationMessage(
            pofile=external_pofile, potmsgset=external_potmsgset,
            suggestion=True)

        transaction.commit()

        self.assertEquals(
            self.potmsgset.getExternallyUsedTranslationMessages(serbian),
            [])

        # If there is an imported translation on the external POTMsgSet,
        # it is returned as the externally used suggestion.
        imported_translation = self.factory.makeSharedTranslationMessage(
            pofile=external_pofile, potmsgset=external_potmsgset,
            suggestion=False, is_imported=True)
        imported_translation.is_current = False

        transaction.commit()

        self.assertEquals(
            self.potmsgset.getExternallyUsedTranslationMessages(serbian),
            [imported_translation])

        # If there is a current translation on the external POTMsgSet,
        # it is returned as the externally used suggestion as well.
        current_translation = self.factory.makeSharedTranslationMessage(
            pofile=external_pofile, potmsgset=external_potmsgset,
            suggestion=False, is_imported=False)

        transaction.commit()

        self.assertEquals(
            self.potmsgset.getExternallyUsedTranslationMessages(serbian),
            [imported_translation, current_translation])

    def test_getExternallySuggestedTranslationMessages(self):
        """Test retrieval of externally suggested translations."""

        # Create an external POTemplate with a POTMsgSet using
        # the same English string as the one in self.potmsgset.
        external_template = self.factory.makePOTemplate()
        product = external_template.productseries.product
        product.translations_usage = ServiceUsage.LAUNCHPAD
        external_potmsgset = self.factory.makePOTMsgSet(
            external_template,
            singular=self.potmsgset.singular_text)
        external_potmsgset.setSequence(external_template, 1)
        external_pofile = self.factory.makePOFile('sr', external_template)
        serbian = external_pofile.language
        self._refreshSuggestiveTemplatesCache()

        transaction.commit()

        # When there is no translation for the external POTMsgSet,
        # no externally used suggestions are returned.
        self.assertEquals(
            self.potmsgset.getExternallySuggestedTranslationMessages(serbian),
            [])

        # If there is a suggestion on the external POTMsgSet,
        # it is returned.
        external_suggestion = self.factory.makeSharedTranslationMessage(
            pofile=external_pofile, potmsgset=external_potmsgset,
            suggestion=True)

        transaction.commit()

        self.assertEquals(
            self.potmsgset.getExternallySuggestedTranslationMessages(serbian),
            [external_suggestion])

        # If there is an imported, non-current translation on the external
        # POTMsgSet, it is not returned as the external suggestion.
        imported_translation = self.factory.makeSharedTranslationMessage(
            pofile=external_pofile, potmsgset=external_potmsgset,
            suggestion=False, is_imported=True)
        imported_translation.is_current = False

        transaction.commit()

        self.assertEquals(
            self.potmsgset.getExternallySuggestedTranslationMessages(serbian),
            [external_suggestion])

        # A current translation on the external POTMsgSet is not
        # considered an external suggestion.
        current_translation = self.factory.makeSharedTranslationMessage(
            pofile=external_pofile, potmsgset=external_potmsgset,
            suggestion=False, is_imported=False)

        transaction.commit()

        self.assertEquals(
            self.potmsgset.getExternallySuggestedTranslationMessages(serbian),
            [external_suggestion])

    def test_hasTranslationChangedInLaunchpad(self):
        """Make sure checking whether a translation is changed in LP works."""

        sr_pofile = self.factory.makePOFile('sr', self.devel_potemplate)
        serbian = sr_pofile.language

        # When there is no translation, it's not considered changed.
        self.assertEquals(
            self.potmsgset.hasTranslationChangedInLaunchpad(
                self.devel_potemplate, serbian),
            False)

        # If only a current, non-imported translation exists, it's not
        # changed in LP.
        current_shared = self.factory.makeSharedTranslationMessage(
            pofile=sr_pofile, potmsgset=self.potmsgset,
            is_imported=False)
        self.assertEquals(
            self.potmsgset.hasTranslationChangedInLaunchpad(
                self.devel_potemplate, serbian),
            False)

        # If imported translation is current, it's not changed in LP.
        current_shared.is_current = False
        imported_shared = self.factory.makeSharedTranslationMessage(
            pofile=sr_pofile, potmsgset=self.potmsgset,
            is_imported=True)
        self.assertEquals(
            self.potmsgset.hasTranslationChangedInLaunchpad(
                self.devel_potemplate, serbian),
            False)

        # If there's a current, diverged translation, and an imported
        # non-current one, it's changed in LP.
        imported_shared.is_current = False
        current_diverged = self.factory.makeTranslationMessage(
            pofile=sr_pofile, potmsgset=self.potmsgset,
            is_imported=False)
        self.assertEquals(
            self.potmsgset.hasTranslationChangedInLaunchpad(
                self.devel_potemplate, serbian),
            True)

        # If imported one is shared and current, yet there is a diverged
        # current translation as well, it is changed in LP.
        imported_shared.is_current = False
        self.assertEquals(
            self.potmsgset.hasTranslationChangedInLaunchpad(
                self.devel_potemplate, serbian),
            True)

    def test_updateTranslation_divergence(self):
        """Test that diverging translations works as expected."""
        sr_pofile = self.factory.makePOFile('sr', self.devel_potemplate)
        serbian = sr_pofile.language

        # We can't use factory methods here because they depend on
        # updateTranslation itself.  So, a bit more boiler-plate than
        # usual.

        # Let's create a shared, current translation.
        shared_translation = self.potmsgset.updateTranslation(
            pofile=sr_pofile, submitter=sr_pofile.owner,
            new_translations=[u'Shared'], is_imported=False,
            lock_timestamp=datetime.now(pytz.UTC))
        self.assertEquals(shared_translation.potemplate, None)
        self.assertTrue(shared_translation.is_current)

        # And let's create a diverged translation by passing `force_diverged`
        # parameter to updateTranslation call.
        diverged_translation = self.potmsgset.updateTranslation(
            pofile=sr_pofile, submitter=sr_pofile.owner,
            new_translations=[u'Diverged'], is_imported=False,
            lock_timestamp=datetime.now(pytz.UTC), force_diverged=True)
        self.assertEquals(diverged_translation.potemplate,
                          self.devel_potemplate)
        # Both shared and diverged translations are marked as current,
        # since shared might be used in other templates which have no
        # divergences.
        self.assertTrue(shared_translation.is_current)
        self.assertTrue(diverged_translation.is_current)

        # But only diverged one is returned as current.
        current_translation = self.potmsgset.getCurrentTranslationMessage(
            self.devel_potemplate, serbian)
        self.assertEquals(current_translation, diverged_translation)

        # Trying to set a new, completely different translation when
        # there is a diverged translation keeps the divergence.
        new_translation = self.potmsgset.updateTranslation(
            pofile=sr_pofile, submitter=sr_pofile.owner,
            new_translations=[u'New diverged'], is_imported=False,
            lock_timestamp=datetime.now(pytz.UTC))
        self.assertEquals(new_translation.potemplate,
                          self.devel_potemplate)
        self.assertTrue(shared_translation.is_current)
        self.assertTrue(new_translation.is_current)

    def test_updateTranslation_divergence_identical_translation(self):
        """Test that identical diverging translations works as expected."""
        # Create the POFile in *all* sharing potemplates.
        sr_pofile_devel = self.factory.makePOFile('sr',
                                                  self.devel_potemplate,
                                                  create_sharing=True)
        serbian = sr_pofile_devel.language
        sr_pofile_stable = (
            self.stable_potemplate.getPOFileByLang(serbian.code))

        # We can't use factory methods here because they depend on
        # updateTranslation itself.  So, a bit more boiler-plate than
        # usual.

        # Let's create a shared, current translation.
        shared_translation = self.potmsgset.updateTranslation(
            pofile=sr_pofile_devel, submitter=sr_pofile_devel.owner,
            new_translations=[u'Shared'], is_imported=False,
            lock_timestamp=datetime.now(pytz.UTC))

        # And let's create a diverged translation on the devel series by
        # passing `force_diverged` parameter to updateTranslation call.
        diverged_translation_devel = self.potmsgset.updateTranslation(
            pofile=sr_pofile_devel, submitter=sr_pofile_devel.owner,
            new_translations=[u'Diverged'], is_imported=False,
            lock_timestamp=datetime.now(pytz.UTC), force_diverged=True)

        # Now we create a diverged translation in the stable series that
        # is identical to the diverged message in the devel series.
        diverged_translation_stable = self.potmsgset.updateTranslation(
            pofile=sr_pofile_stable, submitter=sr_pofile_stable.owner,
            new_translations=[u'Diverged'], is_imported=False,
            lock_timestamp=datetime.now(pytz.UTC), force_diverged=True)

        # This will create a new, diverged message with the same translation
        # but linked to the other potemplate.
        devel_translation = self.potmsgset.getCurrentTranslationMessage(
            self.devel_potemplate, serbian)
        self.assertEquals(diverged_translation_devel, devel_translation)
        self.assertEquals(self.devel_potemplate,
                          devel_translation.potemplate)

        stable_translation = self.potmsgset.getCurrentTranslationMessage(
            self.stable_potemplate, serbian)
        self.assertEquals(diverged_translation_stable, stable_translation)
        self.assertEquals(self.stable_potemplate,
                          stable_translation.potemplate)

    def test_updateTranslation_divergence_shared_identical_translation(self):
        """Test that identical diverging translations works as expected."""
        # Create the POFile in *all* sharing potemplates.
        sr_pofile_devel = self.factory.makePOFile('sr',
                                                  self.devel_potemplate,
                                                  create_sharing=True)
        serbian = sr_pofile_devel.language
        sr_pofile_stable = (
            self.stable_potemplate.getPOFileByLang(serbian.code))

        # We can't use factory methods here because they depend on
        # updateTranslation itself.  So, a bit more boiler-plate than
        # usual.

        # Let's create a shared, current translation.
        shared_translation = self.potmsgset.updateTranslation(
            pofile=sr_pofile_devel, submitter=sr_pofile_devel.owner,
            new_translations=[u'Shared'], is_imported=False,
            lock_timestamp=datetime.now(pytz.UTC))

        # And let's create a diverged translation on the devel series by
        # passing `force_diverged` parameter to updateTranslation call.
        diverged_translation_devel = self.potmsgset.updateTranslation(
            pofile=sr_pofile_devel, submitter=sr_pofile_devel.owner,
            new_translations=[u'Diverged'], is_imported=False,
            lock_timestamp=datetime.now(pytz.UTC), force_diverged=True)

        # Now we create a new shared translation in the stable series that
        # is identical to the diverged message in the devel series.
        new_translation_stable = self.potmsgset.updateTranslation(
            pofile=sr_pofile_stable, submitter=sr_pofile_stable.owner,
            new_translations=[u'Diverged'], is_imported=False,
            lock_timestamp=datetime.now(pytz.UTC))

        # This will create a new shared message with the same translation as
        # the diverged one.
        devel_translation = self.potmsgset.getCurrentTranslationMessage(
            self.devel_potemplate, serbian)
        self.assertEquals(diverged_translation_devel, devel_translation)
        self.assertEquals(self.devel_potemplate,
                          devel_translation.potemplate)

        stable_translation = self.potmsgset.getCurrentTranslationMessage(
            self.stable_potemplate, serbian)
        self.assertEquals(new_translation_stable, stable_translation)
        self.assertEquals(None, stable_translation.potemplate)

        # The old shared translation is not current anymore.
        self.assertFalse(shared_translation.is_current)

    def test_updateTranslation_convergence(self):
        """Test that converging translations works as expected."""
        sr_pofile = self.factory.makePOFile('sr', self.devel_potemplate)
        serbian = sr_pofile.language

        # Let's create a shared, current translation, and diverge from it
        # in this POTemplate.
        shared_translation = self.potmsgset.updateTranslation(
            pofile=sr_pofile, submitter=sr_pofile.owner,
            new_translations=[u'Shared'], is_imported=False,
            lock_timestamp=datetime.now(pytz.UTC))
        diverged_translation = self.potmsgset.updateTranslation(
            pofile=sr_pofile, submitter=sr_pofile.owner,
            new_translations=[u'Diverged'], is_imported=False,
            lock_timestamp=datetime.now(pytz.UTC), force_diverged=True)

        # Setting a diverged translation to exactly match shared one
        # will "converge" it back to the shared one.
        new_translation = self.potmsgset.updateTranslation(
            pofile=sr_pofile, submitter=sr_pofile.owner,
            new_translations=[u'Shared'], is_imported=False,
            lock_timestamp=datetime.now(pytz.UTC))
        self.assertEquals(new_translation, shared_translation)
        self.assertFalse(diverged_translation.is_current)
        self.assertTrue(new_translation.is_current)

        # Current translation is the shared one.
        current_translation = self.potmsgset.getCurrentTranslationMessage(
            self.devel_potemplate, serbian)
        self.assertEquals(current_translation, shared_translation)

    def test_setTranslationCreditsToTranslated(self):
        """Test that translation credits are correctly set as translated."""
        sr_pofile = self.factory.makePOFile('sr', self.devel_potemplate)
        credits_potmsgset = self.factory.makePOTMsgSet(
            self.devel_potemplate, singular=u'translator-credits')
        credits_potmsgset.setTranslationCreditsToTranslated(sr_pofile)
        current = credits_potmsgset.getCurrentTranslationMessage(
            self.devel_potemplate, sr_pofile.language)
        self.assertNotEqual(None, current)

    def test_setTranslationCreditsToTranslated_diverged(self):
        # Even if there's a diverged translation credits translation,
        # we should provide an automatic shared translation instead.
        alsa_utils = getUtility(IProductSet).getByName('alsa-utils')
        trunk = alsa_utils.getSeries('trunk')
        potemplate = trunk.getPOTemplate('alsa-utils')
        es_pofile = potemplate.getPOFileByLang('es')
        credits_potmsgset = potemplate.getPOTMsgSetByMsgIDText(
            u'_: EMAIL OF TRANSLATORS\nYour emails')

        es_current = credits_potmsgset.getCurrentTranslationMessage(
            potemplate, es_pofile.language)
        # Let's make sure this message is also marked as imported
        # and diverged.
        es_current.is_imported = True
        es_current.potemplate = potemplate

        self.assertTrue(es_current.is_current)
        self.assertNotEqual(None, es_current.potemplate)

        # Setting credits as translated will give us a shared translation.
        credits_potmsgset.setTranslationCreditsToTranslated(es_pofile)
        current_shared = credits_potmsgset.getSharedTranslationMessage(
            es_pofile.language)
        self.assertNotEqual(None, current_shared)
        self.assertEqual(None, current_shared.potemplate)

    def test_setTranslationCreditsToTranslated_submitter(self):
        # Submitter on the automated translation message is always
        # the rosetta_experts team.
        sr_pofile = self.factory.makePOFile('sr', self.devel_potemplate)
        translator = self.factory.makePerson()
        sr_pofile.lasttranslator = translator
        sr_pofile.owner = translator
        credits_potmsgset = self.factory.makePOTMsgSet(
            self.devel_potemplate, singular=u'translator-credits')
        current = credits_potmsgset.getCurrentTranslationMessage(
            self.devel_potemplate, sr_pofile.language)

        rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts
        self.assertEqual(rosetta_experts, current.submitter)


class TestPOTMsgSetSuggestions(TestCaseWithFactory):
    """Test retrieval and dismissal of translation suggestions."""

    layer = ZopelessDatabaseLayer

    def _setDateCreated(self, tm):
        removeSecurityProxy(tm).date_created = self.now()

    def _setDateReviewed(self, tm):
        removeSecurityProxy(tm).date_reviewed = self.now()

    def gen_now(self):
        now = datetime.now(pytz.UTC)
        while True:
            yield now
            now += timedelta(milliseconds=1)

    def setUp(self):
        # Create a product with all the boilerplate objects to be able to
        # create TranslationMessage objects.
        super(TestPOTMsgSetSuggestions, self).setUp()
        self.now = self.gen_now().next
        self.foo = self.factory.makeProduct(
            translations_usage=ServiceUsage.LAUNCHPAD)
        self.foo_main = self.factory.makeProductSeries(
            name='main', product=self.foo)

        self.potemplate = self.factory.makePOTemplate(
            productseries=self.foo_main, name="messages")
        self.potmsgset = self.factory.makePOTMsgSet(self.potemplate,
                                                    sequence=1)
        self.pofile = self.factory.makePOFile('eo', self.potemplate)
        # Set up some translation messages with dummy timestamps that will be
        # changed in the tests.
        self.translation = self.factory.makeTranslationMessage(
            self.pofile, self.potmsgset, translations=[u'trans1'],
            reviewer=self.factory.makePerson(), date_updated=self.now())
        self.suggestion1 = self.factory.makeTranslationMessage(
            self.pofile, self.potmsgset, suggestion=True,
            translations=[u'sugg1'], date_updated=self.now())
        self.suggestion2 = self.factory.makeTranslationMessage(
            self.pofile, self.potmsgset, suggestion=True,
            translations=[u'sugg2'], date_updated=self.now())

    def test_dismiss_all(self):
        # Set order of creation and review.
        self._setDateReviewed(self.translation)
        self._setDateCreated(self.suggestion1)
        self._setDateCreated(self.suggestion2)
        # There are two local suggestions now.
        self.assertContentEqual([self.suggestion1, self.suggestion2],
            self.potmsgset.getLocalTranslationMessages(
                self.potemplate, self.pofile.language))
        # Dismiss suggestions.
        self.potmsgset.dismissAllSuggestions(
            self.pofile, self.factory.makePerson(), self.now())
        # There is no local suggestion now.
        self.assertContentEqual([],
            self.potmsgset.getLocalTranslationMessages(
                self.potemplate, self.pofile.language))

    def test_dismiss_nochange(self):
        # Set order of creation and review.
        self._setDateCreated(self.suggestion1)
        self._setDateCreated(self.suggestion2)
        self._setDateReviewed(self.translation)
        # There is no local suggestion.
        self.assertContentEqual([],
            self.potmsgset.getLocalTranslationMessages(
                self.potemplate, self.pofile.language))
        # Dismiss suggestions.
        self.potmsgset.dismissAllSuggestions(
            self.pofile, self.factory.makePerson(), self.now())
        # There is still no local suggestion.
        self.assertContentEqual([],
            self.potmsgset.getLocalTranslationMessages(
                self.potemplate, self.pofile.language))

    def test_dismiss_conflicting_suggestion(self):
        # Set order of creation and review.
        self._setDateReviewed(self.translation)
        self._setDateCreated(self.suggestion1)
        old_now = self.now()
        self._setDateCreated(self.suggestion2)
        # There are two local suggestions now.
        self.assertContentEqual([self.suggestion1, self.suggestion2],
            self.potmsgset.getLocalTranslationMessages(
                self.potemplate, self.pofile.language))
        # Dismiss suggestions using an older timestamp only dismisses those
        # that were filed before that timestamp.
        self.potmsgset.dismissAllSuggestions(
            self.pofile, self.factory.makePerson(), old_now)
        self.assertContentEqual([self.suggestion2],
            self.potmsgset.getLocalTranslationMessages(
                self.potemplate, self.pofile.language))

    def test_dismiss_conflicting_translation(self):
        # Set order of creation and review.
        self._setDateCreated(self.suggestion1)
        old_now = self.now()
        self._setDateReviewed(self.translation)
        self._setDateCreated(self.suggestion2)
        # Only the 2nd suggestion is visible.
        self.assertContentEqual([self.suggestion2],
            self.potmsgset.getLocalTranslationMessages(
                self.potemplate, self.pofile.language))
        # Dismiss suggestions using an older timestamp fails if there is
        # a newer curent translation.
        self.assertRaises(TranslationConflict,
            self.potmsgset.dismissAllSuggestions,
            self.pofile, self.factory.makePerson(), old_now)
        # Still only the 2nd suggestion is visible.
        self.assertContentEqual([self.suggestion2],
            self.potmsgset.getLocalTranslationMessages(
                self.potemplate, self.pofile.language))

    def test_dismiss_empty_translation(self):
        # Set order of creation and review.
        self._setDateCreated(self.suggestion1)
        transaction.commit()
        self._setDateCreated(self.suggestion2)
        transaction.commit()
        # Make the translation a suggestion, too.
        suggestion3 = self.translation
        suggestion3.is_current = False
        self._setDateCreated(suggestion3)
        transaction.commit()
        # All suggestions are visible.
        self.assertContentEqual(
            [self.suggestion1, self.suggestion2, suggestion3],
            self.potmsgset.getLocalTranslationMessages(
                self.potemplate, self.pofile.language))
        transaction.commit()
        # Dismiss suggestions, leaving the translation empty.
        self.potmsgset.dismissAllSuggestions(
            self.pofile, self.factory.makePerson(), self.now())
        transaction.commit()
        current = self.potmsgset.getCurrentTranslationMessage(
            self.potemplate, self.pofile.language)
        self.assertNotEqual(None, current)
        self.assertEqual([None], current.translations)
        # All suggestions are gone.
        self.assertContentEqual([],
            self.potmsgset.getLocalTranslationMessages(
                self.potemplate, self.pofile.language))

    def _setUp_for_getLocalTranslationMessages(self):
        # Suggestions are retrieved using getLocalTranslationMessages.
        # For these tests we need one suggestion that is dismissed (older)
        # and one that is unreviewed (newer).
        self._setDateCreated(self.suggestion1)
        self._setDateReviewed(self.translation)
        self._setDateCreated(self.suggestion2)

    def test_getLocalTranslationMessages_include_unreviewed(self):
        # Setting include_unreviewed to True and include_dismissed to False
        # will only return those that have not been dismissed. This is
        # the default behavior but is made explicit here.
        self._setUp_for_getLocalTranslationMessages()
        self.assertContentEqual(
            [self.suggestion2],
            self.potmsgset.getLocalTranslationMessages(
                self.potemplate, self.pofile.language,
                include_dismissed=False, include_unreviewed=True))

    def test_getLocalTranslationMessages_include_dismissed(self):
        # Setting include_unreviewed to False and include_dismissed to True
        # will only return those that have been dismissed.
        self._setUp_for_getLocalTranslationMessages()
        self.assertContentEqual(
            [self.suggestion1],
            self.potmsgset.getLocalTranslationMessages(
                self.potemplate, self.pofile.language,
                include_dismissed=True, include_unreviewed=False))

    def test_getLocalTranslationMessages_include_all(self):
        # Setting both parameters to True retrieves all suggestions.
        self._setUp_for_getLocalTranslationMessages()
        self.assertContentEqual(
            [self.suggestion1, self.suggestion2],
            self.potmsgset.getLocalTranslationMessages(
                self.potemplate, self.pofile.language,
                include_dismissed=True, include_unreviewed=True))

    def test_getLocalTranslationMessages_include_none(self):
        # Setting both parameters to False retrieves nothing.
        self._setUp_for_getLocalTranslationMessages()
        self.assertContentEqual(
            [],
            self.potmsgset.getLocalTranslationMessages(
                self.potemplate, self.pofile.language,
                include_dismissed=False, include_unreviewed=False))


class TestPOTMsgSetResetTranslation(TestCaseWithFactory):
    """Test resetting the current translation."""

    layer = ZopelessDatabaseLayer

    def gen_now(self):
        now = datetime.now(pytz.UTC)
        while True:
            yield now
            now += timedelta(milliseconds=1)

    def setUp(self):
        # Create a product with all the boilerplate objects to be able to
        # create TranslationMessage objects.
        super(TestPOTMsgSetResetTranslation, self).setUp()
        self.now = self.gen_now().next
        self.foo = self.factory.makeProduct(
            translations_usage=ServiceUsage.LAUNCHPAD)
        self.foo_main = self.factory.makeProductSeries(
            name='main', product=self.foo)

        self.potemplate = self.factory.makePOTemplate(
            productseries=self.foo_main, name="messages")
        self.potmsgset = self.factory.makePOTMsgSet(self.potemplate,
                                                    sequence=1)
        self.pofile = self.factory.makePOFile('eo', self.potemplate)

    def test_resetCurrentTranslation_shared(self):
        # Resetting a shared current translation will change iscurrent=False
        # and there will be no other current translations for this POTMsgSet.

        translation = self.factory.makeTranslationMessage(
            self.pofile, self.potmsgset, translations=[u'Shared translation'],
            reviewer=self.factory.makePerson(),
            is_imported=False, force_diverged=False,
            date_updated=self.now())

        self.potmsgset.resetCurrentTranslation(self.pofile, self.now())
        current = self.potmsgset.getCurrentTranslationMessage(
            self.potemplate, self.pofile.language)
        self.assertTrue(current is None)
        self.assertFalse(translation.is_current)
        self.assertFalse(translation.is_imported)
        self.assertTrue(translation.potemplate is None)

    def test_resetCurrentTranslation_diverged_not_imported(self):
        # Resetting a diverged current translation that was not
        # imported, will change is_current to False and will make it
        # shared.

        translation = self.factory.makeTranslationMessage(
            self.pofile, self.potmsgset, translations=[u'Diverged text'],
            reviewer=self.factory.makePerson(),
            is_imported=False, force_diverged=True,
            date_updated=self.now())

        self.potmsgset.resetCurrentTranslation(self.pofile, self.now())
        current = self.potmsgset.getCurrentTranslationMessage(
            self.potemplate, self.pofile.language)
        self.assertTrue(current is None)
        self.assertFalse(translation.is_current)
        self.assertFalse(translation.is_imported)
        self.assertTrue(translation.potemplate is None)

    def test_resetCurrentTranslation_diverged_imported(self):
        # Resetting a diverged current translation that was imported in
        # Launchpad will change iscurrent to False but the translation
        # message will be still diverged.

        translation = self.factory.makeTranslationMessage(
            self.pofile, self.potmsgset, translations=[u'Imported diverged'],
            reviewer=self.factory.makePerson(),
            is_imported=True, force_diverged=True,
            date_updated=self.now())

        self.potmsgset.resetCurrentTranslation(self.pofile, self.now())
        current = self.potmsgset.getCurrentTranslationMessage(
            self.potemplate, self.pofile.language)
        self.assertTrue(current is None)
        self.assertFalse(translation.is_current)
        self.assertTrue(translation.is_imported)
        self.assertFalse(translation.potemplate is None)


class TestPOTMsgSetCornerCases(TestCaseWithFactory):
    """Test corner cases and constraints."""

    layer = ZopelessDatabaseLayer

    def gen_now(self):
        now = datetime.now(pytz.UTC)
        while True:
            yield now
            now += timedelta(milliseconds=1)

    def setUp(self):
        """Set up context to test in."""
        # Create a product with two series and a shared POTemplate
        # in different series ('devel' and 'stable').
        super(TestPOTMsgSetCornerCases, self).setUp()

        self.pofile = self.factory.makePOFile('sr')
        self.potemplate = self.pofile.potemplate
        self.uploader = getUtility(IPersonSet).getByName('carlos')
        self.now = self.gen_now().next

        # Create a single POTMsgSet that is used across all tests,
        # and add it to only one of the POTemplates.
        self.potmsgset = self.factory.makePOTMsgSet(self.potemplate,
                                                    sequence=1)

    def test_updateTranslation_SharedCurrentConstraint(self):
        # Corner case for bug #373139:
        # Adding a diverged, non-imported translation "tm1",
        # then a shared imported translation "tm2",
        # and finally, a shared imported translation "tm1" (matching original
        # diverged, non-imported translation) marks "tm2" as not current,
        # and makes "tm1" shared.
        tm1 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_imported=False, force_diverged=True)
        tm2 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_imported=True, force_shared=True)
        self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_imported=True)

        self.assertTrue(tm1.is_current)
        self.assertFalse(tm2.is_current)
        self.assertTrue(tm1.potemplate is None)
        self.assertTrue(tm2.potemplate is None)

    def test_updateTranslation_SharedImportedConstraint(self):
        # Corner case for bug #373139:
        # Adding a diverged imported translation "tm1",
        # then a shared imported translation "tm2",
        # and re-uploading "tm1" as just imported
        # makes "tm2" not is_imported, and both are shared.
        tm1 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_imported=True, force_diverged=True)
        tm2 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_imported=True, force_shared=True)
        self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_imported=True)

        self.assertTrue(tm1.is_imported)
        self.assertFalse(tm2.is_imported)
        self.assertTrue(tm1.potemplate is None)
        self.assertTrue(tm2.potemplate is None)

    def test_updateTranslation_DivergedImportedConstraint(self):
        # Corner case for bug #373139:
        # Adding a shared imported translation "tm1",
        # then a diverged imported translation "tm2",
        # and re-uploading "tm1" as imported translation
        # makes "tm2" not is_imported, and both are shared.
        tm1 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_imported=True, force_shared=True)
        tm2 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_imported=True, force_diverged=True)
        self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_imported=True)

        self.assertTrue(tm1.is_imported)
        self.assertFalse(tm2.is_imported)
        self.assertTrue(tm1.potemplate is None)
        self.assertTrue(tm2.potemplate is None)

    def test_updateTranslation_DivergedCurrentConstraint(self):
        # Corner case for bug #373139:
        # Adding a shared non-imported translation "tm0",
        # then a diverged non-imported translation "tm1"
        # (both are still current), then a diverged imported
        # translation (common pre-message-sharing-migration),
        # and we try to activate "tm0" as a forced diverged translation.
        # This makes "tm0" current and diverged, "tm1" non-current
        # and shared (basically, just a regular suggestion), and
        # "tm2" a diverged, non-current but imported translation.
        tm0 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm0"], lock_timestamp=self.now(),
            is_imported=False, force_shared=True)
        tm1 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_imported=False, force_diverged=True)
        tm2 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_imported=True, force_diverged=True)
        self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm0"], lock_timestamp=self.now(),
            is_imported=False, force_diverged=True)

        self.assertTrue(tm0.is_current)
        self.assertFalse(tm1.is_current)
        self.assertFalse(tm2.is_current)
        self.assertTrue(tm2.is_imported)
        self.assertEquals(tm0.potemplate, self.potemplate)
        self.assertTrue(tm1.potemplate is None)
        self.assertEquals(tm2.potemplate, self.potemplate)

    def test_updateTranslation_DivergedImportedToSharedImported(self):
        # Corner case for bug #381645:
        # Adding a shared imported translation "tm1",
        # then a diverged imported translation "tm2",
        # making a shared one current.
        # On importing "tm1" again, we need to remove
        # is_imported flag from diverged message.
        tm1 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_imported=True, force_shared=True)
        tm2 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_imported=True, force_diverged=True)
        tm2.is_current = False
        self.assertTrue(tm1.is_current)
        self.assertFalse(tm2.is_current)

        self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_imported=True)

        self.assertTrue(tm1.is_current)
        self.assertTrue(tm1.is_imported)
        self.assertFalse(tm2.is_current)
        self.assertFalse(tm2.is_imported)
        self.assertTrue(tm1.potemplate is None)

    def test_updateTranslation_DivergedCurrentToSharedImported(self):
        # Corner case for bug #381645:
        # Adding a shared imported translation "tm1",
        # then a diverged, non-imported current translation "tm2".
        # On importing "tm2" again, we need to make it
        # shared, and unmark existing imported message as
        # being current.
        tm1 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_imported=True, force_shared=True)
        tm2 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_imported=False, force_diverged=True)
        self.assertTrue(tm1.is_current)
        self.assertTrue(tm2.is_current)
        self.assertTrue(tm1.is_imported)
        self.assertFalse(tm2.is_imported)

        self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_imported=True)

        self.assertTrue(tm2.is_current)
        self.assertTrue(tm2.is_imported)
        self.assertTrue(tm2.potemplate is None)
        self.assertFalse(tm1.is_current)
        self.assertFalse(tm1.is_imported)

    def test_updateTranslation_SharedImportedToSharedImported(self):
        # Corner case for bug #394224:
        # Adding two imported messages, a shared "tm1" and a diverged "tm2".
        # "tm1" is the current message.
        # On importing "tm2" again, we need to make it shared while marking
        # "tm1" to be not imported because two imported shared translations
        # at the same time would trigger a database constraint.
        tm1 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_imported=True, force_shared=True)
        tm2 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_imported=True, force_diverged=True)
        tm2.is_current = False

        self.assertEquals(None, tm1.potemplate)
        self.assertEquals(self.pofile.potemplate, tm2.potemplate)

        self.assertTrue(tm1.is_current)
        self.assertFalse(tm2.is_current)

        self.assertTrue(tm1.is_imported)
        self.assertTrue(tm2.is_imported)

        self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_imported=False)

        self.assertEquals(None, tm1.potemplate)
        self.assertEquals(None, tm2.potemplate)

        self.assertFalse(tm1.is_current)
        self.assertTrue(tm2.is_current)

        self.assertFalse(tm1.is_imported)
        self.assertTrue(tm2.is_imported)

    def test_updateTranslation_DivergedCurrentToDivergedImported(self):
        # Corner case that came up when fixing bug #394224:
        # Two diverged messages, one imported "tm1", the other "tm2" (current)
        # is not.
        # Updating the first one through web ui (is_imported=False) allows
        # the imported to replace the not imported. The former diverged
        # current message is converged.
        tm1 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_imported=True, force_diverged=True)
        tm2 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_imported=False, force_diverged=True)

        self.assertEquals(self.pofile.potemplate, tm1.potemplate)
        self.assertEquals(self.pofile.potemplate, tm2.potemplate)

        self.assertFalse(tm1.is_current)
        self.assertTrue(tm2.is_current)

        self.assertTrue(tm1.is_imported)
        self.assertFalse(tm2.is_imported)

        self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_imported=False)

        self.assertEquals(self.pofile.potemplate, tm1.potemplate)
        self.assertEquals(None, tm2.potemplate)

        self.assertTrue(tm1.is_current)
        self.assertFalse(tm2.is_current)

        self.assertTrue(tm1.is_imported)
        self.assertFalse(tm2.is_imported)


class TestPOTMsgSetTranslationCredits(TestCaseWithFactory):
    """Test methods related to TranslationCredits."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestPOTMsgSetTranslationCredits, self).setUp()
        self.potemplate = self.factory.makePOTemplate()

    def test_creation_credits(self):
        # Upon creation of a translation credits message,
        # dummy translations are inserted for each POFile.
        eo_pofile = self.factory.makePOFile('eo', potemplate=self.potemplate)
        sr_pofile = self.factory.makePOFile('sr', potemplate=self.potemplate)

        credits = self.factory.makePOTMsgSet(
            self.potemplate, u'translator-credits', sequence=1)

        eo_translation = credits.getCurrentTranslationMessage(
            self.potemplate, eo_pofile.language)
        self.assertIsNot(None, eo_translation,
            "Translation credits are not translated upon creation.")

        sr_translation = credits.getCurrentTranslationMessage(
            self.potemplate, sr_pofile.language)
        self.assertIsNot(None, sr_translation,
            "Translation credits are not translated upon "
            "creation in 2nd POFile.")

    def test_creation_not_translated(self):
        # Normal messages do not receive a dummy translation.
        eo_pofile = self.factory.makePOFile('eo', potemplate=self.potemplate)

        potmsgset = self.factory.makePOTMsgSet(self.potemplate, sequence=1)
        eo_translation = potmsgset.getCurrentTranslationMessage(
            self.potemplate, eo_pofile.language)
        self.assertIs(None, eo_translation)

    def test_creation_not_imported(self):
        # Dummy translation for translation credits are not created as
        # imported and can therefore be overwritten by later imports.
        eo_pofile = self.factory.makePOFile('eo', potemplate=self.potemplate)
        imported_credits = u'Imported credits.'

        credits = self.factory.makePOTMsgSet(
            self.potemplate, u'translator-credits', sequence=1)
        translation = self.factory.makeTranslationMessage(eo_pofile, credits,
             translations=[imported_credits], is_imported=True)

        eo_translation = credits.getCurrentTranslationMessage(
            self.potemplate, eo_pofile.language)
        self.assertEqual(imported_credits, eo_translation.msgstr0.translation,
            "Imported translation credits do not replace dummy credits.")

    def test_creation_pofile(self):
        # When a new pofile is created, dummy translations are created for
        # all translation credits messages.

        credits = self.factory.makePOTMsgSet(
            self.potemplate, u'translator-credits', sequence=1)
        eo_pofile = self.factory.makePOFile('eo', potemplate=self.potemplate)

        eo_translation = credits.getCurrentTranslationMessage(
            self.potemplate, eo_pofile.language)
        self.assertIsNot(None, eo_translation,
            "Translation credits receive no dummy translation upon "
            "POFile creation.")

    def test_translation_credits_gnome(self):
        # Detect all known variations of Gnome translator credits.
        gnome_credits = [
            u'translator-credits',
            u'translator_credits',
            u'translation-credits',
        ]
        for sequence, credits_string in enumerate(gnome_credits):
            credits = self.factory.makePOTMsgSet(
                self.potemplate, credits_string, sequence=sequence+1)
            self.assertTrue(credits.is_translation_credit)
            self.assertEqual(TranslationCreditsType.GNOME,
                             credits.translation_credits_type)

    def test_translation_credits_kde(self):
        # Detect all known variations of KDE translator credits.
        kde_credits = [
            (u'Your emails', u'EMAIL OF TRANSLATORS',
             TranslationCreditsType.KDE_EMAILS),
            (u'Your names', u'NAME OF TRANSLATORS',
             TranslationCreditsType.KDE_NAMES),
        ]
        sequence = 0
        for credits_string, context, credits_type in kde_credits:
            sequence += 1
            credits = self.factory.makePOTMsgSet(
                self.potemplate, credits_string,
                context=context, sequence=sequence)
            self.assertTrue(credits.is_translation_credit)
            self.assertEqual(credits_type, credits.translation_credits_type)

            # Old KDE style.
            sequence += 1
            credits = self.factory.makePOTMsgSet(
                self.potemplate, u'_: %s\n%s' % (context, credits_string),
                sequence=sequence)
            self.assertTrue(credits.is_translation_credit)
            self.assertEqual(credits_type, credits.translation_credits_type)
