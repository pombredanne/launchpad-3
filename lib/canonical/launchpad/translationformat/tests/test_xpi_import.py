# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Functional tests for XPI file format"""
__metaclass__ = type

import os.path
import tempfile
import unittest
import zipfile

from zope.component import getUtility

import canonical.launchpad
from canonical.database.sqlbase import commit
from canonical.launchpad.ftests import sync
from canonical.launchpad.interfaces import (
    IPersonSet, IProductSet, IPOTemplateSet, ITranslationImportQueue,
    RosettaImportStatus)
from canonical.launchpad.translationformat.mozilla_xpi_importer import (
    MozillaXpiImporter)
from canonical.testing import LaunchpadZopelessLayer

def get_en_US_xpi_file_to_import():
    """Return an en-US.xpi file object ready to be imported.

    The file is generated from translationformat/tests/firefox-data/es-US.
    """
    # en-US.xpi file is a ZIP file which contains embedded JAR file (which is
    # also a ZIP file) and a couple of other files.  Embedded JAR file is
    # named 'en-US.jar' and contains translatable resources.

    # Get the root path where the data to generate .xpi file is stored.
    test_root = os.path.join(
        os.path.dirname(canonical.launchpad.__file__),
        'translationformat/tests/firefox-data/en-US')

    # First create a en-US.jar file to be included in XPI file.
    jarfile = tempfile.TemporaryFile()
    jar = zipfile.ZipFile(jarfile, 'w')
    jarlist = []
    data_dir = os.path.join(test_root, 'en-US-jar/')
    for root, dirs, files in os.walk(data_dir):
        for name in files:
            relative_dir = root[len(data_dir):].strip('/')
            jarlist.append(os.path.join(relative_dir, name))
    for file_name in jarlist:
        f = open(os.path.join(data_dir, file_name), 'r')
        jar.writestr(file_name, f.read())
    jar.close()
    jarfile.seek(0)

    # Add remaining bits and en-US.jar to en-US.xpi.

    xpifile = tempfile.TemporaryFile()
    xpi = zipfile.ZipFile(xpifile, 'w')
    xpilist = os.listdir(test_root)
    xpilist.remove('en-US-jar')
    for file_name in xpilist:
        f = open(os.path.join(test_root, file_name), 'r')
        xpi.writestr(file_name, f.read())
    xpi.writestr('chrome/en-US.jar', jarfile.read())
    xpi.close()
    xpifile.seek(0)

    return xpifile


