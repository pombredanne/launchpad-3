# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for pofile translate pages."""

__metaclass__ = type
__all__ = []

import transaction

from lp.testing import (
    login,
    logout,
    WindmillTestCase,
    )
from lp.testing.windmill import (
    constants,
    lpuser,
    )
from lp.translations.windmill.testing import TranslationsWindmillLayer


class POFileTranslationActions(WindmillTestCase):
    """Tests for actions that can be done on a translation message.

    XXX: Move to YUI test.
    """

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
        url = '/evolution/trunk/+pots/evolution-2.2/es/5/+translate'
        dismiss_id = u'msgset_5_dismiss'
        force_suggestion_id = u'msgset_5_force_suggestion'

        # Go to the translation page.
        client, start_url = self.getClientFor(url, user=self.test_user)
        client.waits.forElement(
            id=dismiss_id, timeout=constants.FOR_ELEMENT)
        client.waits.forElement(
            id=force_suggestion_id, timeout=constants.FOR_ELEMENT)

        # Check that initially the checkboxes are not selected.
        client.asserts.assertNotChecked(id=dismiss_id)
        client.asserts.assertNotChecked(id=force_suggestion_id)

        # Click the force suggestion checkbox and verify that it is checked.
        client.click(id=force_suggestion_id)
        client.asserts.assertChecked(id=force_suggestion_id)

        client.click(id=dismiss_id)
        client.asserts.assertChecked(id=dismiss_id)
        client.asserts.assertNotChecked(id=force_suggestion_id)

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

        current_translation = self.factory.makeCurrentTranslationMessage(
            pofile=pofile, potmsgset=potmsgset, translations=['current'])
        transaction.commit()
        suggestion = self.factory.makeSuggestion(
            pofile=pofile, potmsgset=potmsgset, translations=['suggestion'])
        transaction.commit()
        logout()

        url = ('/%s/%s/+pots/%s/pt_BR/1/+translate' % (
                        potemplate.product.name,
                        potemplate.productseries.name,
                        potemplate.name))

        dismiss_id = u'msgset_%s_dismiss' % potmsgset_id
        force_suggestion_id = u'msgset_%s_force_suggestion' % potmsgset_id
        diverge_id = u'msgset_%s_diverge' % potmsgset_id

        # Go to the translation page.
        client, start_url = self.getClientFor(url, user=self.test_user)
        client.waits.forElement(
            id=dismiss_id, timeout=constants.FOR_ELEMENT)
        client.waits.forElement(
            id=force_suggestion_id, timeout=constants.FOR_ELEMENT)
        client.waits.forElement(
            id=diverge_id, timeout=constants.FOR_ELEMENT)

        # Check that initialy the checkboxes are not selected.
        client.asserts.assertNotChecked(id=dismiss_id)
        client.asserts.assertNotChecked(id=force_suggestion_id)
        client.asserts.assertNotChecked(id=diverge_id)

        # Test the diverge translation checking and unchecking.
        client.click(id=diverge_id)
        client.asserts.assertChecked(id=diverge_id)
        client.asserts.assertNotChecked(id=force_suggestion_id)
        client.asserts.assertNotChecked(id=dismiss_id)
        client.asserts.assertElemJS(
            id=force_suggestion_id, js=u'element.disabled')

        client.click(id=diverge_id)
        client.asserts.assertNotChecked(id=diverge_id)
        client.asserts.assertNotChecked(id=force_suggestion_id)
        client.asserts.assertNotChecked(id=dismiss_id)
        client.asserts.assertElemJS(
            id=force_suggestion_id, js=u'!element.disabled')

        # Test the force suggestion checking and unchecking.
        client.click(id=force_suggestion_id)
        client.asserts.assertChecked(id=force_suggestion_id)
        client.asserts.assertNotChecked(id=diverge_id)
        client.asserts.assertNotChecked(id=dismiss_id)
        client.asserts.assertElemJS(
            id=diverge_id, js=u'element.disabled')

        client.click(id=force_suggestion_id)
        client.asserts.assertNotChecked(id=force_suggestion_id)
        client.asserts.assertNotChecked(id=diverge_id)
        client.asserts.assertNotChecked(id=dismiss_id)
        client.asserts.assertElemJS(
            id=diverge_id, js=u'!element.disabled')

        # Test unchecking the diverge translations when dismiss all
        # suggestions is enabled.
        client.click(id=dismiss_id)
        client.asserts.assertElemJS(
            id=force_suggestion_id, js=u'element.disabled')
        client.click(id=diverge_id)
        client.asserts.assertElemJS(
            id=force_suggestion_id, js=u'element.disabled')
        client.asserts.assertNotChecked(id=force_suggestion_id)

        client.click(id=diverge_id)
        client.asserts.assertElemJS(
            id=force_suggestion_id, js=u'element.disabled')
        client.asserts.assertNotChecked(id=force_suggestion_id)

    def _checkResetTranslationSelect(
        self, client, checkbox, singular_new_select, singular_current_select,
        singular_new_field=None, plural_new_select=None):
        """Checks that the new translation select radio buttons are checked
        when ticking 'Someone should review this translation' checkbox.
        """

        client.waits.forElement(
            id=checkbox, timeout=constants.FOR_ELEMENT)
        client.waits.forElement(
            id=singular_new_select, timeout=constants.FOR_ELEMENT)
        client.waits.forElement(
            id=singular_current_select, timeout=constants.FOR_ELEMENT)
        if plural_new_select is not None:
            client.waits.forElement(
                id=plural_new_select, timeout=constants.FOR_ELEMENT)
        if singular_new_field is not None:
            client.waits.forElement(
                id=singular_new_field, timeout=constants.FOR_ELEMENT)

        # Check that initialy the checkbox is not checked and
        # that the radio buttons are not selected.
        client.asserts.assertNotChecked(id=checkbox)
        client.asserts.assertNotChecked(id=singular_new_select)
        client.asserts.assertChecked(id=singular_current_select)
        if plural_new_select is not None:
            client.asserts.assertNotChecked(id=plural_new_select)

        # Check the checkbox
        client.click(id=checkbox)

        # Check that the checkbox and the new translation radio buttons are
        # selected.
        client.asserts.assertChecked(id=checkbox)
        client.asserts.assertChecked(id=singular_new_select)
        client.asserts.assertNotChecked(id=singular_current_select)
        if plural_new_select is not None:
            client.asserts.assertChecked(id=plural_new_select)

        # Then then we uncheck the 'Someone needs to review this translation'
        # checkbox.
        client.click(id=checkbox)

        # Unchecking the 'Someone needs to review this translation' checkbox
        # when the 'New translation' field is empty, will select the current
        # translation.
        client.asserts.assertNotChecked(id=checkbox)
        client.asserts.assertNotChecked(id=singular_new_select)
        client.asserts.assertChecked(id=singular_current_select)
        if plural_new_select is not None:
            client.asserts.assertNotChecked(id=plural_new_select)

        if singular_new_field is not None:
            # Checking again the 'Someone need to review this translation'
            # checkbox, type some text and unchecking it should keep the new
            # translation fields selected
            client.click(id=checkbox)
            client.type(text=u'some test', id=singular_new_field)
            client.click(id=checkbox)

            client.asserts.assertNotChecked(id=checkbox)
            client.asserts.assertChecked(id=singular_new_select)
            client.asserts.assertNotChecked(id=singular_current_select)
            if plural_new_select is not None:
                client.asserts.assertNotChecked(id=plural_new_select)

    def test_pofile_reset_translation_select(self):
        """Test for automatically selecting new translation when
        'Someone needs to review this translations' is checked.

        """
        # Go to the zoom in page for a translation with plural forms.
        client, start_url = self.getClientFor(
            '/ubuntu/hoary/+source/evolution/+pots/evolution-2.2/es/15/'
            '+translate', user=lpuser.TRANSLATIONS_ADMIN)

        checkbox = u'msgset_144_force_suggestion'
        singular_new_select = u'msgset_144_es_translation_0_new_select'
        singular_new_field = u'msgset_144_es_translation_0_new'
        singular_current_select = u'msgset_144_es_translation_0_radiobutton'
        plural_new_select = u'msgset_144_es_translation_1_new_select'
        self._checkResetTranslationSelect(
            client,
            checkbox=checkbox,
            singular_new_select=singular_new_select,
            singular_new_field=singular_new_field,
            singular_current_select=singular_current_select,
            plural_new_select=plural_new_select)

        # Go to the zoom in page for a pt_BR translation with plural forms.
        # pt_BR is a language code using the same delimiter as HTTP form
        # fields and are prone to errors.
        client.open(
            url='%s/ubuntu/hoary/+source/evolution/+pots/'
                'evolution-2.2/pt_BR/15/+translate'
                % TranslationsWindmillLayer.base_url)
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)

        checkbox = u'msgset_144_force_suggestion'
        singular_new_select = u'msgset_144_pt_BR_translation_0_new_select'
        singular_new_field = u'msgset_144_pt_BR_translation_0_new'
        singular_current_select = (
            u'msgset_144_pt_BR_translation_0_radiobutton')
        plural_new_select = u'msgset_144_pt_BR_translation_1_new_select'
        self._checkResetTranslationSelect(
            client,
            checkbox=checkbox,
            singular_new_select=singular_new_select,
            singular_new_field=singular_new_field,
            singular_current_select=singular_current_select,
            plural_new_select=plural_new_select)

        # Go to the zoom in page for a translation without plural forms.
        client.open(
            url='%s/ubuntu/hoary/+source/evolution/+pots/'
                'evolution-2.2/es/19/+translate'
                % TranslationsWindmillLayer.base_url)
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)

        checkbox = u'msgset_148_force_suggestion'
        singular_new_select = u'msgset_148_es_translation_0_new_select'
        singular_current_select = u'msgset_148_es_translation_0_radiobutton'
        self._checkResetTranslationSelect(
            client,
            checkbox=checkbox,
            singular_new_select=singular_new_select,
            singular_current_select=singular_current_select)

        # Go to the zoom out page for some translations.
        self.client.open(
            url='%s/ubuntu/hoary/+source/evolution/+pots/'
                'evolution-2.2/es/+translate'
                % TranslationsWindmillLayer.base_url)
        self.client.waits.forPageLoad(timeout=constants.PAGE_LOAD)

        checkbox = u'msgset_130_force_suggestion'
        singular_new_select = u'msgset_130_es_translation_0_new_select'
        singular_current_select = u'msgset_130_es_translation_0_radiobutton'
        self._checkResetTranslationSelect(
            client,
            checkbox=checkbox,
            singular_new_select=singular_new_select,
            singular_current_select=singular_current_select)

        # Ensure that the other radio buttons are not changed
        client.asserts.assertNotChecked(
            id=u'msgset_131_es_translation_0_new_select')
        client.asserts.assertNotChecked(
            id=u'msgset_132_es_translation_0_new_select')
        client.asserts.assertNotChecked(
            id=u'msgset_133_es_translation_0_new_select')
        client.asserts.assertNotChecked(
            id=u'msgset_134_es_translation_0_new_select')
        client.asserts.assertNotChecked(
            id=u'msgset_135_es_translation_0_new_select')
        client.asserts.assertNotChecked(
            id=u'msgset_136_es_translation_0_new_select')
        client.asserts.assertNotChecked(
            id=u'msgset_137_es_translation_0_new_select')
        client.asserts.assertNotChecked(
            id=u'msgset_138_es_translation_0_new_select')
        client.asserts.assertNotChecked(
            id=u'msgset_139_es_translation_0_new_select')

