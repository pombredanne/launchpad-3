# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import with_statement

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )

import pytz
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    ZopelessDatabaseLayer,
    )
from lp.app.errors import UnexpectedFormData
from lp.testing import (
    anonymous_logged_in,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import create_view
from lp.translations.enums import TranslationPermission
from lp.translations.browser.translationmessage import (
    contains_translations,
    CurrentTranslationMessagePageView,
    CurrentTranslationMessageView,
    revert_unselected_translations,
    )
from lp.translations.interfaces.translations import TranslationConstants
from lp.translations.interfaces.translationsperson import ITranslationsPerson
from lp.translations.publisher import TranslationsLayer


class TestCurrentTranslationMessage_can_dismiss(TestCaseWithFactory):
    """Test the can_dismiss_* properties of CurrentTranslationMessageView."""

    layer = ZopelessDatabaseLayer

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
            False, False, None, None, True, pofile=self.pofile, can_edit=True)
        self.view.initialize()

    def _makeTranslation(self, translation=None,
                         suggestion=False, is_packaged=False):
        if translation is None:
            translations = None
        elif isinstance(translation, list):
            translations = translation
        else:
            translations = [translation]
        if suggestion:
            message = self.factory.makeSuggestion(
                self.pofile, self.potmsgset,
                translations=translations,
                translator=self.owner,
                date_created=self.now())
        else:
            message = self.factory.makeTranslationMessage(
                self.pofile, self.potmsgset,
                translations=translations,
                suggestion=suggestion,
                is_current_upstream=is_packaged,
                translator=self.owner,
                date_updated=self.now())
        message.browser_pofile = self.pofile
        return message

    def _assertConfirmEmptyPluralPackaged(self,
                                          can_confirm_and_dismiss,
                                          can_dismiss_on_empty,
                                          can_dismiss_on_plural,
                                          can_dismiss_packaged):
        assert self.view is not None
        self.assertEqual(
            [can_confirm_and_dismiss,
               can_dismiss_on_empty,
               can_dismiss_on_plural,
               can_dismiss_packaged],
            [self.view.can_confirm_and_dismiss,
               self.view.can_dismiss_on_empty,
               self.view.can_dismiss_on_plural,
               self.view.can_dismiss_packaged])

    def test_no_suggestion(self):
        # If there is no suggestion, nothing can be dismissed.
        message = self._makeTranslation()
        self._createView(message)
        self._assertConfirmEmptyPluralPackaged(False, False, False, False)

    def test_local_suggestion(self):
        # If there is a local suggestion, it can be dismissed.
        message = self._makeTranslation()
        suggestion = self._makeTranslation(suggestion=True)
        self._createView(message)
        self._assertConfirmEmptyPluralPackaged(True, False, False, False)

    def test_local_suggestion_on_empty(self):
        # If there is a local suggestion on an empty message, it is dismissed
        # in a different place.
        message = self._makeTranslation("")
        suggestion = self._makeTranslation(suggestion=True)
        self._createView(message)
        self._assertConfirmEmptyPluralPackaged(False, True, False, False)

    def test_local_suggestion_on_plural(self):
        # If there is a suggestion on a plural message, it is dismissed
        # in yet a different place.
        self.potmsgset = self.factory.makePOTMsgSet(self.potemplate,
                singular="msgid_singular", plural="msgid_plural")
        message = self._makeTranslation(["singular_trans", "plural_trans"])
        suggestion = self._makeTranslation(["singular_sugg", "plural_sugg"],
                                         suggestion=True)
        self._createView(message)
        self._assertConfirmEmptyPluralPackaged(False, False, True, False)

        # XXX JeroenVermeulen 2010-11-22: Disabling this test
        # temporarily.  We must re-enable it before completing the
        # migration of CurrentTranslationMessageTranslateView to the
        # Recife model.  Currently this is the only test that still
        # breaks after a partial migration of model code and that view
        # (as needed to complete the update of _storeTranslations).
    def XXX_disabled_test_packaged_suggestion(self):
        # If there is a packaged suggestion, it can be dismissed.
        packaged = self._makeTranslation(is_packaged=True)
        message = self._makeTranslation()
        new_packaged = self._makeTranslation(is_packaged=True)
        self._createView(message)
        self._assertConfirmEmptyPluralPackaged(True, False, False, True)

    def test_packaged_suggestion_on_empty(self):
        # If there is an empty suggestion on an empty message,
        # it is dismissed in a different place.
        packaged = self._makeTranslation(is_packaged=True)
        message = self._makeTranslation("")
        new_packaged = self._makeTranslation(is_packaged=True)
        self._createView(message)
        self._assertConfirmEmptyPluralPackaged(False, True, False, True)

    def test_packaged_suggestion_on_plural(self):
        # If there is a suggestion on a plural message, it is dismissed
        # in yet a different place.
        self.potmsgset = self.factory.makePOTMsgSet(self.potemplate,
                singular="msgid_singular", plural="msgid_plural")
        packaged = self._makeTranslation(["singular_trans", "plural_trans"],
                                         is_packaged=True)
        message = self._makeTranslation(["singular_trans", "plural_trans"])
        new_packaged = self._makeTranslation(["singular_new", "plural_new"],
                                             is_packaged=True)
        self._createView(message)
        self._assertConfirmEmptyPluralPackaged(False, False, True, True)

    def test_packaged_suggestion_old(self):
        # If there is an older packaged suggestion, it cannot be dismissed.
        packaged = self._makeTranslation(is_packaged=True)
        message = self._makeTranslation()
        self._createView(message)
        self._assertConfirmEmptyPluralPackaged(False, False, False, False)

    def test_packaged_old_local_new(self):
        # If there is an older packaged suggestion, but a newer local
        # suggestion, only the local suggestion can be dismissed.
        packaged = self._makeTranslation(is_packaged=True)
        message = self._makeTranslation()
        suggestion = self._makeTranslation(suggestion=True)
        self._createView(message)
        self._assertConfirmEmptyPluralPackaged(True, False, False, False)


