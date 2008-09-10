#! /usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test `remove_translations` and the `remove-translations-by.py` script."""

__metaclass__ = type

from datetime import datetime
from pytz import timezone
from unittest import TestLoader

from zope.component import getUtility

from storm.store import Store

from canonical.launchpad.ftests import sync
from canonical.launchpad.interfaces import (
    IPersonSet, RosettaTranslationOrigin)
from canonical.launchpad.scripts.remove_translations import (
    check_constraints_safety, check_removal_options,
    normalize_removal_options, remove_translations)
from canonical.launchpad.testing import LaunchpadObjectFactory, TestCase
from canonical.testing import LaunchpadZopelessLayer


class MockOptions:
    """Mock set of options to pass to `check_constraints_safety`."""
    def __init__(self, submitter=None, reviewer=None, ids=None,
                 potemplate=None, language_code=None,
                 not_language=None, is_current=None, is_imported=None,
                 msgid=None, origin=None, force=None):
        self.submitter = submitter
        self.reviewer = reviewer
        self.ids = ids
        self.potemplate = potemplate
        self.language = language_code
        self.not_language = not_language
        self.is_current = is_current
        self.is_imported = is_imported
        self.msgid = msgid
        self.origin = origin
        self.force = force


class TestRemoveTranslationsConstraints(TestCase):
    """Test safety net for translations removal options."""
    layer = LaunchpadZopelessLayer

    def test_RecklessRemoval(self):
        # The script will refuse to run if no specific person or id is
        # targeted.  Operator error is more likely than a use case for
        # casually deleting lots of loosely-specified translations.
        opts = MockOptions(language_code='pa', not_language=True,
            is_current=False, is_imported=True, msgid='foo', origin=1,
            force=True)
        approval, message = check_constraints_safety(opts)
        self.assertFalse(approval)

    def test_RemoveBySubmitter(self):
        # Removing all translations by one submitter is allowed.
        opts = MockOptions(submitter=1)
        approval, message = check_constraints_safety(opts)
        self.assertTrue(approval)

    def test_RemoveByReviewer(self):
        # Removing all translations by one reviewer is allowed.
        opts = MockOptions(reviewer=1)
        approval, message = check_constraints_safety(opts)
        self.assertTrue(approval)

    def test_RemoveById(self):
        # Removing by ids is allowed.
        opts = MockOptions(ids=[1, 2, 3])
        approval, message = check_constraints_safety(opts)
        self.assertTrue(approval)

    def test_EmptyIdList(self):
        # An empty id list is not enough to permit deletion.
        opts = MockOptions(ids=[], language_code='pa', not_language=True,
            is_current=False, is_imported=True, msgid='foo', origin=1,
            force=True)
        approval, message = check_constraints_safety(opts)
        self.assertIn("Refusing unsafe deletion", message)
        self.assertFalse(approval)

    def test_RemoveByPOFile(self):
        # Removing all translations for a template is not allowed by default.
        opts = MockOptions(potemplate=1)
        approval, message = check_constraints_safety(opts)
        self.assertFalse(approval)

    def test_ForceRemoveByPOFile(self):
        # The --force option overrides the safety check against deleting
        # all translations in a template.
        opts = MockOptions(potemplate=1, force=True)
        approval, message = check_constraints_safety(opts)
        self.assertIn("Safety override in effect", message)
        self.assertTrue(approval)


