# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.testing import TestCaseWithFactory
from lp.translations.browser.browser_helpers import text_to_html
from lp.translations.browser.translatablemessage import (
    TranslatableMessageView,
    )
from lp.translations.model.translatablemessage import TranslatableMessage


class TestTranslatableMessageView(TestCaseWithFactory):
    """Test ProductSeries view in translations facet."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        # Create a POTMsgSet and a POFile to create a TranslatableMessage
        # from. Create the view from the message.
        super(TestTranslatableMessageView, self).setUp()
        self.potemplate = self.factory.makePOTemplate()
        self.potmsgset = self.factory.makePOTMsgSet(
            self.potemplate, sequence=1, singular=u"English singular")
        self.pofile = self.factory.makePOFile('eo', self.potemplate)
        self.message = None

    def _create_view(self):
        self.message = TranslatableMessage(self.potmsgset, self.pofile)
        return TranslatableMessageView(self.message,
                                            LaunchpadTestRequest())

    def test_empty_message(self):
        # View information for an empty message.
        view = self._create_view()
        info = view.current_translation

        self.assertEqual(None, info['translator'])
        self.assertEqual(u'', info['translator_class'])
        self.assertContentEqual(
            [{'plural': u"", 'text': u"(no translation yet)"}],
            info['translations'])
        self.assertEqual(u'current_empty', info['translation_class'])

    def test_singular_message(self):
        # View information for a singular message.
        translator = self.factory.makePerson()
        self.factory.makeCurrentTranslationMessage(
            self.pofile, self.potmsgset,
            translations=[u'foo'], translator=translator)
        view = self._create_view()
        info = view.current_translation

        self.assertEqual(u'English singular', view.singular_text)
        self.assertEqual(translator, info['translator'])
        self.assertEqual('translator_singular', info['translator_class'])
        self.assertContentEqual(
            [{'plural': u"", 'text': u"foo"}],
            info['translations'])
        self.assertEqual(u'current', info['translation_class'])

    def test_plural_message(self):
        # View information for a message with plural.
        self.potmsgset.updatePluralForm(u'English plural')
        translator = self.factory.makePerson()
        self.factory.makeCurrentTranslationMessage(
            self.pofile, self.potmsgset,
            translations=[u'foo', u'bar'], translator=translator)
        view = self._create_view()
        info = view.current_translation

        self.assertEqual(u'English plural', view.plural_text)
        self.assertEqual(translator, info['translator'])
        self.assertEqual('translator_plural', info['translator_class'])
        self.assertContentEqual(
            [{'plural': u"Plural 0:", 'text': u"foo"},
             {'plural': u"Plural 1:", 'text': u"bar"}],
            info['translations'])
        self.assertEqual(u'current', info['translation_class'])

    def test_browser_message(self):
        # Special treatment on some characters for browser display.
        TRANSLATION = u"foo \nbar"
        translator = self.factory.makePerson()
        self.potmsgset.updatePluralForm(u'English plural')
        self.factory.makeCurrentTranslationMessage(
            self.pofile, self.potmsgset,
            translations=[TRANSLATION], translator=translator)
        view = self._create_view()
        info = view.current_translation

        self.assertEqual(
            text_to_html(TRANSLATION, self.potmsgset.flags),
            info['translations'][0]['text'])
