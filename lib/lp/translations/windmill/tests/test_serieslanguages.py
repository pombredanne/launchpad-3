# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for series languages."""

__metaclass__ = type
__all__ = []

from lp.testing import WindmillTestCase
from lp.testing.windmill import lpuser
from lp.testing.windmill.constants import (
    PAGE_LOAD,
    SLEEP,
    )
from lp.translations.windmill.testing import TranslationsWindmillLayer


LANGUAGE=(u"//table[@id='languagestats']/descendant::a[text()='%s']"
         u"/parent::td/parent::tr")
UNSEEN_VALIDATOR='className|unseen'


class LanguagesSeriesTest(WindmillTestCase):
    """Tests for serieslanguages."""

    layer = TranslationsWindmillLayer
    suite_name = 'SeriesLanguages Tables'

    def _toggle_languages_visiblity(self):
        self.client.click(id="toggle-languages-visibility")
        self.client.waits.sleep(milliseconds=SLEEP)

    def _assert_languages_visible(self, languages):
        for language, visibility in languages.items():
            xpath = LANGUAGE % language
            if visibility:
                self.client.asserts.assertNotProperty(
                    xpath=xpath, validator=UNSEEN_VALIDATOR)
            else:
                self.client.asserts.assertProperty(
                    xpath=xpath, validator=UNSEEN_VALIDATOR)

    def test_serieslanguages_table(self):
        """Test for filtering preferred languages in serieslanguages table.

        The test cannot fully cover all languages so we just test with a
        person having Catalan and Spanish as preferred languages.
        """
        client = self.client
        start_url = '%s/ubuntu' % TranslationsWindmillLayer.base_url
        user = lpuser.TRANSLATIONS_ADMIN
        # Go to the distribution languages page
        self.client.open(url=start_url)
        self.client.waits.forPageLoad(timeout=PAGE_LOAD)
        user.ensure_login(self.client)

        # A link will be displayed for viewing all languages
        # and only user preferred langauges are displayed
        self.client.asserts.assertProperty(
            id=u'toggle-languages-visibility',
            validator='text|View all languages')
        self._assert_languages_visible({
            u'Catalan': True,
            u'Spanish': True,
            u'French': False,
            u'Croatian': False,
            })

        # Toggle language visibility by clicking the toggle link.
        self._toggle_languages_visiblity()
        self.client.asserts.assertProperty(
            id=u'toggle-languages-visibility',
            validator='text|View only preferred languages')
        # All languages should be visible now
        self._assert_languages_visible({
            u'Catalan': True,
            u'Spanish': True,
            u'French': True,
            u'Croatian': True,
            })
