# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for `TranslationMessage`."""

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )

from pytz import UTC
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing.layers import ZopelessDatabaseLayer
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.side import (
    ITranslationSideTraitsSet,
    TranslationSide,
    )
from lp.translations.interfaces.translationmessage import (
    ITranslationMessage,
    TranslationConflict,
    )
from lp.translations.interfaces.translations import TranslationConstants
from lp.translations.model.potranslation import POTranslation
from lp.translations.model.translationmessage import DummyTranslationMessage


class TestTranslationMessage(TestCaseWithFactory):
    """Unit tests for `TranslationMessage`.

    There aren't many of these.  We didn't do much unit testing back
    then.
    """

    layer = ZopelessDatabaseLayer

    def test_baseline(self):
        message = self.factory.makeCurrentTranslationMessage()
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
        message = self.factory.makeCurrentTranslationMessage(diverged=False)
        self.assertFalse(message.is_diverged)

    def test_is_diverged_true(self):
        message = self.factory.makeCurrentTranslationMessage(diverged=True)
        self.assertTrue(message.is_diverged)

    def test_markReviewed(self):
        message = self.factory.makeCurrentTranslationMessage()
        reviewer = self.factory.makePerson()
        tomorrow = datetime.now(UTC) + timedelta(days=1)

        message.markReviewed(reviewer, tomorrow)

        self.assertEqual(reviewer, message.reviewer)
        self.assertEqual(tomorrow, message.date_reviewed)


