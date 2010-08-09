# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `POTMsgSet.clearCurrentTranslation`."""

__metaclass__ = type

from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class ScenarioMixin:
    layer = DatabaseFunctionalLayer

    def makeUpstreamTemplate(self):
        """Create a POTemplate for a project."""
        productseries = self.factory.makeProductSeries()
        return self.factory.makePOTemplate(productseries=productseries)

    def makeUbuntuTemplate(self):
        """Create a POTemplate for an Ubuntu package."""
        package = self.factory.makeSourcePackage()
        return self.factory.makePOTemplate(
            distroseries=package.distroseries,
            sourcepackagename=package.sourcepackagename)

    def _makePOFile(self, potemplate=None):
        """Create a `POFile` for the given template.

        Also creates a POTemplate if none is given, using
        self.makePOTemplate.
        """
        if potemplate is None:
            potemplate = self.makePOTemplate()
        return self.factory.makePOFile('nl', potemplate=potemplate)

    def _makeTranslationMessage(self, potmsgset, pofile, translations=None,
                                diverged=False):
        """Create a `TranslationMessage` for `potmsgset."""
        return self.factory.makeTranslationMessage(
            pofile=pofile, potmsgset=potmsgset, suggestion=True,
            translations=translations, force_diverged=diverged)

    def test_does_nothing_if_not_translated(self):
        pofile = self._makePOFile()
        traits = pofile.potemplate.translation_side_traits
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        
        potmsgset.clearCurrentTranslation(pofile)

        current = traits.getCurrentMessage(
            potmsgset, pofile.potemplate, pofile.language)
        self.assertIs(None, current)

    def test_deactivates_shared_message(self):
        pofile = self._makePOFile()
        traits = pofile.potemplate.translation_side_traits
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        tm = self._makeTranslationMessage(potmsgset, pofile)
        traits.setFlag(tm)
        self.assertTrue(traits.getFlag(tm))

        potmsgset.clearCurrentTranslation(pofile)

        self.assertFalse(traits.getFlag(tm))

    def test_deactivates_diverged_message(self):
        pofile = self._makePOFile()
        traits = pofile.potemplate.translation_side_traits
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        tm = self._makeTranslationMessage(potmsgset, pofile, diverged=True)
        traits.setFlag(tm, True)

        potmsgset.clearCurrentTranslation(pofile)

        self.assertFalse(traits.getFlag(tm))

    def test_hides_unmasked_shared_message(self):
        pofile = self._makePOFile()
        traits = pofile.potemplate.translation_side_traits
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        shared_tm = self._makeTranslationMessage(potmsgset, pofile)
        traits.setFlag(shared_tm)
        diverged_tm = self._makeTranslationMessage(
            potmsgset, pofile, diverged=True)
        traits.setFlag(diverged_tm)

        potmsgset.clearCurrentTranslation(pofile)

        current = traits.getCurrentMessage(
            potmsgset, pofile.potemplate, pofile.language)
        self.assertIs(None, current.msgstr0)
        self.assertTrue(traits.getFlag(shared_tm))

    def test_ignores_other_message(self):
        pofile = self._makePOFile()
        traits = pofile.potemplate.translation_side_traits
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        tm = self._makeTranslationMessage(potmsgset, pofile)
        traits.setFlag(tm)

        other_template = self.makeOtherPOTemplate()
        other_pofile = self._makePOFile(potemplate=other_template)
        other_tm = self._makeTranslationMessage(potmsgset, pofile)
        traits.other_side_traits.setFlag(other_tm)

        potmsgset.clearCurrentTranslation(pofile)

        self.assertTrue(traits.other_side_traits.getFlag(other_tm))

    def test_deactivates_one_side(self):
        pofile = self._makePOFile()
        traits = pofile.potemplate.translation_side_traits
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        tm = self._makeTranslationMessage(potmsgset, pofile)
        traits.setFlag(tm)
        traits.other_side_traits.setFlag(tm)

        potmsgset.clearCurrentTranslation(pofile)

        self.assertFalse(traits.getFlag(tm))
        self.assertTrue(traits.other_side_flags.getFlag(tm))

    def test_deactivates_both_sides(self):
        pofile = self._makePOFile()
        traits = pofile.potemplate.translation_side_traits
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        tm = self._makeTranslationMessage(potmsgset, pofile)
        traits.setFlag(tm)
        traits.other_side_traits.setFlag(tm)

        potmsgset.clearCurrentTranslation(pofile, share_with_other_side=True)

        self.assertFalse(traits.getFlag(tm))
        self.assertFalse(traits.other_side_traits.getFlag(tm))

    def test_discards_redundant_suggestion(self):
        translations = [self.factory.getUniqueString()]
        pofile = self._makePOFile()
        traits = pofile.potemplate.translation_side_traits
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        tm = self._makeTranslationMessage(potmsgset, pofile, translations)
        traits.setFlag(tm)
        suggestion = self._makeTranslationMessage(
            potmsgset, pofile, translations)

        potmsgset.clearCurrentTranslation(pofile)

        remaining_tms = list(potmsgset.getAllTranslationMessages())
        self.assertEqual(1, len(remaining_tms))
        self.assertIn(remaining_tms[0], [tm, suggestion])

    def test_converges_with_empty_shared_message(self):
        pofile = self._makePOFile()
        traits = pofile.potemplate.translation_side_traits
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        diverged_tm = self._makeTranslationMessage(
            potmsgset, pofile, diverged=True)
        traits.setFlag(diverged_tm)
        blank_shared_tm = self._makeTranslationMessage(potmsgset, pofile, [])
        traits.setFlag(blank_shared_tm)

        potmsgset.clearCurrentTranslation(pofile)

        self.assertTrue(traits.getFlag(blank_shared_tm))
        current = traits.getCurrentMessage(
            potmsgset, pofile.potemplate, pofile.language)
        self.assertEqual(blank_shared_tm, current)


class TestClearCurrentTranslationsUpstream(TestCaseWithFactory,
                                           ScenarioMixin):
    """Test clearCurrentTranslationsUpstream on upstream side."""
    makePOTemplate = ScenarioMixin.makeUpstreamTemplate
    makeOtherPOTemplate = ScenarioMixin.makeUbuntuTemplate


class TestClearCurrentTranslationsUbuntu(TestCaseWithFactory,
                                           ScenarioMixin):
    """Test clearCurrentTranslationsUpstream on Ubuntu side."""
    makePOTemplate = ScenarioMixin.makeUbuntuTemplate
    makeOtherPOTemplate = ScenarioMixin.makeUpstreamTemplate
