# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Gettext PO importer tests."""

__metaclass__ = type

import unittest
import transaction
from zope.component import getUtility
from zope.interface.verify import verifyObject

from canonical.launchpad.translationformat.gettext_po_importer import (
    GettextPOImporter)
from canonical.launchpad.interfaces import (
    IPersonSet, IProductSet, ITranslationFormatImporter,
    ITranslationImportQueue, TranslationFileFormat)
from canonical.testing import LaunchpadZopelessLayer

test_template = r'''
msgid ""
msgstr ""
"PO-Revision-Date: 2005-05-03 20:41+0100\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Content-Type: text/plain; charset=UTF-8\n"

msgid "foo"
msgstr ""
'''

test_translation_file = r'''
msgid ""
msgstr ""
"PO-Revision-Date: 2005-05-03 20:41+0100\n"
"Last-Translator: Carlos Perello Marin <carlos@canonical.com>\n"
"Content-Type: text/plain; charset=UTF-8\n"

msgid "foo"
msgstr "blah"
'''


class GettextPOImporterTestCase(unittest.TestCase):
    """Class test for gettext's .po file imports"""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        # Add a new entry for testing purposes. It's a template one.
        self.translation_import_queue = getUtility(ITranslationImportQueue)
        template_path = 'po/testing.pot'
        is_published = True
        personset = getUtility(IPersonSet)
        importer = personset.getByName('carlos')
        productset = getUtility(IProductSet)
        firefox = productset.getByName('firefox')
        productseries = firefox.getSeries('trunk')
        template_entry = self.translation_import_queue.addOrUpdateEntry(
            template_path, test_template, is_published, importer,
            productseries=productseries)

        # Add another one, a translation file.
        pofile_path = 'po/es.po'
        translation_entry = self.translation_import_queue.addOrUpdateEntry(
            pofile_path, test_translation_file, is_published, importer,
            productseries=productseries)

        transaction.commit()
        self.template_importer = GettextPOImporter()
        self.template_file = self.template_importer.parse(template_entry)
        self.translation_importer = GettextPOImporter()
        self.translation_file = self.translation_importer.parse(
            translation_entry)

    def testInterface(self):
        """Check whether the object follows the interface."""
        self.failUnless(
            verifyObject(ITranslationFormatImporter, self.template_importer),
            "GettextPOImporter doesn't conform to ITranslationFormatImporter"
                "interface.")

    def testFormat(self):
        """Check whether GettextPOImporter say that handles PO file format."""
        format = self.template_importer.getFormat(test_template)
        self.failUnless(
            format == TranslationFileFormat.PO,
            'GettextPOImporter format expected PO but got %s' % format.name)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(GettextPOImporterTestCase))
    return suite