class TestApprove(TestCaseWithFactory):
    """Tests for `TranslationMessage.approve`."""

    layer = ZopelessDatabaseLayer

    def test_approve_activates_message(self):
        # Simple, basic, suggestion approval: a message is untranslated.
        # There is a suggestion for it.  The suggestion gets approved,
        # and thereby becomes the message's current translation.
        pofile = self.factory.makePOFile('br')
        suggestion = self.factory.makeSuggestion(pofile=pofile)
        reviewer = self.factory.makePerson()
        self.assertFalse(suggestion.is_current_upstream)
        self.assertFalse(suggestion.is_current_ubuntu)

        suggestion.approve(pofile, reviewer)

        # By default the suggestion becomes current only on the side
        # (upstream or Ubuntu) that it's being approved on.
        self.assertTrue(suggestion.is_current_upstream)
        self.assertFalse(suggestion.is_current_ubuntu)

    def test_approve_disables_incumbent_message(self):
        # If there was already a current translation, it is disabled
        # when a suggestion is approved.
        pofile, potmsgset = self.factory.makePOFileAndPOTMsgSet('te')
        suggestion = self.factory.makeSuggestion(
            pofile=pofile, potmsgset=potmsgset)
        incumbent_message = self.factory.makeCurrentTranslationMessage(
            pofile=pofile, potmsgset=potmsgset)

        self.assertTrue(incumbent_message.is_current_upstream)
        self.assertFalse(suggestion.is_current_upstream)

        suggestion.approve(pofile, self.factory.makePerson())

        self.assertFalse(incumbent_message.is_current_upstream)
        self.assertTrue(suggestion.is_current_upstream)

    def test_approve_ignores_current_message(self):
        # Approving a message that's already current does nothing.
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
        # If a diverged message is masking a shared one, approving the
        # shared one disables the diverged message and so "converges"
        # with the shared translation.
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
        # Approving the translation message that's already current on
        # the other side converges the upstream and Ubuntu translations.
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
        # In some situations (see POTMsgSet.setCurrentTranslation for
        # details) the approval can be made to propagate to the other
        # side, subject to the share_with_other_side parameter.
        pofile = self.factory.makePOFile('ki')
        suggestion = self.factory.makeSuggestion(pofile=pofile)
        reviewer = self.factory.makePerson()

        self.assertFalse(suggestion.is_current_upstream)
        self.assertFalse(suggestion.is_current_ubuntu)

        suggestion.approve(pofile, reviewer, share_with_other_side=True)

        self.assertTrue(suggestion.is_current_upstream)
        self.assertTrue(suggestion.is_current_ubuntu)

    def test_approve_marks_reviewed(self):
        # Approving a suggestion updates its review fields.
        pofile = self.factory.makePOFile('ko')
        suggestion = self.factory.makeSuggestion(pofile=pofile)
        reviewer = self.factory.makePerson()

        self.assertIs(None, suggestion.reviewer)
        self.assertIs(None, suggestion.date_reviewed)

        suggestion.approve(pofile, reviewer)

        self.assertEqual(reviewer, suggestion.reviewer)
        self.assertNotEqual(None, suggestion.date_reviewed)

    def test_approve_awards_no_karma_if_no_change(self):
        # Approving an already current message generates no karma.
        translator = self.factory.makePerson()
        reviewer = self.factory.makePerson()
        pofile = self.factory.makePOFile('ku')
        existing_translation = self.factory.makeCurrentTranslationMessage(
            pofile=pofile, translator=translator)

        karmarecorder = self.installKarmaRecorder()
        existing_translation.approve(pofile, reviewer)

        self.assertEqual([], karmarecorder.karma_events)

    def test_approve_awards_review_karma(self):
        # A reviewer receives karma for approving suggestions.
        reviewer = self.factory.makePerson()
        pofile = self.factory.makePOFile('be')
        suggestion = self.factory.makeSuggestion(pofile=pofile)

        karmarecorder = self.installKarmaRecorder(person=reviewer)
        suggestion.approve(pofile, reviewer)

        self.assertEqual(1, len(karmarecorder.karma_events))
        self.assertEqual(
            'translationreview', karmarecorder.karma_events[0].action.name)

    def test_approve_awards_suggestion_karma(self):
        # A translator receives karma for suggestions that are approved.
        translator = self.factory.makePerson()
        pofile = self.factory.makePOFile('ba')
        suggestion = self.factory.makeSuggestion(
            pofile=pofile, translator=translator)

        karmarecorder = self.installKarmaRecorder(person=translator)
        suggestion.approve(pofile, self.factory.makePerson())

        self.assertEqual(1, len(karmarecorder.karma_events))
        self.assertEqual(
            'translationsuggestionapproved',
            karmarecorder.karma_events[0].action.name)

    def test_approve_awards_no_karma_for_self_approval(self):
        # A reviewer receives no karma for approving their own
        # suggestion.
        translator = self.factory.makePerson()
        pofile = self.factory.makePOFile('bi')
        suggestion = self.factory.makeSuggestion(
            pofile=pofile, translator=translator)

        karmarecorder = self.installKarmaRecorder(person=translator)
        suggestion.approve(pofile, translator)

        self.assertEqual([], karmarecorder.karma_events)

    def test_approve_detects_conflict(self):
        pofile = self.factory.makePOFile('bo')
        current = self.factory.makeCurrentTranslationMessage(pofile=pofile)
        potmsgset = current.potmsgset
        suggestion = self.factory.makeSuggestion(
            pofile=pofile, potmsgset=potmsgset)
        old = datetime.now(UTC) - timedelta(days=1)

        self.assertRaises(
            TranslationConflict,
            suggestion.approve,
            pofile, self.factory.makePerson(), lock_timestamp=old)

    def test_approve_clones_message_from_other_side_to_diverge(self):
        package = self.factory.makeSourcePackage()
        template=self.factory.makePOTemplate(
            distroseries=package.distroseries,
            sourcepackagename=package.sourcepackagename)
        potmsgset = self.factory.makePOTMsgSet(potemplate=template)
        upstream_pofile = self.factory.makePOFile('nl')
        ubuntu_pofile = self.factory.makePOFile('nl', potemplate=template)
        diverged_tm = self.factory.makeDivergedTranslationMessage(
            pofile=upstream_pofile, potmsgset=potmsgset)
        ubuntu_tm = self.factory.makeSuggestion(
            pofile=ubuntu_pofile, potmsgset=potmsgset)
        ubuntu_tm.is_current_ubuntu = True

        ubuntu_tm.approve(upstream_pofile, self.factory.makePerson())

        upstream_tm = potmsgset.getCurrentTranslation(
            upstream_pofile.potemplate, upstream_pofile.language,
            TranslationSide.UPSTREAM)
        self.assertEqual(ubuntu_tm.all_msgstrs, upstream_tm.all_msgstrs)
        self.assertNotEqual(ubuntu_tm, upstream_tm)


