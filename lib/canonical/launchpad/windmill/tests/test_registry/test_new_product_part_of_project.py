from canonical.launchpad.windmill.testing import lpuser

from windmill.authoring import WindmillTestClient

def test_new_product_part_of_project():
    client = WindmillTestClient(
        'Test /projects/+new "Part of" Picker widget.')

    lpuser.FOO_BAR.ensure_login(client)

    # Load /projects/+new page.
    client.open(url='http://launchpad.dev:8085/projects/+new')
    client.waits.forPageLoad(timeout=u'20000')

    # Click on "Choose" link to show picker for the "owner" field.
    client.click(id=u'show-widget-field-project')
    # Search for "gnome".
    # Only one Picker widget should be visible (without the
    # yui-picker-hidden class) at one time.
    client.type(
        text=u'mirrors',
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
        id=u'field.project', validator=u"value|launchpad-mirrors")
