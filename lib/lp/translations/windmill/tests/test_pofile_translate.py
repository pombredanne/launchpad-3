# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for pofile translate pages."""

__metaclass__ = type
__all__ = []

from canonical.launchpad.windmill.testing import constants, lpuser
from lp.translations.windmill.testing import TranslationsWindmillLayer
from lp.testing import WindmillTestCase


class POFileNewTranslationFieldKeybindings(WindmillTestCase):
    """Tests for keybinding actions associated to the translation field.

    These tests should cover both simple (ie. pt) and composed (ie. pt_br)
    language codes.
    """

    layer = TranslationsWindmillLayer
    suite_name = 'POFile Translate'

    def _check_translation_autoselect(
        self, url, new_translation_id, new_translation_select_id):
        """Checks that the select radio button is checked when typing a new
        translation.
        """
        # Go to the translation page.
        self.client.open(url=url)
        self.client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        self.test_user.ensure_login(self.client)

        # Wait for the new translation field and it's associated radio button.
        self.client.waits.forElement(
            id=new_translation_id, timeout=constants.FOR_ELEMENT)
        self.client.waits.forElement(
            id=new_translation_select_id, timeout=constants.FOR_ELEMENT)

        # Check that the associated radio button is not selected.
        self.client.asserts.assertNotChecked(id=new_translation_select_id)

        # Type a new translation.
        self.client.type(
            id=new_translation_id, text=u'New translation')

        # Check that the associated radio button is selected.
        self.client.asserts.assertChecked(id=new_translation_select_id)

    def test_pofile_new_translation_autoselect(self):
        """Test for automatically selecting new translation on text input.

        When new text is typed into the new translation text fields, the
        associated radio button should be automatically selected.
        """
        self.test_user = lpuser.TRANSLATIONS_ADMIN

        # Test the zoom out view for Evolution trunk Spanish (es).
        start_url = ('http://translations.launchpad.dev:8085/'
                        'evolution/trunk/+pots/evolution-2.2/es/+translate')
        new_translation_id = u'msgset_1_es_translation_0_new'
        new_translation_select_id = u'msgset_1_es_translation_0_new_select'
        self._check_translation_autoselect(
            start_url, new_translation_id, new_translation_select_id)

        # Test the zoom in view for Evolution trunk Brazilian (pt_BR).
        start_url = ('http://translations.launchpad.dev:8085/'
                        'evolution/trunk/+pots/evolution-2.2/'
                        'pt_BR/1/+translate')
        new_translation_id = u'msgset_1_pt_BR_translation_0_new'
        new_translation_select_id = u'msgset_1_pt_BR_translation_0_new_select'
        self._check_translation_autoselect(
            start_url, new_translation_id, new_translation_select_id)

        # Test the zoom out view for Ubuntu Hoary Brazilian (pt_BR).
        start_url = ('http://translations.launchpad.dev:8085/'
                        'ubuntu/hoary/+source/mozilla/+pots/pkgconf-mozilla/'
                        'pt_BR/1/+translate')
        new_translation_id = u'msgset_152_pt_BR_translation_0_new'
        new_translation_select_id = (u'msgset_152_pt_BR'
                                       '_translation_0_new_select')
        self._check_translation_autoselect(
            start_url, new_translation_id, new_translation_select_id)


class POFileTranslatorAndReviewerWorkingMode(WindmillTestCase):
    """Tests for page behaviour in reviewer or translator mode."""

    layer = TranslationsWindmillLayer
    suite_name = 'POFile Translate'

    test_user = lpuser.TRANSLATIONS_ADMIN

    switch_working_mode = u'translation-switch-working-mode'
    force_suggestion = u'msgset_1_force_suggestion'
    new_translation = u'msgset_1_pt_BR_translation_0_new'
    js_code = ("lookupNode({id: '%s'}).innerHTML.search('translator') > 0" %
            switch_working_mode)

    def test_pofile_reviewer_mode(self):
        """Test for reviewer mode.

        Adding new translations will not force them as suggestions.
        """

        self.client.open(
            url='http://translations.launchpad.dev:8085/'
            'evolution/trunk/+pots/evolution-2.2/pt_BR/1/+translate')
        self.client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        self.test_user.ensure_login(self.client)

        self._ensureTranslationMode(reviewer=True)

        self.client.waits.forElement(
            id=self.force_suggestion, timeout=constants.FOR_ELEMENT)
        self.client.type(text=u'New translation', id=self.new_translation)
        self.client.asserts.assertNotChecked(id=self.force_suggestion)

    def test_pofile_translator_mode(self):
        """Test for translator mode.

        Adding new translations will not force them as suggestions.
        """

        self.client.open(
            url='http://translations.launchpad.dev:8085'
            '/evolution/trunk/+pots/evolution-2.2/pt_BR/1/+translate')
        self.client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        self.test_user.ensure_login(self.client)

        self._ensureTranslationMode(translator=True)

        self.client.waits.forElement(
            id=self.force_suggestion, timeout=constants.FOR_ELEMENT)
        self.client.type(text=u'New translation', id=self.new_translation)
        self.client.asserts.assertChecked(id=self.force_suggestion)

        # The new translation will be forced only if the previous new
        # translation field is empty. Othewise the force suggestion checkbox
        # will remain unchecked.
        self.client.click(id=self.force_suggestion)
        self.client.keyPress(
            id=self.new_translation,
            options='a,true,false,false,false,false')
        self.client.asserts.assertNotChecked(id=self.force_suggestion)

    def _ensureTranslationMode(self, reviewer=False, translator=False):
        """Ensure the specified mode is currently selected."""

        if (reviewer is translator):
            raise AssertionError("You must specify a single working mode.")

        self.client.waits.forElement(
            id=self.switch_working_mode, timeout=constants.FOR_ELEMENT)

        current_is_reviewer = self.client.execJS(js=self.js_code)['output']
        need_to_switch_mode = False
        if reviewer and not current_is_reviewer:
            need_to_switch_mode = True
        if translator and current_is_reviewer:
            need_to_switch_mode = True
        if need_to_switch_mode:
            self.client.click(id=self.switch_working_mode)
        else:
            return

        # We check that the mode was changed.
        current_is_reviewer = self.client.execJS(js=self.js_code)['output']

        if reviewer and not current_is_reviewer:
            raise AssertionError("Could not set reviewer mode.")
        if translator and current_is_reviewer:
            raise AssertionError("Could not set reviewer mode.")