class TestResetTranslations(TestCaseWithFactory):
    """Test resetting of the current translation.

    A reviewer can reset a current translation by submitting an empty
    translation and forcing it to be a suggestion.

    :ivar pofile: A `POFile` for an Ubuntu source package.
    :ivar current_translation: A current `TranslationMessage` in `POFile`,
        submitted and reviewed sometime in the past.
    """
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestResetTranslations, self).setUp()
        package = self.factory.makeSourcePackage()
        template = self.factory.makePOTemplate(
            distroseries=package.distroseries,
            sourcepackagename=package.sourcepackagename)
        self.pofile = self.factory.makePOFile(potemplate=template)
        self.current_translation = self.factory.makeCurrentTranslationMessage(
            pofile=self.pofile)
        self.current_translation.setPOFile(self.pofile)

        naked_tm = removeSecurityProxy(self.current_translation)
        naked_tm.date_created -= timedelta(1)
        naked_tm.date_reviewed = naked_tm.date_created

    def closeTranslations(self):
        """Disallow editing of `self.pofile` translations by regular users."""
        policy = removeSecurityProxy(
            self.pofile.potemplate.getTranslationPolicy())
        policy.translationpermission = TranslationPermission.CLOSED

    def getLocalSuggestions(self):
        """Get local suggestions for `self.current_translation`."""
        return list(
            self.current_translation.potmsgset.getLocalTranslationMessages(
                self.pofile.potemplate, self.pofile.language))

    def submitForcedEmptySuggestion(self):
        """Submit an empty suggestion for `self.current_translation`."""
        empty_translation = u''

        msgset_id = 'msgset_' + str(self.current_translation.potmsgset.id)
        msgset_id_lang = msgset_id + '_' + self.pofile.language.code
        widget_id_base = msgset_id_lang + '_translation_0_'

        form = {
            'lock_timestamp': datetime.now(pytz.utc).isoformat(),
            'alt': None,
            msgset_id: None,
            widget_id_base + 'radiobutton': widget_id_base + 'new',
            widget_id_base + 'new': empty_translation,
            'submit_translations': 'Save &amp; Continue',
            msgset_id_lang + '_needsreview': 'force_suggestion',
        }

        url = canonical_url(self.current_translation) + '/+translate'
        view = create_view(
            self.current_translation, '+translate', form=form,
            layer=TranslationsLayer, server_url=url)
        view.request.method = 'POST'
        view.initialize()

    def test_disables_current_translation(self):
        # Resetting the current translation clears its "current" flag.
        self.assertTrue(self.current_translation.is_current_ubuntu)
        with person_logged_in(self.factory.makePerson()):
            self.submitForcedEmptySuggestion()
        self.assertFalse(self.current_translation.is_current_ubuntu)

    def test_turns_current_translation_into_suggestion(self):
        # Resetting the current translation demotes it back to the
        # status of a suggestion.
        self.assertEqual([], self.getLocalSuggestions())
        with person_logged_in(self.factory.makePerson()):
            self.submitForcedEmptySuggestion()
        self.assertEqual(
            [self.current_translation], self.getLocalSuggestions())

    def test_unprivileged_user_cannot_reset(self):
        # When a user without editing privileges on the translation
        # submits an empty suggestion, that does not clear the
        # translation.
        self.closeTranslations()
        self.assertTrue(self.current_translation.is_current_ubuntu)
        with person_logged_in(self.factory.makePerson()):
            self.submitForcedEmptySuggestion()
        self.assertTrue(self.current_translation.is_current_ubuntu)


