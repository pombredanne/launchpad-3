# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
import unittest

import gettextpo
from pytz import timezone
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.app.enums import ServiceUsage
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing.factory import LaunchpadObjectFactory
from lp.translations.interfaces.potemplate import IPOTemplateSet
from lp.translations.interfaces.translationmessage import (
    TranslationValidationStatus,
    )


class TestTranslationSuggestions(unittest.TestCase):
    """Test discovery of translation suggestions."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Set up context to test in."""
        # Pretend we have two products Foo and Bar being translated.
        # Translations used or suggested in the one may show up as
        # suggestions for the other.
        factory = LaunchpadObjectFactory()
        self.factory = factory
        foo_product = factory.makeProduct(
            translations_usage=ServiceUsage.LAUNCHPAD)
        bar_product = factory.makeProduct(
            translations_usage=ServiceUsage.LAUNCHPAD)
        self.foo_trunk = factory.makeProductSeries(
            product=foo_product)
        self.bar_trunk = factory.makeProductSeries(
            product=bar_product)
        self.foo_template = factory.makePOTemplate(self.foo_trunk)
        self.bar_template = factory.makePOTemplate(self.bar_trunk)
        self.nl = getUtility(ILanguageSet).getLanguageByCode('nl')
        self.foo_nl = factory.makePOFile('nl', potemplate=self.foo_template)
        self.bar_nl = factory.makePOFile('nl', potemplate=self.bar_template)
        self._refreshSuggestiveTemplatesCache()

    def _refreshSuggestiveTemplatesCache(self):
        """Update the `SuggestivePOTemplate` cache."""
        getUtility(IPOTemplateSet).populateSuggestivePOTemplatesCache()

    def test_NoSuggestions(self):
        # When a msgid string is unique and nobody has submitted any
        # translations for it, there are no suggestions for translating
        # it whatsoever.
        potmsgset = self.factory.makePOTMsgSet(self.foo_template)
        potmsgset.setSequence(self.foo_template, 1)
        self.assertEquals(
            potmsgset.getExternallyUsedTranslationMessages(self.nl), [])
        self.assertEquals(
            potmsgset.getExternallySuggestedTranslationMessages(self.nl), [])

    def test_SimpleExternallyUsedSuggestion(self):
        # If foo wants to translate "error message 936" and bar happens
        # to have a translation for that, that's an externally used
        # suggestion.
        text = "error message 936"
        foomsg = self.factory.makePOTMsgSet(self.foo_template, text)
        foomsg.setSequence(self.foo_template, 1)
        barmsg = self.factory.makePOTMsgSet(self.bar_template, text)
        barmsg.setSequence(self.bar_template, 1)
        translation = barmsg.updateTranslation(self.bar_nl, self.bar_nl.owner,
            ["foutmelding 936"], is_imported=False,
            lock_timestamp=None)

        transaction.commit()

        used_suggestions = foomsg.getExternallyUsedTranslationMessages(
            self.nl)
        other_suggestions = foomsg.getExternallySuggestedTranslationMessages(
            self.nl)
        self.assertEquals(len(used_suggestions), 1)
        self.assertEquals(used_suggestions[0], translation)
        self.assertEquals(len(other_suggestions), 0)

    def test_DisabledExternallyUsedSuggestions(self):
        # If foo wants to translate "error message 936" and bar happens
        # to have a translation for that, that's an externally used
        # suggestion.
        # If global suggestions are disabled, empty list is returned.
        text = "error message 936"
        foomsg = self.factory.makePOTMsgSet(self.foo_template, text)
        foomsg.setSequence(self.foo_template, 1)
        barmsg = self.factory.makePOTMsgSet(self.bar_template, text)
        barmsg.setSequence(self.bar_template, 1)
        translation = barmsg.updateTranslation(self.bar_nl, self.bar_nl.owner,
            ["foutmelding 936"], is_imported=False,
            lock_timestamp=None)

        transaction.commit()

        # There is a global (externally used) suggestion.
        used_suggestions = foomsg.getExternallyUsedTranslationMessages(
            self.nl)
        self.assertEquals(len(used_suggestions), 1)

        # Override the config option to disable global suggestions.
        new_config = ("""
            [rosetta]
            global_suggestions_enabled = False
            """)
        config.push('disabled_suggestions', new_config)
        disabled_used_suggestions = (
            foomsg.getExternallyUsedTranslationMessages(self.nl))
        self.assertEquals(len(disabled_used_suggestions), 0)
        # Restore the old configuration.
        config.pop('disabled_suggestions')

    def test_SimpleOtherSuggestion(self):
        # Suggestions made for bar can also be useful suggestions for foo.
        text = "Welcome to our application!  We hope to have code soon."
        foomsg = self.factory.makePOTMsgSet(self.foo_template, text)
        foomsg.setSequence(self.foo_template, 1)
        barmsg = self.factory.makePOTMsgSet(self.bar_template, text)
        barmsg.setSequence(self.bar_template, 1)
        suggestion = barmsg.updateTranslation(self.bar_nl,
            self.foo_template.owner, ["Noueh hallo dus."],
            is_imported=False, lock_timestamp=None)
        suggestion.is_current = False

        transaction.commit()

        used_suggestions = foomsg.getExternallyUsedTranslationMessages(
            self.nl)
        other_suggestions = foomsg.getExternallySuggestedTranslationMessages(
            self.nl)
        self.assertEquals(len(used_suggestions), 0)
        self.assertEquals(len(other_suggestions), 1)
        self.assertEquals(other_suggestions[0], suggestion)

    def test_IdenticalSuggestions(self):
        # If two suggestions are identical, the most recent one is used.
        text = "The application has exploded."
        suggested_dutch = "De applicatie is ontploft."
        now = datetime.now(timezone('UTC'))
        before = now - timedelta(1, 1, 1)

        foomsg = self.factory.makePOTMsgSet(self.foo_template, text)
        foomsg.setSequence(self.foo_template, 1)
        barmsg = self.factory.makePOTMsgSet(self.bar_template, text)
        barmsg.setSequence(self.bar_template, 1)
        suggestion1 = barmsg.updateTranslation(self.bar_nl,
            self.foo_template.owner, [suggested_dutch],
            is_imported=False, lock_timestamp=now)
        suggestion2 = barmsg.updateTranslation(self.bar_nl,
            self.bar_template.owner, [suggested_dutch],
            is_imported=False, lock_timestamp=now)
        removeSecurityProxy(suggestion1).date_created = before
        removeSecurityProxy(suggestion2).date_created = before

        # When a third project, oof, contains the same translatable
        # string, only the most recent of the identical suggestions is
        # shown.
        oof_template = self.factory.makePOTemplate()
        oof_potmsgset = self.factory.makePOTMsgSet(
            oof_template, singular=text)
        oof_potmsgset.setSequence(oof_template, 1)
        from storm.store import Store
        Store.of(oof_template).flush()
        transaction.commit()
        suggestions = oof_potmsgset.getExternallyUsedTranslationMessages(
            self.nl)
        self.assertEquals(len(suggestions), 1)
        self.assertEquals(suggestions[0], suggestion1)

    def test_RevertingToUpstream(self):
        # When a msgid string is unique and nobody has submitted any
        # translations for it, there are no suggestions for translating
        # it whatsoever.
        translated_in_launchpad = "Launchpad translation."
        translated_upstream = "Upstream translation."
        potmsgset = self.factory.makePOTMsgSet(self.foo_template)
        suggestion1 = potmsgset.updateTranslation(self.foo_nl,
            self.foo_template.owner, [translated_in_launchpad],
            is_imported=False, lock_timestamp=None)
        suggestion2 = potmsgset.updateTranslation(self.foo_nl,
            self.foo_template.owner, [translated_upstream],
            is_imported=True, lock_timestamp=None)
        current_translation = potmsgset.getCurrentTranslationMessage(
            self.foo_template, self.foo_nl.language)
        imported_translation = potmsgset.getImportedTranslationMessage(
            self.foo_template, self.foo_nl.language)

        self.assertEquals(
            current_translation, imported_translation,
            "Imported message should become current if there are no "
            "previous imported messages.")

    def test_TranslationWithErrors(self):
        # When a msgid string is printf-type string, and translation
        # doesn't match the msgid specifiers, an error is raised.
        cformat_msgid = "%d files"
        translation_with_error = "%s files"

        potmsgset = self.factory.makePOTMsgSet(self.foo_template,
                                               singular=cformat_msgid)
        # Set a c-format flag so error is raised
        naked_potmsgset = removeSecurityProxy(potmsgset)
        naked_potmsgset.flagscomment = "c-format"

        # An exception is raised if one tries to set the broken translation.
        self.assertRaises(
            gettextpo.error,
            potmsgset.updateTranslation,
            self.foo_nl, self.foo_template.owner, [translation_with_error],
            is_imported=True, lock_timestamp=None)

        # However, if ignore_errors=True is passed, then it's saved
        # and marked as a message with errors.
        translation = potmsgset.updateTranslation(
            self.foo_nl, self.foo_template.owner, [translation_with_error],
            is_imported=True, lock_timestamp=None, ignore_errors=True)
        self.assertEquals(translation.validation_status,
                          TranslationValidationStatus.UNKNOWNERROR,
                          "TranslationMessage with errors is not correctly"
                          "marked as such in the database.")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
