# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from datetime import timedelta
from unittest import TestLoader

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.pofiletranslator import (
    IPOFileTranslatorSet)
from lp.translations.scripts.message_sharing_migration import (
    merge_potmsgsets, merge_translationmessages)
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

        merge_potmsgsets(self.templates)

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

        merge_potmsgsets(self.templates)

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

        merge_potmsgsets(self.templates)

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

        The matching POTMsgSets will be merged by the merge_potmsgsets
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

        merge_potmsgsets(self.templates)

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

        merge_potmsgsets(self.templates)

        self.assertEqual(self._getTranslations(), ('bar', 'bar'))

    def test_mergingSharedMessages(self):
        # Shared TranslationMessages don't clash as a result of merging.
        # Instead, the most representative shared message survives as
        # shared.  The translation that "loses out" becomes diverged.
        trunk_message, stable_message = self._makeTranslationMessages(
            'bar', 'splat', trunk_diverged=False, stable_diverged=False)
        trunk_message.is_current = True
        stable_message.is_current = True

        merge_potmsgsets(self.templates)

        # The POTMsgSets are now merged.
        potmsgset = self.trunk_template.getPOTMsgSetByMsgIDText('foo')

        self.assertEqual(self._getTranslations(), ('bar', 'splat'))

        # They share the same TranslationMessage.
        trunk_message, stable_message = self._getMessages()
        self.assertEqual(trunk_message.potemplate, None)
        self.assertEqual(stable_message.potemplate, self.stable_template)

    def test_mergingIdenticalSuggestions(self):
        # Identical suggestions can be merged without breakage.
        trunk_message, stable_message = self._makeTranslationMessages(
            'bar', 'bar', trunk_diverged=False, stable_diverged=False)
        trunk_message.is_current = False
        stable_message.is_current = False

        merge_potmsgsets(self.templates)

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

        merge_potmsgsets(self.templates)

        trunk_message, stable_message = self._getMessages()
        self.assertEqual(trunk_message.potemplate, None)

        # There are still two separate messages; the second (least
        # representative) one is diverged.
        self.assertNotEqual(trunk_message, stable_message)
        self.assertEqual(stable_message.potemplate, self.stable_template)


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

        merge_translationmessages(self.templates)

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

        merge_potmsgsets(self.templates)
        merge_translationmessages(self.templates)

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

        merge_potmsgsets(self.templates)
        merge_translationmessages(self.templates)

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

        merge_potmsgsets(self.templates)
        merge_translationmessages(self.templates)

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

        merge_potmsgsets(self.templates)
        merge_translationmessages(self.templates)

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

        merge_potmsgsets(self.templates)
        merge_translationmessages(self.templates)

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
        merge_potmsgsets(self.templates)
        merge_translationmessages(self.templates)

        poft = poftset.getForPersonPOFile(translator, self.trunk_pofile)
        self.assertEqual(poft.latest_message, stable_message)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
