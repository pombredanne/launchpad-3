# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import doctest

from zope.schema import Choice
from zope.schema.vocabulary import (
    SimpleTerm,
    SimpleVocabulary,
    )

from testtools.matchers import DocTestMatches

from lazr.enum import (
    EnumeratedType,
    Item,
    )

from canonical.launchpad.webapp.menu import structured
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.widgets.itemswidgets import (
    LabeledMultiCheckBoxWidget,
    LaunchpadRadioWidget,
    LaunchpadRadioWidgetWithDescription,
    PlainMultiCheckBoxWidget,
    )
from lp.testing import (
    TestCaseWithFactory,
    )


class ItemWidgetTestCase(TestCaseWithFactory):
    """A test case that sets up an items widget for testing."""

    layer = DatabaseFunctionalLayer

    WIDGET_CLASS = None
    SAFE_TERM = SimpleTerm('object-1', 'token-1', 'Safe title')
    UNSAFE_TERM = SimpleTerm('object-2', 'token-2', '<unsafe> &nbsp; title')

    def setUp(self):
        super(ItemWidgetTestCase, self).setUp()
        self.request = LaunchpadTestRequest()
        self.vocabulary = SimpleVocabulary([self.SAFE_TERM, self.UNSAFE_TERM])
        field = Choice(__name__='test_field', vocabulary=self.vocabulary)
        self.field = field.bind(object())
        self.widget = self.WIDGET_CLASS(
            self.field, self.vocabulary, self.request)

    def assertRenderItem(self, expected, term, checked=False):
        markup = self.widget._renderItem(
            index=1, text=term.title, value=term.token,
            name=self.field.__name__, cssClass=None, checked=checked)
        expected_matcher = DocTestMatches(
            expected, (doctest.NORMALIZE_WHITESPACE |
                       doctest.REPORT_NDIFF | doctest.ELLIPSIS))
        self.assertThat(markup, expected_matcher)


class TestPlainMultiCheckBoxWidget(ItemWidgetTestCase):
    """Test the PlainMultiCheckBoxWidget class."""

    WIDGET_CLASS = PlainMultiCheckBoxWidget

    def test__renderItem_checked(self):
        # Render item in checked state.
        expected = (
            '<input ... checked="checked" ... />&nbsp;Safe title')
        self.assertRenderItem(expected, self.SAFE_TERM, checked=True)

    def test__renderItem_unchecked(self):
        # Render item in unchecked state.
        expected = (
            '<input class="checkboxType" id="test_field.1" name="test_field" '
            'type="checkbox" value="token-1" />&nbsp;Safe title ')
        self.assertRenderItem(expected, self.SAFE_TERM, checked=False)

    def test__renderItem_unsafe_content(self):
        # Render item escapes unsafe markup.
        expected = '<input ... />&nbsp;&lt;unsafe&gt; &amp;nbsp; title '
        self.assertRenderItem(expected, self.UNSAFE_TERM, checked=False)


class TestLabeledMultiCheckBoxWidget(ItemWidgetTestCase):
    """Test the LabeledMultiCheckBoxWidget class."""

    WIDGET_CLASS = LabeledMultiCheckBoxWidget

    def test__renderItem_checked(self):
        # Render item in checked state.
        expected = (
            '<label ...><input ... checked="checked" ... />&nbsp;'
            'Safe title</label>')
        self.assertRenderItem(expected, self.SAFE_TERM, checked=True)

    def test__renderItem_unchecked(self):
        # Render item in unchecked state.
        expected = (
            '<label for="field.test_field.1" style="font-weight: normal">'
            '<input class="checkboxType" id="test_field.1" name="test_field" '
            'type="checkbox" value="token-1" />&nbsp;Safe title</label> ')
        self.assertRenderItem(expected, self.SAFE_TERM, checked=False)

    def test__renderItem_unsafe_content(self):
        # Render item escapes unsafe markup.
        expected = '<label .../>&nbsp;&lt;unsafe&gt; &amp;nbsp; title</label>'
        self.assertRenderItem(expected, self.UNSAFE_TERM, checked=False)


