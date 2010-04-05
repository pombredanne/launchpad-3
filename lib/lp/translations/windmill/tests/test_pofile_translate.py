# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for pofile translate pages."""

__metaclass__ = type
__all__ = []

from canonical.launchpad.windmill.testing import constants, lpuser
from lp.translations.windmill.testing import TranslationsWindmillLayer
from lp.testing import WindmillTestCase


class POFileNewTranslationFieldKeybindings(WindmillTestCase):
    """Tests for keybinding actions associated to the translation field."""

    layer = TranslationsWindmillLayer
    suite_name = 'POFile Translate'

    def test_pofile_new_translation_autoselect(self):
        """Test for automatically selecting new translation on text input.

        When new text is typed into the new translation text fields, the
        associated radio button should be automatically selected.
        """
        client = self.client
        start_url = ('http://translations.launchpad.dev:8085/'
                        'evolution/trunk/+pots/evolution-2.2/es/+translate')
        user = lpuser.TRANSLATIONS_ADMIN
        new_translation_id = u'msgset_1_es_translation_0_new'
        radiobutton_id = u'msgset_1_es_translation_0_new_select'

        # Go to the translation page.
        self.client.open(url=start_url)
        self.client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        user.ensure_login(self.client)

        # Wait for the new translation field and it's associated radio button.
        client.waits.forElement(
            id=new_translation_id, timeout=constants.FOR_ELEMENT)
        client.waits.forElement(
            id=radiobutton_id, timeout=constants.FOR_ELEMENT)

        # Check that the associated radio button is not selected.
        client.asserts.assertNotChecked(id=radiobutton_id)

        # Type a new translation.
        client.type(
            id=new_translation_id, text=u'New translation')

        # Check that the associated radio button is selected.
        client.asserts.assertChecked(id=radiobutton_id)