class XpiTestCase(unittest.TestCase):
    """XPI file import into Launchpad."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        # Get the importer.
        self.importer = getUtility(IPersonSet).getByName('sabdfl')

        # Get the Firefox template.
        firefox_product = getUtility(IProductSet).getByName('firefox')
        firefox_productseries = firefox_product.getSeries('trunk')
        firefox_potemplate_subset = getUtility(IPOTemplateSet).getSubset(
            productseries=firefox_productseries)
        self.firefox_template = firefox_potemplate_subset.new(
            name='firefox',
            translation_domain='firefox',
            path='en-US.xpi',
            owner=self.importer)
        self.spanish_firefox = self.firefox_template.newPOFile('es')

    def setUpTranslationImportQueueForTemplate(self):
        """Return an ITranslationImportQueueEntry for testing purposes."""
        # Get the file to import.
        en_US_xpi =  get_en_US_xpi_file_to_import()

        # Attach it to the import queue.
        translation_import_queue = getUtility(ITranslationImportQueue)
        published = True
        entry = translation_import_queue.addOrUpdateEntry(
            self.firefox_template.path, en_US_xpi.read(), published,
            self.importer, productseries=self.firefox_template.productseries,
            potemplate=self.firefox_template)

        # We must approve the entry to be able to import it.
        entry.status = RosettaImportStatus.APPROVED
        # The file data is stored in the Librarian, so we have to commit the
        # transaction to make sure it's stored properly.
        commit()

        return entry

    def setUpTranslationImportQueueForTranslation(self):
        """Return an ITranslationImportQueueEntry for testing purposes."""
        # Get the file to import. Given the way XPI file format works, we can
        # just use the same template file like a translation one.
        es_xpi =  get_en_US_xpi_file_to_import()

        # Attach it to the import queue.
        translation_import_queue = getUtility(ITranslationImportQueue)
        published = True
        entry = translation_import_queue.addOrUpdateEntry(
            'translations/es.xpi', es_xpi.read(), published,
            self.importer, productseries=self.firefox_template.productseries,
            potemplate=self.firefox_template, pofile=self.spanish_firefox)

        # We must approve the entry to be able to import it.
        entry.status = RosettaImportStatus.APPROVED

        # The file data is stored in the Librarian, so we have to commit the
        # transaction to make sure it's stored properly.
        commit()

        return entry

    def _assertXpiMessageInvariant(self, message):
        """Check whether invariant part of all messages are correct."""
        # msgid and singular_text are always different except for the keyboard
        # shortcuts which are the 'accesskey' and 'commandkey' ones.
        self.failIf(
            (message.msgid_singular.msgid == message.singular_text and
             message.msgid_singular.msgid not in (
                u'foozilla.menu.accesskey', u'foozilla.menu.commandkey')),
            'msgid and singular_text should be different but both are %s' % (
                message.msgid_singular.msgid))

        # Plural forms should be None as this format is not able to handle
        # them.
        self.assertEquals(message.msgid_plural, None)
        self.assertEquals(message.plural_text, None)

        # There is no way to know whether a comment is from a
        # translator or a developer comment, so we have comenttext
        # always as None and store all comments as source comments.
        self.assertEquals(message.commenttext, u'')

        # This format doesn't support any functionality like .po flags.
        self.assertEquals(message.flagscomment, u'')

    def testTemplateImport(self):
        """Test XPI template file import."""
        # Prepare the import queue to handle a new .xpi import.
        entry = self.setUpTranslationImportQueueForTemplate()

        # Now, we tell the PO template to import from the file data it has.
        self.firefox_template.importFromQueue()

        # The status is now IMPORTED:
        sync(entry)
        self.assertEquals(entry.status, RosettaImportStatus.IMPORTED)

        # Let's validate the content of the messages.
        potmsgsets = list(self.firefox_template.getPOTMsgSets())

        messages_msgid_list = []
        for message in potmsgsets:
            messages_msgid_list.append(message.msgid_singular.msgid)

            # Check the common values for all messages.
            self._assertXpiMessageInvariant(message)

            if message.msgid_singular.msgid == u'foozilla.name':
                # It's a normal message that lacks any comment.

                self.assertEquals(message.singular_text, u'FooZilla!')
                self.assertEquals(
                    message.filereferences,
                    u'en-US.xpi/chrome/en-US.jar/test1.dtd(foozilla.name)')
                self.assertEquals(message.sourcecomment, None)

            elif message.msgid_singular.msgid == u'foozilla.play.fire':
                # This one is also a normal message that has a comment.

                self.assertEquals(
                    message.singular_text, u'Do you want to play with fire?')
                self.assertEquals(
                    message.filereferences,
                    u'en-US.xpi/chrome/en-US.jar/test1.dtd' +
                        u'(foozilla.play.fire)')
                self.assertEquals(
                    message.sourcecomment,
                    u"Translators, don't play with fire!")

            elif message.msgid_singular.msgid == u'foozilla.utf8':
                # Now, we can see that special UTF-8 chars are extracted
                # correctly.
                self.assertEquals(
                    message.singular_text, u'\u0414\u0430\u043d=Day')
                self.assertEquals(
                    message.filereferences,
                    u'en-US.xpi/chrome/en-US.jar/test1.properties:5' +
                        u'(foozilla.utf8)')
                self.assertEquals(message.sourcecomment, None)
            elif message.msgid_singular.msgid == u'foozilla.menu.accesskey':
                # access key is a special notation that is supposed to be
                # translated with a key shortcut.
                self.assertEquals(
                    message.singular_text, u'foozilla.menu.accesskey')
                self.assertEquals(
                    message.filereferences,
                    u'en-US.xpi/chrome/en-US.jar/subdir/test2.dtd' +
                        u'(foozilla.menu.accesskey)')
                # The comment shows the key used when there is no translation,
                # which is noted as the en_US translation.
                self.assertEquals(
                    message.sourcecomment, u"Default key in en_US: 'M'")
            elif message.msgid_singular.msgid == u'foozilla.menu.commandkey':
                # command key is a special notation that is supposed to be
                # translated with a key shortcut.
                self.assertEquals(
                    message.singular_text, u'foozilla.menu.commandkey')
                self.assertEquals(
                    message.filereferences,
                    u'en-US.xpi/chrome/en-US.jar/subdir/test2.dtd' +
                        u'(foozilla.menu.commandkey)')
                # The comment shows the key used when there is no translation,
                # which is noted as the en_US translation.
                self.assertEquals(
                    message.sourcecomment, u"Default key in en_US: 'm'")

        # Check that we got all messages.
        self.assertEquals(
            [u'foozilla.happytitle', u'foozilla.menu.accesskey',
             u'foozilla.menu.commandkey', u'foozilla.menu.title',
             u'foozilla.name', u'foozilla.nocomment', u'foozilla.play.fire',
             u'foozilla.play.ice', u'foozilla.title', u'foozilla.utf8',
             u'foozilla_something'],
            sorted(messages_msgid_list))

    def testTranslationImport(self):
        """Test XPI translation file import."""
        # Prepare the import queue to handle a new .xpi import.
        template_entry = self.setUpTranslationImportQueueForTemplate()
        translation_entry = self.setUpTranslationImportQueueForTranslation()

        # Now, we tell the PO template to import from the file data it has.
        self.firefox_template.importFromQueue()
        # And the Spanish translation.
        self.spanish_firefox.importFromQueue()

        # The status is now IMPORTED:
        sync(translation_entry)
        sync(template_entry)
        self.assertEquals(translation_entry.status,
            RosettaImportStatus.IMPORTED)
        self.assertEquals(template_entry.status, RosettaImportStatus.IMPORTED)

        # Let's validate the content of the messages.
        potmsgsets = list(self.firefox_template.getPOTMsgSets())

        messages = [message.msgid_singular.msgid for message in potmsgsets]
        messages.sort()
        self.assertEquals(
            [u'foozilla.happytitle',
             u'foozilla.menu.accesskey',
             u'foozilla.menu.commandkey',
             u'foozilla.menu.title',
             u'foozilla.name',
             u'foozilla.nocomment',
             u'foozilla.play.fire',
             u'foozilla.play.ice',
             u'foozilla.title',
             u'foozilla.utf8',
             u'foozilla_something'],
            messages)

        potmsgset = self.firefox_template.getPOTMsgSetByMsgIDText(
            u'foozilla.name')
        translation = potmsgset.getCurrentTranslationMessage(
            self.spanish_firefox.language)

        # It's a normal message that lacks any comment.
        self.assertEquals(potmsgset.singular_text, u'FooZilla!')

        # With this first import, published and active texts must
        # match.
        self.assertEquals(
            translation.translations,
            potmsgset.getImportedTranslationMessage(
                self.spanish_firefox.language).translations)

        potmsgset = self.firefox_template.getPOTMsgSetByMsgIDText(
            u'foozilla.menu.accesskey')

        # access key is a special notation that is supposed to be
        # translated with a key shortcut.
        self.assertEquals(
            potmsgset.singular_text, u'foozilla.menu.accesskey')
        # The comment shows the key used when there is no translation,
        # which is noted as the en_US translation.
        self.assertEquals(
            potmsgset.sourcecomment, u"Default key in en_US: 'M'")
        # But for the translation import, we get the key directly.
        self.assertEquals(
            potmsgset.getImportedTranslationMessage(
                self.spanish_firefox.language).translations,
            [u'M'])

        potmsgset = self.firefox_template.getPOTMsgSetByMsgIDText(
            u'foozilla.menu.commandkey')
        # command key is a special notation that is supposed to be
        # translated with a key shortcut.
        self.assertEquals(
            potmsgset.singular_text, u'foozilla.menu.commandkey')
        # The comment shows the key used when there is no translation,
        # which is noted as the en_US translation.
        self.assertEquals(
            potmsgset.sourcecomment, u"Default key in en_US: 'm'")
        # But for the translation import, we get the key directly.
        self.assertEquals(
            potmsgset.getImportedTranslationMessage(
                self.spanish_firefox.language).translations,
            [u'm'])

    def testGetLastTranslator(self):
        """Tests whether we extract last translator information correctly."""
        translation_entry = self.setUpTranslationImportQueueForTranslation()
        importer = MozillaXpiImporter()
        translation_file = importer.parse(translation_entry)

        # Let's try with the translation file, it has valid Last Translator
        # information.
        name, email = translation_file.header.getLastTranslator()
        self.assertEqual(name, u'Carlos Perell\xf3 Mar\xedn')
        self.assertEqual(email, u'carlos@canonical.com')


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
