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
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    ZopelessDatabaseLayer,
    )
from lp.app.enums import ServiceUsage
from lp.registry.interfaces.person import IPersonSet
from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.potemplate import IPOTemplateSet
from lp.translations.interfaces.potmsgset import (
    POTMsgSetInIncompatibleTemplatesError,
    TranslationCreditsType,
    )
from lp.translations.interfaces.side import (
    ITranslationSideTraitsSet,
    TranslationSide,
    )
from lp.translations.interfaces.translationfileformat import (
    TranslationFileFormat,
    )
from lp.translations.interfaces.translationmessage import (
    RosettaTranslationOrigin,
    TranslationConflict,
    )
from lp.translations.model.translationmessage import DummyTranslationMessage


class TestTranslationSharedPOTMsgSets(TestCaseWithFactory):
    """Test discovery of translation suggestions."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Set up context to test in."""
        # Create a product with two series and a shared POTemplate
        # in different series ('devel' and 'stable').
        super(TestTranslationSharedPOTMsgSets, self).setUp(
            'carlos@canonical.com')
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
        translation = self.factory.makeCurrentTranslationMessage(
            pofile=en_pofile, potmsgset=potmsgset,
            translations=[DIVERGED_ENGLISH_STRING], diverged=True)
        self.assertEquals(potmsgset.singular_text, ENGLISH_STRING)

    def test_getCurrentTranslationMessageOrDummy_returns_upstream_tm(self):
        pofile = self.factory.makePOFile('nl')
        message = self.factory.makeCurrentTranslationMessage(pofile=pofile)

        self.assertEqual(
            message,
            message.potmsgset.getCurrentTranslationMessageOrDummy(pofile))

    def test_getCurrentTranslationMessageOrDummy_returns_ubuntu_tm(self):
        package = self.factory.makeSourcePackage()
        template = self.factory.makePOTemplate(
            distroseries=package.distroseries,
            sourcepackagename=package.sourcepackagename)
        pofile = self.factory.makePOFile(potemplate=template)
        message = self.factory.makeCurrentTranslationMessage(pofile=pofile)

        self.assertEqual(
            message,
            message.potmsgset.getCurrentTranslationMessageOrDummy(pofile))

    def test_getCurrentTranslationMessageOrDummy_returns_dummy_tm(self):
        pofile = self.factory.makePOFile('nl')
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)

        message = potmsgset.getCurrentTranslationMessageOrDummy(pofile)
        self.assertIsInstance(message, DummyTranslationMessage)

    def test_getCurrentTranslationMessageOrDummy_dummy_is_upstream(self):
        # When getCurrentDummyTranslationMessage creates a dummy for an
        # upstream translation, the dummy is current for upstream (but
        # not for Ubuntu).
        pofile = self.factory.makePOFile('fy')
        dummy = self.potmsgset.getCurrentTranslationMessageOrDummy(pofile)
        self.assertTrue(dummy.is_current_upstream)
        self.assertFalse(dummy.is_current_ubuntu)

    def test_getCurrentTranslationMessageOrDummy_dummy_is_ubuntu(self):
        # When getCurrentDummyTranslationMessage creates a dummy for an
        # Ubuntu translation, the dummy is current for Ubuntu (but
        # not upstream).
        package = self.factory.makeSourcePackage()
        template = self.factory.makePOTemplate(
            distroseries=package.distroseries,
            sourcepackagename=package.sourcepackagename)
        pofile = self.factory.makePOFile(potemplate=template)
        dummy = self.potmsgset.getCurrentTranslationMessageOrDummy(pofile)
        self.assertTrue(dummy.is_current_ubuntu)
        self.assertFalse(dummy.is_current_upstream)

    # XXX henninge 2010-12-10 bug=688519: getCurrentTranslationMessage is not
    # side-aware yet.
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

    def test_getOtherTranslation(self):
        """Test how shared and diverged current translation messages
        interact."""
        # Share POTMsgSet in a template on the other side.
        distroseries = self.factory.makeUbuntuDistroSeries()
        sourcepackagename = self.factory.makeSourcePackageName()
        ubuntu_potemplate = self.factory.makePOTemplate(
            distroseries=distroseries, sourcepackagename=sourcepackagename)
        self.potmsgset.setSequence(ubuntu_potemplate, 1)
        # Get POFiles on both sides.
        pofile = self.factory.makePOFile(potemplate=self.devel_potemplate)
        ubuntu_pofile = self.factory.makePOFile(
            potemplate=ubuntu_potemplate, language=pofile.language)

        # A shared translation is current on both sides.
        shared_translation = self.factory.makeCurrentTranslationMessage(
            pofile=pofile, potmsgset=self.potmsgset, current_other=True)
        self.assertEquals(self.potmsgset.getCurrentTranslationMessage(
            ubuntu_potemplate, ubuntu_pofile.language), shared_translation)
        self.assertEquals(self.potmsgset.getOtherTranslation(
            pofile.language, self.devel_potemplate.translation_side),
            shared_translation)

        # A diverted translation on the other side is not returned.
        diverged_translation = self.factory.makeCurrentTranslationMessage(
            pofile=ubuntu_pofile, potmsgset=self.potmsgset, diverged=True)
        self.assertEquals(self.potmsgset.getCurrentTranslationMessage(
            ubuntu_potemplate, ubuntu_pofile.language), diverged_translation)
        self.assertEquals(self.potmsgset.getOtherTranslation(
            pofile.language, self.devel_potemplate.translation_side),
            shared_translation)

    def test_getSharedTranslation(self):
        """Test how shared and diverged current translation messages
        interact."""
        # Share a POTMsgSet in two templates, and get a Serbian POFile.
        sr_pofile = self.factory.makePOFile('sr', self.devel_potemplate)
        serbian = sr_pofile.language

        # A shared translation matches the current one.
        shared_translation = self.factory.makeCurrentTranslationMessage(
            pofile=sr_pofile, potmsgset=self.potmsgset)
        self.assertEquals(
            self.potmsgset.getSharedTranslation(
                serbian, self.stable_potemplate.translation_side),
            shared_translation)

        # Adding a diverged translation doesn't break getSharedTM.
        diverged_translation = self.factory.makeCurrentTranslationMessage(
            pofile=sr_pofile, potmsgset=self.potmsgset, diverged=True)
        self.assertEquals(
            self.potmsgset.getSharedTranslation(
                serbian, self.stable_potemplate.translation_side),
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
        self.assertContentEqual(
            [],
            self.potmsgset.getLocalTranslationMessages(
                self.devel_potemplate, serbian))

        # A shared suggestion is shown in both templates.
        shared_suggestion = self.factory.makeSuggestion(
            pofile=sr_pofile, potmsgset=self.potmsgset)
        self.assertContentEqual(
            [shared_suggestion],
            self.potmsgset.getLocalTranslationMessages(
                self.devel_potemplate, serbian))
        self.assertContentEqual(
            [shared_suggestion],
            self.potmsgset.getLocalTranslationMessages(
                self.stable_potemplate, serbian))

        # A suggestion on another PO file is still shown in both templates.
        another_suggestion = self.factory.makeSuggestion(
            pofile=sr_stable_pofile, potmsgset=self.potmsgset)
        self.assertContentEqual(
            [shared_suggestion, another_suggestion],
            self.potmsgset.getLocalTranslationMessages(
                self.devel_potemplate, serbian))
        self.assertContentEqual(
            [shared_suggestion, another_suggestion],
            self.potmsgset.getLocalTranslationMessages(
                self.stable_potemplate, serbian))

        # Setting one of the suggestions as current will leave
        # them both 'reviewed' and thus hidden.
        shared_suggestion.approve(sr_pofile, self.factory.makePerson())
        self.assertContentEqual(
            [],
            self.potmsgset.getLocalTranslationMessages(
                self.devel_potemplate, serbian))

    def test_getLocalTranslationMessages_empty_message(self):
        # An empty suggestion is never returned.
        self.potmsgset.setSequence(self.stable_potemplate, 1)
        pofile = self.factory.makePOFile('sr', self.stable_potemplate)
        empty_suggestion = self.factory.makeSuggestion(
            pofile=pofile, potmsgset=self.potmsgset, translations=[None])
        self.assertContentEqual(
            [],
            self.potmsgset.getLocalTranslationMessages(
                self.stable_potemplate, pofile.language))

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
        external_suggestion = self.factory.makeSuggestion(
            pofile=external_pofile, potmsgset=external_potmsgset)

        transaction.commit()

        self.assertEquals(
            self.potmsgset.getExternallyUsedTranslationMessages(serbian),
            [])

        # If there is an imported translation on the external POTMsgSet,
        # it is returned as the externally used suggestion.
        imported_translation = self.factory.makeSharedTranslationMessage(
            pofile=external_pofile, potmsgset=external_potmsgset,
            is_current_upstream=True)
        imported_translation.makeCurrentUbuntu(False)

        transaction.commit()

        self.assertEquals(
            self.potmsgset.getExternallyUsedTranslationMessages(serbian),
            [imported_translation])

        # If there is a current translation on the external POTMsgSet,
        # it is returned as the externally used suggestion as well.
        current_translation = self.factory.makeSharedTranslationMessage(
            pofile=external_pofile, potmsgset=external_potmsgset,
            is_current_upstream=False)

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
        external_suggestion = self.factory.makeSuggestion(
            pofile=external_pofile, potmsgset=external_potmsgset)

        transaction.commit()

        self.assertEquals(
            self.potmsgset.getExternallySuggestedTranslationMessages(serbian),
            [external_suggestion])

        # If there is an imported, non-current translation on the external
        # POTMsgSet, it is not returned as the external suggestion.
        imported_translation = self.factory.makeSharedTranslationMessage(
            pofile=external_pofile, potmsgset=external_potmsgset,
            is_current_upstream=True)
        imported_translation.makeCurrentUbuntu(False)

        transaction.commit()

        self.assertEquals(
            self.potmsgset.getExternallySuggestedTranslationMessages(serbian),
            [external_suggestion])

        # A current translation on the external POTMsgSet is not
        # considered an external suggestion.
        current_translation = self.factory.makeSharedTranslationMessage(
            pofile=external_pofile, potmsgset=external_potmsgset,
            is_current_upstream=False)

        transaction.commit()

        self.assertEquals(
            self.potmsgset.getExternallySuggestedTranslationMessages(serbian),
            [external_suggestion])

    def test_hasTranslationChangedInLaunchpad(self):
        """Check whether a translation is changed in Ubuntu works."""

        sr_pofile = self.factory.makePOFile('sr', self.devel_potemplate)
        serbian = sr_pofile.language

        # When there is no translation, it's not considered changed.
        self.assertEquals(
            self.potmsgset.hasTranslationChangedInLaunchpad(
                self.devel_potemplate, serbian),
            False)

        # If only a current, non-imported translation exists, it's not
        # changed in Ubuntu.
        current_shared = self.factory.makeCurrentTranslationMessage(
            pofile=sr_pofile, potmsgset=self.potmsgset)
        self.assertEquals(
            self.potmsgset.hasTranslationChangedInLaunchpad(
                self.devel_potemplate, serbian),
            False)

        # If the current upstream translation is also current in Ubuntu,
        # it's not changed in Ubuntu.
        imported_shared = self.factory.makeCurrentTranslationMessage(
            pofile=sr_pofile, potmsgset=self.potmsgset,
            current_other=True)
        self.assertEquals(
            self.potmsgset.hasTranslationChangedInLaunchpad(
                self.devel_potemplate, serbian),
            False)

        # If there's a current, diverged translation, and an imported
        # non-current one, it's changed in Ubuntu.
        current_diverged = self.factory.makeCurrentTranslationMessage(
            pofile=sr_pofile, potmsgset=self.potmsgset, diverged=True)
        self.assertEquals(
            self.potmsgset.hasTranslationChangedInLaunchpad(
                self.devel_potemplate, serbian),
            True)

        # If the there is  a different non-diverged translations,
        # it's changed in Ubuntu.
        current = self.factory.makeCurrentTranslationMessage(
            pofile=sr_pofile, potmsgset=self.potmsgset)
        self.assertTrue(current.is_current_upstream)
        self.assertTrue(imported_shared.is_current_ubuntu)
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
            new_translations=[u'Shared'], is_current_upstream=False,
            lock_timestamp=datetime.now(pytz.UTC))
        self.assertEquals(shared_translation.potemplate, None)
        self.assertTrue(shared_translation.is_current_ubuntu)

        # And let's create a diverged translation by passing `force_diverged`
        # parameter to updateTranslation call.
        diverged_translation = self.potmsgset.updateTranslation(
            pofile=sr_pofile, submitter=sr_pofile.owner,
            new_translations=[u'Diverged'], is_current_upstream=False,
            lock_timestamp=datetime.now(pytz.UTC), force_diverged=True)
        self.assertEquals(diverged_translation.potemplate,
                          self.devel_potemplate)
        # Both shared and diverged translations are marked as current,
        # since shared might be used in other templates which have no
        # divergences.
        self.assertTrue(shared_translation.is_current_ubuntu)
        self.assertTrue(diverged_translation.is_current_ubuntu)

        # But only diverged one is returned as current.
        current_translation = self.potmsgset.getCurrentTranslationMessage(
            self.devel_potemplate, serbian)
        self.assertEquals(current_translation, diverged_translation)

        # Trying to set a new, completely different translation when
        # there is a diverged translation keeps the divergence.
        new_translation = self.potmsgset.updateTranslation(
            pofile=sr_pofile, submitter=sr_pofile.owner,
            new_translations=[u'New diverged'], is_current_upstream=False,
            lock_timestamp=datetime.now(pytz.UTC))
        self.assertEquals(new_translation.potemplate,
                          self.devel_potemplate)
        self.assertTrue(shared_translation.is_current_ubuntu)
        self.assertTrue(new_translation.is_current_ubuntu)

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
            new_translations=[u'Shared'], is_current_upstream=False,
            lock_timestamp=datetime.now(pytz.UTC))

        # And let's create a diverged translation on the devel series by
        # passing `force_diverged` parameter to updateTranslation call.
        diverged_translation_devel = self.potmsgset.updateTranslation(
            pofile=sr_pofile_devel, submitter=sr_pofile_devel.owner,
            new_translations=[u'Diverged'], is_current_upstream=False,
            lock_timestamp=datetime.now(pytz.UTC), force_diverged=True)

        # Now we create a diverged translation in the stable series that
        # is identical to the diverged message in the devel series.
        diverged_translation_stable = self.potmsgset.updateTranslation(
            pofile=sr_pofile_stable, submitter=sr_pofile_stable.owner,
            new_translations=[u'Diverged'], is_current_upstream=False,
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
            new_translations=[u'Shared'], is_current_upstream=False,
            lock_timestamp=datetime.now(pytz.UTC))

        # And let's create a diverged translation on the devel series by
        # passing `force_diverged` parameter to updateTranslation call.
        diverged_translation_devel = self.potmsgset.updateTranslation(
            pofile=sr_pofile_devel, submitter=sr_pofile_devel.owner,
            new_translations=[u'Diverged'], is_current_upstream=False,
            lock_timestamp=datetime.now(pytz.UTC), force_diverged=True)

        # Now we create a new shared translation in the stable series that
        # is identical to the diverged message in the devel series.
        new_translation_stable = self.potmsgset.updateTranslation(
            pofile=sr_pofile_stable, submitter=sr_pofile_stable.owner,
            new_translations=[u'Diverged'], is_current_upstream=False,
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
        self.assertFalse(shared_translation.is_current_ubuntu)

    def test_updateTranslation_convergence(self):
        """Test that converging translations works as expected."""
        sr_pofile = self.factory.makePOFile('sr', self.devel_potemplate)
        serbian = sr_pofile.language

        # Let's create a shared, current translation, and diverge from it
        # in this POTemplate.
        shared_translation = self.potmsgset.updateTranslation(
            pofile=sr_pofile, submitter=sr_pofile.owner,
            new_translations=[u'Shared'], is_current_upstream=False,
            lock_timestamp=datetime.now(pytz.UTC))
        diverged_translation = self.potmsgset.updateTranslation(
            pofile=sr_pofile, submitter=sr_pofile.owner,
            new_translations=[u'Diverged'], is_current_upstream=False,
            lock_timestamp=datetime.now(pytz.UTC), force_diverged=True)

        # Setting a diverged translation to exactly match shared one
        # will "converge" it back to the shared one.
        new_translation = self.potmsgset.updateTranslation(
            pofile=sr_pofile, submitter=sr_pofile.owner,
            new_translations=[u'Shared'], is_current_upstream=False,
            lock_timestamp=datetime.now(pytz.UTC))
        self.assertEquals(new_translation, shared_translation)
        self.assertFalse(diverged_translation.is_current_ubuntu)
        self.assertTrue(new_translation.is_current_ubuntu)

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
        current = credits_potmsgset.getCurrentTranslation(
            self.devel_potemplate, sr_pofile.language,
            TranslationSide.UPSTREAM)
        self.assertNotEqual(None, current)
        self.assertEquals(
            RosettaTranslationOrigin.LAUNCHPAD_GENERATED, current.origin)

    def test_setTranslationCreditsToTranslated_noop_when_translated(self):
        """Test that translation credits don't change."""
        sr_pofile = self.factory.makePOFile('sr', self.devel_potemplate)
        credits_potmsgset = self.factory.makePOTMsgSet(
            self.devel_potemplate, singular=u'translator-credits')
        old_credits = credits_potmsgset.setCurrentTranslation(
            sr_pofile, sr_pofile.potemplate.owner, {0: 'credits'},
            RosettaTranslationOrigin.SCM, share_with_other_side=True)
        credits_potmsgset.setTranslationCreditsToTranslated(sr_pofile)
        current = credits_potmsgset.getCurrentTranslation(
            self.devel_potemplate, sr_pofile.language,
            TranslationSide.UPSTREAM)
        self.assertEquals(old_credits, current)

    def test_setTranslationCreditsToTranslated_noop_when_not_credits(self):
        """Test that translation doesn't change on a non-credits message."""
        sr_pofile = self.factory.makePOFile('sr', self.devel_potemplate)
        not_credits_potmsgset = self.factory.makePOTMsgSet(
            self.devel_potemplate, singular=u'non-credit message')
        not_credits_potmsgset.setTranslationCreditsToTranslated(sr_pofile)
        current = not_credits_potmsgset.getCurrentTranslation(
            self.devel_potemplate, sr_pofile.language,
            TranslationSide.UPSTREAM)
        self.assertIs(None, current)

    def test_setTranslationCreditsToTranslated_diverged(self):
        # Even if there's a diverged translation credits translation,
        # we should provide an automatic shared translation instead.
        sr_pofile = self.factory.makePOFile('sr', self.devel_potemplate)
        credits_potmsgset = self.factory.makePOTMsgSet(
            self.devel_potemplate, singular=u'translator-credits')
        diverged_credits = self.factory.makeCurrentTranslationMessage(
            sr_pofile, credits_potmsgset)
        # Since translation credits are special, we can't easily create
        # a diverged translation on it, though it may already exist in
        # the DB.
        removeSecurityProxy(diverged_credits).potemplate = (
            sr_pofile.potemplate)
        # Make sure that worked (not a real test).
        test_diverged_credits = credits_potmsgset.getCurrentTranslation(
            sr_pofile.potemplate, sr_pofile.language,
            sr_pofile.potemplate.translation_side)
        self.assertTrue(test_diverged_credits.is_current_upstream)
        self.assertEquals(
            sr_pofile.potemplate, test_diverged_credits.potemplate)

        credits_potmsgset.setTranslationCreditsToTranslated(sr_pofile)

        # Shared translation is generated.
        shared = credits_potmsgset.getSharedTranslation(
            sr_pofile.language, sr_pofile.potemplate.translation_side)
        self.assertNotEquals(diverged_credits, shared)
        self.assertIsNot(None, shared)

    def test_setTranslationCreditsToTranslated_submitter(self):
        # Submitter on the automated translation message is always
        # the rosetta_experts team.
        sr_pofile = self.factory.makePOFile('sr', self.devel_potemplate)
        translator = self.factory.makePerson()
        sr_pofile.lasttranslator = translator
        sr_pofile.owner = translator
        credits_potmsgset = self.factory.makePOTMsgSet(
            self.devel_potemplate, singular=u'translator-credits')
        current = credits_potmsgset.getCurrentTranslation(
            self.devel_potemplate, sr_pofile.language,
            TranslationSide.UPSTREAM)

        rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts
        self.assertEqual(rosetta_experts, current.submitter)


class TestPOTMsgSetSuggestions(TestCaseWithFactory):
    """Test retrieval and dismissal of translation suggestions."""

    layer = DatabaseFunctionalLayer

    def _setDateCreated(self, tm):
        removeSecurityProxy(tm).date_created = self.now()

    def _setDateReviewed(self, tm):
        naked_tm = removeSecurityProxy(tm)
        if naked_tm.reviewer is None:
            naked_tm.reviewer = self.factory.makePerson()
        naked_tm.date_reviewed = self.now()

    def _setDateUpdated(self, tm):
        removeSecurityProxy(tm).date_updated = self.now()

    def gen_now(self):
        now = datetime.now(pytz.UTC)
        while True:
            yield now
            now += timedelta(milliseconds=1)

    def setUp(self):
        # Create a product with all the boilerplate objects to be able to
        # create TranslationMessage objects.
        super(TestPOTMsgSetSuggestions, self).setUp('carlos@canonical.com')
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
        self.translation = self.factory.makeCurrentTranslationMessage(
            removeSecurityProxy(self.pofile), self.potmsgset,
            translations=[u'trans1'], reviewer=self.factory.makePerson(),
            current_other=True, date_created=self.now())
        self.suggestion1 = self.factory.makeSuggestion(
            self.pofile, self.potmsgset, translations=[u'sugg1'],
            date_created=self.now())
        self.suggestion2 = self.factory.makeSuggestion(
            self.pofile, self.potmsgset, translations=[u'sugg2'],
            date_created=self.now())
        self._setDateCreated(self.suggestion2)

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
        suggestion3.makeCurrentUbuntu(False)
        suggestion3.makeCurrentUpstream(False)
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
        current = self.potmsgset.getCurrentTranslation(
            self.potemplate, self.pofile.language,
            self.potemplate.translation_side)
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

    layer = DatabaseFunctionalLayer

    def gen_now(self):
        now = datetime.now(pytz.UTC)
        while True:
            yield now
            now += timedelta(milliseconds=1)

    def _getCurrentMessage(self):
        traits = getUtility(ITranslationSideTraitsSet).getTraits(
            self.potemplate.translation_side)
        return traits.getCurrentMessage(
            self.potmsgset, self.potemplate, self.pofile.language)

    def setUp(self):
        # Create a product with all the boilerplate objects to be able to
        # create TranslationMessage objects.
        super(TestPOTMsgSetResetTranslation, self).setUp(
            'carlos@canonical.com')
        self.now = self.gen_now().next
        self.foo = self.factory.makeProduct(
            translations_usage=ServiceUsage.LAUNCHPAD)
        self.foo_main = self.factory.makeProductSeries(
            name='main', product=self.foo)

        template = self.potemplate = self.factory.makePOTemplate(
            productseries=self.foo_main, name="messages")
        self.potmsgset = self.factory.makePOTMsgSet(template, sequence=1)
        self.pofile = self.factory.makePOFile('eo', template)

    def test_resetCurrentTranslation_shared(self):
        # Resetting a shared current translation deactivates it, and
        # leaves no other current translation in its place.
        translation = self.factory.makeCurrentTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset)

        self.potmsgset.resetCurrentTranslation(self.pofile)

        current = self._getCurrentMessage()
        self.assertTrue(current is None)
        self.assertFalse(translation.is_current_ubuntu)
        self.assertFalse(translation.is_current_upstream)
        self.assertFalse(translation.is_diverged)

    def test_resetCurrentTranslation_diverged_not_imported(self):
        # Resetting a diverged current translation disables it and makes
        # it shared.  In other words, it becomes a suggestion.
        translation = self.factory.makeCurrentTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset)

        self.potmsgset.resetCurrentTranslation(self.pofile)

        current = self._getCurrentMessage()
        self.assertTrue(current is None)
        self.assertFalse(translation.is_current_ubuntu)
        self.assertFalse(translation.is_current_upstream)
        self.assertFalse(translation.is_diverged)

    def test_resetCurrentTranslation_unmasks_shared(self):
        # Resetting a diverged translation reverts the POTMsgSet to its
        # current shared translation.
        shared = self.factory.makeCurrentTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset)
        diverged = self.factory.makeDivergedTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset)

        self.assertNotEqual(shared, diverged)
        self.assertTrue(diverged.is_current_upstream)
        self.assertTrue(shared.is_current_upstream)
        self.assertEqual(diverged, self._getCurrentMessage())

        self.potmsgset.resetCurrentTranslation(self.pofile)

        self.assertEqual(shared, self._getCurrentMessage())

    def test_resetCurrentTranslation_resets_one_side(self):
        # By default, resetting a translation works only on one
        # translation side.
        current = self.factory.makeCurrentTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset, current_other=True)
        traits = getUtility(ITranslationSideTraitsSet).getTraits(
            self.potemplate.translation_side)

        self.assertTrue(traits.getFlag(current))
        self.assertTrue(traits.other_side_traits.getFlag(current))

        self.potmsgset.resetCurrentTranslation(
            self.pofile, share_with_other_side=False)

        self.assertFalse(traits.getFlag(current))
        self.assertTrue(traits.other_side_traits.getFlag(current))

    def test_resetCurrentTranslation_resets_both_sides(self):
        # The share_with_other_side parameter lets you reset a current
        # translation on both translation sides.
        current = self.factory.makeCurrentTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset, current_other=True)

        self.assertTrue(current.is_current_upstream)
        self.assertTrue(current.is_current_ubuntu)

        self.potmsgset.resetCurrentTranslation(
            self.pofile, share_with_other_side=True)

        self.assertFalse(current.is_current_upstream)
        self.assertFalse(current.is_current_ubuntu)

    def test_resetCurrentTranslation_does_not_override_other_message(self):
        # Resetting a message does not reset the current translation on
        # the other translation side if it's not the same one as on this
        # side.
        self.assertIs(None, self.potemplate.distroseries)
        other_potemplate = self.factory.makePOTemplate(
            distroseries=self.factory.makeDistroSeries(),
            sourcepackagename=self.factory.makeSourcePackageName())
        other_pofile = self.factory.makePOFile(
            self.pofile.language.code, potemplate=other_potemplate)

        message_this = self.factory.makeCurrentTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset)
        message_other = self.factory.makeCurrentTranslationMessage(
            pofile=other_pofile, potmsgset=self.potmsgset)
        traits = getUtility(ITranslationSideTraitsSet).getTraits(
            self.potemplate.translation_side)

        self.assertTrue(traits.other_side_traits.getFlag(message_other))

        self.potmsgset.resetCurrentTranslation(
            self.pofile, share_with_other_side=True)

        self.assertTrue(traits.other_side_traits.getFlag(message_other))

    def test_resetCurrentTranslation_detects_conflict(self):
        now = self.now()
        current = self.factory.makeCurrentTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset)
        current.markReviewed(self.factory.makePerson(), now)

        self.assertRaises(
            TranslationConflict,
            self.potmsgset.resetCurrentTranslation,
            self.pofile, now - timedelta(1))


