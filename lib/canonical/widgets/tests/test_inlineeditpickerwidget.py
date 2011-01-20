# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the InlineEditPickerWidget."""

__metaclass__ = type

from zope.interface import Interface
from zope.schema import Choice

from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.widgets.lazrjs import InlineEditPickerWidget
from lp.testing import (
    ANONYMOUS,
    login,
    TestCase,
    )


class TestInlineEditPickerWidget(TestCase):

    layer = DatabaseFunctionalLayer

    def test_huge_vocabulary_is_searchable(self):
        # Make sure that when given a field for a huge vocabulary, the picker
        # is set to show the search box.
        class ITest(Interface):
            test_field = Choice(vocabulary='ValidPersonOrTeam')
        login(ANONYMOUS)
        widget = InlineEditPickerWidget(
            None, None, ITest['test_field'], None)
        self.assertTrue(widget.show_search_box)

    def test_normal_vocabulary_is_not_searchable(self):
        # Make sure that when given a field for a normal vocabulary, the picker
        # is set to show the search box.
        class ITest(Interface):
            test_field = Choice(vocabulary='UserTeamsParticipation')
        login(ANONYMOUS)
        widget = InlineEditPickerWidget(
            None, None, ITest['test_field'], None)
        self.assertFalse(widget.show_search_box)
