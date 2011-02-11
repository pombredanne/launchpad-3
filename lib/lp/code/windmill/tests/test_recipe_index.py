# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for branch statuses."""

__metaclass__ = type
__all__ = []

import transaction
import unittest

from lp.code.windmill.testing import CodeWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill.constants import (
    FOR_ELEMENT,
    PAGE_LOAD,
    SLEEP,
    )


class TestRecipeSetDaily(WindmillTestCase):
    """Test setting the daily build flag."""

    layer = CodeWindmillLayer
    suite_name = "Recipe daily build flag setting"

    BUILD_DAILY_TEXT = u'//span[@id="edit-build_daily"]/span[@class="value"]'
    BUILD_DAILY_POPUP = u'//div[contains(@class, "yui3-ichoicelist-content")]'

    def test_inline_recipe_daily_build(self):
        eric = self.factory.makePerson(
            name="eric", displayname="Eric the Viking", password="test",
            email="eric@example.com")
        recipe = self.factory.makeSourcePackageRecipe(owner=eric)
        transaction.commit()

        client, start_url = self.getClientFor(recipe, user=eric)
        client.click(xpath=self.BUILD_DAILY_TEXT)
        # Make sure there is a popup.
        client.waits.forElement(xpath=self.BUILD_DAILY_POPUP)
        # Change the flag to build daily.

        client.click(link=u'Build daily')
        client.waits.sleep(milliseconds=SLEEP)

        client.asserts.assertText(
            xpath=self.BUILD_DAILY_TEXT, validator=u'Build daily')

        # Reload the page and make sure the change sticks.
        client.open(url=start_url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.asserts.assertText(
            xpath=self.BUILD_DAILY_TEXT, validator=u'Build daily')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
