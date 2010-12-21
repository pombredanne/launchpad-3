# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Translation Importer tests."""

__metaclass__ = type

from zope.component import getUtility
from zope.interface.verify import verifyObject

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.registry.interfaces.product import IProductSet
from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.potemplate import IPOTemplateSet
from lp.translations.interfaces.translationfileformat import (
    TranslationFileFormat,
    )
from lp.translations.interfaces.translationimporter import (
    ITranslationImporter,
    )
from lp.translations.utilities.translation_common_format import (
    TranslationMessageData,
    )
from lp.translations.utilities.translation_import import (
    importers,
    is_identical_translation,
    TranslationImporter,
    )


class TranslationImporterTestCase(TestCaseWithFactory):
    """Class test for translation importer component"""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TranslationImporterTestCase, self).setUp()
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

    def testTemplateSuffixes(self):
        """Check for changes in filename suffixes that identify templates."""
        self.assertEqual(
            self.translation_importer.template_suffixes,
            ['.pot', 'en-US.xpi'])

    def _assertIsNotTemplate(self, path):
        self.assertFalse(
            self.translation_importer.isTemplateName(path),
            'Mistook "%s" for a template name.' % path)

    def _assertIsTemplate(self, path):
        self.assertTrue(
            self.translation_importer.isTemplateName(path),
            'Failed to recognize "%s" as a template name.' % path)

    def testTemplateNameRecognition(self):
        """Test that we can recognize templates by name."""
        self._assertIsNotTemplate("sales.xls")
        self._assertIsNotTemplate("dotlessname")

        self._assertIsTemplate("bar.pot")
        self._assertIsTemplate("foo/bar.pot")
        self._assertIsTemplate("foo.bar.pot")
        self._assertIsTemplate("en-US.xpi")
        self._assertIsTemplate("translations/en-US.xpi")

        self._assertIsNotTemplate("pt_BR.po")
        self._assertIsNotTemplate("pt_BR.xpi")
        self._assertIsNotTemplate("pt-BR.xpi")

    def testHiddenFilesRecognition(self):
        # Hidden files and directories (leading dot) are recognized.
        hidden_files = [
            ".hidden.pot",
            ".hidden/foo.pot",
            "po/.hidden/foo.pot",
            "po/.hidden.pot",
            "bla/.hidden/foo/bar.pot",
            ]
        visible_files = [
            "not.hidden.pot",
            "not.hidden/foo.pot",
            "po/not.hidden/foo.pot",
            "po/not.hidden.pot",
            "bla/not.hidden/foo/bar.pot",
            ]
        for path in hidden_files:
            self.assertTrue(
                self.translation_importer.isHidden(path),
                'Failed to recognized "%s" as a hidden file.' % path)
        for path in visible_files:
            self.assertFalse(
                self.translation_importer.isHidden(path),
                'Failed to recognized "%s" as a visible file.' % path)

    def _assertIsTranslation(self, path):
        self.assertTrue(
            self.translation_importer.isTranslationName(path),
            'Failed to recognize "%s" as a translation file name.' % path)

    def _assertIsNotTranslation(self, path):
        self.assertFalse(
            self.translation_importer.isTranslationName(path),
            'Mistook "%s for a translation file name.' % path)

    def testTranslationNameRecognition(self):
        """Test that we can recognize translation files by name."""
        self._assertIsNotTranslation("sales.xls")
        self._assertIsNotTranslation("dotlessname")

        self._assertIsTranslation("el.po")
        self._assertIsTranslation("po/el.po")
        self._assertIsTranslation("po/package-el.po")
        self._assertIsTranslation("po/package-zh_TW.po")
        self._assertIsTranslation("en-GB.xpi")
        self._assertIsTranslation("translations/en-GB.xpi")

        self._assertIsNotTranslation("hi.pot")
        self._assertIsNotTranslation("po/hi.pot")
        self._assertIsNotTranslation("en-US.xpi")
        self._assertIsNotTranslation("translations/en-US.xpi")

    def testIsIdenticalTranslation(self):
        """Test `is_identical_translation`."""
        msg1 = TranslationMessageData()
        msg2 = TranslationMessageData()
        msg1.msgid_singular = "foo"
        msg2.msgid_singular = "foo"

        self.assertTrue(is_identical_translation(msg1, msg2),
            "Two blank translation messages do not evaluate as identical.")

        msg1.msgid_plural = "foos"
        self.assertFalse(is_identical_translation(msg1, msg2),
            "Message with fewer plural forms is accepted as identical.")
        msg2.msgid_plural = "splat"
        self.assertFalse(is_identical_translation(msg1, msg2),
            "Messages with different plurals accepted as identical.")
        msg2.msgid_plural = "foos"
        self.assertTrue(is_identical_translation(msg1, msg2),
            "Messages with identical plural forms not accepted as identical.")

        msg1._translations = ["le foo"]
        self.assertFalse(is_identical_translation(msg1, msg2),
            "Failed to distinguish translated message from untranslated one.")
        msg2._translations = ["le foo"]
        self.assertTrue(is_identical_translation(msg1, msg2),
            "Identical translations not accepted as identical.")

        msg1._translations = ["le foo", "les foos"]
        self.assertFalse(is_identical_translation(msg1, msg2),
            "Failed to distinguish message with missing plural translation.")
        msg2._translations = ["le foo", "les foos"]
        self.assertTrue(is_identical_translation(msg1, msg2),
            "Identical plural translations not accepted as equal.")

        msg1._translations = ["le foo", "les foos", "beaucoup des foos"]
        self.assertFalse(is_identical_translation(msg1, msg2),
            "Failed to distinguish message with extra plural translations.")
        msg2._translations = ["le foo", "les foos", "beaucoup des foos", None]
        self.assertTrue(is_identical_translation(msg1, msg2),
            "Identical multi-form messages not accepted as identical.")