class TestAcceptAsImported(TestCaseWithFactory):
    """Tests for `TranslationMessage.acceptAsImported`.

    This method is a lot like `TranslationMessage.approve`, so this test
    mainly exercises what it does differently.
    """

    layer = ZopelessDatabaseLayer

    def test_accept_activates_message(self):
        # An untranslated message receives an imported translation.
        pofile = self.factory.makePOFile()
        suggestion = self.factory.makeSuggestion(pofile=pofile)
        reviewer = self.factory.makePerson()
        self.assertFalse(suggestion.is_current_upstream)
        self.assertFalse(suggestion.is_current_ubuntu)

        suggestion.acceptAsImported(pofile)

        # By default the suggestion becomes current only on the side
        # (upstream or Ubuntu) that it's being approved on.
        self.assertTrue(suggestion.is_current_upstream)
        self.assertFalse(suggestion.is_current_ubuntu)

    def test_accept_can_make_other_side_track(self):
        # In some situations (see POTMsgSet.setCurrentTranslation for
        # details) the acceptance can be made to propagate to the other
        # side, subject to the share_with_other_side parameter.
        pofile = self.factory.makePOFile()
        suggestion = self.factory.makeSuggestion(pofile=pofile)
        reviewer = self.factory.makePerson()

        self.assertFalse(suggestion.is_current_upstream)
        self.assertFalse(suggestion.is_current_ubuntu)

        suggestion.acceptAsImported(pofile, share_with_other_side=True)

        self.assertTrue(suggestion.is_current_upstream)
        self.assertTrue(suggestion.is_current_ubuntu)

    def test_accept_marks_not_reviewed(self):
        # Accepting a suggestion does not update its review fields.
        pofile = self.factory.makePOFile()
        suggestion = self.factory.makeSuggestion(pofile=pofile)
        reviewer = self.factory.makePerson()

        self.assertIs(None, suggestion.reviewer)
        self.assertIs(None, suggestion.date_reviewed)

        suggestion.acceptAsImported(pofile)

        self.assertIs(None, suggestion.reviewer)
        self.assertIs(None, suggestion.date_reviewed)

    def test_accept_awards_no_karma(self):
        # The translator receives no karma.
        translator = self.factory.makePerson()
        pofile = self.factory.makePOFile()
        suggestion = self.factory.makeSuggestion(
            pofile=pofile, translator=translator)

        karmarecorder = self.installKarmaRecorder(person=translator)
        suggestion.acceptAsImported(pofile)

        self.assertEqual([], karmarecorder.karma_events)

    def test_accept_old_style_activates_message_if_untranslated(self):
        # An untranslated message receives an imported translation.
        pofile = self.factory.makePOFile()
        suggestion = self.factory.makeSuggestion(pofile=pofile)
        reviewer = self.factory.makePerson()
        self.assertFalse(suggestion.is_current_upstream)
        self.assertFalse(suggestion.is_current_ubuntu)

        suggestion.acceptAsImported(pofile, old_style_import=True)

        # Messages are always accepted on the other side, too.
        self.assertTrue(suggestion.is_current_upstream)
        self.assertFalse(suggestion.is_current_ubuntu)

    def test_accept_old_style_no_previously_imported(self):
        # If there was already a current translation, but no previously
        # imported one, it is disabled when a suggestion is accepted.
        pofile, potmsgset = self.factory.makePOFileAndPOTMsgSet()
        suggestion = self.factory.makeSuggestion(
            pofile=pofile, potmsgset=potmsgset)
        incumbent_message = self.factory.makeCurrentTranslationMessage(
            pofile=pofile, potmsgset=potmsgset)

        self.assertTrue(incumbent_message.is_current_upstream)
        self.assertFalse(suggestion.is_current_upstream)

        suggestion.acceptAsImported(pofile, old_style_import=True)

        self.assertFalse(incumbent_message.is_current_upstream)
        self.assertTrue(suggestion.is_current_upstream)
        # Messages are always accepted on the other side, too.
        self.assertTrue(suggestion.is_current_ubuntu)

    def test_accept_old_style_previously_imported(self):
        # If there was already a current translation, and a previously
        # imported one, the current translation is left untouched.
        pofile, potmsgset = self.factory.makePOFileAndPOTMsgSet()
        imported_message = self.factory.makeCurrentTranslationMessage(
            pofile=pofile, potmsgset=potmsgset, current_other=True)
        imported_message.is_current_upstream = False

        suggestion = self.factory.makeSuggestion(
            pofile=pofile, potmsgset=potmsgset)
        incumbent_message = self.factory.makeCurrentTranslationMessage(
            pofile=pofile, potmsgset=potmsgset)

        self.assertTrue(incumbent_message.is_current_upstream)
        self.assertFalse(suggestion.is_current_upstream)
        self.assertTrue(imported_message.is_current_ubuntu)

        suggestion.acceptAsImported(pofile, old_style_import=True)

        self.assertTrue(incumbent_message.is_current_upstream)
        self.assertFalse(suggestion.is_current_upstream)
        # Messages are always accepted on the other side, too.
        self.assertFalse(imported_message.is_current_ubuntu)
        self.assertTrue(suggestion.is_current_ubuntu)

    def test_accept_old_style_current_message(self):
        # Accepting a message that's already current does nothing on this
        # side but makes sure the other side's flag is set.
        pofile = self.factory.makePOFile()
        translation = self.factory.makeCurrentTranslationMessage(
            pofile=pofile)
        self.assertTrue(translation.is_current_upstream)
        self.assertFalse(translation.is_current_ubuntu)

        translation.approve(pofile, old_style_import=True)

        self.assertTrue(translation.is_current_upstream)
        self.assertTrue(translation.is_current_ubuntu)

    def test_accept_old_style_detects_conflict(self):
        pofile = self.factory.makePOFile()
        current = self.factory.makeCurrentTranslationMessage(pofile=pofile)
        potmsgset = current.potmsgset
        suggestion = self.factory.makeSuggestion(
            pofile=pofile, potmsgset=potmsgset)
        old = datetime.now(UTC) - timedelta(days=1)

        self.assertRaises(
            TranslationConflict,
            suggestion.acceptAsImported,
            pofile, old_style_import=True, lock_timestamp=old)


