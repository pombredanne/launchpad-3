# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Translation Importer tests."""

__metaclass__ = type

import unittest
from zope.component import getUtility
from zope.interface.verify import verifyObject

from canonical.launchpad.translationformat import (
    importers, TranslationImporter)
from canonical.launchpad.interfaces import (
    IPersonSet, IProductSet, IPOTemplateSet, ITranslationImporter,
    TranslationFileFormat)
from canonical.testing import LaunchpadZopelessLayer


class TranslationImporterTestCase(unittest.TestCase):
    """Class test for translation importer component"""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        # Add a new entry for testing purposes. It's a template one.
        productset = getUtility(IProductSet)
        evolution = productset.getByName('evolution')
        productseries = evolution.getSeries('trunk')
        potemplateset = getUtility(IPOTemplateSet)
        potemplate_subset = potemplateset.getSubset(
            productseries=productseries)
        evolution_template = potemplate_subset.getPOTemplateByName(
            'evolution-2.2')
        spanish_translation = evolution_template.getPOFileByLang('es')

        self.translation_importer = TranslationImporter()
        self.translation_importer.pofile = spanish_translation
        self.translation_importer.potemplate = evolution_template

    def testInterface(self):
        """Check whether the object follows the interface."""
        self.failUnless(
            verifyObject(ITranslationImporter, self.translation_importer),
            "TranslationImporter doesn't follow the interface")

    def testGetPersonByEmail(self):
        """Check whether we create new persons with the correct explanation.

        When importing a POFile, it may be necessary to create new Person
        entries, to represent the last translators of that POFile.
        """
        test_email = 'danilo@canonical.com'
        personset = getUtility(IPersonSet)

        # The account we are going to use is not yet in Launchpad.
        self.failUnless(
            personset.getByEmail(test_email) is None,
            'There is already an account for %s' % test_email)

        person = self.translation_importer._getPersonByEmail(test_email)

        self.assertEqual(
            person.creation_rationale.name, 'POFILEIMPORT',
            '%s was not created due to a POFile import' % test_email)
        self.assertEqual(
            person.creation_comment,
            'when importing the %s translation of %s' % (
                self.translation_importer.pofile.language.displayname,
                self.translation_importer.potemplate.displayname))

    def testGetImporterByFileFormat(self):
        """Check whether we get the right importer from the file format."""
        po_format_importer = (
            self.translation_importer.getTranslationFormatImporter(
                TranslationFileFormat.PO))

        self.failUnless(po_format_importer is not None, (
            'There is no importer for PO file format!'))

        kdepo_format_importer = (
            self.translation_importer.getTranslationFormatImporter(
                TranslationFileFormat.KDEPO))

        self.failUnless(kdepo_format_importer is not None, (
            'There is no importer for KDE PO file format!'))

        xpi_format_importer = (
            self.translation_importer.getTranslationFormatImporter(
                TranslationFileFormat.XPI))

        self.failUnless(xpi_format_importer is not None, (
            'There is no importer for XPI file format!'))

    def testGetTranslationFileFormatByFileExtension(self):
        """Checked whether file format precedence works correctly."""

        # Even if the file extension is the same for both PO and KDEPO
        # file formats, a PO file containing no KDE-style messages is
        # recognized as regular PO file.
        po_format = self.translation_importer.getTranslationFileFormat(
            ".po", u'msgid "message"\nmsgstr ""')

        self.failUnless(po_format==TranslationFileFormat.PO, (
            'Regular PO file is not recognized as such!'))

        # And PO file with KDE-style messages is recognised as KDEPO file.
        kde_po_format = self.translation_importer.getTranslationFileFormat(
            ".po", u'msgid "_: kde context\nmessage"\nmsgstr ""')

        self.failUnless(kde_po_format==TranslationFileFormat.KDEPO, (
            'KDE PO file is not recognized as such!'))

        xpi_format = self.translation_importer.getTranslationFileFormat(
            ".xpi", u"")

        self.failUnless(xpi_format==TranslationFileFormat.XPI, (
            'Mozilla XPI file is not recognized as such!'))

    def testNoConflictingPriorities(self):
        """Check that no two importers for the same file extension have
        exactly the same priority."""
        all_extensions = self.translation_importer.supported_file_extensions
        for file_extension in all_extensions:
            priorities = []
            for format, importer in importers.iteritems():
                if file_extension in importer.file_extensions:
                    self.failUnless(
                        importer.priority not in priorities,
                        "Duplicate priority %d for file extension %s." % (
                            importer.priority, file_extension))
                    priorities.append(importer.priority)

    def testFileExtensionsWithImporters(self):
        """Check whether we get the right list of file extensions handled."""
        self.assertEqual(
            self.translation_importer.supported_file_extensions,
            ['.po', '.pot', '.xpi'])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TranslationImporterTestCase))
    return suite

