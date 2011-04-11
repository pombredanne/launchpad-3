# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from lp.bugs.windmill.testing import BugsWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import lpuser
from lp.testing.windmill.constants import (
    FOR_ELEMENT,
    )


class TestInlineAssignment(WindmillTestCase):

    layer = BugsWindmillLayer

    def test_inline_assignment_non_contributer(self):
        """Test assigning bug to a non contributor displays a confirmation."""

        import transaction
        # Create a person who has not contributed
        fred = self.factory.makePerson(name="fred")
        transaction.commit()

        client, start_url = self.getClientFor(
            "/firefox/+bug/1", lpuser.SAMPLE_PERSON)

        ASSIGN_BUTTON = (u'//*[@id="affected-software"]//tr//td[5]' +
            '//button[contains(@class, "yui3-activator-act")]')
        client.waits.forElement(xpath=ASSIGN_BUTTON, timeout=FOR_ELEMENT)
        client.click(xpath=ASSIGN_BUTTON)

        VISIBLE_PICKER_OVERLAY = (
            u'//div[contains(@class, "yui3-picker ") and '
             'not(contains(@class, "yui3-picker-hidden"))]')

        client.waits.forElement(
            xpath=VISIBLE_PICKER_OVERLAY, timeout=FOR_ELEMENT)

        def full_picker_element_xpath(element_path):
            return VISIBLE_PICKER_OVERLAY + element_path

        client.type(xpath=full_picker_element_xpath(
            "//input[@class='yui3-picker-search']"), text='fred')
        client.click(xpath=full_picker_element_xpath(
            "//div[@class='yui3-picker-search-box']/button"))

        PICKER_RESULT = full_picker_element_xpath(
            "//ul[@class='yui3-picker-results']/li[1]/span")

        client.waits.forElement(xpath=PICKER_RESULT, timeout=FOR_ELEMENT)
        client.click(xpath=PICKER_RESULT)

        CONFIRMATION = ("//div[@class='important-notice-balloon']")
        client.waits.forElement(xpath=CONFIRMATION, timeout=FOR_ELEMENT)
        self.client.asserts.assertTextIn(
            xpath=CONFIRMATION,
            validator="Fred did not previously have any assigned bugs")
