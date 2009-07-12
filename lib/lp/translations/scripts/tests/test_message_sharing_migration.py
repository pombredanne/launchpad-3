# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from datetime import timedelta
from logging import ERROR
from unittest import TestLoader

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.pofiletranslator import (
    IPOFileTranslatorSet)
from lp.translations.scripts.message_sharing_migration import (
    MessageSharingMerge)
from canonical.testing import LaunchpadZopelessLayer


class TranslatableProductMixin:
    """Mixin: set up product with two series & templates for testing.

    Sets up a product with series "trunk" and "stable," each with a
    template.
    """
    def setUpProduct(self):
        self.product = self.factory.makeProduct()
        self.trunk = self.product.getSeries('trunk')
        self.stable = self.factory.makeProductSeries(
            product=self.product, owner=self.product.owner, name='stable')
        self.trunk_template = self.factory.makePOTemplate(
            productseries=self.trunk, name='template',
            owner=self.product.owner)
        self.stable_template = self.factory.makePOTemplate(
            productseries=self.stable, name='template',
            owner=self.product.owner)

        # Force trunk to be the "most representative" template.
        self.stable_template.iscurrent = False
        self.templates = [self.trunk_template, self.stable_template]

        self.script = MessageSharingMerge('tms-merging-test')
        self.script.logger.setLevel(ERROR)