class TestRemoveTranslationsOptionsNormalization(TestCase):
    """Test `normalize_removal_options`."""
    layer = LaunchpadZopelessLayer

    def test_TrivialOptionsNormalization(self):
        opts = MockOptions()
        normalize_removal_options(opts)
        self.assertEqual(opts.submitter, None)
        self.assertEqual(opts.reviewer, None)
        self.assertEqual(opts.ids, None)
        self.assertEqual(opts.potemplate, None)
        self.assertEqual(opts.language, None)
        self.assertEqual(opts.not_language, None)
        self.assertEqual(opts.is_current, None)
        self.assertEqual(opts.is_imported, None)
        self.assertEqual(opts.msgid, None)
        self.assertEqual(opts.origin, None)
        self.assertEqual(opts.force, None)

    def test_NormalizeSubmitter(self):
        opts = MockOptions(submitter='1')
        normalize_removal_options(opts)
        self.assertEqual(opts.submitter, 1)

    def test_SubmitterLookup(self):
        user = getUtility(IPersonSet).getByName('sabdfl')
        opts = MockOptions(submitter=user.name)
        normalize_removal_options(opts)
        self.assertEqual(opts.submitter, user.id)

    def test_UnknownSubmitterName(self):
        opts = MockOptions(submitter='a-nonexistent-user')
        self.assertRaises(LookupError, normalize_removal_options, opts)

    def test_NormalizeReviewer(self):
        opts = MockOptions(reviewer='2')
        normalize_removal_options(opts)
        self.assertEqual(opts.reviewer, 2)

    def test_ReviewerLookup(self):
        user = getUtility(IPersonSet).getByName('name12')
        opts = MockOptions(reviewer=user.name)
        normalize_removal_options(opts)
        self.assertEqual(opts.reviewer, user.id)

    def test_UnknownReviewerName(self):
        opts = MockOptions(reviewer='a-nonexistent-user')
        self.assertRaises(LookupError, normalize_removal_options, opts)

    def test_NormalizeIds(self):
        opts = MockOptions(ids=['5', '6'])
        normalize_removal_options(opts)
        self.assertEqual(sorted(opts.ids), [5, 6])

    def test_NonNumericId(self):
        opts = MockOptions(ids=[1, 'foo', 3])
        self.assertRaises(ValueError, normalize_removal_options, opts)

    def test_NormalizePOTemplate(self):
        opts = MockOptions(potemplate='9')
        normalize_removal_options(opts)
        self.assertEqual(opts.potemplate, 9)

    def test_NormalizeOrigin(self):
        opts = MockOptions(origin='1')
        normalize_removal_options(opts)
        self.assertEqual(opts.origin, 1)

    def test_OriginLookup(self):
        opts = MockOptions(origin='ROSETTAWEB')
        normalize_removal_options(opts)
        self.assertEqual(opts.origin, 2)

    def test_NormalizeIsCurrent(self):
        opts = MockOptions(is_current='1')
        normalize_removal_options(opts)
        self.assertEqual(opts.is_current, True)

    def test_NormalizeIsImported(self):
        opts = MockOptions(is_imported='true')
        normalize_removal_options(opts)
        self.assertEqual(opts.is_imported, True)

    def test_NormalizeBool0(self):
        opts = MockOptions(is_current='0')
        normalize_removal_options(opts)
        self.assertEqual(opts.is_current, False)

    def test_NormalizeBool1(self):
        opts = MockOptions(is_current='1')
        normalize_removal_options(opts)
        self.assertEqual(opts.is_current, True)

    def test_NormalizeBoolFalse(self):
        opts = MockOptions(is_current='false')
        normalize_removal_options(opts)
        self.assertEqual(opts.is_current, False)

    def test_NormalizeBoolTrue(self):
        opts = MockOptions(is_current='true')
        normalize_removal_options(opts)
        self.assertEqual(opts.is_current, True)

    def test_NormalizeBoolFALSE(self):
        opts = MockOptions(is_current='FALSE')
        normalize_removal_options(opts)
        self.assertEqual(opts.is_current, False)

    def test_NormalizeBoolTRUE(self):
        opts = MockOptions(is_current='TRUE')
        normalize_removal_options(opts)
        self.assertEqual(opts.is_current, True)