class TestApproveAsDiverged(TestCaseWithFactory):
    """Tests for `TranslationMessage.approveAsDiverged`."""

    layer = ZopelessDatabaseLayer

    def _makeCounterpartPOFile(self, pofile):
        """Make a `POFile` on the opposite translation side.

        :param pofile: A `POFile` to match.  Assumed to be on the
            "upstream" translation side.
        """
        assert pofile.potemplate.productseries is not None, (
            "This test needs a product template; got a package template.""")
        other_template = self.factory.makePOTemplate(
            distroseries=self.factory.makeDistroSeries(),
            sourcepackagename=self.factory.makeSourcePackageName())

        return self.factory.makePOFile(
            pofile.language.code, potemplate=other_template)

    def test_makeCounterpartPOFile(self):
        # self.factory.makePOFile makes POFiles on the upstream side by
        # default.  self._makeCounterpartPOFile makes POFiles on the
        # Ubuntu side.
        pofile = self.factory.makePOFile('es')
        other_pofile = self._makeCounterpartPOFile(pofile)

        self.assertEqual(pofile.language, other_pofile.language)
        self.assertNotEqual(
            pofile.potemplate.translation_side,
            other_pofile.potemplate.translation_side)

    def test_no_change(self):
        # Approving and diverging a message that's already active and
        # diverged for this POFile does nothing.  Even the reviewer
        # stays unchanged.
        translator = self.factory.makePerson()
        original_reviewer = self.factory.makePerson()
        later_reviewer = self.factory.makePerson()
        pofile = self.factory.makePOFile('es_AR')
        message = self.factory.makeDivergedTranslationMessage(
            pofile=pofile, translator=translator, reviewer=original_reviewer)

        resulting_message = message.approveAsDiverged(pofile, later_reviewer)

        self.assertEqual(message, resulting_message)
        self.assertEqual(translator, message.submitter)
        self.assertEqual(original_reviewer, message.reviewer)
        self.assertEqual(pofile.potemplate, message.potemplate)

    def test_activates_and_diverges(self):
        # Approving a simple suggestion activates and diverges it.
        pofile = self.factory.makePOFile('es_BO')
        suggestion = self.factory.makeSuggestion(pofile=pofile)

        resulting_message = suggestion.approveAsDiverged(
            pofile, self.factory.makePerson())

        self.assertEqual(suggestion, resulting_message)
        self.assertTrue(suggestion.is_current_upstream)
        self.assertTrue(suggestion.is_diverged)
        self.assertEqual(pofile.potemplate, suggestion.potemplate)

    def test_activating_reviews(self):
        # Activating a message marks it as reviewed.
        pofile = self.factory.makePOFile('es_BO')
        reviewer = self.factory.makePerson()
        suggestion = self.factory.makeSuggestion(pofile=pofile)

        resulting_message = suggestion.approveAsDiverged(pofile, reviewer)

        self.assertEqual(reviewer, resulting_message.reviewer)

    def test_diverge_current_shared_leaves_message_intact(self):
        # Calling approveAsDiverged on the current shared translation
        # leaves it untouched.
        original_reviewer = self.factory.makePerson()
        later_reviewer = self.factory.makePerson()
        pofile = self.factory.makePOFile('es_CL')
        message = self.factory.makeCurrentTranslationMessage(
            pofile=pofile, reviewer=original_reviewer)

        resulting_message = message.approveAsDiverged(pofile, later_reviewer)

        self.assertEqual(message, resulting_message)
        self.assertEqual(original_reviewer, message.reviewer)
        self.assertFalse(message.is_diverged)

    def test_diverge_current_shared_message_unmasks_it(self):
        # Calling approveAsDiverged on the current shared translation
        # deactivates any diverged message that may be masking it.
        pofile = self.factory.makePOFile('es_CO')
        reviewer = self.factory.makePerson()
        shared = self.factory.makeCurrentTranslationMessage(pofile=pofile)
        diverged = self.factory.makeDivergedTranslationMessage(
            pofile=pofile, potmsgset=shared.potmsgset)

        self.assertTrue(shared.is_current_upstream)
        self.assertTrue(diverged.is_current_upstream)
        self.assertFalse(shared.is_diverged)
        self.assertTrue(diverged.is_diverged)

        shared.approveAsDiverged(pofile, reviewer)

        self.assertTrue(shared.is_current_upstream)
        self.assertFalse(diverged.is_current_upstream)
        self.assertFalse(shared.is_diverged)

    def test_does_not_affect_other_side(self):
        # Approving a message that's current on the other side clones
        # it, so that the other side remains unaffected by this local
        # change.
        reviewer = self.factory.makePerson()
        pofile = self.factory.makePOFile('es_CR')
        other_pofile = self._makeCounterpartPOFile(pofile)
        suggestion = self.factory.makeCurrentTranslationMessage(
            pofile=other_pofile)
        self.assertEqual(
            (False, True),
            (suggestion.is_current_upstream, suggestion.is_current_ubuntu))

        resulting_message = suggestion.approveAsDiverged(pofile, reviewer)

        self.assertNotEqual(suggestion, resulting_message)
        self.assertEqual(pofile.potemplate, resulting_message.potemplate)
        self.assertFalse(suggestion.is_diverged)
        self.assertTrue(resulting_message.is_current_upstream)
        self.assertEqual(
            (False, True),
            (suggestion.is_current_upstream, suggestion.is_current_ubuntu))

    def test_does_not_affect_diverged_elsewhere(self):
        # Approving a message that's current and diverged to another
        # template clones it, so that the other template remains
        # unaffected by this local change.
        reviewer = self.factory.makePerson()
        pofile = self.factory.makePOFile('es_DO')
        elsewhere = self.factory.makePOFile('es_DO')

        suggestion = self.factory.makeDivergedTranslationMessage(
            pofile=elsewhere)

        resulting_message = suggestion.approveAsDiverged(pofile, reviewer)

        self.assertNotEqual(suggestion, resulting_message)
        self.assertEqual(pofile.potemplate, resulting_message.potemplate)
        self.assertEqual(elsewhere.potemplate, suggestion.potemplate)
        self.assertTrue(resulting_message.is_current_upstream)
        self.assertTrue(suggestion.is_current_upstream)

    def test_detects_conflict(self):
        # Trying to approve and diverge a message based on outdated
        # information raises TranslationConflict.
        reviewer = self.factory.makePerson()
        pofile = self.factory.makePOFile('es_EC')
        suggestion = self.factory.makeSuggestion(pofile=pofile)
        current = self.factory.makeDivergedTranslationMessage(
            pofile=pofile, potmsgset=suggestion.potmsgset)
        earlier = current.date_reviewed - timedelta(1)

        self.assertRaises(
            TranslationConflict,
            suggestion.approveAsDiverged,
            pofile, reviewer, lock_timestamp=earlier)

    def test_passes_conflict_check_if_no_conflict(self):
        # Trying to approve and diverge a message based on up-to-date
        # works without raising a conflict.
        reviewer = self.factory.makePerson()
        pofile = self.factory.makePOFile('es_GT')
        suggestion = self.factory.makeSuggestion(pofile=pofile)
        current = self.factory.makeDivergedTranslationMessage(
            pofile=pofile, potmsgset=suggestion.potmsgset)
        later = current.date_reviewed + timedelta(1)

        suggestion.approveAsDiverged(pofile, reviewer, lock_timestamp=later)

        self.assertTrue(suggestion.is_current_upstream)

    def test_passes_conflict_check_if_same_translations(self):
        # Trying to approve and diverge a message based on outdated
        # information works just fine if in the meantime the suggestion
        # has become the diverged current translation.
        reviewer = self.factory.makePerson()
        pofile = self.factory.makePOFile('es_HN')
        current = self.factory.makeDivergedTranslationMessage(pofile=pofile)
        earlier = current.date_reviewed - timedelta(1)

        current.approveAsDiverged(pofile, reviewer, lock_timestamp=earlier)

        self.assertTrue(current.is_current_upstream)

    def test_updates_pofile(self):
        # Approving a message as a diverged translation marks the POFile
        # as updated.
        reviewer = self.factory.makePerson()
        pofile = self.factory.makePOFile('es_MX')
        suggestion = self.factory.makeSuggestion(pofile=pofile)
        earlier = pofile.date_changed - timedelta(1)
        pofile.markChanged(timestamp=earlier)

        self.assertEqual(earlier, pofile.date_changed)
        suggestion.approveAsDiverged(pofile, reviewer)
        self.assertNotEqual(earlier, pofile.date_changed)
        self.assertEqual(suggestion.date_reviewed, pofile.date_changed)


