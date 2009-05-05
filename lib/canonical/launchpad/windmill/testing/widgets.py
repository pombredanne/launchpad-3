# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test helpers for common AJAX widgets."""

__metaclass__ = type
__all__ = []


from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing import lpuser


class InlineEditorWidgetTest:
    """Test that the inline editor widget is working properly on a page."""

    def __init__(self, url, widget_id, expected_value, new_value, name=None,
                 suite='inline_editor', user=lpuser.NO_PRIV):
        """Create a new InlineEditorWidgetTest.

        :param url: The URL to the page on which the widget lives.
        :param widget_id: The HTML id of the widget.
        :param expected_value: The current expected value of the widget.
        :param new_value: The value to change the field to.
        :param suite: The suite in which this test is part of.
        :param user: The user who should be logged in.
        """
        self.url = url
        if name is None:
            self.__name__ = ('test_%s_inline_edit'
                             % widget_id.replace('-', '_'))
        else:
            self.__name__ = name
        self.widget_id = widget_id
        self.expected_value = expected_value
        self.new_value = new_value
        self.suite = suite
        self.user = user

    def __call__(self):
        """Tests the widget is hooked and works properly.

        The test:
        * opens the url;
        * asserts that the widget is initialized to the expected value;
        * uses the inline editor to change to the new value;
        * asserts that the page was updated with the new value;
        * reloads and verifies that the new value sticked.
        """
        client = WindmillTestClient(self.suite)

        self.user.ensure_login(client)

        client.open(url=self.url)
        client.waits.forPageLoad(timeout=u'20000')
        client.waits.forElement(
            xpath=u"//h1[@id='%s']/a/img" % self.widget_id, timeout=u'8000')
        client.asserts.assertText(
            xpath=u"//h1[@id='%s']/span[1]" % self.widget_id,
            validator=self.expected_value)
        client.click(xpath=u"//h1[@id='%s']/a/img" % self.widget_id)
        client.waits.forElement(
            xpath=u"//h1[@id='%s']/a/img" % self.widget_id, timeout=u'8000')
        client.waits.forElement(
            timeout=u'8000',
            xpath=u"//h1[@id='%s']//textarea" % self.widget_id)
        client.type(
            xpath=u"//h1[@id='%s']//textarea" % self.widget_id,
            text=self.new_value)
        client.click(xpath=u"//h1[@id='%s']//button[1]" % self.widget_id)
        client.asserts.assertNode(
            xpath=u"//h1[@id='%s']/span[1]" % self.widget_id)
        client.asserts.assertText(
            xpath=u"//h1[@id='%s']/span[1]" % self.widget_id,
            validator=self.new_value)

        # And make sure it's actually saved on the server.
        client.open(url=self.url)
        client.waits.forPageLoad(timeout=u'20000')
        client.asserts.assertNode(
            xpath=u"//h1[@id='%s']/span[1]" % self.widget_id)
        client.asserts.assertText(
            xpath=u"//h1[@id='%s']/span[1]" % self.widget_id,
            validator=self.new_value)

def _search_picker_widget(client, search_text, result_index):
    """Search in picker widget and select an item."""
    # Search for search_text in picker widget.
    search_box_xpath = (u"//table[contains(@class, 'yui-picker') "
                         "and not(contains(@class, 'yui-picker-hidden'))]"
                         "//input[@class='yui-picker-search']")
    client.waits.forElement(xpath=search_box_xpath, timeout=u'20000')
    client.type(text=search_text, xpath=search_box_xpath)
    client.click(
        xpath=u"//table[contains(@class, 'yui-picker') "
               "and not(contains(@class, 'yui-picker-hidden'))]"
               "//div[@class='yui-picker-search-box']/button")
    # Select item at the result_index in the list.
    item_xpath = (u"//table[contains(@class, 'yui-picker') "
                     "and not(contains(@class, 'yui-picker-hidden'))]"
                     "//ul[@class='yui-picker-results']/li[%d]/span"
                     % result_index)
    client.waits.forElement(xpath=item_xpath, timeout=u'20000')
    client.click(xpath=item_xpath)


class InlinePickerWidgetSearchTest:
    """Test that the Picker widget edits a value inline."""

    def __init__(self, url, activator_id, search_text, result_index,
                 new_value, name=None, suite='inline_picker_search_test',
                 user=lpuser.FOO_BAR):
        """Create a new InlinePickerSearchWidgetTest.

        :param url: The URL to the page on which the widget lives.
        :param activator_id: The HTML id of the activator widget.
        :param search_text: Picker search value.
        :param result_index: Item in picker result to select.
        :param new_value: The value to change the field to.
        :param name: Override the test name, if necessary.
        :param suite: The suite in which this test is part of.
        :param user: The user who should be logged in.
        """
        self.url = url
        if name is None:
            self.__name__ = 'test_%s_inline_picker' % (
                activator_id.replace('-', '_'),)
        else:
            self.__name__ = name
        self.activator_id = activator_id
        self.search_text = search_text
        self.result_index = result_index
        self.new_value = new_value
        self.suite = suite
        self.user = user

    def __call__(self):
        client = WindmillTestClient(self.suite)
        self.user.ensure_login(client)

        # Load page.
        client.open(url=self.url)
        client.waits.forPageLoad(timeout=u'20000')

        # Click on edit button.
        button_xpath = (
            u"//span[@id='%s']"
             "/button[not(contains(@class, 'yui-activator-hidden'))]"
             % self.activator_id)
        client.waits.forElement(xpath=button_xpath, timeout=u'20000')
        client.click(xpath=button_xpath)

        # Search picker.
        _search_picker_widget(client, self.search_text,
                              self.result_index)

        # Verify update.
        client.waits.sleep(milliseconds=u'2000')
        client.asserts.assertText(
            xpath=u"//span[@id='%s']//a" % self.activator_id,
            validator=self.new_value)

        # Reload the page to verify that the selected value is persisted.
        client.open(url=self.url)
        client.waits.forPageLoad(timeout=u'20000')

        # Verify update, again.
        client.waits.forElement(
            xpath=u"//span[@id='%s']//a" % self.activator_id,
            timeout=u'20000')
        client.asserts.assertText(
            xpath=u"//span[@id='%s']//a" % self.activator_id,
            validator=self.new_value)