class TestPOTMsgSetCornerCases(TestCaseWithFactory):
    """Test corner cases and constraints."""

    layer = DatabaseFunctionalLayer

    def gen_now(self):
        now = datetime.now(pytz.UTC)
        while True:
            yield now
            now += timedelta(milliseconds=1)

    def setUp(self):
        """Set up context to test in."""
        # Create a product with two series and a shared POTemplate
        # in different series ('devel' and 'stable').
        super(TestPOTMsgSetCornerCases, self).setUp('carlos@canonical.com')

        self.pofile = self.factory.makePOFile('sr')
        self.potemplate = self.pofile.potemplate
        self.uploader = getUtility(IPersonSet).getByName('carlos')
        self.now = self.gen_now().next

        # Create a single POTMsgSet that is used across all tests,
        # and add it to only one of the POTemplates.
        self.potmsgset = self.factory.makePOTMsgSet(self.potemplate,
                                                    sequence=1)

    def disabled_test_updateTranslation_SharedCurrentConstraint(self):
        # Corner case for bug #373139:
        # Adding a diverged, non-imported translation "tm1",
        # then a shared imported translation "tm2",
        # and finally, a shared imported translation "tm1" (matching original
        # diverged, non-imported translation) marks "tm2" as not current,
        # and makes "tm1" shared.
        tm1 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_current_upstream=False, force_diverged=True)
        tm2 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_current_upstream=True, force_shared=True)
        self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_current_upstream=True)

        self.assertTrue(tm1.is_current_ubuntu)
        self.assertFalse(tm2.is_current_ubuntu)
        self.assertTrue(tm1.potemplate is None)
        self.assertTrue(tm2.potemplate is None)

    def test_updateTranslation_SharedImportedConstraint(self):
        # Corner case for bug #373139:
        # Adding a diverged imported translation "tm1",
        # then a shared imported translation "tm2",
        # and re-uploading "tm1" as just imported
        # makes "tm2" not is_current_upstream, and both are shared.
        tm1 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_current_upstream=True, force_diverged=True)
        tm2 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_current_upstream=True, force_shared=True)
        self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_current_upstream=True)

        self.assertTrue(tm1.is_current_upstream)
        self.assertFalse(tm2.is_current_upstream)
        self.assertTrue(tm1.potemplate is None)
        self.assertTrue(tm2.potemplate is None)

    def test_updateTranslation_DivergedImportedConstraint(self):
        # Corner case for bug #373139:
        # Adding a shared imported translation "tm1",
        # then a diverged imported translation "tm2",
        # and re-uploading "tm1" as imported translation
        # makes "tm2" not is_current_upstream, and both are shared.
        tm1 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_current_upstream=True, force_shared=True)
        tm2 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_current_upstream=True, force_diverged=True)
        self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_current_upstream=True)

        self.assertTrue(tm1.is_current_upstream)
        self.assertFalse(tm2.is_current_upstream)
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
            is_current_upstream=False, force_shared=True)
        tm1 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_current_upstream=False, force_diverged=True)
        tm2 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_current_upstream=True, force_diverged=True)
        self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm0"], lock_timestamp=self.now(),
            is_current_upstream=False, force_diverged=True)

        self.assertTrue(tm0.is_current_ubuntu)
        self.assertFalse(tm1.is_current_ubuntu)
        self.assertFalse(tm2.is_current_ubuntu)
        self.assertTrue(tm2.is_current_upstream)
        self.assertEquals(tm0.potemplate, self.potemplate)
        self.assertTrue(tm1.potemplate is None)
        self.assertEquals(tm2.potemplate, self.potemplate)

    def test_updateTranslation_DivergedImportedToSharedImported(self):
        # Corner case for bug #381645:
        # Adding a shared imported translation "tm1",
        # then a diverged imported translation "tm2",
        # making a shared one current.
        # On importing "tm1" again, we need to remove
        # is_current_upstream flag from diverged message.
        tm1 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_current_upstream=True, force_shared=True)
        self.assertTrue(tm1.is_current_ubuntu)
        tm2 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_current_upstream=True, force_diverged=True)
        tm2.makeCurrentUbuntu(False)

        self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_current_upstream=True)

        self.assertTrue(tm1.is_current_ubuntu)
        self.assertTrue(tm1.is_current_upstream)
        self.assertFalse(tm2.is_current_ubuntu)
        self.assertFalse(tm2.is_current_upstream)
        self.assertTrue(tm1.potemplate is None)

    def disabled_test_updateTranslation_DivergedCurrentToSharedImported(self):
        # Corner case for bug #381645:
        # Adding a shared imported translation "tm1",
        # then a diverged, non-imported current translation "tm2".
        # On importing "tm2" again, we need to make it
        # shared, and unmark existing imported message as
        # being current.
        tm1 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_current_upstream=True, force_shared=True)
        tm2 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_current_upstream=False, force_diverged=True)
        self.assertTrue(tm1.is_current_ubuntu)
        self.assertTrue(tm2.is_current_ubuntu)
        self.assertTrue(tm1.is_current_upstream)
        self.assertFalse(tm2.is_current_upstream)

        self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_current_upstream=True)

        self.assertTrue(tm2.is_current_ubuntu)
        self.assertTrue(tm2.is_current_upstream)
        self.assertTrue(tm2.potemplate is None)
        self.assertFalse(tm1.is_current_ubuntu)
        self.assertFalse(tm1.is_current_upstream)

    def test_updateTranslation_SharedImportedToSharedImported(self):
        # Corner case for bug #394224:
        # Adding two imported messages, a shared "tm1" and a diverged "tm2".
        # "tm1" is the current message.
        # On importing "tm2" again, we need to make it shared while marking
        # "tm1" to be not imported because two imported shared translations
        # at the same time would trigger a database constraint.
        tm1 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_current_upstream=True, force_shared=True)
        tm2 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_current_upstream=True, force_diverged=True)
        tm2.makeCurrentUbuntu(False)

        self.assertEquals(None, tm1.potemplate)
        self.assertEquals(self.pofile.potemplate, tm2.potemplate)

        self.assertTrue(tm1.is_current_ubuntu)
        self.assertFalse(tm2.is_current_ubuntu)

        self.assertTrue(tm1.is_current_upstream)
        self.assertTrue(tm2.is_current_upstream)

        self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_current_upstream=False)

        self.assertEquals(None, tm1.potemplate)
        self.assertEquals(None, tm2.potemplate)

        self.assertFalse(tm1.is_current_ubuntu)
        self.assertTrue(tm2.is_current_ubuntu)

        self.assertFalse(tm1.is_current_upstream)
        self.assertTrue(tm2.is_current_upstream)

    def test_updateTranslation_DivergedCurrentToDivergedImported(self):
        # Corner case that came up when fixing bug #394224:
        # Two diverged messages, one current-upstream "tm1", the other "tm2"
        # (current-Ubuntu) is not.
        # Updating the first one through the web ui
        # (is_current_upstream=False) allows the current-upstream one to
        # replace the one that's not current-upstream. The former diverged
        # ubuntu message is converged.
        tm1 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_current_upstream=True, force_diverged=True)
        tm2 = self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm2"], lock_timestamp=self.now(),
            is_current_upstream=False, force_diverged=True)

        self.assertEquals(self.pofile.potemplate, tm1.potemplate)
        self.assertEquals(self.pofile.potemplate, tm2.potemplate)

        self.assertFalse(tm1.is_current_ubuntu)
        self.assertTrue(tm2.is_current_ubuntu)

        self.assertTrue(tm1.is_current_upstream)
        self.assertFalse(tm2.is_current_upstream)

        self.potmsgset.updateTranslation(
            self.pofile, self.uploader, [u"tm1"], lock_timestamp=self.now(),
            is_current_upstream=False)

        self.assertEquals(self.pofile.potemplate, tm1.potemplate)
        self.assertEquals(None, tm2.potemplate)

        self.assertTrue(tm1.is_current_ubuntu)
        self.assertFalse(tm2.is_current_ubuntu)

        self.assertTrue(tm1.is_current_upstream)
        self.assertFalse(tm2.is_current_upstream)


