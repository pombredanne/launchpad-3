# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import datetime, timedelta
import pytz
from unittest import TestLoader

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import LaunchpadZopelessLayer
from lp.testing import TestCaseWithFactory
from lp.translations.browser.pofile import POFileBaseView


class TestPOFileBaseView(TestCaseWithFactory):
    """Test POFileBaseView."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestPOFileBaseView, self).setUp()
        self.potemplate = self.factory.makePOTemplate()
        self.pofile = self.factory.makePOFile('eo', self.potemplate)



class TestPOFileBaseViewFiltering(TestCaseWithFactory):
    """Test POFileBaseView filtering functions."""

    layer = LaunchpadZopelessLayer

    def gen_now(self):
        now = datetime.now(pytz.UTC)
        while True:
            yield now
            now += timedelta(milliseconds=1)

    def setUp(self):
        super(TestPOFileBaseViewFiltering, self).setUp()
        self.now = self.gen_now().next
        self.potemplate = self.factory.makePOTemplate()
        self.pofile = self.factory.makePOFile('eo', self.potemplate)

        # Create a number of POTMsgsets in different states.
        # An untranslated message.
        self.untranslated = self.factory.makePOTMsgSet(
            self.potemplate, sequence=1)
        # A translated message.
        self.translated = self.factory.makePOTMsgSet(
            self.potemplate, sequence=2)
        self.factory.makeTranslationMessage(self.pofile, self.translated)
        # A translated message with a new suggestion.
        self.new_suggestion = self.factory.makePOTMsgSet(
            self.potemplate, sequence=3)
        self.factory.makeTranslationMessage(
            self.pofile, self.new_suggestion,
            date_updated=self.now())
        self.factory.makeTranslationMessage(
            self.pofile, self.new_suggestion, suggestion=True,
            date_updated=self.now())
        # An imported that was changed in Launchpad.
        self.changed = self.factory.makePOTMsgSet(
            self.potemplate, sequence=4)
        self.factory.makeTranslationMessage(
            self.pofile, self.changed, is_imported=True,
            date_updated=self.now())
        self.factory.makeTranslationMessage(
            self.pofile, self.changed,
            date_updated=self.now())

        # Update statistics so that shown_count returns correct values.
        self.pofile.updateStatistics()

    def _assertEqualPOTMsgSets(self, expected, messages):
        self.assertEqual(expected, [tm.potmsgset for tm in messages])

    def test_show_all_messages(self):
        # The default is to show all messages.
        view = POFileBaseView(self.pofile, LaunchpadTestRequest())
        view.initialize()
        self.assertEqual('all', view.DEFAULT_SHOW)
        self.assertEqual(view.DEFAULT_SHOW, view.show)
        self.assertEqual(4, view.shown_count)
        self._assertEqualPOTMsgSets(
            [self.untranslated, self.translated,
             self.new_suggestion, self.changed],
            view.messages)

    def test_show_translated(self):
        form = {'show': 'translated'}
        view = POFileBaseView(self.pofile, LaunchpadTestRequest(form=form))
        view.initialize()
        self.assertEqual(3, view.shown_count)
        self._assertEqualPOTMsgSets(
            [self.translated, self.new_suggestion, self.changed],
            view.messages)

    def test_show_untranslated(self):
        form = {'show': 'untranslated'}
        view = POFileBaseView(self.pofile, LaunchpadTestRequest(form=form))
        view.initialize()
        self.assertEqual(1, view.shown_count)
        self._assertEqualPOTMsgSets([self.untranslated], view.messages)

    def test_show_new_suggestions(self):
        form = {'show': 'new_suggestions'}
        view = POFileBaseView(self.pofile, LaunchpadTestRequest(form=form))
        view.initialize()
        self.assertEqual(1, view.shown_count)
        self._assertEqualPOTMsgSets([self.new_suggestion], view.messages)

    def test_show_changed_in_launchpad(self):
        form = {'show': 'changed_in_launchpad'}
        view = POFileBaseView(self.pofile, LaunchpadTestRequest(form=form))
        view.initialize()
        self.assertEqual(1, view.shown_count)
        self._assertEqualPOTMsgSets(
             [self.changed], view.messages)

    def test_show_invalid_filter(self):
        # Invalid filter strings default to showing all messages.
        form = {'show': 'foo_bar'}
        view = POFileBaseView(self.pofile, LaunchpadTestRequest(form=form))
        view.initialize()
        self.assertEqual(view.DEFAULT_SHOW, view.show)
        self._assertEqualPOTMsgSets(
            [self.untranslated, self.translated,
             self.new_suggestion, self.changed],
            view.messages)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

