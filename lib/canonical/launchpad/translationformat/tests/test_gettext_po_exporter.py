# Copyright 2004-2007 Canonical Ltd. All rights reserved.

__metaclass__ = type

import doctest
import unittest
from textwrap import dedent
from zope.interface.verify import verifyObject

from canonical.launchpad.helpers import test_diff
from canonical.launchpad.interfaces import ITranslationFormatExporter
from canonical.launchpad.translationformat import gettext_po_exporter
from canonical.launchpad.translationformat.gettext_po_exporter import (
    GettextPOExporter)
from canonical.launchpad.translationformat.gettext_po_parser import (
    POParser)
from canonical.testing import LaunchpadZopelessLayer


class GettextPOExporterTestCase(unittest.TestCase):
    """Class test for gettext's .po file exports"""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.parser = POParser()
        self.translation_exporter = GettextPOExporter()

    def _compareImportAndExport(self, import_file, export_file):
        """Compare imported file and the export we got from it.

        :param import_file: buffer with the source file content.
        :param export_file: buffer with the output file content.
        """
        import_lines = [line for line in import_file.split('\n')]
        # Remove X-Launchpad-Export-Date line to prevent time bombs in tests.
        export_lines = [
            line for line in export_file.split('\n')
            if (not line.startswith('"X-Launchpad-Export-Date:') and
                not line.startswith('"X-Generator: Launchpad'))]

        for i in range(len(import_lines)):
            self.assertEqual(
                export_lines[i], import_lines[i],
                "Output doesn't match:\n\n %s" % test_diff(
                    import_lines, export_lines))

    def testInterface(self):
        """Check whether the object follows the interface."""
        self.failUnless(
            verifyObject(ITranslationFormatExporter, self.translation_exporter),
            "GettextPOExporter doesn't follow the interface")

    def testGeneralExport(self):
        """Check different kind of messages export."""

        pofile_cy = dedent('''
            msgid ""
            msgstr ""
            "Project-Id-Version: foo\\n"
            "Report-Msgid-Bugs-To: \\n"
            "POT-Creation-Date: 2007-07-09 03:39+0100\\n"
            "PO-Revision-Date: 2001-09-09 01:46+0000\\n"
            "Last-Translator: Kubla Kahn <kk@pleasure-dome.com>\\n"
            "Language-Team: LANGUAGE <LL@li.org>\\n"
            "MIME-Version: 1.0\\n"
            "Content-Type: text/plain; charset=UTF-8\\n"
            "Content-Transfer-Encoding: 8bit\\n"
            "Plural-Forms: nplurals=4; plural=n==1 ? 0 : n==2 ? 1 : (n != 8 || n != 11) ? "
            "2 : 3;\\n"

            msgid "foo"
            msgid_plural "foos"
            msgstr[0] "cy-F001"
            msgstr[1] "cy-F002"
            msgstr[2] ""
            msgstr[3] ""

            #, fuzzy
            msgid "zig"
            msgstr "zag"

            #, c-format
            msgid "zip"
            msgstr "zap"

            # tove
            #. borogove
            #: rath
            msgid "zog"
            msgstr "zug"

            #~ msgid "zot"
            #~ msgstr "zat"
            ''')
        cy_translation_file = self.parser.parse(pofile_cy)
        cy_translation_file.is_template = False
        cy_translation_file.language_code = 'cy'
        cy_translation_file.path = 'po/cy.po'
        cy_translation_file.translation_domain = 'testing'
        exported_cy_file = self.translation_exporter.exportTranslationFiles(
            [cy_translation_file])

        self._compareImportAndExport(
            pofile_cy.strip(), exported_cy_file.read().strip())

    def testEncodingExport(self):
        """Test that PO headers specifying character sets are respected."""

        def compare(self, pofile):
            "Compare the original text with the exported one."""
            # This is the word 'Japanese' in Japanese, in Unicode.
            nihongo_unicode = u'\u65e5\u672c\u8a9e'
            translation_file = self.parser.parse(pofile)
            translation_file.is_template = False
            translation_file.language_code = 'ja'
            translation_file.path = 'po/ja.po'
            translation_file.translation_domain = 'testing'

            # We are sure that 'Japanese' is correctly stored as Unicode so
            # we are sure the exporter does its job instead of just export
            # what was imported.
            self.assertEqual(
                translation_file.messages[0].translations,
                [nihongo_unicode])

            exported_file = self.translation_exporter.exportTranslationFiles(
                [translation_file])

            self._compareImportAndExport(
                pofile.strip(), exported_file.read().strip())

        # File representing the same PO file three times. Each is identical
        # except for the charset declaration in the header.
        pofiles = [
            dedent('''
                msgid ""
                msgstr ""
                "Project-Id-Version: foo\\n"
                "Report-Msgid-Bugs-To: \\n"
                "POT-Creation-Date: 2007-07-09 03:39+0100\\n"
                "PO-Revision-Date: 2001-09-09 01:46+0000\\n"
                "Last-Translator: Kubla Kahn <kk@pleasure-dome.com>\\n"
                "Language-Team: LANGUAGE <LL@li.org>\\n"
                "MIME-Version: 1.0\\n"
                "Content-Type: text/plain; charset=UTF-8\\n"
                "Content-Transfer-Encoding: 8bit\\n"

                msgid "Japanese"
                msgstr "\xe6\x97\xa5\xe6\x9c\xac\xe8\xaa\x9e"
                '''),
            dedent('''
                msgid ""
                msgstr ""
                "Project-Id-Version: foo\\n"
                "Report-Msgid-Bugs-To: \\n"
                "POT-Creation-Date: 2007-07-09 03:39+0100\\n"
                "PO-Revision-Date: 2001-09-09 01:46+0000\\n"
                "Last-Translator: Kubla Kahn <kk@pleasure-dome.com>\\n"
                "Language-Team: LANGUAGE <LL@li.org>\\n"
                "MIME-Version: 1.0\\n"
                "Content-Type: text/plain; charset=Shift-JIS\\n"
                "Content-Transfer-Encoding: 8bit\\n"

                msgid "Japanese"
                msgstr "\x93\xfa\x96\x7b\x8c\xea"
                '''),
            dedent('''
                msgid ""
                msgstr ""
                "Project-Id-Version: foo\\n"
                "Report-Msgid-Bugs-To: \\n"
                "POT-Creation-Date: 2007-07-09 03:39+0100\\n"
                "PO-Revision-Date: 2001-09-09 01:46+0000\\n"
                "Last-Translator: Kubla Kahn <kk@pleasure-dome.com>\\n"
                "Language-Team: LANGUAGE <LL@li.org>\\n"
                "MIME-Version: 1.0\\n"
                "Content-Type: text/plain; charset=EUC-JP\\n"
                "Content-Transfer-Encoding: 8bit\\n"

                msgid "Japanese"
                msgstr "\xc6\xfc\xcb\xdc\xb8\xec"
                ''')
            ]
        for pofile in pofiles:
            compare(self, pofile)


    def testBrokenEncodingExport(self):
        """Test what happens when the content and the encoding don't agree.

        If a pofile fails to encode using the character set specified in the
        header, the header should be changed to specify to UTF-8 and the
        pofile exported accordingly.
        """

        pofile = dedent('''
            msgid ""
            msgstr ""
            "Project-Id-Version: foo\\n"
            "Report-Msgid-Bugs-To: \\n"
            "POT-Creation-Date: 2007-07-09 03:39+0100\\n"
            "PO-Revision-Date: 2001-09-09 01:46+0000\\n"
            "Last-Translator: Kubla Kahn <kk@pleasure-dome.com>\\n"
            "Language-Team: LANGUAGE <LL@li.org>\\n"
            "MIME-Version: 1.0\\n"
            "Content-Type: text/plain; charset=%s\\n"
            "Content-Transfer-Encoding: 8bit\\n"

            msgid "a"
            msgstr "%s"
            ''')
        translation_file = self.parser.parse(
            pofile % ('ISO-8859-15', '\xe1'))
        translation_file.is_template = False
        translation_file.language_code = 'es'
        translation_file.path = 'po/es.po'
        translation_file.translation_domain = 'testing'
        # Force the export as ASCII, it will not be possible because
        # translation is not available in that encoding and thus, we should
        # get an export in UTF-8.
        translation_file.header.charset = 'ASCII'
        exported_file = self.translation_exporter.exportTranslationFiles(
            [translation_file])

        self._compareImportAndExport(
            pofile.strip() % ('UTF-8', '\xc3\xa1'),
            exported_file.read().strip())

    def testIncompletePluralMessage(self):
        """Test export correctness for partial plural messages."""

        pofile = dedent('''
            msgid ""
            msgstr ""
            "Project-Id-Version: foo\\n"
            "Report-Msgid-Bugs-To: \\n"
            "POT-Creation-Date: 2007-07-09 03:39+0100\\n"
            "PO-Revision-Date: 2001-09-09 01:46+0000\\n"
            "Last-Translator: Kubla Kahn <kk@pleasure-dome.com>\\n"
            "Language-Team: LANGUAGE <LL@li.org>\\n"
            "MIME-Version: 1.0\\n"
            "Content-Type: text/plain; charset=UTF-8\\n"
            "Content-Transfer-Encoding: 8bit\\n"
            "Plural-Forms: nplurals=2; plural=(n != 1);\\n"

            msgid "1 dead horse"
            msgid_plural "%%d dead horses"
            msgstr[0] "ning\xc3\xban caballo muerto"
            %s''')
        translation_file = self.parser.parse(pofile % (''))
        translation_file.is_template = False
        translation_file.language_code = 'es'
        translation_file.path = 'po/es.po'
        translation_file.translation_domain = 'testing'
        exported_file = self.translation_exporter.exportTranslationFiles(
            [translation_file])

        self._compareImportAndExport(
            pofile.strip() % 'msgstr[1] ""', exported_file.read().strip())


def test_suite():
    # Run gettext po exporter doc tests.
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(gettext_po_exporter))
    suite.addTest(unittest.makeSuite(GettextPOExporterTestCase))
    return suite
