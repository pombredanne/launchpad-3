# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import simplejson
from zope.schema.vocabulary import getVocabularyRegistry

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.widgets.popup import VocabularyPickerWidget
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

    def test_widget_template_properties(self):
        picker_widget = VocabularyPickerWidget(
            self.bound_field, self.vocabulary, self.request)
        self.assertEqual(
            'ValidTeamOwner', picker_widget.vocabulary_name)
        self.assertEqual(
            simplejson.dumps(self.vocabulary.displayname),
            picker_widget.header_text)
        self.assertEqual(
            simplejson.dumps(self.vocabulary.step_title),
            picker_widget.step_title_text)
        self.assertEqual(
            'show-widget-field-teamowner', picker_widget.show_widget_id)
        self.assertEqual(
            'field.teamowner', picker_widget.input_id)
        self.assertEqual(
            simplejson.dumps(None), picker_widget.extra_no_results_message)