class TestRemoveTranslationsOptionsCheck(TestCase):
    """Test `check_removal_options`.

    The check can have only two outcomes: an exception or a normal
    return.  So checks for normal use just call `check_removal_options`
    and leave it at that.
    """
    def test_TrivialRemovalOptionsCheck(self):
        check_removal_options(MockOptions())

    def test_AllRemovalOptionsCheck(self):
        opts = MockOptions(
            submitter=1, reviewer=2, ids=[3, 4, 5], potemplate=6,
            language_code='pa', not_language=True, is_current=False,
            is_imported=True, msgid='translatable string', force=True)
        check_removal_options(opts)

    def test_BadSubmitter(self):
        self.assertRaises(
            ValueError, check_removal_options, MockOptions(submitter="9"))

    def test_BadReviewer(self):
        self.assertRaises(
            ValueError, check_removal_options, MockOptions(reviewer="8"))

    def test_BadId(self):
        self.assertRaises(
            ValueError, check_removal_options, MockOptions(ids=99))

    def test_BadTemplate(self):
        self.assertRaises(
            ValueError, check_removal_options, MockOptions(potemplate="100"))

    def test_BadLanguage(self):
        self.assertRaises(
            ValueError, check_removal_options, MockOptions(language_code=46))

    def test_BadNotLanguage(self):
        self.assertRaises(
            ValueError, check_removal_options, MockOptions(not_language="0"))

    def test_BadIsCurrent(self):
        self.assertRaises(
            ValueError, check_removal_options, MockOptions(is_current=1))

    def test_BadIsImported(self):
        self.assertRaises(
            ValueError, check_removal_options, MockOptions(is_imported=0))

    def test_BadMsgId(self):
        self.assertRaises(
            ValueError, check_removal_options, MockOptions(msgid=122))

    def test_BadOrigin(self):
        self.assertRaises(
            ValueError, check_removal_options, MockOptions(origin='SCM'))

    def test_BadForce(self):
        self.assertRaises(
            ValueError, check_removal_options, MockOptions(force='True'))


