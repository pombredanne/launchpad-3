# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.schema import Choice
from zope.schema.vocabulary import (
    SimpleTerm,
    SimpleVocabulary,
    )

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.widgets.itemswidgets import (
    PlainMultiCheckBoxWidget,
    LabeledMultiCheckBoxWidget,
    )
from lp.testing import (
    TestCaseWithFactory,
    )


class ItemWidgetTestCase(TestCaseWithFactory):
    """A test case that sets up an items widget for testing"""

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
        self.assertEqual(expected, markup)


class TestPlainMultiCheckBoxWidget(ItemWidgetTestCase):
    """Test the PlainMultiCheckBoxWidget class."""

    WIDGET_CLASS = PlainMultiCheckBoxWidget

    def test__renderItem_checked(self):
        # Render item in checked state.
        expected = (
            '<input class="checkboxType" checked="checked" id="test_field.1" '
            'name="test_field" type="checkbox" value="token-1" />&nbsp;'
            'Safe title ')
        self.assertRenderItem(expected, self.SAFE_TERM, checked=True)

    def test__renderItem_unchecked(self):
        # Render item in unchecked state.
        expected = (
            '<input class="checkboxType" id="test_field.1" name="test_field" '
            'type="checkbox" value="token-1" />&nbsp;Safe title ')
        self.assertRenderItem(expected, self.SAFE_TERM, checked=False)

    def test__renderItem_unsafe_content(self):
        # Render item iterpolation is safe.
        expected = (
            '<input class="checkboxType" id="test_field.1" name="test_field" '
            'type="checkbox" value="token-2" />&nbsp;'
            '&lt;unsafe&gt; &amp;nbsp; title ')
        self.assertRenderItem(expected, self.UNSAFE_TERM, checked=False)


class TestLabeledMultiCheckBoxWidget(ItemWidgetTestCase):
    """Test the PlainMultiCheckBoxWidget class."""

    WIDGET_CLASS = LabeledMultiCheckBoxWidget

    def test__renderItem_checked(self):
        # Render item in checked state.
        expected = (
            '<label for="field.test_field.1" style="font-weight: normal">'
            '<input class="checkboxType" checked="checked" id="test_field.1" '
            'name="test_field" type="checkbox" value="token-1" />&nbsp;'
            'Safe title</label> ')
        self.assertRenderItem(expected, self.SAFE_TERM, checked=True)

    def test__renderItem_unchecked(self):
        # Render item in unchecked state.
        expected = (
            '<label for="field.test_field.1" style="font-weight: normal">'
            '<input class="checkboxType" id="test_field.1" name="test_field" '
            'type="checkbox" value="token-1" />&nbsp;Safe title</label> ')
        self.assertRenderItem(expected, self.SAFE_TERM, checked=False)

    def test__renderItem_unsafe_content(self):
        # Render item iterpolation is safe.
        expected = (
            '<label for="field.test_field.1" style="font-weight: normal">'
            '<input class="checkboxType" id="test_field.1" name="test_field" '
            'type="checkbox" value="token-2" />&nbsp;'
            '&lt;unsafe&gt; &amp;nbsp; title</label> ')
        self.assertRenderItem(expected, self.UNSAFE_TERM, checked=False)
