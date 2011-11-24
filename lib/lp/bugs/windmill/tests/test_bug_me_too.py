# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from itertools import count

from windmill.authoring import WindmillTestClientException

from lp.bugs.windmill.testing import BugsWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import (
    constants,
    lpuser,
    )


AFFECTS_ME_TOO_XPATH = u"//span[@id='affectsmetoo']"
DYNAMIC_SPAN_XPATH = AFFECTS_ME_TOO_XPATH + u"/span[@class='dynamic']"
VALUE_LOCATION_XPATH = DYNAMIC_SPAN_XPATH + u"//span[@class='value']"
EDIT_ICON_XPATH = DYNAMIC_SPAN_XPATH + u"//img[@class='editicon']"

OVERLAY_XPATH = u"//div[@id='yui3-pretty-overlay-modal']"

def retry(client, attempts=3, delay=2000, initial_delay=1000):
    """Decorator for attempting Windmill operations multiple times.

    This exists because a lot of time has been spent trying to get
    waits.forProperty() and waits.forJS() to work properly (at all,
    really) in this test module, without success. It's also near
    impossible to figure out why. Simply put, it's more reliable,
    quicker and therefore less expensive to fix this here.
    """
    def decorator(func):
        client.waits.sleep(milliseconds=initial_delay)
        for attempt in count(1):
            try:
                return func(client)
            except WindmillTestClientException:
                if attempt == attempts:
                    raise
            client.waits.sleep(milliseconds=delay)
    return decorator


class TestMeToo(WindmillTestCase):

    layer = BugsWindmillLayer
    suite_name = 'Bug "me too" test'

    def test_me_too(self):
        """Test the "this bug affects me too" options on bug pages.

        This test ensures that, with Javascript enabled, the "me too"
        status can be edited in-page.
        """

        # Open bug 11 and wait for it to finish loading.
        client, start_url = self.getClientFor(
            '/jokosher/+bug/11', user=lpuser.SAMPLE_PERSON,
            view_name='+index')

        # Ensure the link for "Does this bug affect you?" is setup.
        client.waits.forElement(
            xpath=VALUE_LOCATION_XPATH, timeout=constants.FOR_ELEMENT)
        client.asserts.assertText(
            xpath=VALUE_LOCATION_XPATH,
            validator=u"Does this bug affect you?")

        # There is an edit icon next to the text which can be clicked to
        # edit the "me too" status. However, we won't click it with
        # Windmill because the widget actually responds to mouse-down, and
        # Windmill seems to do something funny instead.
        client.click(xpath=EDIT_ICON_XPATH)

        # Wait for the modal dialog to appear.
        client.waits.forElement(id=u'yui3-pretty-overlay-modal')

        # There's a close button if we change our mind.
        client.click(
            xpath=(u"//div[@id='yui3-pretty-overlay-modal']//"
                   u"a[@class='close-button']"))

        # Wait for the modal dialog to disappear. Unfortunately the test
        # below doesn't work, nor does testing clientWidth, or anything I
        # could think of, so it's commented out.

        # client.asserts.assertElemJS(
        #     id=u'yui3-pretty-overlay-modal',
        #     js=(u'getComputedStyle(element, '
        #         u'"visibility").visibility == "hidden"'))

        # However, we want to mark this bug as affecting the logged-in
        # user. We can also click on the content box of the "me too"
        # widget; we are not forced to use the edit icon.
        client.click(xpath=AFFECTS_ME_TOO_XPATH)
        client.waits.forElement(id=u'yui3-pretty-overlay-modal')

        # Let's say the bug does not affect the logged-in user.
        client.click(
            xpath=OVERLAY_XPATH + u"//a[contains(@href, '#false')]")

        # Wait for the save to complete, by observing that the bug is now
        # marked as affecting the current user.
        @retry(client)
        def check_for_save_not_affects(client):
            client.asserts.assertText(
                xpath=VALUE_LOCATION_XPATH,
                validator=u"This bug doesn't affect you")

        # Hah! But this bug does affect the logged-in user! The logged-in
        # user made a mistake, oh noes. Better fix that.
        client.click(xpath=AFFECTS_ME_TOO_XPATH)
        client.waits.forElement(id=u'yui3-pretty-overlay-modal')
        client.click(
            xpath=OVERLAY_XPATH + u"//a[contains(@href, '#true')]")

        # The bug is now marked as affecting the current user.
        @retry(client)
        def check_for_save_does_affect(client):
            client.asserts.assertText(
                xpath=VALUE_LOCATION_XPATH,
                validator=u"This bug affects you")
