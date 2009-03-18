from canonical.launchpad.windmill.testing import lpuser

from windmill.authoring import WindmillTestClient

def test_product_edit_people():
    client = WindmillTestClient('Project +edit-people Picker widget test')

    lpuser.FOO_BAR.ensure_login(client)
    # Load +edit-people page.
    client.open(url='http://launchpad.dev:8085/firefox/+edit-people')
    client.waits.forPageLoad(timeout=u'20000')

    # Click on "Choose" link to show picker for the "owner" field.
    client.click(id=u'show-widget-field-owner')
    # Search for "guadamen".
    client.type(
        text=u'guadamen',
        xpath=u"//table[contains(@class, 'yui-picker') "
               "and not(contains(@class, 'yui-picker-hidden'))]"
               "//input[@class='yui-picker-search']")
    # Click the search button.
    client.click(
        xpath=u"//table[contains(@class, 'yui-picker') "
               "and not(contains(@class, 'yui-picker-hidden'))]"
               "//div[@class='yui-picker-search-box']/button")
    # Choose the first item in the list.
    client.click(
        xpath=u"//table[contains(@class, 'yui-picker') "
               "and not(contains(@class, 'yui-picker-hidden'))]"
               "//ul[@class='yui-picker-results']/li[1]/span")
    # Verify value.
    client.asserts.assertProperty(
        id=u'field.owner', validator=u"value|guadamen")

    # Click on "Choose" link to show picker for the "driver" field.
    client.click(id=u'show-widget-field-driver')
    # Search for "foo".
    client.type(
        text=u'foo',
        xpath=u"//table[contains(@class, 'yui-picker') "
               "and not(contains(@class, 'yui-picker-hidden'))]"
               "//input[@class='yui-picker-search']")
    # Click the search button.
    client.click(
        xpath=u"//table[contains(@class, 'yui-picker') "
               "and not(contains(@class, 'yui-picker-hidden'))]"
               "//div[@class='yui-picker-search-box']/button")
    # Choose the first item in the list.
    client.click(
        xpath=u"//table[contains(@class, 'yui-picker') "
               "and not(contains(@class, 'yui-picker-hidden'))]"
               "//ul[@class='yui-picker-results']/li[1]/span")
    # Verify value.
    client.asserts.assertProperty(
        id=u'field.driver', validator=u"value|name16")