class TestLaunchpadRadioWidget(ItemWidgetTestCase):
    """Test the LaunchpadRadioWidget class."""

    WIDGET_CLASS = LaunchpadRadioWidget

    def test__renderItem_checked(self):
        # Render item in checked state.
        expected = (
            '<label ...><input ... checked="checked" ... />&nbsp;'
            'Safe title</label>')
        self.assertRenderItem(expected, self.SAFE_TERM, checked=True)

    def test__renderItem_unchecked(self):
        # Render item in unchecked state.
        expected = (
            '<label style="font-weight: normal">'
            '<input class="radioType" id="test_field.1" name="test_field" '
            'type="radio" value="token-1" />&nbsp;Safe title</label>')
        self.assertRenderItem(expected, self.SAFE_TERM, checked=False)

    def test__renderItem_unsafe_content(self):
        # Render item escapes unsafe markup.
        expected = (
            '<label ...><input ... />'
            '&nbsp;&lt;unsafe&gt; &amp;nbsp; title</label>')
        self.assertRenderItem(expected, self.UNSAFE_TERM, checked=False)

    def test__renderItem_without_label(self):
        # Render item omits a wrapping label if the text contains a label.
        html_term = SimpleTerm(
            'object-3', 'token-3', structured('<label>title</label>'))
        expected = ('<input ... />&nbsp;<label>title</label>')
        self.assertRenderItem(expected, html_term, checked=False)


class TestLaunchpadRadioWidgetWithDescription(TestCaseWithFactory):
    """Test the LaunchpadRadioWidgetWithDescription class."""

    layer = DatabaseFunctionalLayer

    class TestEnum(EnumeratedType):
        SAFE_TERM = Item('item-1', description='Safe title')
        UNSAFE_TERM = Item('item-<2>', description='<unsafe> &nbsp; title')

    def setUp(self):
        super(TestLaunchpadRadioWidgetWithDescription, self).setUp()
        self.request = LaunchpadTestRequest()
        field = Choice(__name__='test_field', vocabulary=self.TestEnum)
        self.field = field.bind(object())
        self.widget = LaunchpadRadioWidgetWithDescription(
            self.field, self.TestEnum, self.request)

    def assertRenderItem(self, expected, method, enum_item):
        markup = method(
            index=1, text=enum_item.title, value=enum_item.name,
            name=self.field.__name__, cssClass=None)
        expected_matcher = DocTestMatches(
            expected, (doctest.NORMALIZE_WHITESPACE |
                       doctest.REPORT_NDIFF | doctest.ELLIPSIS))
        self.assertThat(markup, expected_matcher)

    def test_renderSelectedItem(self):
        # Render checked="checked" item in checked state.
        expected = (
            '<tr> <td rowspan="2">'
            '<input class="radioType" checked="checked" id="test_field.1" '
            'name="test_field" type="radio" value="SAFE_TERM" /></td> '
            '<td><label for="test_field.1">item-1</label></td> </tr> '
            '<tr> <td class="formHelp">Safe title</td> </tr>')
        self.assertRenderItem(
            expected, self.widget.renderSelectedItem, self.TestEnum.SAFE_TERM)

    def test_renderItem(self):
        # Render item in unchecked state.
        expected = (
            '<tr> <td rowspan="2">'
            '<input class="radioType" id="test_field.1" '
            'name="test_field" type="radio" value="SAFE_TERM" /></td> '
            '<td><label for="test_field.1">item-1</label></td> </tr> '
            '<tr> <td class="formHelp">Safe title</td> </tr>')
        self.assertRenderItem(
            expected, self.widget.renderItem, self.TestEnum.SAFE_TERM)

    def test_renderSelectedItem_unsafe_content(self):
        # Render selected item escapes unsafe markup.
        expected = (
            '<...>item-&lt;2&gt;<...>&lt;unsafe&gt; &amp;nbsp; title<...>')
        self.assertRenderItem(
            expected,
            self.widget.renderSelectedItem, self.TestEnum.UNSAFE_TERM)

    def test_renderItem_unsafe_content(self):
        # Render item escapes unsafe markup.
        expected = (
            '<...>item-&lt;2&gt;<...>&lt;unsafe&gt; &amp;nbsp; title<...>')
        self.assertRenderItem(
            expected, self.widget.renderItem, self.TestEnum.UNSAFE_TERM)
