# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Translation Importer tests."""

__metaclass__ = type

import transaction

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.services.log.logger import DevNullLogger
from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.matchers import Provides
from lp.translations.enums import RosettaImportStatus
from lp.translations.interfaces.translationfileformat import (
    TranslationFileFormat,
    )
from lp.translations.interfaces.translationimporter import (
    ITranslationImporter,
    )
from lp.translations.utilities.translation_common_format import (
    TranslationMessageData,
    )
from lp.translations.utilities.sanitize import MixedNewlineMarkersError
from lp.translations.utilities.translation_import import (
    importers,
    is_identical_translation,
    message_text_attributes,
    POFileImporter,
    POTFileImporter,
    TranslationImporter,
    verify_message_newline_consistency,
    )


class FakeImportQueueEntry:
    by_maintainer = True
    format = TranslationFileFormat.PO
    content = None

    def __init__(self, potemplate, pofile=None):
        self.importer = potemplate.owner
        self.potemplate = potemplate
        self.pofile = pofile


class FakeTranslationFile:
    header = None


class FakeParser:
    uses_source_string_msgids = False

    def parse(self, entry):
        return FakeTranslationFile()


class TranslationImporterTestCase(TestCaseWithFactory):
    """Class test for translation importer component"""
    layer = LaunchpadZopelessLayer

    def testInterface(self):
        """Check whether the object follows the interface."""
        self.assertThat(TranslationImporter(), Provides(ITranslationImporter))

    def testGetImporterByFileFormat(self):
        """Check whether we get the right importer from the file format."""
        importer = TranslationImporter()
        self.assertIsNot(
            None,
            importer.getTranslationFormatImporter(TranslationFileFormat.PO))
        self.assertIsNot(
            None,
            importer.getTranslationFormatImporter(
                TranslationFileFormat.KDEPO))
        self.assertIsNot(
            None,
            importer.getTranslationFormatImporter(TranslationFileFormat.XPI))

    def testGetTranslationFileFormatByFileExtension(self):
        """Checked whether file format precedence works correctly."""
        importer = TranslationImporter()

        # Even if the file extension is the same for both PO and KDEPO
        # file formats, a PO file containing no KDE-style messages is
        # recognized as regular PO file.
        self.assertEqual(
            TranslationFileFormat.PO,
            importer.getTranslationFileFormat(
                ".po", u'msgid "message"\nmsgstr ""'))

        # And PO file with KDE-style messages is recognised as KDEPO file.
        self.assertEqual(
            TranslationFileFormat.KDEPO,
            importer.getTranslationFileFormat(
                ".po", u'msgid "_: kde context\nmessage"\nmsgstr ""'))

        self.assertEqual(
            TranslationFileFormat.XPI,
            importer.getTranslationFileFormat(".xpi", u""))

    def testNoConflictingPriorities(self):
        """Check that no two importers for the same file extension have
        exactly the same priority."""
        for file_extension in TranslationImporter().supported_file_extensions:
            priorities = []
            for format, importer in importers.iteritems():
                if file_extension in importer.file_extensions:
                    self.assertNotIn(importer.priority, priorities)
                    priorities.append(importer.priority)

    def testFileExtensionsWithImporters(self):
        """Check whether we get the right list of file extensions handled."""
        self.assertEqual(
            ['.po', '.pot', '.xpi'],
            TranslationImporter().supported_file_extensions)

    def testTemplateSuffixes(self):
        """Check for changes in filename suffixes that identify templates."""
        self.assertEqual(
            ['.pot', 'en-US.xpi'], TranslationImporter().template_suffixes)

    def _assertIsNotTemplate(self, path):
        self.assertFalse(
            TranslationImporter().isTemplateName(path),
            'Mistook "%s" for a template name.' % path)

    def _assertIsTemplate(self, path):
        self.assertTrue(
            TranslationImporter().isTemplateName(path),
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
        importer = TranslationImporter()
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
                importer.isHidden(path),
                'Failed to recognized "%s" as a hidden file.' % path)
        for path in visible_files:
            self.assertFalse(
                importer.isHidden(path),
                'Failed to recognized "%s" as a visible file.' % path)

    def _assertIsTranslation(self, path):
        self.assertTrue(
            TranslationImporter().isTranslationName(path),
            'Failed to recognize "%s" as a translation file name.' % path)

    def _assertIsNotTranslation(self, path):
        self.assertFalse(
            TranslationImporter().isTranslationName(path),
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

    def test_unseen_messages_stay_intact(self):
        # If an import does not mention a particular msgid, that msgid
        # keeps its current translation.
        pofile = self.factory.makePOFile()
        template = pofile.potemplate
        potmsgset1 = self.factory.makePOTMsgSet(template, sequence=1)
        potmsgset2 = self.factory.makePOTMsgSet(template, sequence=2)
        existing_translation = self.factory.makeCurrentTranslationMessage(
            pofile=pofile, potmsgset=potmsgset1)

        text = """
            msgid ""
            msgstr ""
            "MIME-Version: 1.0\\n"
            "Content-Type: text/plain; charset=UTF-8\\n"
            "Content-Transfer-Encoding: 8bit\\n"
            "X-Launchpad-Export-Date: 2010-11-24\\n"

            msgid "%s"
            msgstr "A translation."
        """ % potmsgset2.msgid_singular.msgid

        entry = self.factory.makeTranslationImportQueueEntry(
            'foo.po', potemplate=template,
            status=RosettaImportStatus.APPROVED, content=text)
        entry.pofile = pofile
        entry.status = RosettaImportStatus.APPROVED
        transaction.commit()

        self.assertTrue(existing_translation.is_current_upstream)
        TranslationImporter().importFile(entry)
        self.assertTrue(existing_translation.is_current_upstream)

    def test_template_importMessage_updates_file_references(self):
        # Importing a template message updates the filereferences on an
        # existing POTMsgSet.
        template = self.factory.makePOTemplate()
        potmsgset = self.factory.makePOTMsgSet(potemplate=template)
        old_file_references = self.factory.getUniqueString()
        new_file_references = self.factory.getUniqueString()
        potmsgset.filereferences = old_file_references
        message = TranslationMessageData()
        message.msgid_singular = potmsgset.singular_text
        message.file_references = new_file_references
        queue_entry = FakeImportQueueEntry(template)
        importer = POTFileImporter(queue_entry, FakeParser(), DevNullLogger())
        importer.importMessage(message)
        self.assertEqual(new_file_references, potmsgset.filereferences)

    def test_translation_importMessage_does_not_update_file_references(self):
        # Importing a translation message does not update the
        # filereferences on an existing POTMsgSet.  (It used to, which
        # is what caused bug 715854).
        pofile = self.factory.makePOFile()
        potmsgset = self.factory.makePOTMsgSet(potemplate=pofile.potemplate)
        old_file_references = self.factory.getUniqueString()
        new_file_references = self.factory.getUniqueString()
        potmsgset.filereferences = old_file_references
        message = TranslationMessageData()
        message.msgid_singular = potmsgset.singular_text
        message.file_references = new_file_references
        queue_entry = FakeImportQueueEntry(pofile.potemplate, pofile)
        importer = POFileImporter(queue_entry, FakeParser(), DevNullLogger())
        importer.importMessage(message)
        self.assertEqual(old_file_references, potmsgset.filereferences)


class FakeMessage:
    msgid_singular = None
    msgid_plural = None
    singular_text = None
    plural_text = None
    translations = ()


class NewlineVerificationTests(TestCase):
    def test_attribute_ok(self):
        # If a message's attributes are None or strings without mixed
        # newlines, then no exception is raise.
        for attr_name in message_text_attributes:
            message = FakeMessage()
            message.msgid_singular = 'no mixed newlines here'
            # The next call doesn't raise an exception.
            verify_message_newline_consistency(message)

    def test_attribute_not_ok(self):
        # If a message's attributes contain mixed newlines, an exception is
        # raised.
        for attr_name in message_text_attributes:
            message = FakeMessage()
            setattr(message, attr_name, 'mixed\rnewlines\n')
            e = self.assertRaises(
                MixedNewlineMarkersError,
                verify_message_newline_consistency, message)
            # The error message mentions the attribute name.
            self.assertEqual(
                e.args[0],
                "%s text ('mixed\\rnewlines\\n') " % attr_name +
                "mixes different newline markers.")

    def test_translations_ok(self):
        # If a message's translations are None or strings without mixed
        # newlines, then no exception is raise.
        message = FakeMessage()
        message.translations = ['no mixed newlines here']
        # The next call doesn't raise an exception.
        verify_message_newline_consistency(message)

    def test_translations_not_ok(self):
        # If a message's translations contain mixed newlines, an exception is
        # raised.
        message = FakeMessage()
        message.translations = ['mixed\rnewlines\n']
        e = self.assertRaises(
            MixedNewlineMarkersError,
            verify_message_newline_consistency, message)
        # The error message mentions the translation index ("0" in this case).
        self.assertEqual(
            e.args[0],
            "translation 0 text ('mixed\\rnewlines\\n') "
            "mixes different newline markers.")
