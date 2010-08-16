# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for `TranslationMessage`."""

__metaclass__ = type

from datetime import datetime, timedelta
from pytz import UTC

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.testing import verifyObject
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing import TestCaseWithFactory
from lp.translations.model.potranslation import POTranslation
from lp.translations.model.translationmessage import DummyTranslationMessage
from lp.translations.interfaces.side import ITranslationSideTraitsSet
from lp.translations.interfaces.translationmessage import (
    ITranslationMessage)
from lp.translations.interfaces.translations import TranslationConstants
from canonical.testing import ZopelessDatabaseLayer


class TestTranslationMessage(TestCaseWithFactory):
    """Unit tests for `TranslationMessage`.

    There aren't many of these.  We didn't do much unit testing back
    then.
    """

    layer = ZopelessDatabaseLayer

    def test_baseline(self):
        message = self.factory.makeTranslationMessage()
        verifyObject(ITranslationMessage, message)

    def test_dummy_translationmessage(self):
        pofile = self.factory.makePOFile('nl')
        potmsgset = self.factory.makePOTMsgSet(pofile.potemplate)
        dummy = DummyTranslationMessage(pofile, potmsgset)
        verifyObject(ITranslationMessage, dummy)

    def test_is_diverged_false(self):
        # ITranslationMessage.is_diverged is a little helper to let you
        # say "message.is_diverged" which can be clearer than
        # "message.potemplate is not None."
        message = self.factory.makeTranslationMessage(force_diverged=False)
        self.assertFalse(message.is_diverged)

    def test_is_diverged_true(self):
        message = self.factory.makeTranslationMessage(force_diverged=True)
        self.assertTrue(message.is_diverged)

    def test_markReviewed(self):
        message = self.factory.makeTranslationMessage()
        reviewer = self.factory.makePerson()
        tomorrow = datetime.now(UTC) + timedelta(days=1)

        message.markReviewed(reviewer, tomorrow)

        self.assertEqual(reviewer, message.reviewer)
        self.assertEqual(tomorrow, message.date_reviewed)


