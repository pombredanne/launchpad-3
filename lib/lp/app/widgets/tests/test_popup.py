# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
from zope.interface.interface import InterfaceClass

__metaclass__ = type

import simplejson
from zope.interface import Interface
from zope.schema import Choice
from zope.schema.vocabulary import getVocabularyRegistry

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.widgets.popup import VocabularyPickerWidget
from lp.testing import TestCaseWithFactory


class TestVocabularyPickerWidget(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestVocabularyPickerWidget, self).setUp()

        # We want to force creation of a field with an invalid HTML id.
        class TestMetaClass(InterfaceClass):
            def __init__(self, name, bases=(), attrs=None, __doc__=None,
                         __module__=None):
                attrs = {"test_field+": Choice(vocabulary='ValidTeamOwner')}
                super(TestMetaClass, self).__init__(
                    name, bases=bases, attrs=attrs, __doc__=__doc__,
                    __module__=__module__)

        # The schema class for the widget.
        class ITest(Interface):
            __metaclass__ = TestMetaClass

        context = self.factory.makeTeam()
        field = ITest['test_field+']
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
        # The widget name is encoded to get the widget's ID. It must only
        # contain valid HTML characters.
        self.assertEqual(
            'show-widget-field-test_field', picker_widget.show_widget_id)
        self.assertEqual(
            'field.test_field+', picker_widget.input_id)
        self.assertEqual(
            simplejson.dumps(None), picker_widget.extra_no_results_message)
