from canonical.launchpad.windmill.testing import lpuser

from windmill.authoring import WindmillTestClient

def test_change_assignee():
    """Test inplace editing of the bugtask assignee.

    This excercises the Activator and Picker widgets.
    """
    client = WindmillTestClient('BugTask assignee test')

    lpuser.FOO_BAR.ensure_login(client)
    # Load bug page.
    client.open(url='http://bugs.launchpad.dev:8085/bugs/1')
    client.waits.forPageLoad(timeout=u'20000')

    # Click on assignee edit button for first bugtask.
    client.waits.forElement(
        xpath=u"//span[@id='assignee-content-box-2']/button",
        timeout=u'20000')
    client.click(xpath=u"//span[@id='assignee-content-box-2']/button")
    # Search for "admin" in picker widget.
    client.type(
        text=u'admin',
        xpath=u"//table[contains(@class, 'yui-picker') "
               "and not(contains(@class, 'yui-picker-hidden'))]"
               "//input[@class='yui-picker-search']")
    client.click(
        xpath=u"//table[contains(@class, 'yui-picker') "
               "and not(contains(@class, 'yui-picker-hidden'))]"
               "//div[@class='yui-picker-search-box']/button")
    # Select first item in list (Commercial Admins).
    client.click(
        xpath=u"//table[contains(@class, 'yui-picker') "
               "and not(contains(@class, 'yui-picker-hidden'))]"
               "//ul[@class='yui-picker-results']/li[1]/span")
    # Verify update.
    client.asserts.assertText(
        xpath=u"//span[@id='assignee-content-box-2']//a",
        validator=u'Commercial Subscription Admins')

    # Click on assignee edit button for another bugtask.
    client.click(xpath=u"//span[@id='assignee-content-box-17']/button")
    # Search for "admin" in picker widget.
    client.type(
        text=u'admin',
        xpath=u"//table[contains(@class, 'yui-picker') "
               "and not(contains(@class, 'yui-picker-hidden'))]"
               "//input[@class='yui-picker-search']")
    client.click(
        xpath=u"//table[contains(@class, 'yui-picker') "
               "and not(contains(@class, 'yui-picker-hidden'))]"
               "//div[@class='yui-picker-search-box']/button")
    # Select second item in list (Foo Bar).
    client.click(
        xpath=u"//table[contains(@class, 'yui-picker') "
               "and not(contains(@class, 'yui-picker-hidden'))]"
               "//ul[@class='yui-picker-results']/li[2]/span")
    # Verify update.
    client.asserts.assertText(
        xpath=u"//span[@id='assignee-content-box-17']//a",
        validator=u'Foo Bar')