class TestApprove(TestCaseWithFactory):
    layer = ZopelessDatabaseLayer

    def test_approve_activates_message(self):
        pofile = self.factory.makePOFile('br')
        suggestion = self.factory.makeSharedTranslationMessage(
            pofile=pofile, suggestion=True)
        reviewer = self.factory.makePerson()
        self.assertFalse(suggestion.is_current_upstream)
        self.assertFalse(suggestion.is_current_ubuntu)

        suggestion.approve(pofile, reviewer)

        self.assertTrue(suggestion.is_current_upstream)
        self.assertFalse(suggestion.is_current_ubuntu)

    def test_approve_disables_incumbent_message(self):
        pofile, potmsgset = self.factory.makePOFileAndPOTMsgSet('te')
        suggestion = self.factory.makeSharedTranslationMessage(
            pofile=pofile, potmsgset=potmsgset, suggestion=True)
        incumbent_message = self.factory.makeCurrentTranslationMessage(
            pofile=pofile, potmsgset=potmsgset)

        self.assertTrue(incumbent_message.is_current_upstream)
        self.assertFalse(suggestion.is_current_upstream)

        suggestion.approve(pofile, self.factory.makePerson())

        self.assertFalse(incumbent_message.is_current_upstream)
        self.assertTrue(suggestion.is_current_upstream)

    def test_approve_ignores_current_message(self):
        pofile = self.factory.makePOFile('eu')
        translation = self.factory.makeCurrentTranslationMessage(
            pofile=pofile)
        submitter = translation.submitter
        original_reviewer = translation.reviewer
        new_reviewer = self.factory.makePerson()
        self.assertTrue(translation.is_current_upstream)
        self.assertFalse(translation.is_current_ubuntu)

        translation.approve(pofile, new_reviewer)

        # The message was already approved, so nothing changes.
        self.assertTrue(translation.is_current_upstream)
        self.assertFalse(translation.is_current_ubuntu)
        self.assertEqual(submitter, translation.submitter)
        self.assertEqual(original_reviewer, translation.reviewer)

    def test_approve_can_converge(self):
        pofile = self.factory.makePOFile('he')
        translations = [self.factory.getUniqueString()]
        reviewer = self.factory.makePerson()
        traits = getUtility(ITranslationSideTraitsSet).getTraits(
            pofile.potemplate.translation_side)

        diverged = self.factory.makeCurrentTranslationMessage(
            pofile=pofile, diverged=True)
        potmsgset = diverged.potmsgset
        shared = self.factory.makeCurrentTranslationMessage(
            pofile=pofile, potmsgset=potmsgset, translations=translations)

        shared.approve(pofile, reviewer)

        self.assertFalse(diverged.is_current_upstream)
        self.assertEqual(shared, traits.getCurrentMessage(
            potmsgset, pofile.potemplate, pofile.language))

    def test_approve_can_track_other_side(self):
        upstream_pofile = self.factory.makePOFile('ar')
        package = self.factory.makeSourcePackage()
        ubuntu_template = self.factory.makePOTemplate(
            sourcepackagename=package.sourcepackagename,
            distroseries=package.distroseries)
        ubuntu_pofile = self.factory.makePOFile(
            'ar', potemplate=ubuntu_template)
        other_side_message = self.factory.makeCurrentTranslationMessage(
            pofile=upstream_pofile)
        self.assertTrue(other_side_message.is_current_upstream)
        self.assertFalse(other_side_message.is_current_ubuntu)

        other_side_message.approve(ubuntu_pofile, self.factory.makePerson())

        self.assertTrue(other_side_message.is_current_upstream)
        self.assertTrue(other_side_message.is_current_ubuntu)

    def test_approve_can_make_other_side_track(self):
        pofile = self.factory.makePOFile('ki')
        suggestion = self.factory.makeSharedTranslationMessage(
            pofile=pofile, suggestion=True)
        reviewer = self.factory.makePerson()

        self.assertFalse(suggestion.is_current_upstream)
        self.assertFalse(suggestion.is_current_ubuntu)

        suggestion.approve(pofile, reviewer, share_with_other_side=True)

        self.assertTrue(suggestion.is_current_upstream)
        self.assertTrue(suggestion.is_current_ubuntu)

    def test_approve_marks_reviewed(self):
        pofile = self.factory.makePOFile('ko')
        suggestion = self.factory.makeSharedTranslationMessage(
            pofile=pofile, suggestion=True)
        reviewer = self.factory.makePerson()

        self.assertIs(None, suggestion.reviewer)
        self.assertIs(None, suggestion.date_reviewed)

        suggestion.approve(pofile, reviewer)

        self.assertEqual(reviewer, suggestion.reviewer)
        self.assertNotEqual(None, suggestion.date_reviewed)

    def test_approve_awards_no_karma_if_no_change(self):
        translator = self.factory.makePerson()
        reviewer = self.factory.makePerson()
        pofile = self.factory.makePOFile('ku')
        existing_translation = self.factory.makeCurrentTranslationMessage(
            pofile=pofile, translator=translator)

        karmarecorder = self.installKarmaRecorder()
        existing_translation.approve(pofile, reviewer)

        self.assertEqual([], karmarecorder.karma_events)

    def test_approve_awards_review_karma(self):
        reviewer = self.factory.makePerson()
        pofile = self.factory.makePOFile('be')
        suggestion = self.factory.makeSharedTranslationMessage(
            pofile=pofile, suggestion=True)

        karmarecorder = self.installKarmaRecorder(person=reviewer)
        suggestion.approve(pofile, reviewer)

        self.assertEqual(1, len(karmarecorder.karma_events))
        self.assertEqual(
            'translationreview', karmarecorder.karma_events[0].action.name)

    def test_approve_awards_suggestion_karma(self):
        translator = self.factory.makePerson()
        pofile = self.factory.makePOFile('ba')
        suggestion = self.factory.makeSharedTranslationMessage(
            pofile=pofile, translator=translator, suggestion=True)

        karmarecorder = self.installKarmaRecorder(person=translator)
        suggestion.approve(pofile, self.factory.makePerson())

        self.assertEqual(1, len(karmarecorder.karma_events))
        self.assertEqual(
            'translationsuggestionapproved',
            karmarecorder.karma_events[0].action.name)

    def test_approve_awards_no_karma_for_self_approval(self):
        translator = self.factory.makePerson()
        pofile = self.factory.makePOFile('bi')
        suggestion = self.factory.makeSharedTranslationMessage(
            pofile=pofile, translator=translator, suggestion=True)

        karmarecorder = self.installKarmaRecorder(person=translator)
        suggestion.approve(pofile, translator)

        self.assertEqual([], karmarecorder.karma_events)


