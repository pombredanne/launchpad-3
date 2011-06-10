# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import simplejson

from zope.interface import Interface
from zope.interface.interface import InterfaceClass
from zope.schema import Choice
from zope.schema.vocabulary import getVocabularyRegistry

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.widgets.popup import VocabularyPickerWidget
from lp.testing import TestCaseWithFactory


class TestMetaClass(InterfaceClass):
# We want to force creation of a field with an invalid HTML id.
    def __init__(self, name, bases=(), attrs=None, __doc__=None,
                 __module__=None):
        attrs = {
            "test_invalid_chars+":
            Choice(vocabulary='ValidTeamOwner'),
            "test_valid.item":
            Choice(vocabulary='ValidTeamOwner')}
        super(TestMetaClass, self).__init__(
            name, bases=bases, attrs=attrs, __doc__=__doc__,
            __module__=__module__)


class ITest(Interface):
# The schema class for the widget we will test.
    __metaclass__ = TestMetaClass


class TestVocabularyPickerWidget(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestVocabularyPickerWidget, self).setUp()
        self.context = self.factory.makeTeam()
        vocabulary_registry = getVocabularyRegistry()
        self.vocabulary = vocabulary_registry.get(
            self.context, 'ValidTeamOwner')
        self.request = LaunchpadTestRequest()

    def test_widget_template_properties(self):
        # Check the picker widget is correctly set up for a field which has a
        # name containing only valid HTML ID characters.

        field = ITest['test_valid.item']
        bound_field = field.bind(self.context)
        picker_widget = VocabularyPickerWidget(
            bound_field, self.vocabulary, self.request)

        self.assertEqual(
            'ValidTeamOwner', picker_widget.vocabulary_name)
        self.assertEqual(
            simplejson.dumps(self.vocabulary.displayname),
            picker_widget.header_text)
        self.assertEqual(
            simplejson.dumps(self.vocabulary.step_title),
            picker_widget.step_title_text)
        self.assertEqual(
            'show-widget-field-test_valid-item', picker_widget.show_widget_id)
        self.assertEqual(
            'field.test_valid.item', picker_widget.input_id)
        self.assertEqual(
            simplejson.dumps(None), picker_widget.extra_no_results_message)
        markup = picker_widget()
        self.assertIn(
            "Y.lp.app.picker.create('ValidTeamOwner', config);", markup)

    def test_widget_fieldname_with_invalid_html_chars(self):
        # Check the picker widget is correctly set up for a field which has a
        # name containing some invalid HTML ID characters.

        field = ITest['test_invalid_chars+']
        bound_field = field.bind(self.context)
        picker_widget = VocabularyPickerWidget(
            bound_field, self.vocabulary, self.request)

        # The widget name is encoded to get the widget's ID. It must only
        # contain valid HTML characters.
        self.assertEqual(
            'show-widget-field-test_invalid_chars-'
            'ZmllbGQudGVzdF9pbnZhbGlkX2NoYXJzKw',
            picker_widget.show_widget_id)
        self.assertEqual(
            'field.test_invalid_chars-ZmllbGQudGVzdF9pbnZhbGlkX2NoYXJzKw',
            picker_widget.input_id)

    def test_widget_suggestions(self):
        # The suggestions menu is shown when the input is invalid and there
        # are matches to suggest to the user.
        field = ITest['test_valid.item']
        bound_field = field.bind(self.context)
        request = LaunchpadTestRequest(form={'field.test_valid.item': 'foo'})
        picker_widget = VocabularyPickerWidget(
            bound_field, self.vocabulary, request)
        matches = list(picker_widget.matches)
        self.assertEqual(1, len(matches))
        self.assertEqual('Foo Bar', matches[0].title)
        markup = picker_widget()
        self.assertIn('id="field.test_valid.item-suggestions"', markup)
        self.assertIn(
            "Y.DOM.byId('field.test_valid.item-suggestions')", markup)
        self.assertTextMatchesExpressionIgnoreWhitespace(
            'Y.lp.app.picker.connect_select_menu\( '
            'select_menu, text_input\);',
            markup)
