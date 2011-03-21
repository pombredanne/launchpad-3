# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

from lp.bugs.windmill.testing import BugsWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import lpuser
from lp.testing.windmill.constants import (
    FOR_ELEMENT,
    PAGE_LOAD,
    SLEEP,
    )


SUBSCRIPTION_LINK = u'//div[@id="portlet-subscribers"]/div/div/a'
PERSON_LINK = u'//div[@id="subscribers-links"]/div/a[@name="%s"]'


class TestInlineSubscribing(WindmillTestCase):

    layer = BugsWindmillLayer
    suite_name = 'Inline bug page subscribers test'

    def test_inline_subscriber(self):
        # This test fails intermittently.  See bug #516781.
        """Test inline subscribing on bugs pages.

        This test makes sure that subscribing and unsubscribing
        from a bug works inline on a bug page.
        """
        client = self.client

        bug_url = u'%s/bugs/%%s' % BugsWindmillLayer.base_url
        # Open a bug page and wait for it to finish loading.
        client.open(url=bug_url % 11)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        lpuser.SAMPLE_PERSON.ensure_login(client)

        # Ensure the subscriber's portlet has finished loading.
        client.waits.forElement(
            id=u'subscribers-links', timeout=FOR_ELEMENT)

        # "Sample Person" should not be subscribed initially.
        client.asserts.assertText(
            xpath=SUBSCRIPTION_LINK, validator=u'Subscribe')

        # Subscribe "Sample Person" and check that the subscription
        # link now reads "Unsubscribe", that the person's name
        # appears in the subscriber's list, and that the icon
        # has changed to the remove icon.
        client.click(xpath=SUBSCRIPTION_LINK)
        client.waits.sleep(milliseconds=SLEEP)
        client.asserts.assertText(
            xpath=SUBSCRIPTION_LINK, validator=u'Unsubscribe')
        client.asserts.assertNode(xpath=PERSON_LINK % u'Sample Person')
        client.asserts.assertProperty(
            xpath=SUBSCRIPTION_LINK,
            validator=u'className|remove')

        # Make sure the unsubscribe link also works, that
        # the person's named is removed from the subscriber's list,
        # and that the icon has changed to the add icon.
        client.click(xpath=SUBSCRIPTION_LINK)
        client.waits.sleep(milliseconds=SLEEP)
        client.asserts.assertText(
            xpath=SUBSCRIPTION_LINK, validator=u'Subscribe')
        client.asserts.assertProperty(
            xpath=SUBSCRIPTION_LINK,
            validator=u'className|add')
        client.asserts.assertNotNode(xpath=PERSON_LINK % u'Sample Person')

        # Subscribe again in order to check that the minus icon
        # next to the subscriber's name works as an inline unsubscribe link.
        client.click(xpath=SUBSCRIPTION_LINK)
        client.waits.sleep(milliseconds=SLEEP)
        client.asserts.assertText(
            xpath=SUBSCRIPTION_LINK, validator=u'Unsubscribe')
        client.click(id=u'unsubscribe-icon-subscriber-12')
        client.waits.sleep(milliseconds=SLEEP)
        client.asserts.assertText(
            xpath=SUBSCRIPTION_LINK, validator=u'Subscribe')
        client.asserts.assertProperty(
            xpath=SUBSCRIPTION_LINK,
            validator=u'className|add')
        client.asserts.assertNotNode(xpath=PERSON_LINK % u'Sample Person')

        # Test inline subscribing of others by subscribing Ubuntu Team.
        # To confirm, look for the Ubuntu Team element after subscribing.
        client.click(link=u'Subscribe someone else')
        client.waits.forElement(
            name=u'search', timeout=FOR_ELEMENT)
        client.type(
            text=u'ubuntu-team',
            xpath=u'//div[contains(@class, "yui3-picker ") '
                   'and not(contains(@class, "yui3-picker-hidden"))]'
                   '//div[@class="yui3-picker-search-box"]'
                   '/input[@name="search"]')
        client.click(
            xpath=u'//div[contains(@class, "yui3-picker ") '
                   'and not(contains(@class, "yui3-picker-hidden"))]'
                   '//div[@class="yui3-picker-search-box"]/button')
        search_result_xpath = (
            u'//div[contains(@class, "yui3-picker ") '
            'and not(contains(@class, "yui3-picker-hidden"))]'
            '//ul[@class="yui3-picker-results"]/li[1]/span')
        client.waits.forElement(
            xpath=search_result_xpath, timeout=FOR_ELEMENT)
        client.click(xpath=search_result_xpath)
        client.waits.forElement(
            xpath=PERSON_LINK % u'Ubuntu Team', timeout=FOR_ELEMENT)

        # If we subscribe the user again,
        # the icon should still be the person icon.
        client.click(xpath=SUBSCRIPTION_LINK)
        client.waits.sleep(milliseconds=SLEEP)
        client.asserts.assertProperty(
            xpath=(PERSON_LINK % u'Sample Person') + '/span',
            validator=u'className|person')

        # Sample Person is logged in currently. She is not a
        # member of Ubuntu Team, and so, does not have permission
        # to unsubscribe the team.
        client.asserts.assertNotNode(id=u'unsubscribe-icon-subscriber-17')

        # Login Foo Bar who is a member of Ubuntu Team.
        # After login, wait for the page load and subscribers portlet.
        lpuser.FOO_BAR.ensure_login(client)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.waits.forElement(
            id=u'subscribers-links', timeout=FOR_ELEMENT)

        # Now test inline unsubscribing of a team, by ensuring
        # that Ubuntu Team is removed from the subscribers list.
        client.click(id=u'unsubscribe-icon-subscriber-17')
        client.waits.sleep(milliseconds=SLEEP)
        client.asserts.assertNotNode(xpath=PERSON_LINK % u'Ubuntu Team')
        client.asserts.assertText(
            xpath=SUBSCRIPTION_LINK, validator=u'Unsubscribe')
        client.asserts.assertProperty(
            xpath=SUBSCRIPTION_LINK,
            validator=u'className|remove')

        # Test unsubscribing via the remove icon for duplicates.
        # First, go to bug 6 and subscribe.
        client.open(url=bug_url % 6)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.waits.forElement(
            id=u'subscribers-links', timeout=FOR_ELEMENT)
        client.click(xpath=SUBSCRIPTION_LINK)
        client.waits.sleep(milliseconds=SLEEP)
        client.asserts.assertText(
            xpath=SUBSCRIPTION_LINK, validator=u'Unsubscribe')
        client.asserts.assertNode(xpath=PERSON_LINK % u'Foo Bar')
        # Bug 6 is a dupe of bug 5, so go to bug 5 to unsubscribe.
        client.open(url=bug_url % 5)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.waits.forElement(
            id=u'subscribers-links', timeout=FOR_ELEMENT)
        client.click(id=u'unsubscribe-icon-subscriber-16')
        client.waits.sleep(milliseconds=SLEEP)
        client.asserts.assertText(
            xpath=SUBSCRIPTION_LINK, validator=u'Subscribe')
        client.asserts.assertNotNode(xpath=PERSON_LINK % u'Foo Bar')
        # Then back to bug 6 to confirm the duplicate is also unsubscribed.
        client.open(url=bug_url % 6)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.waits.forElement(
            id=u'subscribers-links', timeout=FOR_ELEMENT)
        client.asserts.assertText(
            xpath=SUBSCRIPTION_LINK, validator=u'Subscribe')
        client.asserts.assertNotNode(xpath=PERSON_LINK % u'Foo Bar')

        # Subscribe/Unsubscribe link handling when dealing
        # with duplicates...
        #
        # First test case, ensure unsubscribing works when
        # dealing with a duplicate and an indirect subscription.
        lpuser.SAMPLE_PERSON.ensure_login(client)
        # Go to bug 6, the dupe, and subscribe.
        client.open(url=bug_url % 6)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.waits.forElement(
            id=u'subscribers-links', timeout=FOR_ELEMENT)
        client.click(xpath=SUBSCRIPTION_LINK)
        client.waits.sleep(milliseconds=SLEEP)
        client.asserts.assertText(
            xpath=SUBSCRIPTION_LINK, validator=u'Unsubscribe')
        # Now back to bug 5.
        client.open(url=bug_url % 5)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.waits.forElement(
            id=u'subscribers-links', timeout=FOR_ELEMENT)
        # Confirm there are 2 subscriber links: one in duplicate subscribers,
        # and one in indirect subscribers.
        client.waits.sleep(milliseconds=SLEEP)
        client.asserts.assertNode(
            xpath=(u'//div[@id="subscribers-from-duplicates"]'
                   '/div/a[@name="Sample Person"]'))
        client.asserts.assertNode(
            xpath=(u'//div[@id="subscribers-indirect"]'
                   '/div/a[text() = "Sample Person"]'))
        # Clicking "Unsubscribe" successfully removes the duplicate
        # subscription but the indirect subscription remains.
        client.click(xpath=SUBSCRIPTION_LINK)
        client.waits.sleep(milliseconds=SLEEP)
        client.asserts.assertNotNode(
            xpath=(u'//div[@id="subscribers-from-duplicates"]'
                   '/div/a[@name="Sample Person"]'))
        client.asserts.assertNode(
            xpath=(u'//div[@id="subscribers-indirect"]'
                   '/div/a[text() = "Sample Person"]'))

        # Second test case, confirm duplicate handling is correct between
        # direct and duplicate subscriptions.  Subscribe directly to bug 5.
        client.click(xpath=SUBSCRIPTION_LINK)
        client.waits.sleep(milliseconds=SLEEP)
        client.asserts.assertText(
            xpath=SUBSCRIPTION_LINK, validator=u'Unsubscribe')
        # Go to bug 6, the dupe, and subscribe.
        client.open(url=bug_url % 6)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.waits.forElement(
            id=u'subscribers-links', timeout=FOR_ELEMENT)
        client.click(xpath=SUBSCRIPTION_LINK)
        client.waits.sleep(milliseconds=SLEEP)
        client.asserts.assertText(
            xpath=SUBSCRIPTION_LINK, validator=u'Unsubscribe')
        # Now back to bug 5. Confirm there are 2 subscriptions.
        client.open(url=bug_url % 5)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.waits.forElement(
            id='direct-subscriber-12', timeout=FOR_ELEMENT)
        # The first click unsubscribes the direct subscription, leaving
        # the duplicate subscription.
        client.click(xpath=SUBSCRIPTION_LINK)
        client.waits.sleep(milliseconds=SLEEP)
        client.asserts.assertNotNode(
            xpath=(u'//div[@id="subscribers-links"]'
                   '/div/a[@name="Sample Person"]'))
        client.asserts.assertNode(
            xpath=(u'//div[@id="subscribers-from-duplicates"]'
                   '/div/a[@name="Sample Person"]'))
        # The second unsubscribe removes the duplicate, too.
        client.click(xpath=SUBSCRIPTION_LINK)
        client.waits.sleep(milliseconds=SLEEP)
        client.asserts.assertNotNode(
            xpath=(u'//div[@id="subscribers-from-duplicates"]'
                   '/div/a[@name="Sample Person"]'))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