class TestTranslationMessageFindIdenticalMessage(TestCaseWithFactory):
    """Tests for `TranslationMessage.findIdenticalMessage`."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        """Create common objects for all tests.

        Arranges for a `ProductSeries` with `POTemplate` and
        `POTMsgSet`, as well as a Dutch translation.  Also sets up
        another template in the same series with another template and
        potmsgset and translation.  The tests will modify the second
        translation message in various ways and then try to find it by
        calling findIdenticalMessage on the first one.
        """
        super(TestTranslationMessageFindIdenticalMessage, self).setUp()
        self.product = self.factory.makeProduct()
        self.trunk = self.product.getSeries('trunk')
        self.template = self.factory.makePOTemplate(
            productseries=self.trunk, name="shared")
        self.other_template = self.factory.makePOTemplate(
            productseries=self.trunk, name="other")
        self.potmsgset = self.factory.makePOTMsgSet(
            potemplate=self.template, singular='foo', plural='foos',
            sequence=1)
        self.other_potmsgset = self.factory.makePOTMsgSet(
            potemplate=self.other_template, singular='bar', plural='bars',
            sequence=1)
        self.pofile = self.factory.makePOFile(
            potemplate=self.template, language_code='nl')
        self.other_pofile = self.factory.makePOFile(
            potemplate=self.other_template, language_code='nl')

        self.translation_strings = [
            'foe%d' % form
            for form in xrange(TranslationConstants.MAX_PLURAL_FORMS)]

        self.message = self.factory.makeTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            translations=self.translation_strings)
        self.message.potemplate = self.template

        self.other_message = self.factory.makeTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.other_potmsgset,
            translations=self.translation_strings)
        self.other_message.potemplate = self.other_template

    def _getLanguage(self, code):
        """Convenience shortcut: find a language given its code."""
        languageset = getUtility(ILanguageSet)
        return languageset.getLanguageByCode(code)

    def _find(self, potmsgset, potemplate):
        """Convenience shortcut for self.message.findIdenticalMessage."""
        direct_message = removeSecurityProxy(self.message)
        return direct_message.findIdenticalMessage(potmsgset, potemplate)

    def _getPOTranslation(self, translation):
        """Retrieve or create a `POTranslation`."""
        return POTranslation.getOrCreateTranslation(translation)

    def test_findIdenticalMessageFindsIdenticalMessage(self):
        # Basic use of findIdenticalMessage: it finds identical
        # messages.
        # The other tests here are variations on this basic case, where
        # you'll see the effects of small differences in conditions on
        # the outcome.
        clone = self._find(self.other_potmsgset, self.other_template)
        self.assertEqual(clone, self.other_message)

    def test_findIdenticalMessageDoesNotFindSelf(self):
        # x.findIdenticalMessage(...) will never return x.
        find_self = self._find(self.potmsgset, self.template)
        self.assertEqual(find_self, None)

    def test_nullTemplateEqualsNullTemplate(self):
        # Shared messages can be equal.  The fact that NULL is not equal
        # to NULL in SQL does not confuse the comparison.
        self.message.potemplate = None
        self.other_message.potemplate = None
        clone = self._find(self.other_potmsgset, None)
        self.assertEqual(clone, self.other_message)

    def test_SharedMessageDoesNotMatchDivergedMessage(self):
        # When we're looking for a message for given template, we don't
        # get shared ones.
        self.other_message.potemplate = None
        nonclone = self._find(self.other_potmsgset, self.other_template)
        self.assertEqual(nonclone, None)

    def test_DivergedMessageDoesNotMatchSharedMessage(self):
        # When we're looking for a shared message, we don't get diverged
        # ones.
        nonclone = self._find(self.other_potmsgset, None)
        self.assertEqual(nonclone, None)

    def test_findIdenticalMessageChecksPOTMsgSet(self):
        # If another message has a different POTMsgSet than the one
        # we're looking for, it is not considered identical.
        nonclone = self._find(self.potmsgset, self.other_template)
        self.assertEqual(nonclone, None)

    def test_findIdenticalMessageChecksPOTemplate(self):
        # If another message has a different POTemplate than the one
        # we're looking for, it is not considered identical.
        nonclone = self._find(self.other_potmsgset, self.template)
        self.assertEqual(nonclone, None)

    def test_findIdenticalMessageChecksLanguage(self):
        # If another message has a different POTemplate than the one
        # we're looking for, it is not considered identical.
        self.other_message.language = self._getLanguage('el')
        nonclone = self._find(self.other_potmsgset, self.other_template)
        self.assertEqual(nonclone, None)

    def test_findIdenticalMessageChecksFirstForm(self):
        # Messages with different translations are not identical.
        self.other_message.msgstr0 = self._getPOTranslation('xyz')
        nonclone = self._find(self.other_potmsgset, self.other_template)
        self.assertEqual(nonclone, None)

    def test_findIdenticalMessageChecksLastForm(self):
        # All plural forms of the messages' translations are compared,
        # up to and including the highest form supported.
        last_form = 'msgstr%d' % (TranslationConstants.MAX_PLURAL_FORMS - 1)
        translation = self._getPOTranslation('zyx')
        setattr(self.other_message, last_form, translation)
        nonclone = self._find(self.other_potmsgset, self.other_template)
        self.assertEqual(nonclone, None)
