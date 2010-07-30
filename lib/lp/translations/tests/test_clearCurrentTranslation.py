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

    def getCurrentUpstreamMessage(self, potmsgset, pofile):
        """Find the message that is current for upstream."""
        return potmsgset.getImportedTranslationMessage(
            pofile.potemplate, pofile.language)
    
    def getCurrentUbuntuMessage(self, potmsgset, pofile):
        """Find the message that is current for Ubuntu."""
        return potmsgset.getCurrentTranslationMessage(
            pofile.potemplate, pofile.language)
    
    def _makePOFile(self, potemplate=None):
        """Create a `POFile` for the given template.

        Also creates a POTemplate if none is given, using
        self.makePOTemplate.
        """
        if potemplate is None:
            potemplate = self.makePOTemplate()
        return self.factory.makePOFile('nl', potemplate=potemplate)

    def _isCurrent(self, translationmessage):
        """Is `translationmessage` current on the side we're testing?"""
        return getattr(translationmessage, self.this_flag)

    def _isCurrentOther(self, translationmessage):
        """Is `translationmessage` current on the other side?"""
        return getattr(translationmessage, self.other_flag)

    def _setCurrent(self, translationmessage, current=True):
        """Set "current" flag on `translationmessage`."""

    def _setCurrentOther(self, translationmessage, current=True):
        """Set "current" flag on `translationmessage` for other side."""

    def _makeTranslationMessage(self, potmsgset, pofile, translations=None,
                                diverged=False):
        """Create a `TranslationMessage` for `potmsgset."""
        return self.factory.makeTranslationMessage(
            pofile=pofile, potmsgset=potmsgset, suggestion=True,
            translations=translations, force_diverged=diverged)

    def test_deactivates_shared_message(self):
        pofile = self._makePOFile()
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        tm = self._makeTranslationMessage(potmsgset, pofile)
        self._setCurrent(tm)
        self.assertTrue(self._isCurrent(tm))

        potmsgset.clearCurrentTranslation(pofile)

        self.assertFalse(self._isCurrent(tm))

    def test_deactivates_diverged_message(self):
        pofile = self._makePOFile()
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        tm = self._makeTranslationMessage(potmsgset, pofile, diverged=True)
        self._setCurrent(tm)
        self.assertTrue(self._isCurrent(tm))

        potmsgset.clearCurrentTranslation(pofile)

        self.assertFalse(self._isCurrent(tm))

    def test_hides_unmasked_shared_message(self):
        pofile = self._makePOFile()
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        shared_tm = self._makeTranslationMessage(potmsgset, pofile)
        self._setCurrent(shared_tm)
        diverged_tm = self._makeTranslationMessage(
            potmsgset, pofile, diverged=True)
        self._setCurrent(diverged_tm)

        potmsgset.clearCurrentTranslation(pofile)

        current = self.getCurrentMessage(potmsgset, pofile)
        self.assertIs(None, current.msgstr0)
        self.assertTrue(self._isCurrent(shared_tm))

    def test_ignores_other_message(self):
        pofile = self._makePOFile()
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        tm = self._makeTranslationMessage(potmsgset, pofile)
        self._setCurrent(tm)

        other_template = self.makeOtherPOTemplate()
        other_pofile = self._makePOFile(potemplate=other_template)
        other_tm = self._makeTranslationMessage(potmsgset, pofile)
        self._setCurrentOther(other_tm)

        potmsgset.clearCurrentTranslation(pofile)

        self.assertTrue(self._isCurrentOther(other_tm))

    def test_deactivates_one_side(self):
        pofile = self._makePOFile()
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        tm = self._makeTranslationMessage(potmsgset, pofile)
        self._setCurrent(tm)
        self._setCurrentOther(tm)

        potmsgset.clearCurrentTranslation(pofile)

        self.assertFalse(self._isCurrent(tm))
        self.assertTrue(self._isCurrentOther(tm))

    def test_deactivates_both_sides(self):
        pofile = self._makePOFile()
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        tm = self._makeTranslationMessage(potmsgset, pofile)
        self._setCurrent(tm)
        self._setCurrentOther(tm)

        potmsgset.clearCurrentTranslation(pofile, share_with_other_side=True)

        self.assertFalse(self._isCurrent(tm))
        self.assertFalse(self._isCurrentOther(tm))

    def test_discards_redundant_suggestion(self):
        translations = [self.factory.getUniqueString()]
        pofile = self._makePOFile()
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        tm = self._makeTranslationMessage(potmsgset, pofile, translations)
        self._setCurrent(tm)
        suggestion = self._makeTranslationMessage(
            potmsgset, pofile, translations)

        potmsgset.clearCurrentTranslation(pofile)

        remaining_tms = list(potmsgset.getAllTranslationMessages())
        self.assertEqual(1, len(remaining_tms))
        self.assertIn(remaining_tms[0], [tm, suggestion])

    def test_converges_with_hidden_shared_message(self):
        pofile = self._makePOFile()
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        diverged_tm = self._makeTranslationMessage(
            potmsgset, pofile, diverged=True)
        self._setCurrent(diverged_tm)
        blank_shared_tm = self._makeTranslationMessage(potmsgset, pofile, [])
        self._setCurrent(blank_shared_tm)

        potmsgset.clearCurrentTranslation(pofile)

        self.assertTrue(self._isCurrent(blank_shared_tm))
        current_message = self.getCurrentMessage(potmsgset, pofile)
        self.assertEqual(blank_shared_tm, current_message)


class TestClearCurrentTranslationsUpstream(TestCaseWithFactory,
                                           ScenarioMixin):
    """Test clearCurrentTranslationsUpstream on upstream side."""
    makePOTemplate = ScenarioMixin.makeUpstreamTemplate
    makeOtherPOTemplate = ScenarioMixin.makeUbuntuTemplate
    this_flag = 'is_current_upstream'
    other_flag = 'is_current_ubuntu'
    getCurrentMessage = ScenarioMixin.getCurrentUpstreamMessage


class TestClearCurrentTranslationsUbuntu(TestCaseWithFactory,
                                           ScenarioMixin):
    """Test clearCurrentTranslationsUpstream on Ubuntu side."""
    makePOTemplate = ScenarioMixin.makeUbuntuTemplate
    makeOtherPOTemplate = ScenarioMixin.makeUpstreamTemplate
    this_flag = 'is_current_ubuntu'
    other_flag = 'is_current_upstream'
    getCurrentMessage = ScenarioMixin.getCurrentUbuntuMessage
