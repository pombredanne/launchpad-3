# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from datetime import datetime, timedelta
import pytz
from unittest import TestLoader

from canonical.launchpad.browser.translationmessage import (
    CurrentTranslationMessageView)
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import LaunchpadZopelessLayer
from lp.testing import TestCaseWithFactory


class TestCurrentTranslationMessage_can_dismiss(TestCaseWithFactory):
    """Test the can_dismiss_* properties of CurrentTranslationMessageView."""

    layer = LaunchpadZopelessLayer

    def _gen_now(self):
        now = datetime.now(pytz.UTC)
        while True:
            yield now
            now += timedelta(milliseconds=1)

    def setUp(self):
        super(TestCurrentTranslationMessage_can_dismiss, self).setUp()
        self.owner = self.factory.makePerson()
        self.potemplate = self.factory.makePOTemplate(owner=self.owner)
        self.pofile = self.factory.makePOFile('eo',
                                              potemplate=self.potemplate)
        self.potmsgset = self.factory.makePOTMsgSet(self.potemplate)
        self.view = None
        self.now = self._gen_now().next

    def _createView(self, message):
        self.view = CurrentTranslationMessageView(
            message, LaunchpadTestRequest(),
            {}, dict(enumerate(message.translations)),
            False, None, None, True)
        self.view.user_is_official_translator = True
        self.view.initialize()

    def _makeTranslation(self, translation=None,
                         suggestion=False, is_imported=False):
        if translation is None:
            translations = None
        elif isinstance(translation, list):
            translations = translation
        else:
            translations = [translation]
        message = self.factory.makeTranslationMessage(
            self.pofile, self.potmsgset,
            translations=translations,
            suggestion=suggestion,
            is_imported=is_imported,
            translator=self.owner,
            date_updated=self.now())
        message.browser_pofile = self.pofile
        return message

    def _assertConfirmEmptyPlural(self, can_confirm_and_dismiss,
                         can_dismiss_on_empty,
                         can_dismiss_on_plural):
        assert self.view is not None
        self.assertEqual(
            [can_confirm_and_dismiss,
               can_dismiss_on_empty,
               can_dismiss_on_plural],
            [self.view.can_confirm_and_dismiss,
               self.view.can_dismiss_on_empty,
               self.view.can_dismiss_on_plural])

    def test_no_suggestion(self):
        # If there is no suggestion, nothing can be dismissed.
        message = self._makeTranslation()
        self._createView(message)
        self._assertConfirmEmptyPlural(False, False, False)

    def test_local_suggestion(self):
        # If there is a local suggestion, it can be dismissed.
        message = self._makeTranslation()
        suggestion = self._makeTranslation(suggestion=True)
        self._createView(message)
        self._assertConfirmEmptyPlural(True, False, False)

    def test_local_suggestion_on_empty(self):
        # If there is a local suggestion on an empty message, it is dismissed
        # in a different place.
        message = self._makeTranslation("")
        suggestion = self._makeTranslation(suggestion=True)
        self._createView(message)
        self._assertConfirmEmptyPlural(False, True, False)

    def test_local_suggestion_on_plural(self):
        # If there is a suggestion on a plural message, it is dismissed
        # in yet a different place.
        self.potmsgset = self.factory.makePOTMsgSet(self.potemplate,
                singular="msgid_singular", plural="msgid_plural")
        message = self._makeTranslation(["singular_trans", "plural_trans"])
        suggestion = self._makeTranslation(["singular_sugg", "plural_sugg"],
                                         suggestion=True)
        self._createView(message)
        self._assertConfirmEmptyPlural(False, False, True)

    def test_imported_suggestion(self):
        # If there is an imported suggestion, it can be dismissed.
        packaged = self._makeTranslation(is_imported=True)
        message = self._makeTranslation()
        new_packaged = self._makeTranslation(is_imported=True)
        self._createView(message)
        self._assertConfirmEmptyPlural(True, False, False)

    def test_imported_suggestion_on_empty(self):
        # If there is an empty suggestion on an empty message,
        # it is dismissed in a different place.
        packaged = self._makeTranslation(is_imported=True)
        message = self._makeTranslation("")
        new_packaged = self._makeTranslation(is_imported=True)
        self._createView(message)
        self._assertConfirmEmptyPlural(False, True, False)

    def test_imported_suggestion_on_plural(self):
        # If there is a suggestion on a plural message, it is dismissed
        # in yet a different place.
        self.potmsgset = self.factory.makePOTMsgSet(self.potemplate,
                singular="msgid_singular", plural="msgid_plural")
        packaged = self._makeTranslation(["singular_trans", "plural_trans"],
                                         is_imported=True)
        message = self._makeTranslation(["singular_trans", "plural_trans"])
        new_packaged = self._makeTranslation(["singular_new", "plural_new"],
                                             is_imported=True)
        self._createView(message)
        self._assertConfirmEmptyPlural(False, False, True)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
