# Copyright 2009 Canonical Ltd.  All rights reserved.

from canonical.launchpad.windmill.testing import lpuser

from windmill.authoring import WindmillTestClient

WAIT_PAGELOAD = u'30000'
WAIT_ELEMENT_COMPLETE = u'30000'
WAIT_CHECK_CHANGE = u'1000'
BUG_URL = u'http://bugs.launchpad.dev:8085/bugs/11'
SUBSCRIPTION_LINK = u'//div[@id="portlet-subscribers"]/div/div/a'
SUBSCRIBERS_LIST_PERSON = u'//div[@id="subscriber-name12"]'

def test_inline_subscriber():
    """Test inline subscribing on bugs pages.

    This test makes sure that subscribing and unsubscribing
    from a bug works inline on a bug page.
    """
    client = WindmillTestClient('Inline bug page subscribers test')

    lpuser.SAMPLE_PERSON.ensure_login(client)

    # Open a bug page and wait for it to finish loading.
    client.open(url=BUG_URL)
    client.waits.forPageLoad(timeout=WAIT_PAGELOAD)

    # Ensure the subscriber's portlet has finished loading.
    client.waits.forElement(
        xpath=u'//div[@id="subscribers-links"]',
        timeout=WAIT_ELEMENT_COMPLETE)

    # "Sample Person" should not be subscribed initially.
    client.asserts.assertText(
        xpath=SUBSCRIPTION_LINK, validator=u'Subscribe')

    # Subscribe "Sample Person" and check that the subscription
    # link now reads "Unsubscribe", that the person's name
    # appears in the subscriber's list, and that the icon
    # has changed to the remove icon.
    client.click(xpath=SUBSCRIPTION_LINK)
    client.waits.sleep(milliseconds=WAIT_CHECK_CHANGE)
    client.asserts.assertText(
        xpath=SUBSCRIPTION_LINK, validator=u'Unsubscribe')
    client.asserts.assertNode(xpath=SUBSCRIBERS_LIST_PERSON)
    client.asserts.assertProperty(
        xpath=SUBSCRIPTION_LINK,
        validator='style.backgroundImage|url(/@@/remove)')

    # Make sure the unsubscribe link also works, that
    # the person's named is removed from the subscriber's list,
    # and that the icon has changed to the add icon.
    client.click(xpath=SUBSCRIPTION_LINK)
    client.waits.sleep(milliseconds=WAIT_CHECK_CHANGE)
    client.asserts.assertText(
        xpath=SUBSCRIPTION_LINK, validator=u'Subscribe')
    client.asserts.assertProperty(
        xpath=SUBSCRIPTION_LINK,
        validator='style.backgroundImage|url(/@@/add)')
    client.asserts.assertNotNode(xpath=SUBSCRIBERS_LIST_PERSON)

    # Subscribe again in order to check that the minus icon
    # next to the subscriber's name works as an inline unsubscribe link.
    client.click(xpath=SUBSCRIPTION_LINK)
    client.waits.sleep(milliseconds=WAIT_CHECK_CHANGE)
    client.asserts.assertText(
        xpath=SUBSCRIPTION_LINK, validator=u'Unsubscribe')
    client.click(xpath=u'//a[@id="unsubscribe-name12"]/img')
    client.waits.sleep(milliseconds=WAIT_CHECK_CHANGE)
    client.asserts.assertText(
        xpath=SUBSCRIPTION_LINK, validator=u'Subscribe')
    client.asserts.assertProperty(
        xpath=SUBSCRIPTION_LINK,
        validator='style.backgroundImage|url(/@@/add)')
    client.asserts.assertNotNode(xpath=SUBSCRIBERS_LIST_PERSON)