class TestPOTMsgSetTranslationCredits(TestCaseWithFactory):
    """Test methods related to TranslationCredits."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPOTMsgSetTranslationCredits, self).setUp(
            'carlos@canonical.com')
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
        self.factory.makeCurrentTranslationMessage(
            eo_pofile, credits, translations=[imported_credits],
            current_other=True)

        eo_translation = credits.getCurrentTranslation(
            self.potemplate, eo_pofile.language,
            self.potemplate.translation_side)
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


class TestPOTMsgSet_submitSuggestion(TestCaseWithFactory):
    """Test `POTMsgSet.submitSuggestion`."""

    layer = ZopelessDatabaseLayer

    def _makePOFileAndPOTMsgSet(self, msgid=None, with_plural=False):
        """Set up a `POFile` with `POTMsgSet`."""
        return self.factory.makePOFileAndPOTMsgSet(
            'nl', msgid=msgid, with_plural=with_plural)

    def _listenForKarma(self, pofile):
        """Set up `KarmaRecorder` on `pofile`."""
        template = pofile.potemplate
        return self.installKarmaRecorder(
            person=template.owner, action_name='translationsuggestionadded',
            product=template.product, distribution=template.distribution,
            sourcepackagename=template.sourcepackagename)

    def test_new_suggestion(self):
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()
        owner = pofile.potemplate.owner
        translation = {0: self.factory.getUniqueString()}

        suggestion = potmsgset.submitSuggestion(pofile, owner, translation)

        self.assertEqual(translation[0], suggestion.msgstr0.translation)
        self.assertEqual(None, suggestion.msgstr1)
        self.assertEqual(pofile.language, suggestion.language)
        self.assertEqual(None, suggestion.potemplate)
        self.assertEqual(pofile.potemplate.owner, suggestion.submitter)
        self.assertEqual(potmsgset, suggestion.potmsgset)
        self.assertIs(None, suggestion.date_reviewed)
        self.assertIs(None, suggestion.reviewer)
        self.assertFalse(suggestion.is_current_ubuntu)
        self.assertFalse(suggestion.is_current_upstream)
        self.assertEqual(
            RosettaTranslationOrigin.ROSETTAWEB, suggestion.origin)
        self.assertTrue(suggestion.is_complete)

    def test_new_suggestion_karma(self):
        # Karma is assigned for a new suggestion.
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()
        owner = pofile.potemplate.owner
        translation = {0: self.factory.getUniqueString()}
        karma_listener = self._listenForKarma(pofile)

        potmsgset.submitSuggestion(pofile, owner, translation)

        self.assertNotEqual(0, len(karma_listener.karma_events))

    def test_repeated_suggestion_karma(self):
        # No karma is assigned for repeating an existing suggestion.
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()
        owner = pofile.potemplate.owner
        translation = {0: self.factory.getUniqueString()}
        potmsgset.submitSuggestion(pofile, owner, translation)
        karma_listener = self._listenForKarma(pofile)

        potmsgset.submitSuggestion(pofile, owner, translation)

        self.assertEqual([], karma_listener.karma_events)

    def test_plural_forms(self):
        pofile, potmsgset = self._makePOFileAndPOTMsgSet(with_plural=True)
        owner = pofile.potemplate.owner
        translations = {
            0: self.factory.getUniqueString(),
            1: self.factory.getUniqueString(),
            }

        suggestion = potmsgset.submitSuggestion(pofile, owner, translations)
        self.assertEqual(translations[0], suggestion.msgstr0.translation)
        self.assertEqual(translations[1], suggestion.msgstr1.translation)

        # The remaining forms are untranslated.
        self.assertIs(None, suggestion.msgstr2)

    def test_repeated_suggestion(self):
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()
        owner = pofile.potemplate.owner
        translation = {0: self.factory.getUniqueString()}
        suggestion = potmsgset.submitSuggestion(pofile, owner, translation)

        repeat = potmsgset.submitSuggestion(pofile, owner, translation)

        self.assertEqual(suggestion, repeat)

    def test_same_as_shared(self):
        # A suggestion identical to a shared current translation is a
        # repeated suggestion.
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()
        owner = pofile.potemplate.owner
        translation = {0: self.factory.getUniqueString()}
        shared_message = self.factory.makeSharedTranslationMessage(
            pofile=pofile, potmsgset=potmsgset, translator=owner,
            translations=translation)
        self.assertTrue(shared_message.is_current_ubuntu)

        suggestion = potmsgset.submitSuggestion(pofile, owner, translation)

        self.assertEqual(shared_message, suggestion)

    def test_same_as_diverged(self):
        # A suggestion identical to a diverged current translation for
        # the same template is a repeated suggestion.
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()
        owner = pofile.potemplate.owner
        translation = {0: self.factory.getUniqueString()}
        diverged_message = self.factory.makeCurrentTranslationMessage(
            pofile=pofile, potmsgset=potmsgset, translator=owner,
            translations=translation, diverged=True)

        suggestion = potmsgset.submitSuggestion(pofile, owner, translation)

        self.assertEqual(diverged_message, suggestion)

    def test_same_as_diverged_elsewhere(self):
        # If a suggestion is identical to a diverged current translation
        # in another, sharing template, that doesn't make the suggestion
        # a repeated suggestion.
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()
        owner = pofile.potemplate.owner
        series2 = self.factory.makeProductSeries(
            product=pofile.potemplate.product)
        template2 = self.factory.makePOTemplate(
            productseries=series2, name=pofile.potemplate.name)
        pofile2 = template2.getPOFileByLang(pofile.language.code)
        translation = {0: self.factory.getUniqueString()}
        diverged_message = self.factory.makeCurrentTranslationMessage(
            pofile=pofile2, potmsgset=potmsgset, translator=owner,
            translations=translation, diverged=True)

        suggestion = potmsgset.submitSuggestion(pofile, owner, translation)

        self.assertNotEqual(diverged_message, suggestion)

    def test_same_as_hidden_shared(self):
        # A suggestion identical to a shared message is a repeated
        # suggestion even if the shared message is "hidden" by a
        # diverged message.
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()
        owner = pofile.potemplate.owner
        translation = {0: self.factory.getUniqueString()}
        translation2 = {0: self.factory.getUniqueString()}
        shared_message = self.factory.makeSharedTranslationMessage(
            pofile=pofile, potmsgset=potmsgset, translator=owner,
            translations=translation)
        diverged_message = self.factory.makeCurrentTranslationMessage(
            pofile=pofile, potmsgset=potmsgset, translator=owner,
            translations=translation2, diverged=True)

        suggestion = potmsgset.submitSuggestion(pofile, owner, translation)

        self.assertEqual(shared_message, suggestion)

    def test_suggestions_on_sharing_templates(self):
        # A suggestion identical to another one on a template that
        # shares with its own is a repeated suggestion.
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()
        owner = pofile.potemplate.owner
        series2 = self.factory.makeProductSeries(
            product=pofile.potemplate.product)
        template2 = self.factory.makePOTemplate(
            productseries=series2, name=pofile.potemplate.name)
        pofile2 = template2.getPOFileByLang(pofile.language.code)
        translation = {0: self.factory.getUniqueString()}

        suggestion = potmsgset.submitSuggestion(pofile, owner, translation)
        suggestion2 = potmsgset.submitSuggestion(pofile2, owner, translation)

        self.assertEqual(suggestion, suggestion2)

    def test_credits_message(self):
        # Suggestions for translation-credits messages are ignored.
        pofile, potmsgset = self._makePOFileAndPOTMsgSet(
            msgid='translator-credits')
        self.assertTrue(potmsgset.is_translation_credit)
        owner = pofile.potemplate.owner
        translation = {0: self.factory.getUniqueString()}

        suggestion = potmsgset.submitSuggestion(pofile, owner, translation)

        self.assertIs(None, suggestion)

    def test_credits_karma(self):
        # No karma is assigned for suggestions on translation credits.
        pofile, potmsgset = self._makePOFileAndPOTMsgSet(
            msgid='translator-credits')
        self.assertTrue(potmsgset.is_translation_credit)
        owner = pofile.potemplate.owner
        translation = {0: self.factory.getUniqueString()}
        karma_listener = self._listenForKarma(pofile)

        suggestion = potmsgset.submitSuggestion(pofile, owner, translation)

        self.assertEqual([], karma_listener.karma_events)


class TestSetCurrentTranslation(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSetCurrentTranslation, self).setUp('carlos@canonical.com')

    def _makePOFileAndPOTMsgSet(self):
        pofile = self.factory.makePOFile('nl')
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        return pofile, potmsgset

    def _makeTranslations(self, potmsgset, forms=1):
        """Produce a POTranslations dict of random translations."""
        return dict(
            (form, self.factory.getUniqueString())
            for form in xrange(forms))

    def test_baseline(self):
        # setCurrentTranslation sets the current translation
        # for a message.
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()
        translations = self._makeTranslations(potmsgset)
        origin = RosettaTranslationOrigin.SCM

        message = potmsgset.setCurrentTranslation(
            pofile, pofile.potemplate.owner, translations, origin)

        self.assertEqual(message, potmsgset.getCurrentTranslation(
            pofile.potemplate, pofile.language,
            pofile.potemplate.translation_side))
        self.assertEqual(origin, message.origin)

    def test_identical(self):
        # Setting the same message twice leaves the original as-is.
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()
        translations = self._makeTranslations(potmsgset)

        first_message = potmsgset.setCurrentTranslation(
            pofile, pofile.potemplate.owner, translations,
            RosettaTranslationOrigin.ROSETTAWEB)
        second_message = potmsgset.setCurrentTranslation(
            pofile, self.factory.makePerson(), translations,
            RosettaTranslationOrigin.SCM)

        self.assertEqual(first_message, second_message)
        message = first_message
        self.assertEqual(pofile.potemplate.owner, message.submitter)
        self.assertEqual(RosettaTranslationOrigin.ROSETTAWEB, message.origin)

    def test_share_with_other_side(self):
        # If requested, the translation can also be set on the other side.
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()
        translations = self._makeTranslations(potmsgset)
        origin = RosettaTranslationOrigin.ROSETTAWEB

        message = potmsgset.setCurrentTranslation(
            pofile, pofile.potemplate.owner, translations, origin,
            share_with_other_side=True)

        self.assertEqual(message, potmsgset.getOtherTranslation(
            pofile.language, pofile.potemplate.translation_side))

    def test_detects_conflict(self):
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()
        translations = self._makeTranslations(potmsgset)
        origin = RosettaTranslationOrigin.ROSETTAWEB

        # A translator bases a change on a page view from 5 minutes ago.
        lock_timestamp = datetime.now(pytz.UTC) - timedelta(minutes=5)

        # Meanwhile someone else changes the same message's translation.
        newer_translation = self.factory.makeCurrentTranslationMessage(
            pofile=pofile, potmsgset=potmsgset)

        # This raises a translation conflict.
        self.assertRaises(
            TranslationConflict,
            potmsgset.setCurrentTranslation,
            pofile, pofile.potemplate.owner, translations, origin,
            lock_timestamp=lock_timestamp)


class BaseTestGetCurrentTranslation(object):
    layer = DatabaseFunctionalLayer

    def test_no_translation(self):
        # getCurrentTranslation returns None when there's no translation.
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()
        current = potmsgset.getCurrentTranslation(
            pofile.potemplate, pofile.language, self.this_side)
        self.assertIs(None, current)

    def test_basic_get(self):
        # getCurrentTranslation gets the current translation
        # for a message.
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()
        translations = {
            0: self.factory.getUniqueString('translation'), }
        origin = RosettaTranslationOrigin.SCM
        message = potmsgset.setCurrentTranslation(
            pofile, pofile.potemplate.owner, translations, origin)

        current = potmsgset.getCurrentTranslation(
            pofile.potemplate, pofile.language, self.this_side)
        self.assertEqual(message, current)

    def test_requires_side(self):
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()
        self.assertRaises(
            AssertionError,
            potmsgset.getCurrentTranslation,
            pofile.potemplate, pofile.language, None)

    def test_other_languages_ignored(self):
        # getCurrentTranslation never returns a translation for another
        # language.
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()
        pofile_other_language = self.factory.makePOFile(
            potemplate=pofile.potemplate)
        translations = {
            0: self.factory.getUniqueString('translation'), }
        origin = RosettaTranslationOrigin.SCM
        message = potmsgset.setCurrentTranslation(
            pofile_other_language, pofile.potemplate.owner,
            translations, origin)

        current = potmsgset.getCurrentTranslation(
            pofile.potemplate, pofile.language, self.this_side)
        self.assertIs(None, current)

    def test_other_diverged_no_translation(self):
        # getCurrentTranslation gets the current upstream translation
        # for a message.
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()
        pofile_other = self._makeOtherPOFile(pofile, potmsgset)

        # Create a diverged translation in pofile_other.
        translations = {
            0: self.factory.getUniqueString('translation'), }
        suggestion = potmsgset.submitSuggestion(
            pofile_other, pofile_other.potemplate.owner, translations)
        suggestion.approveAsDiverged(
            pofile_other, pofile_other.potemplate.owner)

        current = potmsgset.getCurrentTranslation(
            pofile.potemplate, pofile.language, self.this_side)
        self.assertIs(None, current)

    def test_other_side(self):
        # getCurrentTranslation gets the current translation
        # for a message depending on the side that is specified.
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()
        pofile_other = self._makeOtherPOFile(pofile, potmsgset)

        # Create current translations in 'pofile' and 'pofile_other'.
        translations_here = {
            0: self.factory.getUniqueString('here'), }
        translations_other = {
            0: self.factory.getUniqueString('other'), }
        origin = RosettaTranslationOrigin.SCM

        current_translation = potmsgset.setCurrentTranslation(
            pofile, pofile.potemplate.owner,
            translations_here, origin)
        other_translation = potmsgset.setCurrentTranslation(
            pofile_other, pofile_other.potemplate.owner,
            translations_other, origin)

        self.assertEquals(
            current_translation,
            potmsgset.getCurrentTranslation(
                pofile_other.potemplate, pofile_other.language,
                self.this_side))
        self.assertEquals(
            other_translation,
            potmsgset.getCurrentTranslation(
                pofile.potemplate, pofile.language, self.other_side))

    def test_prefers_diverged(self):
        # getCurrentTranslation prefers a diverged translation if
        # it's available for the given potemplate.
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()

        # Create both a shared and a diverged translation in pofile.
        translations_shared = {
            0: self.factory.getUniqueString('shared'), }
        translations_diverged = {
            0: self.factory.getUniqueString('diverged'), }
        origin = RosettaTranslationOrigin.SCM
        shared_message = potmsgset.setCurrentTranslation(
            pofile, pofile.potemplate.owner, translations_shared, origin)
        diverged_message = potmsgset.submitSuggestion(
            pofile, pofile.potemplate.owner, translations_diverged)
        diverged_message.approveAsDiverged(pofile, pofile.potemplate.owner)

        current = potmsgset.getCurrentTranslation(
            pofile.potemplate, pofile.language, self.this_side)
        self.assertEquals(diverged_message, current)

    def test_shared_when_requested(self):
        # getCurrentTranslation returns a shared translation even with
        # diverged translation present if shared one was asked for.
        pofile, potmsgset = self._makePOFileAndPOTMsgSet()

        # Create both a shared and a diverged translation in pofile.
        translations_shared = {
            0: self.factory.getUniqueString('shared'), }
        translations_diverged = {
            0: self.factory.getUniqueString('diverged'), }
        origin = RosettaTranslationOrigin.SCM
        shared_message = potmsgset.setCurrentTranslation(
            pofile, pofile.potemplate.owner, translations_shared, origin)
        diverged_message = potmsgset.submitSuggestion(
            pofile, pofile.potemplate.owner, translations_diverged)
        diverged_message.approveAsDiverged(pofile, pofile.potemplate.owner)

        current = potmsgset.getCurrentTranslation(
            None, pofile.language, self.this_side)
        self.assertEquals(shared_message, current)


class TestGetCurrentTranslationForUpstreams(BaseTestGetCurrentTranslation,
                                            TestCaseWithFactory):
    """getCurrentTranslation working on an upstream POFile."""

    def setUp(self):
        super(TestGetCurrentTranslationForUpstreams, self).setUp(
            'carlos@canonical.com')
        self.this_side = TranslationSide.UPSTREAM
        self.other_side = TranslationSide.UBUNTU

    def _makePOFileAndPOTMsgSet(self):
        pofile = self.factory.makePOFile()
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        return pofile, potmsgset

    def _makeOtherPOFile(self, pofile, potmsgset):
        sp = self.factory.makeSourcePackage()
        potemplate = self.factory.makePOTemplate(
            name=pofile.potemplate.name,
            distroseries=sp.distroseries,
            sourcepackagename=sp.sourcepackagename)
        pofile_other = self.factory.makePOFile(potemplate=potemplate,
                                               language=pofile.language)
        potmsgset.setSequence(potemplate, 1)
        return pofile_other


class TestGetCurrentTranslationForUbuntu(BaseTestGetCurrentTranslation,
                                         TestCaseWithFactory):
    """getCurrentTranslation working on an Ubuntu POFile."""

    def setUp(self):
        super(TestGetCurrentTranslationForUbuntu, self).setUp(
            'carlos@canonical.com')
        self.this_side = TranslationSide.UBUNTU
        self.other_side = TranslationSide.UPSTREAM

    def _makePOFileAndPOTMsgSet(self):
        sp = self.factory.makeSourcePackage()
        potemplate = self.factory.makePOTemplate(
            distroseries=sp.distroseries,
            sourcepackagename=sp.sourcepackagename)
        pofile = self.factory.makePOFile(potemplate=potemplate)
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        return pofile, potmsgset

    def _makeOtherPOFile(self, pofile, potmsgset):
        potemplate = self.factory.makePOTemplate(name=pofile.potemplate.name)
        pofile_other = self.factory.makePOFile(potemplate=potemplate,
                                               language=pofile.language)
        potmsgset.setSequence(potemplate, 1)
        return pofile_other


class TestCheckForConflict(TestCaseWithFactory):
    """Test POTMsgSet._checkForConflict."""

    layer = ZopelessDatabaseLayer

    def test_passes_nonconflict(self):
        # If there is no conflict, _checkForConflict completes normally.
        current_tm = self.factory.makeCurrentTranslationMessage()
        potmsgset = removeSecurityProxy(current_tm.potmsgset)
        newer = current_tm.date_reviewed + timedelta(days=1)

        potmsgset._checkForConflict(current_tm, newer)

    def test_detects_conflict(self):
        # If there's been another translation since lock_timestamp,
        # _checkForConflict raises TranslationConflict.
        current_tm = self.factory.makeCurrentTranslationMessage()
        potmsgset = removeSecurityProxy(current_tm.potmsgset)
        older = current_tm.date_reviewed - timedelta(days=1)

        self.assertRaises(
            TranslationConflict,
            potmsgset._checkForConflict,
            current_tm, older)

    def test_passes_identical_change(self):
        # When concurrent translations are identical, there is no
        # conflict.
        current_tm = self.factory.makeCurrentTranslationMessage()
        potmsgset = removeSecurityProxy(current_tm.potmsgset)
        older = current_tm.date_reviewed - timedelta(days=1)

        potmsgset._checkForConflict(
            current_tm, older, potranslations=current_tm.all_msgstrs)

    def test_quiet_if_no_current_message(self):
        # If there is no current translation, _checkForConflict accepts
        # that as conflict-free.
        potemplate = self.factory.makePOTemplate()
        potmsgset = self.factory.makePOTMsgSet(potemplate, sequence=1)
        old = datetime.now(pytz.UTC) - timedelta(days=366)

        removeSecurityProxy(potmsgset)._checkForConflict(None, old)

    def test_quiet_if_no_timestamp(self):
        # If there is no lock_timestamp, _checkForConflict does not
        # check for conflicts.
        current_tm = self.factory.makeCurrentTranslationMessage()
        potmsgset = removeSecurityProxy(current_tm.potmsgset)

        removeSecurityProxy(potmsgset)._checkForConflict(current_tm, None)


class TestFindTranslationMessage(TestCaseWithFactory):
    """Test `POTMsgSet.findTranslationMessage`."""

    layer = ZopelessDatabaseLayer

    def _makeTranslations(self):
        """Produce an arbitrary translation."""
        return {0: self.factory.getUniqueString()}

    def _makeSharedAndDivergedMessages(self, pofile, potmsgset, translations):
        """Create shared and diverged `TranslationMessage`s.

        :param pofile: The `POFile` to create messages for.  Has to be
            for a `Product`, not a `SourcePackage` to accommodate this
            method's implementation.
        :param potmsgset: The `POTMsgSet` that the `TranslationMessage`s
            should translate.
        :param translations: A dict mapping plural forms to strings.
            The `TranslationMessage`s will translate to these strings.
        :return: A tuple consisting of a shared `TranslationMessage` and
            a diverged one.
        """
        template = pofile.potemplate
        assert template.productseries is not None, (
            "This test assumes a product template; got a package template.")
        other_template = self.factory.makePOTemplate(
            distroseries=self.factory.makeDistroSeries(),
            sourcepackagename=self.factory.makeSourcePackageName())
        other_pofile = self.factory.makePOFile(
            pofile.language.code, potemplate=other_template)

        diverged = self.factory.makeDivergedTranslationMessage(
            pofile=pofile, potmsgset=potmsgset,
            translations=translations)
        shared = self.factory.makeCurrentTranslationMessage(
            pofile=other_pofile, potmsgset=potmsgset,
            translations=translations)

        return shared, diverged

    def test_makeSharedAndDivergedMessages(self):
        pofile, potmsgset = self.factory.makePOFileAndPOTMsgSet('zun')
        translations = self._makeTranslations()
        shared, diverged = self._makeSharedAndDivergedMessages(
            pofile, potmsgset, translations)

        self.assertNotEqual(shared, diverged)
        self.assertFalse(shared.is_diverged)
        self.assertTrue(diverged.is_diverged)
        for message in shared, diverged:
            self.assertEqual(potmsgset, message.potmsgset)
            self.assertEqual(translations[0], message.translations[0])

    def test_finds_nothing_if_no_message(self):
        pofile, potmsgset = self.factory.makePOFileAndPOTMsgSet('aa')
        translations = self._makeTranslations()

        potmsgset = removeSecurityProxy(potmsgset)
        found = potmsgset.findTranslationMessage(
            pofile, translations=translations)
        self.assertIs(None, found)

    def test_finds_matching_message(self):
        pofile, potmsgset = self.factory.makePOFileAndPOTMsgSet('ab')
        translations = self._makeTranslations()
        message = self.factory.makeSuggestion(
            pofile=pofile, potmsgset=potmsgset, translations=translations)

        potmsgset = removeSecurityProxy(potmsgset)
        found = potmsgset.findTranslationMessage(
            pofile, translations=translations)
        self.assertEqual(message, found)

    def test_ignores_different_message(self):
        pofile, potmsgset = self.factory.makePOFileAndPOTMsgSet('ae')
        translations = self._makeTranslations()
        self.factory.makeSuggestion(
            pofile=pofile, potmsgset=potmsgset, translations=translations)

        potmsgset = removeSecurityProxy(potmsgset)
        found = potmsgset.findTranslationMessage(
            pofile, translations=self._makeTranslations())
        self.assertIs(None, found)

    def test_finds_diverged_message(self):
        pofile, potmsgset = self.factory.makePOFileAndPOTMsgSet('af')
        translations = self._makeTranslations()
        message = self.factory.makeCurrentTranslationMessage(
            pofile=pofile, potmsgset=potmsgset, translations=translations,
            diverged=True)

        potmsgset = removeSecurityProxy(potmsgset)
        found = potmsgset.findTranslationMessage(
            pofile, translations=translations)
        self.assertEqual(message, found)

    def test_ignores_diverged_message_in_other_pofile(self):
        pofile, potmsgset = self.factory.makePOFileAndPOTMsgSet('ak')
        translations = self._makeTranslations()
        other_pofile = self.factory.makePOFile(pofile.language.code)
        potmsgset.setSequence(pofile.potemplate, 1)

        self.factory.makeCurrentTranslationMessage(
            pofile=other_pofile, potmsgset=potmsgset,
            translations=translations, diverged=True)

        potmsgset = removeSecurityProxy(potmsgset)
        found = potmsgset.findTranslationMessage(
            pofile, translations=translations)
        self.assertIs(None, found)

    def test_prefers_diverged_message_by_default(self):
        pofile, potmsgset = self.factory.makePOFileAndPOTMsgSet('am')
        translations = self._makeTranslations()
        shared, diverged = self._makeSharedAndDivergedMessages(
            pofile, potmsgset, translations)

        potmsgset = removeSecurityProxy(potmsgset)
        found = potmsgset.findTranslationMessage(
            pofile, translations=translations)
        self.assertEqual(diverged, found)

    def test_prefers_diverged_message_if_instructed(self):
        pofile, potmsgset = self.factory.makePOFileAndPOTMsgSet('am')
        translations = self._makeTranslations()
        shared, diverged = self._makeSharedAndDivergedMessages(
            pofile, potmsgset, translations)

        potmsgset = removeSecurityProxy(potmsgset)
        found = potmsgset.findTranslationMessage(
            pofile, translations=translations, prefer_shared=False)
        self.assertEqual(diverged, found)

    def test_prefers_shared_message_if_instructed(self):
        pofile, potmsgset = self.factory.makePOFileAndPOTMsgSet('am')
        translations = self._makeTranslations()
        shared, diverged = self._makeSharedAndDivergedMessages(
            pofile, potmsgset, translations)

        potmsgset = removeSecurityProxy(potmsgset)
        found = potmsgset.findTranslationMessage(
            pofile, translations=translations, prefer_shared=True)
        self.assertEqual(shared, found)