class TestTranslationMessage(TestCaseWithFactory):
    """Basic unit tests for TranslationMessage class.
    """
    layer = ZopelessDatabaseLayer

    def test_getOnePOFile(self):
        language = self.factory.makeLanguage('sr@test')
        pofile = self.factory.makePOFile(language.code)
        tm = self.factory.makeCurrentTranslationMessage(pofile=pofile)
        self.assertEquals(pofile, tm.getOnePOFile())

    def test_getOnePOFile_shared(self):
        language = self.factory.makeLanguage('sr@test')
        pofile1 = self.factory.makePOFile(language.code)
        pofile2 = self.factory.makePOFile(language.code)
        tm = self.factory.makeCurrentTranslationMessage(pofile=pofile1)
        # Share this POTMsgSet with the other POTemplate (and POFile).
        tm.potmsgset.setSequence(pofile2.potemplate, 1)
        self.assertTrue(tm.getOnePOFile() in [pofile1, pofile2])

    def test_getOnePOFile_no_pofile(self):
        # When POTMsgSet is obsolete (sequence=0), no matching POFile
        # is returned.
        language = self.factory.makeLanguage('sr@test')
        pofile = self.factory.makePOFile(language.code)
        tm = self.factory.makeCurrentTranslationMessage(pofile=pofile)
        tm.potmsgset.setSequence(pofile.potemplate, 0)
        self.assertEquals(None, tm.getOnePOFile())


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

        self.message = self.factory.makeCurrentTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            translations=self.translation_strings)
        self.message.potemplate = self.template

        self.other_message = self.factory.makeCurrentTranslationMessage(
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
