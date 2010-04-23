# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for pofile translate pages."""

__metaclass__ = type
__all__ = []

import transaction

from canonical.launchpad.windmill.testing import constants, lpuser
from lp.translations.windmill.testing import TranslationsWindmillLayer
from lp.testing import login, logout, WindmillTestCase


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


class POFileTranslationActions(WindmillTestCase):
    """Tests for actions that can be done on a translation message."""

    layer = TranslationsWindmillLayer
    suite_name = 'POFile Translation Actions'

    def test_dismiss_uncheck_force_suggestion(self):
        """Test the unchecking of force suggestion on dismissal.

        Checking the dismiss all suggestions checkbox will uncheck a
        previously ticked checkbox that forces submitting the current
        translation as a suggestion.
        """

        self.test_user = lpuser.TRANSLATIONS_ADMIN
        # Test the zoom out view for Evolution trunk Spanish (es).
        url = ('http://translations.launchpad.dev:8085/'
                        'evolution/trunk/+pots/evolution-2.2/es/5/+translate')
        dismiss_id = u'msgset_5_dismiss'
        force_suggestion_id = u'msgset_5_force_suggestion'

        # Go to the translation page.
        self.client.open(url=url)
        self.client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        self.test_user.ensure_login(self.client)
        self.client.waits.forElement(
            id=dismiss_id, timeout=constants.FOR_ELEMENT)
        self.client.waits.forElement(
            id=force_suggestion_id, timeout=constants.FOR_ELEMENT)

        # Check that initially the checkboxes are not selected.
        self.client.asserts.assertNotChecked(id=dismiss_id)
        self.client.asserts.assertNotChecked(id=force_suggestion_id)

        # Click the force suggestion checkbox and verify that it is checked.
        self.client.click(id=force_suggestion_id)
        self.client.asserts.assertChecked(id=force_suggestion_id)

        self.client.click(id=dismiss_id)
        self.client.asserts.assertChecked(id=dismiss_id)
        self.client.asserts.assertNotChecked(id=force_suggestion_id)

    def test_diverge_and_force_suggestion_mutual_exclusion(self):
        """Test the mutual exclusion of diverge and force suggestion.

        Diverge current translation and force suggestion checkbox can not
        be enabled at the same time. Checking one option will disable the
        other.

        If suggestions are dismissed, unchecking the diverge checkbox will
        keep the force suggesion disabled.
        """

        self.test_user = lpuser.TRANSLATIONS_ADMIN
        # Test the zoom out view for Evolution trunk Spanish (es).

        login('admin@canonical.com')
        pofile = self.factory.makePOFile('pt_BR')
        potemplate = pofile.potemplate
        potmsgset = self.factory.makePOTMsgSet(potemplate)
        potmsgset.setSequence(potemplate, 1)
        potmsgset_id = potmsgset.id

        current_translation = self.factory.makeTranslationMessage(
            pofile=pofile, potmsgset=potmsgset, translations=['current'])
        transaction.commit()
        suggestion = self.factory.makeTranslationMessage(
            pofile=pofile, potmsgset=potmsgset,
            translations=['suggestion'], suggestion=True)
        transaction.commit()
        logout()

        url = ('http://translations.launchpad.dev:8085/'
                        '%s/%s/+pots/%s/pt_BR/1/+translate' % (
                        potemplate.product.name,
                        potemplate.productseries.name,
                        potemplate.name))

        dismiss_id = u'msgset_%s_dismiss' % potmsgset_id
        force_suggestion_id = u'msgset_%s_force_suggestion' % potmsgset_id
        diverge_id = u'msgset_%s_diverge' % potmsgset_id

        # Go to the translation page.
        self.client.open(url=url)
        self.client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        self.test_user.ensure_login(self.client)
        self.client.waits.forElement(
            id=dismiss_id, timeout=constants.FOR_ELEMENT)
        self.client.waits.forElement(
            id=force_suggestion_id, timeout=constants.FOR_ELEMENT)
        self.client.waits.forElement(
            id=diverge_id, timeout=constants.FOR_ELEMENT)

        # Check that initialy the checkboxes are not selected.
        self.client.asserts.assertNotChecked(id=dismiss_id)
        self.client.asserts.assertNotChecked(id=force_suggestion_id)
        self.client.asserts.assertNotChecked(id=diverge_id)

        # Test the diverge translation checking and unchecking.
        self.client.click(id=diverge_id)
        self.client.asserts.assertChecked(id=diverge_id)
        self.client.asserts.assertNotChecked(id=force_suggestion_id)
        self.client.asserts.assertNotChecked(id=dismiss_id)
        self.client.asserts.assertElemJS(
            id=force_suggestion_id, js=u'element.disabled')

        self.client.click(id=diverge_id)
        self.client.asserts.assertNotChecked(id=diverge_id)
        self.client.asserts.assertNotChecked(id=force_suggestion_id)
        self.client.asserts.assertNotChecked(id=dismiss_id)
        self.client.asserts.assertElemJS(
            id=force_suggestion_id, js=u'!element.disabled')

        # Test the force suggestion checking and unchecking.
        self.client.click(id=force_suggestion_id)
        self.client.asserts.assertChecked(id=force_suggestion_id)
        self.client.asserts.assertNotChecked(id=diverge_id)
        self.client.asserts.assertNotChecked(id=dismiss_id)
        self.client.asserts.assertElemJS(
            id=diverge_id, js=u'element.disabled')

        self.client.click(id=force_suggestion_id)
        self.client.asserts.assertNotChecked(id=force_suggestion_id)
        self.client.asserts.assertNotChecked(id=diverge_id)
        self.client.asserts.assertNotChecked(id=dismiss_id)
        self.client.asserts.assertElemJS(
            id=diverge_id, js=u'!element.disabled')

        # Test unchecking the diverge translations when dismiss all
        # suggestions is enabled.
        self.client.click(id=dismiss_id)
        self.client.asserts.assertElemJS(
            id=force_suggestion_id, js=u'element.disabled')
        self.client.click(id=diverge_id)
        self.client.asserts.assertElemJS(
            id=force_suggestion_id, js=u'element.disabled')
        self.client.asserts.assertNotChecked(id=force_suggestion_id)

        self.client.click(id=diverge_id)
        self.client.asserts.assertElemJS(
            id=force_suggestion_id, js=u'element.disabled')
        self.client.asserts.assertNotChecked(id=force_suggestion_id)
