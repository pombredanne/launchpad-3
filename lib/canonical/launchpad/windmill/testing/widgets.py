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
            self.__name__ = 'test_%s_inline_edit' % widget_id.replace('-', '_')
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
