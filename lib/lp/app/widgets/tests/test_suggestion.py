# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


from datetime import (
    datetime,
    timedelta,
    )
import doctest

from pytz import utc

from zope.component import provideUtility
from zope.interface import implements
from zope.schema import Choice
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import (
    SimpleTerm,
    SimpleVocabulary,
    )
from zope.security.proxy import removeSecurityProxy

from testtools.matchers import DocTestMatches

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.launchpad.webapp.vocabulary import IHugeVocabulary
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.widgets.suggestion import (
    SuggestionWidget,
    TargetBranchWidget,
    )
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class Simple:
    """A simple class to test fields ans widgets."""

    def __init__(self, name, displayname):
        self.name = name
        self.displayname = displayname


class SimpleHugeVocabulary(SimpleVocabulary):
    implements(IHugeVocabulary)
    displayname = "Simple objects"
    step_title = "Select something"

    def __call__(self, context):
        # Allow an instance to be used as a utility.
        return self


class TestSuggestionWidget(TestCaseWithFactory):
    """Test the SuggestionWidget class."""

    layer = DatabaseFunctionalLayer

    SAFE_OBJECT = Simple('token-1', 'Safe title')
    UNSAFE_OBJECT = Simple('token-2', '<unsafe> &nbsp; title')

    SAFE_TERM = SimpleTerm(
        SAFE_OBJECT, SAFE_OBJECT.name, SAFE_OBJECT.displayname)
    UNSAFE_TERM = SimpleTerm(
        UNSAFE_OBJECT, UNSAFE_OBJECT.name, UNSAFE_OBJECT.displayname)

    class ExampleSuggestionWidget(SuggestionWidget):

        @staticmethod
        def _getSuggestions(context):
            return SimpleVocabulary([TestSuggestionWidget.SAFE_TERM])

        def _autoselectOther(self):
            on_key_press = "selectWidget('%s', event);" % self._otherId()
            self.other_selection_widget.onKeyPress = on_key_press

    def setUp(self):
        super(TestSuggestionWidget, self).setUp()
        request = LaunchpadTestRequest()
        vocabulary = SimpleHugeVocabulary(
            [self.SAFE_TERM, self.UNSAFE_TERM])
        provideUtility(
            vocabulary, provides=IVocabularyFactory,
            name='SimpleHugeVocabulary')
        field = Choice(
            __name__='test_field', vocabulary="SimpleHugeVocabulary")
        self.field = field.bind(object())
        self.widget = self.ExampleSuggestionWidget(
            self.field, vocabulary, request)

    def assertRenderItem(self, expected, term, checked=False):
        markup = self.widget._renderItem(
            index=1, text=term.title, value=term.token,
            name=self.field.__name__, cssClass=None, checked=checked)
        expected_matcher = DocTestMatches(
            expected, (doctest.NORMALIZE_WHITESPACE |
                       doctest.REPORT_NDIFF | doctest.ELLIPSIS))
        self.assertThat(markup, expected_matcher)

    def test__renderItem_checked(self):
        # Render item in checked state.
        expected = (
            '<input ... checked="checked" ... />&nbsp;Safe title')
        self.assertRenderItem(expected, self.SAFE_TERM, checked=True)

    def test__renderItem_unchecked(self):
        # Render item in unchecked state.
        expected = (
            '<input class="radioType" id="test_field.1" name="test_field" '
            'type="radio" value="token-1" />&nbsp;Safe title ')
        self.assertRenderItem(expected, self.SAFE_TERM, checked=False)

    def test__renderItem_unsafe_content(self):
        # Render item escapes unsafe markup.
        expected = '<input ... />&nbsp;&lt;unsafe&gt; &amp;nbsp; title '
        self.assertRenderItem(expected, self.UNSAFE_TERM, checked=False)

    def test_renderItems(self):
        # Render all vocabulary and the other option as items.
        markups = self.widget.renderItems(None)
        self.assertEqual(2, len(markups))
        expected = (
            """<input class="radioType" checked="checked" ...
            value="token-1" />&nbsp;<label ...>Safe title</label>""")
        expected_matcher = DocTestMatches(
            expected, (doctest.NORMALIZE_WHITESPACE |
                       doctest.REPORT_NDIFF | doctest.ELLIPSIS))
        self.assertThat(markups[0], expected_matcher)
        expected = (
            """<input class="radioType" ...
             onClick="this.form['field.test_field.test_field'].focus()" ...
             value="other" />&nbsp;<label ...>Other:</label>
             <input type="text" value="" ...
             onKeyPress="selectWidget('field.test_field.1', event);"
             .../>...""")
        expected_matcher = DocTestMatches(
            expected, (doctest.NORMALIZE_WHITESPACE |
                       doctest.REPORT_NDIFF | doctest.ELLIPSIS))
        self.assertThat(markups[1], expected_matcher)


def make_target_branch_widget(branch):
    """Given a branch, return a widget for selecting where to land it."""
    choice = Choice(vocabulary='Branch').bind(branch)
    request = LaunchpadTestRequest()
    return TargetBranchWidget(choice, None, request)


class TestTargetBranchWidget(TestCaseWithFactory):
    """Test the TargetBranchWidget class."""

    layer = DatabaseFunctionalLayer

    def test_stale_target(self):
        """Targets for proposals older than 90 days are not considered."""
        bmp = self.factory.makeBranchMergeProposal()
        target = bmp.target_branch
        source = self.factory.makeBranchTargetBranch(target.target)
        with person_logged_in(bmp.registrant):
            widget = make_target_branch_widget(source)
            self.assertIn(target, widget.suggestion_vocab)
            stale_date = datetime.now(utc) - timedelta(days=91)
            removeSecurityProxy(bmp).date_created = stale_date
            widget = make_target_branch_widget(source)
        self.assertNotIn(target, widget.suggestion_vocab)
