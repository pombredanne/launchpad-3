# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0102

__metaclass__ = type

import unittest

from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import ZopelessDatabaseLayer
from lp.app.enums import ServiceUsage
from lp.testing.factory import LaunchpadObjectFactory


class TestTranslationSharingPOTemplate(unittest.TestCase):
    """Test behaviour of "sharing" PO templates."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        """Set up context to test in."""
        # Create a product with two series and sharing POTemplates
        # in different series ('devel' and 'stable').
        factory = LaunchpadObjectFactory()
        self.factory = factory
        self.foo = self.factory.makeProduct(
            translations_usage=ServiceUsage.LAUNCHPAD)
        self.foo_devel = factory.makeProductSeries(
            name='devel', product=self.foo)
        self.foo_stable = factory.makeProductSeries(
            name='stable', product=self.foo)

        # POTemplate is a 'sharing' one if it has the same name ('messages').
        self.devel_potemplate = factory.makePOTemplate(
            productseries=self.foo_devel, name="messages")
        self.stable_potemplate = factory.makePOTemplate(self.foo_stable,
                                                        name="messages")

        # Create a single POTMsgSet that is used across all tests,
        # and add it to only one of the POTemplates.
        self.potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate)
        self.potmsgset.setSequence(self.devel_potemplate, 1)

    def test_getPOTMsgSets(self):
        self.potmsgset.setSequence(self.stable_potemplate, 1)

        devel_potmsgsets = list(self.devel_potemplate.getPOTMsgSets())
        stable_potmsgsets = list(self.stable_potemplate.getPOTMsgSets())

        self.assertEquals(devel_potmsgsets, [self.potmsgset])
        self.assertEquals(devel_potmsgsets, stable_potmsgsets)

    def test_getPOTMsgSetByMsgIDText(self):
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate,
                                               singular="Open file",
                                               sequence=2)

        # We can retrieve the potmsgset by its ID text.
        read_potmsgset = self.devel_potemplate.getPOTMsgSetByMsgIDText(
            "Open file")
        self.assertEquals(potmsgset, read_potmsgset)

    def test_getPOTMsgSetBySequence(self):
        sequence = 2
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate,
                                               sequence=sequence)

        # We can retrieve the potmsgset by its sequence.
        read_potmsgset = self.devel_potemplate.getPOTMsgSetBySequence(
            sequence)
        self.assertEquals(potmsgset, read_potmsgset)

        # It's still not present in different sharing PO template.
        read_potmsgset = self.stable_potemplate.getPOTMsgSetBySequence(
            sequence)
        self.assertEquals(read_potmsgset, None)

    def test_getPOTMsgSetByID(self):
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate,
                                               sequence=3)
        id = potmsgset.id

        # We can retrieve the potmsgset by its ID.
        read_potmsgset = self.devel_potemplate.getPOTMsgSetByID(id)
        self.assertEquals(potmsgset, read_potmsgset)

        # Getting this one in a different template doesn't work.
        read_potmsgset = self.stable_potemplate.getPOTMsgSetByID(id)
        self.assertEquals(read_potmsgset, None)

        # Nor can you get an entry with a made up ID.
        random_id = 100000 + self.factory.getUniqueInteger()
        read_potmsgset = self.devel_potemplate.getPOTMsgSetByID(random_id)
        self.assertEquals(read_potmsgset, None)

    def test_hasMessageID(self):
        naked_potemplate = removeSecurityProxy(self.devel_potemplate)
        # Let's get details we need for a POTMsgSet that is
        # already in the POTemplate.
        present_msgid_singular = self.potmsgset.msgid_singular
        present_msgid_plural = self.potmsgset.msgid_plural
        present_context = self.potmsgset.context
        has_message_id = naked_potemplate.hasMessageID(
            present_msgid_singular, present_msgid_plural, present_context)
        self.assertEquals(has_message_id, True)

    def test_hasPluralMessage(self):
        naked_potemplate = removeSecurityProxy(self.devel_potemplate)

        # At the moment, a POTemplate has no plural form messages.
        self.assertEquals(self.devel_potemplate.hasPluralMessage(), False)

        # Let's add a POTMsgSet with plural forms.
        plural_potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate,
                                                      singular="singular",
                                                      plural="plural")
        plural_potmsgset.setSequence(self.devel_potemplate, 4)

        # Now, template contains a plural form message.
        self.assertEquals(self.devel_potemplate.hasPluralMessage(), True)

    def test_expireAllMessages(self):
        devel_potmsgsets = list(self.devel_potemplate.getPOTMsgSets())
        self.assertEquals(len(devel_potmsgsets) > 0, True)

        # Expiring all messages brings the count back to zero.
        self.devel_potemplate.expireAllMessages()
        devel_potmsgsets = list(self.devel_potemplate.getPOTMsgSets())
        self.assertEquals(len(devel_potmsgsets), 0)

        # Expiring all messages even when all are already expired still works.
        self.devel_potemplate.expireAllMessages()
        devel_potmsgsets = list(self.devel_potemplate.getPOTMsgSets())
        self.assertEquals(len(devel_potmsgsets), 0)

    def test_createPOTMsgSetFromMsgIDs(self):
        # We need a 'naked' potemplate to make use of getOrCreatePOMsgID
        # private method.
        naked_potemplate = removeSecurityProxy(self.devel_potemplate)

        # Let's create a new POTMsgSet.
        singular_text = self.factory.getUniqueString()
        msgid_singular = naked_potemplate.getOrCreatePOMsgID(singular_text)
        potmsgset = self.devel_potemplate.createPOTMsgSetFromMsgIDs(
            msgid_singular=msgid_singular)
        self.assertEquals(potmsgset.msgid_singular, msgid_singular)

        # And let's add it to the devel_potemplate.
        potmsgset.setSequence(self.devel_potemplate, 5)
        devel_potmsgsets = list(self.devel_potemplate.getPOTMsgSets())
        self.assertEquals(len(devel_potmsgsets), 2)

        # Creating it with a different context also works.
        msgid_context = self.factory.getUniqueString()
        potmsgset_context = self.devel_potemplate.createPOTMsgSetFromMsgIDs(
            msgid_singular=msgid_singular, context=msgid_context)
        self.assertEquals(potmsgset_context.msgid_singular, msgid_singular)
        self.assertEquals(potmsgset_context.context, msgid_context)

    def test_getOrCreateSharedPOTMsgSet(self):
        # Let's create a new POTMsgSet.
        singular_text = self.factory.getUniqueString()
        potmsgset = self.devel_potemplate.getOrCreateSharedPOTMsgSet(
            singular_text, None)

        # If we try to add a POTMsgSet with identical strings,
        # we get back the existing one.
        same_potmsgset = self.devel_potemplate.getOrCreateSharedPOTMsgSet(
            singular_text, None)
        self.assertEquals(potmsgset, same_potmsgset)

        # And even if we do it in the shared template, existing
        # POTMsgSet is returned.
        shared_potmsgset = self.stable_potemplate.getOrCreateSharedPOTMsgSet(
            singular_text, None)
        self.assertEquals(potmsgset, shared_potmsgset)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
