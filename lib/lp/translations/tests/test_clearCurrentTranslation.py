# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `POTMsgSet.clearCurrentTranslation`."""

__metaclass__ = type

from zope.security.proxy import removeSecurityProxy

from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.translationmessage import (
    RosettaTranslationOrigin)

ORIGIN = RosettaTranslationOrigin.SCM


class ScenarioMixin:
    layer = DatabaseFunctionalLayer

    def makePOTemplate(self):
        """Create a POTemplate for the side that's being tested."""
        raise NotImplementedError()

    def makeOtherPOTemplate(self):
        """Create a POTemplate for the other side."""
        raise NotImplementedError()

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
        """Create a (non-current) TranslationMessage for potmsgset."""
        if translations is None:
            translations = {0: self.factory.getUniqueString()}
        message = potmsgset.submitSuggestion(
            pofile, pofile.potemplate.owner, translations)

        if diverged:
            removeSecurityProxy(message).potemplate = pofile.potemplate
        return message

    def test_does_nothing_if_not_translated(self):
        pofile = self._makePOFile()
        template = pofile.potemplate
        potmsgset = self.factory.makePOTMsgSet(template, sequence=1)

        potmsgset.clearCurrentTranslation(pofile, template.owner, ORIGIN)

        current = template.translation_side_traits.getCurrentMessage(
            potmsgset, template, pofile.language)
        self.assertIs(None, current)

    def test_deactivates_shared_message(self):
        pofile = self._makePOFile()
        template = pofile.potemplate
        traits = template.translation_side_traits
        potmsgset = self.factory.makePOTMsgSet(template, sequence=1)
        tm = self._makeTranslationMessage(potmsgset, pofile)
        traits.setFlag(tm, True)
        self.assertTrue(traits.getFlag(tm))

        potmsgset.clearCurrentTranslation(pofile, template.owner, ORIGIN)

        self.assertFalse(traits.getFlag(tm))

    def test_deactivates_diverged_message(self):
        pofile = self._makePOFile()
        template = pofile.potemplate
        traits = template.translation_side_traits
        potmsgset = self.factory.makePOTMsgSet(template, sequence=1)
        tm = self._makeTranslationMessage(potmsgset, pofile, diverged=True)
        traits.setFlag(tm, True)

        potmsgset.clearCurrentTranslation(pofile, template.owner, ORIGIN)

        self.assertFalse(traits.getFlag(tm))

    def test_hides_unmasked_shared_message(self):
        # When disabling a diverged message that masks a (nonempty)
        # shared message, clearCurrentTranslation leaves an empty
        # diverged message to mask the shared message.
        pofile = self._makePOFile()
        template = pofile.potemplate
        traits = template.translation_side_traits
        potmsgset = self.factory.makePOTMsgSet(template, sequence=1)
        shared_tm = self._makeTranslationMessage(potmsgset, pofile)
        traits.setFlag(shared_tm, True)
        diverged_tm = self._makeTranslationMessage(
            potmsgset, pofile, diverged=True)
        traits.setFlag(diverged_tm, True)

        potmsgset.clearCurrentTranslation(pofile, template.owner, ORIGIN)

        current = traits.getCurrentMessage(
            potmsgset, template, pofile.language)
        self.assertNotEqual(shared_tm, current)
        self.assertNotEqual(diverged_tm, current)
        self.assertTrue(current.is_empty)
        self.assertTrue(current.is_diverged)
        self.assertEqual(template.owner, current.reviewer)

        self.assertTrue(traits.getFlag(shared_tm))

    def test_ignores_other_message(self):
        pofile = self._makePOFile()
        template = pofile.potemplate
        traits = template.translation_side_traits
        potmsgset = self.factory.makePOTMsgSet(template, sequence=1)
        tm = self._makeTranslationMessage(potmsgset, pofile)
        traits.setFlag(tm, True)

        other_template = self.makeOtherPOTemplate()
        other_pofile = self._makePOFile(potemplate=other_template)
        other_tm = self._makeTranslationMessage(potmsgset, pofile)
        traits.other_side_traits.setFlag(other_tm, True)

        potmsgset.clearCurrentTranslation(pofile, template.owner, ORIGIN)

        self.assertTrue(traits.other_side_traits.getFlag(other_tm))

    def test_deactivates_one_side(self):
        pofile = self._makePOFile()
        template = pofile.potemplate
        traits = template.translation_side_traits
        potmsgset = self.factory.makePOTMsgSet(template, sequence=1)
        tm = self._makeTranslationMessage(potmsgset, pofile)
        traits.setFlag(tm, True)
        traits.other_side_traits.setFlag(tm, True)

        potmsgset.clearCurrentTranslation(pofile, template.owner, ORIGIN)

        self.assertFalse(traits.getFlag(tm))
        self.assertTrue(traits.other_side_traits.getFlag(tm))

    def test_deactivates_both_sides(self):
        pofile = self._makePOFile()
        template = pofile.potemplate
        traits = template.translation_side_traits
        potmsgset = self.factory.makePOTMsgSet(template, sequence=1)
        tm = self._makeTranslationMessage(potmsgset, pofile)
        traits.setFlag(tm, True)
        traits.other_side_traits.setFlag(tm, True)

        potmsgset.clearCurrentTranslation(
            pofile, template.owner, ORIGIN, share_with_other_side=True)

        self.assertFalse(traits.getFlag(tm))
        self.assertFalse(traits.other_side_traits.getFlag(tm))

    def test_discards_redundant_suggestion(self):
        translations = [self.factory.getUniqueString()]
        pofile = self._makePOFile()
        template = pofile.potemplate
        potmsgset = self.factory.makePOTMsgSet(template, sequence=1)
        tm = self._makeTranslationMessage(potmsgset, pofile, translations)
        template.translation_side_traits.setFlag(tm, True)
        suggestion = self._makeTranslationMessage(
            potmsgset, pofile, translations)

        potmsgset.clearCurrentTranslation(pofile, template.owner, ORIGIN)

        remaining_tms = list(potmsgset.getAllTranslationMessages())
        self.assertEqual(1, len(remaining_tms))
        self.assertIn(remaining_tms[0], [tm, suggestion])

    def test_converges_with_empty_shared_message(self):
        pofile = self._makePOFile()
        template = pofile.potemplate
        traits = template.translation_side_traits
        potmsgset = self.factory.makePOTMsgSet(template, sequence=1)
        diverged_tm = self._makeTranslationMessage(
            potmsgset, pofile, diverged=True)
        traits.setFlag(diverged_tm, True)
        blank_shared_tm = self._makeTranslationMessage(potmsgset, pofile, [])
        traits.setFlag(blank_shared_tm, True)

        potmsgset.clearCurrentTranslation(pofile, template.owner, ORIGIN)

        self.assertTrue(traits.getFlag(blank_shared_tm))
        current = traits.getCurrentMessage(
            potmsgset, template, pofile.language)
        self.assertEqual(blank_shared_tm, current)


class TestClearCurrentTranslationUpstream(TestCaseWithFactory,
                                          ScenarioMixin):
    """Test clearCurrentTranslationUpstream on upstream side."""
    makePOTemplate = ScenarioMixin.makeUpstreamTemplate
    makeOtherPOTemplate = ScenarioMixin.makeUbuntuTemplate

    def setUp(self):
        super(TestClearCurrentTranslationUpstream, self).setUp(
            'carlos@canonical.com')


class TestClearCurrentTranslationUbuntu(TestCaseWithFactory,
                                        ScenarioMixin):
    """Test clearCurrentTranslationUpstream on Ubuntu side."""
    makePOTemplate = ScenarioMixin.makeUbuntuTemplate
    makeOtherPOTemplate = ScenarioMixin.makeUpstreamTemplate

    def setUp(self):
        super(TestClearCurrentTranslationUbuntu, self).setUp(
            'carlos@canonical.com')
