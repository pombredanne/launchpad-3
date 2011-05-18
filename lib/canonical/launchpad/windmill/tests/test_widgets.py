# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the Windmill test doubles themselves."""

__metaclass__ = type

from mocker import (
    KWARGS,
    Mocker,
    )

from lp.testing import TestCase
from lp.testing.windmill.widgets import OnPageWidget


class TestOnPageWidget(TestCase):

    """Tests for the OnPageWidget JavaScript widgets helper."""

    def test_valid_widget_xpath(self):
        widget = OnPageWidget(None, 'widget')
        self.assertEqual(u"//div[contains(@class, 'widget ')]", widget.xpath)

    def test_visible_xpath_property(self):
        widget = OnPageWidget(None, 'widget')
        self.assertEqual(u"//div[contains(@class, 'widget ') "
                         "and not(contains(@class, 'widget-hidden'))]",
                         widget.visible_xpath)

    def test_hidden_xpath_property(self):
        widget = OnPageWidget(None, 'widget')
        self.assertEqual(u"//div[contains(@class, 'widget ') "
                         "and contains(@class, 'widget-hidden')]",
                         widget.hidden_xpath)


class TestWidgetVisibility(TestCase):

    def setUp(self):
        super(TestWidgetVisibility, self).setUp()
        self.mocker = Mocker()

    def make_client_with_expected_visibility(self, expected_visibility_attr):
        widget = OnPageWidget(None, 'widget')
        expected_value = getattr(widget, expected_visibility_attr)

        # Set up the Mock
        client = self.mocker.mock()

        # Expectation
        client.waits.forElement(KWARGS, xpath=expected_value)

        return client

    def test_widget_visible_check(self):
        client = self.make_client_with_expected_visibility('visible_xpath')
        with self.mocker:
            widget = OnPageWidget(client, 'widget')
            widget.should_be_visible()

    def test_widget_hidden_check(self):
        client = self.make_client_with_expected_visibility('hidden_xpath')
        with self.mocker:
            widget = OnPageWidget(client, 'widget')
            widget.should_be_hidden()