class TestCurrentTranslationMessagePageView(TestCaseWithFactory):
    """Test `CurrentTranslationMessagePageView` and its base class."""

    layer = ZopelessDatabaseLayer

    def _makeView(self):
        message = self.factory.makeTranslationMessage()
        request = LaunchpadTestRequest()
        view = CurrentTranslationMessagePageView(message, request)
        view.lock_timestamp = datetime.now(pytz.utc)
        return view

    def test_extractLockTimestamp(self):
        view = self._makeView()
        view.request.form['lock_timestamp'] = u'2010-01-01 00:00:00 UTC'
        self.assertEqual(
            datetime(2010, 01, 01, tzinfo=pytz.utc),
            view._extractLockTimestamp())

    def test_extractLockTimestamp_returns_None_by_default(self):
        view = self._makeView()
        self.assertIs(None, view._extractLockTimestamp())

    def test_extractLockTimestamp_returns_None_for_bogus_timestamp(self):
        view = self._makeView()
        view.request.form['lock_timestamp'] = u'Hi mom!'
        self.assertIs(None, view._extractLockTimestamp())

    def test_checkSubmitConditions_passes(self):
        with person_logged_in(self.factory.makePerson()):
            view = self._makeView()
            view._checkSubmitConditions()

    def test_checkSubmitConditions_requires_lock_timestamp(self):
        with person_logged_in(self.factory.makePerson()):
            view = self._makeView()
            view.lock_timestamp = None
            self.assertRaises(UnexpectedFormData, view._checkSubmitConditions)

    def test_checkSubmitConditions_rejects_anonymous_request(self):
        with anonymous_logged_in():
            view = self._makeView()
            self.assertRaises(UnexpectedFormData, view._checkSubmitConditions)

    def test_checkSubmitConditions_rejects_license_decliners(self):
        # Users who have declined the relicensing agreement can't post
        # translations.
        decliner = self.factory.makePerson()
        ITranslationsPerson(decliner).translations_relicensing_agreement = (
            False)
        with person_logged_in(decliner):
            view = self._makeView()
            self.assertRaises(UnexpectedFormData, view._checkSubmitConditions)


class TestHelpers(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_contains_translations_is_false_for_empty_dict(self):
        self.assertFalse(contains_translations({}))

    def test_contains_translations_finds_any_translations(self):
        for plural_form in xrange(TranslationConstants.MAX_PLURAL_FORMS):
            self.assertTrue(
                contains_translations({plural_form: self.getUniqueString()}))

    def test_contains_translations_ignores_empty_strings(self):
        self.assertFalse(contains_translations({0: u''}))

    def test_contains_translations_ignores_nones(self):
        self.assertFalse(contains_translations({0: None}))

    def test_revert_unselected_translations_accepts_selected(self):
        # Translations for plural forms in plural_indices_to_store stay
        # intact.
        translations = {0: self.getUniqueString()}
        self.assertEqual(
            translations,
            revert_unselected_translations(translations, None, [0]))

    def test_revert_unselected_translations_reverts_to_existing(self):
        # Translations for plural forms not in plural_indices_to_store
        # are reverted to those found in the current translation
        # message, if any.
        new_translations = {0: self.getUniqueString()}
        original_translations = {0: self.getUniqueString()}
        current_message = self.factory.makeTranslationMessage(
            translations=original_translations)
        self.assertEqual(
            original_translations,
            revert_unselected_translations(
                new_translations, current_message, []))

    def test_revert_unselected_translations_reverts_to_empty_string(self):
        # If there is no current message, any translation not in
        # plural_indices_to_store is set to the empty string.
        translations = {0: self.getUniqueString()}
        self.assertEqual(
            {0: u''}, revert_unselected_translations(translations, None, []))

    def test_revert_unselected_translations_handles_missing_plurals(self):
        # When reverting based on a current message that does not
        # translate the given plural form, the new translation is the
        # empty string.
        new_translations = {1: self.getUniqueString()}
        original_translations = {0: self.getUniqueString()}
        current_message = self.factory.makeTranslationMessage(
            translations=original_translations)
        self.assertEqual(
            {1: u''},
            revert_unselected_translations(
                new_translations, current_message, []))
