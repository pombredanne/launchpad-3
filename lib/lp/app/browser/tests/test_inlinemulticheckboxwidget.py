# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the InlineMultiCheckboxWidget."""

__metaclass__ = type

import simplejson

from zope.interface import Interface
from zope.schema import List
from zope.schema._field import Choice
from zope.schema.vocabulary import getVocabularyRegistry

from lazr.enum import EnumeratedType, Item

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.browser.lazrjs import InlineMultiCheckboxWidget
from lp.testing import (
    TestCaseWithFactory,
    )


class Alphabet(EnumeratedType):
    """A vocabulary for testing."""
    A = Item("A", "Letter A")
    B = Item("B", "Letter B")

class TestInlineMultiCheckboxWidget(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def getWidget(self, **kwargs):
        class ITest(Interface):
            test_field = List(
                Choice(vocabulary='BuildableDistroSeries'))
        return InlineMultiCheckboxWidget(
                    None, ITest['test_field'], "Label", **kwargs)

    def test_items_for_field_vocabulary(self):
        widget = self.getWidget(attribute_type="reference")
        expected_items = []
        vocab = getVocabularyRegistry().get(None, 'BuildableDistroSeries')
        style = 'font-weight: normal;'
        for item in vocab:
            save_value = canonical_url(item.value, force_local_path=True)
            new_item = {
                'name': item.title,
                'token': item.token,
                'style': style,
                'checked': False,
                'value': save_value}
            expected_items.append(new_item)
        self.assertEqual(simplejson.dumps(expected_items), widget.json_items)

    def test_items_for_custom_vocabulary(self):
        widget = self.getWidget(vocabulary=Alphabet)
        expected_items = []
        style = 'font-weight: normal;'
        for item in Alphabet:
            new_item = {
                'name': item.title,
                'token': item.token,
                'style': style,
                'checked': False,
                'value': item.value.name}
            expected_items.append(new_item)
        self.assertEqual(simplejson.dumps(expected_items), widget.json_items)

    def test_selected_items_checked(self):
        widget = self.getWidget(
            vocabulary=Alphabet, selected_items=[Alphabet.A])
        expected_items = []
        style = 'font-weight: normal;'
        for item in Alphabet:
            new_item = {
                'name': item.title,
                'token': item.token,
                'style': style,
                'checked': item.value == Alphabet.A,
                'value': item.value.name}
            expected_items.append(new_item)
        self.assertEqual(simplejson.dumps(expected_items), widget.json_items)
