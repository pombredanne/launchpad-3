# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.interface import (
    Interface,
    implements,
    )
from zope.schema import Choice
from zope.schema.vocabulary import (
    SimpleTerm,
    SimpleVocabulary,
    )

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.widgets.itemswidgets import (
    PlainMultiCheckBoxWidget,
    )
from lp.testing import (
    person_logged_in,
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

        class ITest(Interface):
            test_field = Choice(
                title=u'status', vocabulary=self.vocabulary)

        class TestObject:
            implements(ITest)

            def __init__(self, status=None):
                self.status = status

        self.field = ITest['test_field'].bind(TestObject())
        self.widget = self.WIDGET_CLASS(
            self.field, self.vocabulary, self.request)


class TestPlainMultiCheckBoxWidget(ItemWidgetTestCase):
    """Test the TargetBranchWidget class."""

    WIDGET_CLASS = PlainMultiCheckBoxWidget

    def test__renderItem(self):
        # Render item iterpolation is safe.
        markup = self.widget._renderItem(
            index=1,
            text=self.UNSAFE_TERM.title, value=self.UNSAFE_TERM.token,
            name=self.field.__name__, cssClass=None, checked=False)
        expected = (
            '<input class="checkboxType" id="test_field.1" name="test_field" '
            'type="checkbox" value="token-2" />&nbsp;'
            '&lt;unsafe&gt; &amp;nbsp; title ')
        self.assertEqual(expected, markup)
