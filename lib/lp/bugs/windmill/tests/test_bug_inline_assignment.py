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
        """Test assigning bug to a non contributer displays a notification."""

        import transaction
        # Create a person who has not contributed
        fred = self.factory.makePerson(name="fred")
        transaction.commit()

        client, start_url = self.getClientFor(
            "/firefox/+bug/1", lpuser.SAMPLE_PERSON)

        ASSIGN_BUTTON = (u'("#affected-software tr td:nth-child(5) '
            '.yui3-activator-act")')
        client.waits.forElement(jquery=ASSIGN_BUTTON, timeout=FOR_ELEMENT)
        client.click(jquery=ASSIGN_BUTTON+'[0]')

        VISIBLE_PICKER_OVERLAY = (
            u'//div[contains(@class, "yui3-picker ") and '
             'not(contains(@class, "yui3-picker-hidden"))]')

        def full_picker_element_xpath(element_path):
            return VISIBLE_PICKER_OVERLAY + element_path

        client.waits.forElement(
            xpath=VISIBLE_PICKER_OVERLAY, timeout=FOR_ELEMENT)

        client.type(xpath=full_picker_element_xpath(
            "//input[@class='yui3-picker-search']"), text='fred')
        client.click(xpath=full_picker_element_xpath(
            "//div[@class='yui3-picker-search-box']/button"))
#        client.waits.forElement(
#            jquery=u'(.yui-picker-assign-me-button)', timeout=FOR_ELEMENT)
#        client.type(jquery=u'(.yui3-picker-search)', text='fred')
#        client.click(jquery=u'(button.lazr-search)[0]')
#        client.click(jquery=u'(button.lazr-search)[0]')
#        client.waits.forElement(
#            jquery='u(ul.yui3-picker-results)[0]', timeout=FOR_ELEMENT)

        PICKER_RESULT = full_picker_element_xpath(
            "//ul[@class='yui3-picker-results']/li[1]/span")

        client.waits.forElement(xpath=PICKER_RESULT, timeout=FOR_ELEMENT)
        client.click(xpath=PICKER_RESULT)

        WARNING_NOTIFICATION = ("//div[contains(@class, 'warning') and "
            "contains(@class, 'message')]")
        client.waits.forElement(xpath=WARNING_NOTIFICATION, timeout=60000)
        self.client.asserts.assertTextIn(
            xpath=WARNING_NOTIFICATION,
            validator="Fred did not previously have any assigned bugs")
