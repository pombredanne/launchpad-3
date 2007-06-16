# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Gettext PO importer tests."""

__metaclass__ = type

import unittest
import transaction
from zope.component import getUtility
from zope.interface.verify import verifyObject

from canonical.launchpad.translationformat.gettext_po_importer import (
    GettextPoImporter)
from canonical.launchpad.interfaces import (
    IPersonSet, IProductSet, ITranslationFormatImporter,
    ITranslationImportQueue)
from canonical.lp.dbschema import TranslationFileFormat
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


class GettextPoImporterTestCase(unittest.TestCase):
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
        self.template_importer = GettextPoImporter()
        self.template_importer.parse(template_entry)
        self.translation_importer = GettextPoImporter()
        self.translation_importer.parse(translation_entry)

    def testInterface(self):
        """Check whether the object follows the interface."""
        self.failUnless(
            verifyObject(ITranslationFormatImporter, self.template_importer),
            "GettextPoImporter doesn't conform to ITranslationFormatImporter"
                "interface.")

    def testFormat(self):
        """Check whether GettextPoImporter say that handles PO file format."""
        self.failUnless(
            self.template_importer.format == TranslationFileFormat.PO,
            'GettextPoImporter format expected PO but got %s' % (
                self.template_importer.format.name))

    def testGetLastTranslator(self):
        """Tests whether we extract last translator information correctly."""
        # When it's the default one in Gettext (FULL NAME <EMAIL@ADDRESS>),
        # used in templates, we get a tuple with None values.
        name, email = self.template_importer.getLastTranslator()
        self.failUnless(name is None,
            "Didn't detect default Last Translator name")
        self.failUnless(email is None,
            "Didn't detect default Last Translator email")

        # Let's try with the translation file, it has valid Last Translator
        # information.
        name, email = self.translation_importer.getLastTranslator()
        self.assertEqual(name, 'Carlos Perello Marin')
        self.assertEqual(email, 'carlos@canonical.com')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(GettextPoImporterTestCase))
    return suite