class TestPOTMsgSetMerging(TestCaseWithFactory, TranslatableProductMixin):
    """Test merging of POTMsgSets."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        # This test needs the privileges of rosettaadmin (to delete
        # POTMsgSets) but it also needs to set up test conditions which
        # requires other privileges.
        self.layer.switchDbUser('postgres')
        super(TestPOTMsgSetMerging, self).setUp(user='mark@hbd.com')
        super(TestPOTMsgSetMerging, self).setUpProduct()

    def test_matchedPOTMsgSetsShare(self):
        # Two identically-keyed POTMsgSets will share.  Where two
        # sharing templates had matching POTMsgSets, they will share
        # one.
        trunk_potmsgset = self.factory.makePOTMsgSet(
            self.trunk_template, singular='foo', sequence=1)
        stable_potmsgset = self.factory.makePOTMsgSet(
            self.stable_template, singular='foo', sequence=1)

        self.script._mergePOTMsgSets(self.templates)

        trunk_messages = list(self.trunk_template.getPOTMsgSets(False))
        stable_messages = list(self.stable_template.getPOTMsgSets(False))

        self.assertEqual(trunk_messages, [trunk_potmsgset])
        self.assertEqual(trunk_messages, stable_messages)

    def test_mergePOTMsgSets_is_idempotent(self):
        # merge_potmsgsets can be run again on a situation it's
        # produced.  It will produce the same situation.
        trunk_potmsgset = self.factory.makePOTMsgSet(
            self.trunk_template, singular='foo', sequence=1)
        stable_potmsgset = self.factory.makePOTMsgSet(
            self.stable_template, singular='foo', sequence=1)

        self.script._mergePOTMsgSets(self.templates)
        self.script._mergePOTMsgSets(self.templates)

        trunk_messages = list(self.trunk_template.getPOTMsgSets(False))
        stable_messages = list(self.stable_template.getPOTMsgSets(False))

        self.assertEqual(trunk_messages, [trunk_potmsgset])
        self.assertEqual(trunk_messages, stable_messages)

    def test_unmatchedPOTMsgSetsDoNotShare(self):
        # Only identically-keyed potmsgsets get merged.
        trunk_potmsgset = self.factory.makePOTMsgSet(
            self.trunk_template, singular='foo', sequence=1)
        stable_potmsgset = self.factory.makePOTMsgSet(
            self.stable_template, singular='foo', context='bar', sequence=1)

        self.script._mergePOTMsgSets(self.templates)

        trunk_messages = list(self.trunk_template.getPOTMsgSets(False))
        stable_messages = list(self.stable_template.getPOTMsgSets(False))

        self.assertNotEqual(trunk_messages, stable_messages)

        self.assertEqual(trunk_messages, [trunk_potmsgset])
        self.assertEqual(stable_messages, [stable_potmsgset])

    def test_sharingPreservesSequenceNumbers(self):
        # Sequence numbers are preserved when sharing.
        self.factory.makePOTMsgSet(
            self.trunk_template, singular='foo', sequence=3)
        self.factory.makePOTMsgSet(
            self.stable_template, singular='foo', sequence=9)

        self.script._mergePOTMsgSets(self.templates)

        trunk_potmsgset = self.trunk_template.getPOTMsgSetByMsgIDText('foo')
        stable_potmsgset = self.stable_template.getPOTMsgSetByMsgIDText('foo')
        self.assertEqual(trunk_potmsgset.getSequence(self.trunk_template), 3)
        self.assertEqual(
            stable_potmsgset.getSequence(self.stable_template), 9)


class TranslatedProductMixin(TranslatableProductMixin):
    """Like TranslatableProductMixin, but adds actual POTMsgSets.

    Also provides handy methods to set and verify translations for the
    POTMsgSets.

    Creates one POTMsgSet for trunk and one for stable, i.e. a
    pre-sharing situation.
    """
    def setUpProduct(self):
        super(TranslatedProductMixin, self).setUpProduct()

        self.trunk_potmsgset = self.factory.makePOTMsgSet(
            self.trunk_template, singular='foo', sequence=1)

        self.stable_potmsgset = self.factory.makePOTMsgSet(
            self.stable_template, singular='foo', sequence=1)

        self.msgid = self.trunk_potmsgset.msgid_singular

        self.dutch = getUtility(ILanguageSet).getLanguageByCode('nl')

        self.trunk_pofile = self.factory.makePOFile(
            'nl', potemplate=self.trunk_template,
            owner=self.trunk_template.owner)
        self.stable_pofile = self.factory.makePOFile(
            'nl', potemplate=self.stable_template,
            owner=self.trunk_template.owner)

    def _makeTranslationMessage(self, pofile, potmsgset, text, diverged):
        """Set a translation for given message in given translation."""
        message = self.factory.makeTranslationMessage(
            pofile=pofile, potmsgset=potmsgset, translations=[text],
            translator=pofile.owner)
        if diverged:
            message.potemplate = pofile.potemplate
        else:
            message.potemplate = None

        return message

    def _makeTranslationMessages(self, trunk_string, stable_string,
                                 trunk_diverged=True, stable_diverged=True):
        """Translate the POTMsgSets in our trunk and stable templates.

        :param trunk_string: translation string to use in trunk.
        :param stable_string: translation string to use in stable.
        :return: a pair of new TranslationMessages for trunk and
            stable, respectively.
        """
        trunk_potmsgset, stable_potmsgset = self._getPOTMsgSets()
        trunk_message = self._makeTranslationMessage(
            pofile=self.trunk_pofile, potmsgset=trunk_potmsgset,
            text=trunk_string, diverged=trunk_diverged)
        stable_message = self._makeTranslationMessage(
            pofile=self.stable_pofile, potmsgset=stable_potmsgset,
            text=stable_string, diverged=stable_diverged)

        return (trunk_message, stable_message)

    def _getPOTMsgSet(self, template):
        """Get POTMsgSet for given template."""
        return removeSecurityProxy(template)._getPOTMsgSetBy(
            msgid_singular=self.msgid, sharing_templates=True)

    def _getPOTMsgSets(self):
        """Get POTMsgSets in our trunk and stable series."""
        return (
            self._getPOTMsgSet(self.trunk_template),
            self._getPOTMsgSet(self.stable_template))

    def _getMessage(self, potmsgset, template):
        """Get TranslationMessage for given POTMsgSet in given template."""
        message = potmsgset.getCurrentTranslationMessage(
            potemplate=template, language=self.dutch)
        if not message:
            # No diverged message here, so check for a shared one.
            message = potmsgset.getSharedTranslationMessage(
                language=self.dutch)
        return message

    def _getMessages(self):
        """Get current TranslationMessages in trunk and stable POTMsgSets."""
        trunk_potmsgset, stable_potmsgset = self._getPOTMsgSets()
        return (
            self._getMessage(trunk_potmsgset, self.trunk_template),
            self._getMessage(stable_potmsgset, self.stable_template))

    def _getTranslation(self, message):
        """Get (singular) translation string from TranslationMessage."""
        if message and message.translations:
            return message.translations[0]
        else:
            return None

    def _getTranslations(self):
        """Get translated strings for trunk and stable POTMsgSets."""
        (trunk_message, stable_message) = self._getMessages()
        return (
            self._getTranslation(trunk_message),
            self._getTranslation(stable_message))


class TestPOTMsgSetMergingAndTranslations(TestCaseWithFactory,
                                          TranslatedProductMixin):
    """Test how merging of POTMsgSets affects translations."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Set up test environment with.

        The test setup includes:
         * Two templates for the "trunk" and "stable" release series.
         * Matching POTMsgSets for the string "foo" in each.

        The matching POTMsgSets will be merged by the _mergePOTMsgSets
        call.
        """
        self.layer.switchDbUser('postgres')
        super(TestPOTMsgSetMergingAndTranslations, self).setUp(
            user='mark@hbd.com')
        super(TestPOTMsgSetMergingAndTranslations, self).setUpProduct()

    def test_sharingDivergedMessages(self):
        # Diverged TranslationMessages stay with their respective
        # templates even if their POTMsgSets are merged.
        trunk_message, stable_message = self._makeTranslationMessages(
            'bar', 'splat', trunk_diverged=True, stable_diverged=True)
        trunk_message.is_current = True
        stable_message.is_current = True

        self.script._mergePOTMsgSets(self.templates)

        self.assertEqual(self._getTranslations(), ('bar', 'splat'))
        self.assertEqual(self._getMessages(), (trunk_message, stable_message))

    def test_mergingIdenticalSharedMessages(self):
        # Shared, identical TranslationMessages do not clash when their
        # POTMsgSets are merged; the POTMsgSet will still have the same
        # translations in the merged templates.
        trunk_message, stable_message = self._makeTranslationMessages(
            'bar', 'bar', trunk_diverged=False, stable_diverged=False)
        trunk_message.is_current = True
        stable_message.is_current = True

        self.script._mergePOTMsgSets(self.templates)

        self.assertEqual(self._getTranslations(), ('bar', 'bar'))

    def test_mergingSharedMessages(self):
        # Shared TranslationMessages don't clash as a result of merging.
        # Instead, the most representative shared message survives as
        # shared.  The translation that "loses out" becomes diverged.
        trunk_message, stable_message = self._makeTranslationMessages(
            'bar2', 'splat2', trunk_diverged=False, stable_diverged=False)
        trunk_message.is_current = True
        stable_message.is_current = True

        self.script._mergePOTMsgSets(self.templates)

        # The POTMsgSets are now merged.
        potmsgset = self.trunk_template.getPOTMsgSetByMsgIDText('foo')

        # The "losing" message stays current within its template.
        self.assertEqual(self._getTranslations(), ('bar2', 'splat2'))

        trunk_message, stable_message = self._getMessages()

        # The TranslationMessage for trunk remains the shared one.
        self.assertEqual(trunk_message.potemplate, None)
        # The "losing" message became diverged; it is now specific to
        # its original template.
        self.assertEqual(stable_message.potemplate, self.stable_template)

    def test_mergingIdenticalSuggestions(self):
        # Identical suggestions can be merged without breakage.
        trunk_message, stable_message = self._makeTranslationMessages(
            'bar', 'bar', trunk_diverged=False, stable_diverged=False)
        trunk_message.is_current = False
        stable_message.is_current = False

        self.script._mergePOTMsgSets(self.templates)

        # Having these suggestions does not mean that there are current
        # translations.
        self.assertEqual(self._getTranslations(), (None, None))

    def test_clashingSharedTranslations(self):
        # When merging POTMsgSets that both have shared translations,
        # the most representative shared translation wins.
        trunk_message, stable_message = self._makeTranslationMessages(
            'foe', 'barr', trunk_diverged=False, stable_diverged=False)
        trunk_message.is_current = True
        stable_message.is_current = True

        self.script._mergePOTMsgSets(self.templates)

        trunk_message, stable_message = self._getMessages()
        self.assertEqual(trunk_message.potemplate, None)

        # There are still two separate messages; the second (least
        # representative) one is diverged.
        self.assertNotEqual(trunk_message, stable_message)
        self.assertEqual(stable_message.potemplate, self.stable_template)

    def test_currentMessageDoesNotMergeIntoSuggestion(self):
        # A less-representative, current TranslationMessage is not merged
        # into an identical suggestion if the target already has another
        # translation for the same message.
        trunk_message, stable_message = self._makeTranslationMessages(
            'smurf', 'smurf', trunk_diverged=False, stable_diverged=False)
        trunk_message.is_current = False
        stable_message.is_current = True

        current_message = self._makeTranslationMessage(
            self.trunk_pofile, trunk_message.potmsgset, 'bzo', False)
        current_message.is_current = True

        self.assertEqual(self._getTranslations(), ('bzo', 'smurf'))

        self.script._mergePOTMsgSets(self.templates)

        # The current translations stay as they are.
        self.assertEqual(self._getTranslations(), ('bzo', 'smurf'))

        # All three of the messages still exist, despite two of the
        # translations being near-identical.
        current_message, stable_message = self._getMessages()
        expected_tms = set([current_message, trunk_message, stable_message])
        tms = set(trunk_message.potmsgset.getAllTranslationMessages())
        self.assertEqual(tms, expected_tms)
        self.assertEqual(len(tms), 3)

    def test_duplicatesAreCleanedUp(self):
        # The POTMsgSet merging function cleans up any duplicate
        # TranslationMessages that might get in the way.
        trunk_message, stable_message = self._makeTranslationMessages(
            'snaggle', 'snaggle')
        trunk_message.is_current = False
        trunk_message.sync()

        potmsgset = trunk_message.potmsgset

        stable_message.is_imported = True
        stable_message.potemplate = trunk_message.potemplate
        stable_message.potmsgset = potmsgset
        stable_message.sync()

        # We've set up a situation where trunk has two identical
        # messages (one of which is current, the other imported) and
        # stable has none.
        self.assertEqual(self._getTranslations(), ('snaggle', None))
        tms = set(potmsgset.getAllTranslationMessages())
        self.assertEqual(tms, set([trunk_message, stable_message]))

        self.script._mergePOTMsgSets(self.templates)

        # The duplicates have been cleaned up.
        self.assertEqual(potmsgset.getAllTranslationMessages().count(), 1)
        
        # The is_current and is_imported flags from the duplicate
        # messages have been merged into a single, current, imported
        # message.
        message = self._getMessage(potmsgset, self.trunk_template)
        self.assertTrue(message.is_current)
        self.assertTrue(message.is_imported)


class TestTranslationMessageNonMerging(TestCaseWithFactory,
                                       TranslatedProductMixin):
    """Test TranslationMessages that don't share."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.layer.switchDbUser('postgres')
        super(TestTranslationMessageNonMerging, self).setUp(
            user='mark@hbd.com')
        super(TestTranslationMessageNonMerging, self).setUpProduct()

    def test_MessagesAreNotSharedAcrossPOTMsgSets(self):
        # Merging TranslationMessages does not merge messages that
        # belong to different POTMsgSets, no matter how similar they may
        # be.
        self._makeTranslationMessages('x', 'x')

        self.script._mergeTranslationMessages(self.templates)

        trunk_message, stable_message = self._getMessages()
        self.assertNotEqual(trunk_message, stable_message)

        # Each message may of course still become shared within the
        # context of its respective POTMsgSet.
        self.assertEqual(trunk_message.potemplate, None)
        self.assertEqual(stable_message.potemplate, None)