class TestRemoveTranslations(TestCase):
    """Test `remove_translations`."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        # Acquire privileges to delete TranslationMessages.  That's not
        # something we normally do.  Actually we should test under
        # rosettaadmin, but that user does not have all the privileges
        # needed to set up this test.  A separate doctest
        # remove-translations-by.txt tests a realistic run of the
        # remove-translations-by.py script under the actual rosettaadmin
        # db user.
        self.layer.switchDbUser('postgres')

        # Set up a template with Dutch and German translations.  The
        # messages we set up here are invariant; they remain untouched
        # by deletions done in the test case.
        self.factory = LaunchpadObjectFactory()
        self.nl_pofile = self.factory.makePOFile('nl')
        self.potemplate = self.nl_pofile.potemplate
        self.de_pofile = self.factory.makePOFile(
            'de', potemplate=self.potemplate)

        self.nl_message, self.de_message = self._makeMessages(
            "This message is not to be deleted.",
            "Dit bericht mag niet worden verwijderd.",
            "Diese Nachricht soll nicht erloescht werden.")

        self.untranslated_message = self.factory.makePOTMsgSet(
            self.potemplate, 'This message is untranslated.')

        self._checkInvariant()

    def _setTranslation(self, potmsgset, pofile, text, submitter=None,
                        is_imported=False):
        """Set translation for potmsgset in pofile to text."""
        if submitter is None:
            submitter = self.potemplate.owner
        return potmsgset.updateTranslation(
            pofile, submitter, {0: text}, is_fuzzy=False,
            is_imported=is_imported,
            lock_timestamp=datetime.now(timezone('UTC')))

    def _makeMessages(self, template_text, nl_text, de_text,
                      submitter=None, is_imported=False):
        """Create message, and translate it to Dutch & German."""
        message = self.factory.makePOTMsgSet(self.potemplate, template_text)
        owner = self.potemplate.owner
        new_nl_message = self._setTranslation(
            message, self.nl_pofile, nl_text, submitter=submitter,
            is_imported=is_imported)
        new_de_message = self._setTranslation(
            message, self.de_pofile, de_text, submitter=submitter,
            is_imported=is_imported)
        return new_nl_message, new_de_message

    def _getContents(self, pofile):
        return sorted(
            message.msgstr0.translation
            for message in pofile.translation_messages
            if message.msgstr0 is not None
            )

    def _checkInvariant(self):
        """Check that our translations are in their original state.

        Tests in this test case don't work in the usual way, by making
        changes and then testing for them.  Instead they make changes by
        creating new messages, and then using `remove_translations` to
        undo those changes.
        
        We see that a removal worked correctly by verifying that the
        invariant is restored.
        """
        # First make sure we're not reading out of cache.
        sync(self.nl_pofile)
        sync(self.de_pofile)

        self.assertEqual(
            self._getContents(self.nl_pofile),
            ["Dit bericht mag niet worden verwijderd."])
        self.assertEqual(
            self._getContents(self.de_pofile),
            ["Diese Nachricht soll nicht erloescht werden."])

    def _remove(self, **kwargs):
        """Front-end for `remove_translations`.  Flushes changes first."""
        Store.of(self.potemplate).flush()
        return remove_translations(**kwargs)

    def test_RemoveNone(self):
        # If no messages match the given constraints, nothing is
        # deleted.
        rowcount = self._remove(
            submitter=1, ids=[self.de_message.id], language_code='br')
        self.assertEqual(rowcount, 0)
        self._checkInvariant()

    def test_RemoveById(self):
        # We can remove messages by id.  Other messages are not
        # affected.
        new_nl_message1 = self._setTranslation(
            self.untranslated_message, self.nl_pofile, "A Dutch translation")
        new_nl_message2 = self._setTranslation(
            self.untranslated_message, self.nl_pofile, "Double Dutch")
        self.assertEqual(
            self._getContents(self.nl_pofile), [
                "A Dutch translation",
                "Dit bericht mag niet worden verwijderd.",
                "Double Dutch",
                ])

        rowcount = self._remove(ids=[new_nl_message1.id, new_nl_message2.id])

        self.assertEqual(rowcount, 2)
        self._checkInvariant()

    def test_RemoveBySubmitter(self):
        # Remove messages by submitter id.
        carlos = getUtility(IPersonSet).getByName('carlos')
        (new_nl_message, new_de_message) = self._makeMessages(
            "Submitted by Carlos", "Ingevoerd door Carlos",
            "Von Carlos eingefuehrt", submitter=carlos)

        # Ensure that at least one message's reviewer is not the same
        # as the submitter, so we know we're not accidentally matching
        # on reviewer instead.
        new_nl_message.reviewer = self.potemplate.owner

        rowcount = self._remove(submitter=carlos)

        self._checkInvariant()

    def test_RemoveByReviewer(self):
        # Remove messages by reviewer id.
        carlos = getUtility(IPersonSet).getByName('carlos')
        (new_nl_message, new_de_message) = self._makeMessages(
            "Submitted by Carlos", "Ingevoerd door Carlos",
            "Von Carlos eingefuehrt")
        new_nl_message.reviewer = carlos
        new_de_message.reviewer = carlos

        rowcount = self._remove(reviewer=carlos)

        self._checkInvariant()

    def test_RemoveByTemplate(self):
        # Remove messages by template.  Limit this deletion by ids as
        # well to avoid breaking the test invariant.  To show that the
        # template limitation really does add a limit on top of the ids
        # themselves, we also pass the id of another message in a
        # different template.  That message is not deleted.
        (new_nl_message, new_de_message) = self._makeMessages(
            "Foo", "Foe", "Fu")

        unrelated_nl_pofile = self.factory.makePOFile('nl')
        potmsgset = self.factory.makePOTMsgSet(
            unrelated_nl_pofile.potemplate, 'Foo')
        unrelated_nl_message = potmsgset.updateTranslation(
            unrelated_nl_pofile, unrelated_nl_pofile.potemplate.owner,
            {0: "Foe"}, is_fuzzy=False, is_imported=False,
            lock_timestamp=datetime.now(timezone('UTC')))

        ids = [new_nl_message.id, new_de_message.id, unrelated_nl_message.id]
        rowcount = self._remove(ids=ids, potemplate=self.potemplate.id)

        self._checkInvariant()
        self.assertEqual(self._getContents(unrelated_nl_pofile), ["Foe"])

    def test_RemoveByLanguage(self):
        # Remove messages by language.  Pass the ids of one Dutch
        # message and one German message, but specify Dutch as the
        # language to delete from; only the Dutch message is deleted.
        potmsgset = self.factory.makePOTMsgSet(self.potemplate, 'Bar')
        message = self._setTranslation(potmsgset, self.nl_pofile, 'Cafe')

        self._remove(ids=[message.id, self.de_message.id], language_code='nl')

        self._checkInvariant()

    def test_RemoveByNotLanguage(self):
        # Remove messages, but spare otherwise matching messages that
        # are in German.
        potmsgset = self.factory.makePOTMsgSet(self.potemplate, 'Hi')
        message = self._setTranslation(potmsgset, self.nl_pofile, 'Hoi')

        self._remove(
            ids=[message.id, self.de_message.id], language_code='de',
            not_language=True)

        self._checkInvariant()

    def test_RemoveCurrent(self):
        # Remove current messages, but not non-current messages.
        (new_nl_message, new_de_message) = self._makeMessages(
            "translate", "vertalen", "uebersetzen")
        self.nl_message.is_current = False

        ids = [self.nl_message.id, new_nl_message.id, new_de_message.id]
        self._remove(ids=ids, is_current=True)

        self.nl_message.is_current = True
        self._checkInvariant()

    def test_RemoveNotCurrent(self):
        # Remove current messages, but not non-current messages.
        (new_nl_message, new_de_message) = self._makeMessages(
            "write", "schrijven", "schreiben")
        new_nl_message.is_current = False
        new_de_message.is_current = False

        ids = [self.nl_message.id, new_nl_message.id, new_de_message.id]
        self._remove(ids=ids, is_current=False)

        self._checkInvariant()

    def test_RemoveImported(self):
        # Remove current messages, but not non-current messages.
        (new_nl_message, new_de_message) = self._makeMessages(
            "book", "boek", "Buch")
        new_nl_message.is_imported = True
        new_de_message.is_imported = True

        ids = [self.nl_message.id, new_nl_message.id, new_de_message.id]
        self._remove(ids=ids, is_imported=True)

        self._checkInvariant()

    def test_RemoveNotImported(self):
        # Remove current messages, but not non-current messages.
        (new_nl_message, new_de_message) = self._makeMessages(
            "helicopter", "helikopter", "Hubschauber")
        self.nl_message.is_imported = True

        ids = [self.nl_message.id, new_nl_message.id, new_de_message.id]
        self._remove(ids=ids, is_imported=False)

        self.nl_message.is_imported = False
        self._checkInvariant()

    def test_RemoveMsgId(self):
        # Remove translations by msgid_singular.
        (new_nl_message, new_de_message) = self._makeMessages(
            "save", "bewaren", "speichern")

        self._remove(msgid_singular="save")

        self._checkInvariant()

    def test_RemoveOrigin(self):
        # Remove translations by origin.
        self.assertEqual(
            self.nl_message.origin, RosettaTranslationOrigin.ROSETTAWEB)
        (new_nl_message, new_de_message) = self._makeMessages(
            "new", "nieuw", "neu", is_imported=True)
        self.assertEqual(new_nl_message.origin, RosettaTranslationOrigin.SCM)
        self.assertEqual(new_de_message.origin, RosettaTranslationOrigin.SCM)

        self._remove(
            potemplate=self.potemplate, origin=RosettaTranslationOrigin.SCM)

        self._checkInvariant()


def test_suite():
    # Removing TranslationMessage rows requires special database privileges.
    return TestLoader().loadTestsFromName(__name__)
