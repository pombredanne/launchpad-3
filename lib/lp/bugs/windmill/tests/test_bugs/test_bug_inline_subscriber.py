# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from canonical.launchpad.windmill.testing import lpuser

from windmill.authoring import WindmillTestClient

WAIT_PAGELOAD = u'30000'
WAIT_ELEMENT_COMPLETE = u'30000'
WAIT_CHECK_CHANGE = u'1000'
BUG_URL = u'http://bugs.launchpad.dev:8085/bugs/11'
SUBSCRIPTION_LINK = u'//div[@id="portlet-subscribers"]/div/div/a'
SAMPLE_PERSON_ID = u'subscriber-name12'

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
        id=u'subscribers-links', timeout=WAIT_ELEMENT_COMPLETE)

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
    client.asserts.assertNode(id=SAMPLE_PERSON_ID)
    client.asserts.assertProperty(
        xpath=SUBSCRIPTION_LINK,
        validator=u'style.backgroundImage|url(/@@/remove)')

    # Make sure the unsubscribe link also works, that
    # the person's named is removed from the subscriber's list,
    # and that the icon has changed to the add icon.
    client.click(xpath=SUBSCRIPTION_LINK)
    client.waits.sleep(milliseconds=WAIT_CHECK_CHANGE)
    client.asserts.assertText(
        xpath=SUBSCRIPTION_LINK, validator=u'Subscribe')
    client.asserts.assertProperty(
        xpath=SUBSCRIPTION_LINK,
        validator=u'style.backgroundImage|url(/@@/add)')
    client.asserts.assertNotNode(id=SAMPLE_PERSON_ID)

    # Subscribe again in order to check that the minus icon
    # next to the subscriber's name works as an inline unsubscribe link.
    client.click(xpath=SUBSCRIPTION_LINK)
    client.waits.sleep(milliseconds=WAIT_CHECK_CHANGE)
    client.asserts.assertText(
        xpath=SUBSCRIPTION_LINK, validator=u'Unsubscribe')
    client.click(id=u'unsubscribe-icon-name12')
    client.waits.sleep(milliseconds=WAIT_CHECK_CHANGE)
    client.asserts.assertText(
        xpath=SUBSCRIPTION_LINK, validator=u'Subscribe')
    client.asserts.assertProperty(
        xpath=SUBSCRIPTION_LINK,
        validator=u'style.backgroundImage|url(/@@/add)')
    client.asserts.assertNotNode(id=SAMPLE_PERSON_ID)

    # Test inline subscribing of others by subscribing Ubuntu Team.
    # To confirm, look for the Ubuntu Team element after subscribing.
    client.click(link=u'Subscribe someone else')
    client.waits.forElement(
        name=u'search', timeout=WAIT_ELEMENT_COMPLETE)
    client.type(text=u'ubuntu-team', name=u'search')
    client.click(
        xpath=u'//table[contains(@class, "yui-picker") '
               'and not(contains(@class, "yui-picker-hidden"))]'
               '//div[@class="yui-picker-search-box"]/button')
    search_result_xpath = (u'//table[contains(@class, "yui-picker") '
                            'and not(contains(@class, "yui-picker-hidden"))]'
                            '//ul[@class="yui-picker-results"]/li[2]/span')
    client.waits.forElement(
        xpath=search_result_xpath, timeout=WAIT_ELEMENT_COMPLETE)
    client.click(xpath=search_result_xpath)
    client.waits.forElement(
        id=u'subscribers-links', timeout=WAIT_ELEMENT_COMPLETE)
    client.asserts.assertNode(id=u'subscriber-ubuntu-team')

    # The same team cannot be subscribed again.
    client.click(link=u'Subscribe someone else')
    client.waits.forElement(
        name=u'search', timeout=WAIT_ELEMENT_COMPLETE)
    client.type(text=u'ubuntu-team', name=u'search')
    client.click(
        xpath=u'//table[contains(@class, "yui-picker") '
               'and not(contains(@class, "yui-picker-hidden"))]'
               '//div[@class="yui-picker-search-box"]/button')
    search_result_xpath = (u'//table[contains(@class, "yui-picker") '
                            'and not(contains(@class, "yui-picker-hidden"))]'
                            '//ul[@class="yui-picker-results"]/li[2]/span')
    client.waits.forElement(
        xpath=search_result_xpath, timeout=WAIT_ELEMENT_COMPLETE)
    client.click(xpath=search_result_xpath)
    client.waits.forElement(
        classname=u'yui-lazr-formoverlay-errors',
        timeout=WAIT_ELEMENT_COMPLETE)
    client.asserts.assertText(
        classname=u'yui-lazr-formoverlay-errors',
        validator=u'Ubuntu Team has already been subscribed')
    # Clear the error message by clicking the OK button.
    client.click(
        xpath=u'//div[@class="yui-lazr-formoverlay-actions"]/button[2]')

    # Sample Person is logged in currently. She is not a
    # member of Ubuntu Team, and so, does not have permission
    # to unsubscribe the team.
    client.asserts.assertNotNode(id=u'unsubscribe-icon-ubuntu-team')

    # Login Foo Bar who is a member of Ubuntu Team.
    # After login, wait for the page load and subscribers portlet.
    lpuser.FOO_BAR.ensure_login(client)
    client.waits.forPageLoad(timeout=WAIT_PAGELOAD)
    client.waits.forElement(
        id=u'subscribers-links', timeout=WAIT_ELEMENT_COMPLETE)

    # Now test inline unsubscribing of a team, by ensuring
    # that Ubuntu Team is removed from the subscribers list.
    client.click(id=u'unsubscribe-icon-ubuntu-team')
    client.waits.sleep(milliseconds=WAIT_CHECK_CHANGE)
    client.asserts.assertNotNode(id=u'subscriber-ubuntu-team')