class InlinePickerWidgetButtonTest:
    """Test custom buttons/links added to the Picker."""

    def __init__(self, url, activator_id, button_class, new_value,
                 name=None, suite='inline_picker_button_test',
                 user=lpuser.FOO_BAR):
        """Create a new InlinePickerWidgetButtonTest.

        :param url: The URL to the page on which the widget lives.
        :param activator_id: The HTML id of the activator widget.
        :param button_class: The CSS class identifying the button.
        :param new_value: The value to change the field to.
        :param name: Override the test name, if necessary.
        :param suite: The suite in which this test is part of.
        :param user: The user who should be logged in.
        """
        self.url = url
        self.activator_id = activator_id
        self.button_class = button_class
        self.new_value = new_value
        self.suite = suite
        self.user = user
        if name is None:
            self.__name__ = 'test_%s_inline_picker' % (
                activator_id.replace('-', '_'),)
        else:
            self.__name__ = name

    def __call__(self):
        client = WindmillTestClient(self.suite)
        self.user.ensure_login(client)

        # Load page.
        client.open(url=self.url)
        client.waits.forPageLoad(timeout=u'25000')

        # Click on edit button.
        button_xpath = (
            u"//span[@id='%s']"
             "/button[not(contains(@class, 'yui-activator-hidden'))]"
             % self.activator_id)
        client.waits.forElement(xpath=button_xpath, timeout=u'25000')
        client.click(xpath=button_xpath)

        # Click on remove button.
        remove_button_xpath = (
            u"//table[contains(@class, 'yui-picker') "
             "and not(contains(@class, 'yui-picker-hidden'))]"
             "//*[contains(@class, '%s')]" % self.button_class)
        client.waits.forElement(xpath=remove_button_xpath, timeout=u'25000')
        client.click(xpath=remove_button_xpath)
        client.waits.sleep(milliseconds=u'2000')

        # Verify removal.
        client.asserts.assertText(
            xpath=u"//span[@id='%s']/span[@class='yui-activator-data-box']"
                  % self.activator_id,
            validator=self.new_value)

        # Reload the page to verify that the selected value is persisted.
        client.open(url=self.url)
        client.waits.forPageLoad(timeout=u'25000')

        # Verify removal, again.
        client.waits.forElement(
            xpath=u"//span[@id='%s']/span[@class='yui-activator-data-box']"
                  % self.activator_id,
            timeout=u'25000')
        client.asserts.assertText(
            xpath=u"//span[@id='%s']/span[@class='yui-activator-data-box']"
                  % self.activator_id,
            validator=self.new_value)


class FormPickerWidgetTest:
    """Test that the Picker widget edits a form value properly."""

    def __init__(self, url, short_field_name, search_text, result_index,
                 new_value, name=None, suite='form_picker',
                 user=lpuser.FOO_BAR):
        """Create a new FormPickerWidgetTest.

        :param url: The URL to the page on which the widget lives.
        :param short_field_name: The name of the Zope attribute. For example,
                                 'owner' which has the id 'field.owner'.
        :param search_text: Picker search value.
        :param result_index: Item in picker result to select.
        :param new_value: The value to change the field to.
        :param name: Override the test name, if necessary.
        :param suite: The suite in which this test is part of.
        :param user: The user who should be logged in.
        """
        self.url = url
        if name is None:
            self.__name__ = 'test_%s_form_picker' % (
                short_field_name.replace('-', '_'),)
        else:
            self.__name__ = name
        self.search_text = search_text
        self.result_index = result_index
        self.new_value = new_value
        self.suite = suite
        self.user = user
        self.choose_link_id = 'show-widget-field-%s' % short_field_name
        self.field_id = 'field.%s' % short_field_name

    def __call__(self):
        client = WindmillTestClient(self.suite)
        self.user.ensure_login(client)

        # Load page.
        client.open(url=self.url)
        client.waits.forPageLoad(timeout=u'20000')

        # Click on "Choose" link to show picker for the given field.
        client.click(id=self.choose_link_id)

        # Search picker.
        _search_picker_widget(client, self.search_text, self.result_index)

        # Verify value.
        client.asserts.assertProperty(
            id=self.field_id, validator=u"value|%s" % self.new_value)
