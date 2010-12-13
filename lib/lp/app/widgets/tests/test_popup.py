# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.schema.vocabulary import getVocabularyRegistry

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.widgets.popup import VocabularyPickerWidget
from lp.registry.interfaces.person import ITeam
from lp.testing import TestCaseWithFactory


class TestVocabularyPickerWidget(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestVocabularyPickerWidget, self).setUp()
        context = self.factory.makeTeam()
        field = ITeam['teamowner']
        self.bound_field = field.bind(context)
        vocabulary_registry = getVocabularyRegistry()
        self.vocabulary = vocabulary_registry.get(context, 'ValidTeamOwner')
        self.request = LaunchpadTestRequest()

    def test_js_template_args(self):
        picker_widget = VocabularyPickerWidget(
            self.bound_field, self.vocabulary, self.request)
        js_template_args = picker_widget.js_template_args()
        self.assertEqual(
            'ValidTeamOwner', js_template_args['vocabulary'])
        self.assertEqual(
            self.vocabulary.displayname, js_template_args['header'])
        self.assertEqual(
            self.vocabulary.step_title, js_template_args['step_title'])
        self.assertEqual(
            'show-widget-field-teamowner', js_template_args['show_widget_id'])
        self.assertEqual(
            'field.teamowner', js_template_args['input_id'])
        self.assertEqual(
            None, js_template_args['extra_no_results_message'])