class TestTranslationMessageMerging(TestCaseWithFactory,
                                    TranslatedProductMixin):
    """Test merging of TranslationMessages."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.layer.switchDbUser('postgres')
        super(TestTranslationMessageMerging, self).setUp(user='mark@hbd.com')
        super(TestTranslationMessageMerging, self).setUpProduct()

    def test_messagesCanStayDiverged(self):
        # When POTMsgSets with diverged translations are merged, the
        # most-representative translation becomes shared but the rest
        # stays diverged.
        self._makeTranslationMessages(
            'a', 'b', trunk_diverged=True, stable_diverged=True)

        self.script._mergePOTMsgSets(self.templates)
        self.script._mergeTranslationMessages(self.templates)

        # Translations for the existing templates stay as they are.
        self.assertEqual(self._getTranslations(), ('a', 'b'))

        trunk_message, stable_message = self._getMessages()
        self.assertNotEqual(trunk_message, stable_message)
        self.assertEqual(trunk_message.potemplate, None)
        self.assertEqual(stable_message.potemplate, self.stable_template)

    def test_sharingIdenticalMessages(self):
        # Identical translation messages are merged into one.
        self._makeTranslationMessages(
            'x', 'x', trunk_diverged=True, stable_diverged=True)

        self.script._mergePOTMsgSets(self.templates)
        self.script._mergeTranslationMessages(self.templates)

        trunk_message, stable_message = self._getMessages()
        self.assertEqual(trunk_message, stable_message)
        self.assertEqual(trunk_message.potemplate, None)

        # Translations for the existing templates stay as they are.
        self.assertEqual(self._getTranslations(), ('x', 'x'))

        # Redundant messages are deleted.
        tms = trunk_message.potmsgset.getAllTranslationMessages()
        self.assertEqual(list(tms), [trunk_message])

    def test_sharingSuggestions(self):
        # POTMsgSet merging may leave suggestions diverged.
        # TranslationMessage merging makes sure those are shared.
        trunk_message, stable_message = self._makeTranslationMessages(
            'gah', 'ulp', trunk_diverged=False, stable_diverged=True)

        trunk_message.is_current = False
        stable_message.is_current = False

        self.script._mergePOTMsgSets(self.templates)
        self.script._mergeTranslationMessages(self.templates)

        # Translations for the existing templates stay as they are.
        self.assertEqual(self._getTranslations(), (None, None))

        # Suggestions all become shared.
        self.assertEqual(trunk_message.potemplate, None)
        self.assertEqual(stable_message.potemplate, None)

    def test_mergingLessRepresentativeShared(self):
        # If a less-representative shared message is merged with a
        # more-representative diverged message, the previously shared
        # message stays the shared one.
        self._makeTranslationMessages(
            'ips', 'unq', trunk_diverged=True, stable_diverged=False)

        self.script._mergePOTMsgSets(self.templates)
        self.script._mergeTranslationMessages(self.templates)

        # Translations for the existing templates stay as they are.
        self.assertEqual(self._getTranslations(), ('ips', 'unq'))

        trunk_message, stable_message = self._getMessages()
        self.assertEqual(trunk_message.potemplate, self.trunk_template)
        self.assertEqual(stable_message.potemplate, None)

    def test_suggestionMergedIntoCurrentMessage(self):
        # A less-representative suggestion can be merged into an
        # existing, more-representative current message.  (If the
        # suggestion's POTMsgSet did not have a current translation,
        # this implies that it gains one).
        trunk_message, stable_message = self._makeTranslationMessages(
            'n', 'n', trunk_diverged=False, stable_diverged=True)
        stable_message.is_current = False

        self.assertEqual(self._getTranslations(), ('n', None))

        self.script._mergePOTMsgSets(self.templates)
        self.script._mergeTranslationMessages(self.templates)

        # The less-representative POTMsgSet gains a translation, because
        # it now uses the shared translation.
        self.assertEqual(self._getTranslations(), ('n', 'n'))

        trunk_message, stable_message = self._getMessages()
        self.assertEqual(trunk_message, stable_message)
        self.assertEqual(trunk_message.potemplate, None)
        self.assertTrue(trunk_message.is_current)

        # Redundant messages are deleted.
        tms = trunk_message.potmsgset.getAllTranslationMessages()
        self.assertEqual(list(tms), [trunk_message])

    def test_clashingPOFileTranslatorEntries(self):
        # POFileTranslator is maintained by a trigger on
        # TranslationMessage.  Fiddling with TranslationTemplateItems
        # directly bypasses it, so the script must make sure that
        # POFileTranslator respects its unique constraints.

        # In this scenario, "trunk" has a TranslationMessage with a
        # matching POFileTranslator entry.  This message is happy where
        # it is; it's not changing in any way during the test.
        poftset = getUtility(IPOFileTranslatorSet)

        translator = self.trunk_template.owner

        contented_potmsgset = self.factory.makePOTMsgSet(
            self.trunk_template, singular='snut', sequence=2)
        contented_message = self._makeTranslationMessage(
            self.trunk_pofile, contented_potmsgset, 'druf', False)
        self.assertEqual(contented_message.submitter, translator)
        poft = poftset.getForPersonPOFile(translator, self.trunk_pofile)
        self.assertEqual(poft.latest_message, contented_message)

        # Then there's the pair of POTMsgSets that are identical between
        # trunk and stable.  This one is translated only in stable.
        # Merging will transfer that TranslationMessage from
        # stable to trunk (where it becomes the shared message) through
        # direct manipulation of TranslationTemplateItem.
        stable_message = self._makeTranslationMessage(
                self.stable_pofile, self.stable_potmsgset, 'fulb', False)
        self.assertEqual(
            stable_message.submitter, contented_message.submitter)

        stable_message = removeSecurityProxy(stable_message)

        # As it happens, this message is more recent than the happy one.
        # This doesn't matter except it makes our test more predictable.
        stable_message.date_created += timedelta(0, 0, 1)
        poft = poftset.getForPersonPOFile(translator, self.stable_pofile)
        self.assertEqual(poft.latest_message, stable_message)
        removeSecurityProxy(poft).date_last_touched = (
            stable_message.date_created)

        # Now the migration script runs.  This also carries the
        # POFileTranslator record for stable_message into trunk_pofile.
        # The one for contented_message disappears in the process.
        self.script._mergePOTMsgSets(self.templates)
        self.script._mergeTranslationMessages(self.templates)

        poft = poftset.getForPersonPOFile(translator, self.trunk_pofile)
        self.assertEqual(poft.latest_message, stable_message)


class TestMapMessages(TestCaseWithFactory, TranslatedProductMixin):
    """Test _mapExistingMessages and friends."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.layer.switchDbUser('postgres')
        super(TestMapMessages, self).setUp(user='mark@hbd.com')
        super(TestMapMessages, self).setUpProduct()

    def test_NoMessagesToMap(self):
        # Mapping an untranslated POTMsgSet produces an empty dict.
        empty = self.script._mapExistingMessages(self.trunk_potmsgset)
        self.assertEqual(empty, {})

    def test_MapSharedMessage(self):
        # Map existing, shared translation for a POTMsgSet.
        message = self._makeTranslationMessage(
            pofile=self.trunk_pofile, potmsgset=self.trunk_potmsgset,
            text='winslow', diverged=False)

        map = self.script._mapExistingMessages(message.potmsgset)
        key = self.script._getPOTMsgSetTranslationMessageKey(message)
        expected = {key: { self.trunk_template: [message]}}

    def test_MapDivergedMessage(self):
        # Map existing, diverged translation for a POTMsgSet.
        message = self._makeTranslationMessage(
            pofile=self.trunk_pofile, potmsgset=self.trunk_potmsgset,
            text='winslow', diverged=True)

        map = self.script._mapExistingMessages(message.potmsgset)
        key = self.script._getPOTMsgSetTranslationMessageKey(message)
        expected = {key: {self.trunk_template: [message]}}

        self.assertEqual(map, expected)

    def test_FindNoUsedMessage(self):
        # Test _findUsedMessage against a case where there are no used
        # messages.
        message = self._makeTranslationMessage(
            pofile=self.trunk_pofile, potmsgset=self.trunk_potmsgset,
            text='godot', diverged=False)
        message.is_current = False
        key = self.script._getPOTMsgSetTranslationMessageKey(message)
        map = {key: {self.trunk_template: [message]}}

        self.assertEqual(self.script._findUsedMessages(map), ({}, {}))

    def test_FindUsedMessages(self):
        # _findUsedMessages maps diverged messages based on template,
        # language, and variant.  The difference for shared messages is
        # that their template is None.
        imported_message = self._makeTranslationMessage(
            pofile=self.trunk_pofile, potmsgset=self.trunk_potmsgset,
            text='pog', diverged=True)
        imported_message.is_current = False
        imported_message.is_imported = True
        current_message = self._makeTranslationMessage(
            pofile=self.trunk_pofile, potmsgset=self.trunk_potmsgset,
            text='klexdigal', diverged=False)

        current_key = self.script._getPOTMsgSetTranslationMessageKey(
            current_message)
        imported_key = self.script._getPOTMsgSetTranslationMessageKey(
            imported_message)

        map = {
            current_key: {self.trunk_template: [current_message]},
            imported_key: { self.trunk_template: [imported_message]},
        }

        expected = (
            {(None, self.dutch, None): current_message},
            {(self.trunk_template, self.dutch, None): imported_message})
        
        self.assertEqual(self.script._findUsedMessages(map), expected)

    def test_ScrubPOTMsgSetTranslationsWithoutDuplication(self):
        # _scrubPOTMsgSetTranslations eliminates duplicated
        # TranslationMessages.  If it doesn't find any, nothing happens.
        message = self._makeTranslationMessage(
            pofile=self.trunk_pofile, potmsgset=self.trunk_potmsgset,
            text='gbzidh', diverged=False)
        map = self.script._scrubPOTMsgSetTranslations(self.trunk_potmsgset)
        key = self.script._getPOTMsgSetTranslationMessageKey(message)
        self.assertEqual(map, {key: {None: [message]}})

    def test_ScrubPOTMsgSetTranslationsWithDuplication(self):
        # If there are duplicate TranslationMessages, one inherits all
        # their is_current/is_imported flags and the others disappear.
        # XXX JeroenVermeulen 2009-06-15
        # spec=message-sharing-prevent-duplicates: We're going to have a
        # unique index for this.  When it becomes impossible to perform
        # this test, both it and _scrubPOTMsgSetTranslations can be
        # retired.
        message1, message2 = self._makeTranslationMessages(
            'tigidou', 'tigidou', trunk_diverged=True, stable_diverged=True)
        message2.is_current = False
        message2.is_imported = True
        message2.potmsgset = self.trunk_potmsgset
        message2.potemplate = self.trunk_template

        map = self.script._scrubPOTMsgSetTranslations(self.trunk_potmsgset)

        message, no_message = self._getMessages()

        # The resulting map has only one of the identical messages.
        key = self.script._getPOTMsgSetTranslationMessageKey(message)
        self.assertEqual(map, {key: {self.trunk_template: [message]}})

        # The remaining message combines the flags from both its
        # predecessors.
        self.assertEqual(
            (message.is_current, message.is_imported),
            (True, True))

    def test_FindCurrentClash(self):
        # _findClashes finds messages that would be "in the way" (as far
        # as the is_current/is_imported flags are concerned) if we try
        # to move a message to another template and potmsgset.
        trunk_message, stable_message = self._makeTranslationMessages(
            'ex', 'why', trunk_diverged=False, stable_diverged=False)
        current_clash, imported_clash, twin = self.script._findClashes(
            stable_message, self.trunk_potmsgset, None)

        # Moving stable_message fully into trunk would clash with
        # trunk_message.
        self.assertEqual(current_clash, trunk_message)

        # There's no conflict for the is_imported flag.
        self.assertEqual(imported_clash, None)

        # Nor does stable_message have a twin in trunk.
        self.assertEqual(twin, None)

    def test_FindImportedClash(self):
        # Finding is_imported clashes works just like finding is_current
        # clashes.
        trunk_message, stable_message = self._makeTranslationMessages(
            'ex', 'why', trunk_diverged=False, stable_diverged=False)

        for message in (trunk_message, stable_message):
            message.is_current = False
            message.is_imported = True

        current_clash, imported_clash, twin = self.script._findClashes(
            stable_message, self.trunk_potmsgset, None)

        self.assertEqual(current_clash, None)
        self.assertEqual(imported_clash, trunk_message)
        self.assertEqual(twin, None)

    def test_FindTwin(self):
        # _findClashes also finds "twin" messages: ones with the same
        # translations, for the same language.
        trunk_message, stable_message = self._makeTranslationMessages(
            'klob', 'klob', trunk_diverged=False, stable_diverged=False)
        trunk_message.is_current = False

        current_clash, imported_clash, twin = self.script._findClashes(
            stable_message, self.trunk_potmsgset, None)

        self.assertEqual(current_clash, None)
        self.assertEqual(imported_clash, None)
        self.assertEqual(twin, trunk_message)

    def test_FindClashesWithTwin(self):
        # Clashes with a twin are ignored; they can be resolved by
        # merging messages.
        trunk_message, stable_message = self._makeTranslationMessages(
            'sniw', 'sniw', trunk_diverged=False, stable_diverged=False)

        current_clash, imported_clash, twin = self.script._findClashes(
            stable_message, self.trunk_potmsgset, None)

        self.assertEqual(current_clash, None)
        self.assertEqual(imported_clash, None)
        self.assertEqual(twin, trunk_message)

    def test_FindClashesWithNonTwin(self):
        # _findClashes can find both a twin and a "flag conflict" in the
        # same place.
        trunk_message, stable_message = self._makeTranslationMessages(
            'sniw', 'sniw', trunk_diverged=False, stable_diverged=False)
        trunk_message.is_current = False
        current_message = self._makeTranslationMessage(
            self.trunk_pofile, self.trunk_potmsgset, 'gah', False)

        current_clash, imported_clash, twin = self.script._findClashes(
            stable_message, self.trunk_potmsgset, None)

        self.assertEqual(current_clash, current_message)
        self.assertEqual(imported_clash, None)
        self.assertEqual(twin, trunk_message)

    def test_FindCurrentClashFromDicts(self):
        # Like test_FindCurrentClash, but using cached dicts.
        trunk_message, stable_message = self._makeTranslationMessages(
            'ex', 'why', trunk_diverged=False, stable_diverged=False)

        trunk_key = self.script._getPOTMsgSetTranslationMessageKey(
            trunk_message)
        stable_key = self.script._getPOTMsgSetTranslationMessageKey(
            stable_message)

        existing = self.script._mapExistingMessages(self.trunk_potmsgset)
        current, imported = self.script._findUsedMessages(existing)
        current_clash, imported_clash, twin = (
            self.script._findClashesFromDicts(
                existing, current, imported, stable_message))

        self.assertEqual(current_clash, trunk_message)
        self.assertEqual(imported_clash, None)
        self.assertEqual(twin, None)


    def test_FindImportedClashFromDicts(self):
        # Like test_FindImportedClash, but using cached dicts.
        trunk_message, stable_message = self._makeTranslationMessages(
            'ex', 'why', trunk_diverged=False, stable_diverged=False)

        for message in (trunk_message, stable_message):
            message.is_current = False
            message.is_imported = True

        existing = self.script._mapExistingMessages(self.trunk_potmsgset)
        current, imported = self.script._findUsedMessages(existing)
        current_clash, imported_clash, twin = (
            self.script._findClashesFromDicts(
                existing, current, imported, stable_message))

        self.assertEqual(current_clash, None)
        self.assertEqual(imported_clash, trunk_message)
        self.assertEqual(twin, None)

    def test_FindTwinFromDicts(self):
        # Like test_FindTwin, but using cached dicts.
        trunk_message, stable_message = self._makeTranslationMessages(
            'klob', 'klob', trunk_diverged=False, stable_diverged=False)
        trunk_message.is_current = False

        existing = self.script._mapExistingMessages(self.trunk_potmsgset)
        current, imported = self.script._findUsedMessages(existing)
        current_clash, imported_clash, twin = (
            self.script._findClashesFromDicts(
                existing, current, imported, stable_message))

        self.assertEqual(current_clash, None)
        self.assertEqual(imported_clash, None)
        self.assertEqual(twin, trunk_message)

    def test_FindClashesWithTwinFromDicts(self):
        # Like test_FindClashesWithTwin, but using cached dicts.
        trunk_message, stable_message = self._makeTranslationMessages(
            'sniw', 'sniw', trunk_diverged=False, stable_diverged=False)

        existing = self.script._mapExistingMessages(self.trunk_potmsgset)
        current, imported = self.script._findUsedMessages(existing)
        current_clash, imported_clash, twin = (
            self.script._findClashesFromDicts(
                existing, current, imported, stable_message))

        self.assertEqual(current_clash, None)
        self.assertEqual(imported_clash, None)
        self.assertEqual(twin, trunk_message)

    def test_FindClashesWithNonTwinFromDicts(self):
        # Like test_FindClashesWithNonTwin, but using cached dicts.
        trunk_message, stable_message = self._makeTranslationMessages(
            'sniw', 'sniw', trunk_diverged=False, stable_diverged=False)
        trunk_message.is_current = False
        current_message = self._makeTranslationMessage(
            self.trunk_pofile, self.trunk_potmsgset, 'gah', False)

        existing = self.script._mapExistingMessages(self.trunk_potmsgset)
        current, imported = self.script._findUsedMessages(existing)
        current_clash, imported_clash, twin = (
            self.script._findClashesFromDicts(
                existing, current, imported, stable_message))

        self.assertEqual(current_clash, current_message)
        self.assertEqual(imported_clash, None)
        self.assertEqual(twin, trunk_message)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
