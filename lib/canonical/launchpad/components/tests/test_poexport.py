# Copyright 2004-2005 Canonical Ltd. All rights reserved.

__metaclass__ = type

import pytz
import unittest
from datetime import datetime

from canonical.launchpad.components.poexport import export_rows
from canonical.launchpad.helpers import test_diff

class TestPOTemplate:
    """Pretend to be a potemplate for testing purposes."""

    def __init__(self, has_plural_message=False):
        self.has_plural_message = has_plural_message

    def hasPluralMessage(self):
        return self.has_plural_message


class TestRow:
    """Pretend to be a database row for testing purposes."""

    def __init__(self, **kw):
        self.columns = {
            'pofile': None,
            'variant': None,
            'isfuzzy': False,
            'potheader': 'Project-Id-Version: foo\n',
            'poheader': 'Content-Type: text/plain; charset=UTF-8\n',
            'potopcomment': '',
            'pofuzzyheader': False,
            'flagscomment': None,
            'pocommenttext': '',
            'sourcecomment': '',
            'filereferences': '',
            'activesubmission': 65,
            'popluralforms': 2,
        }
        self.columns.update(kw)

        for key, value in self.columns.iteritems():
            setattr(self, key, value)

    def clone(self, **kw):
        columns = dict(self.columns)
        columns.update(kw)

        return TestRow(**columns)

class ExportTest(unittest.TestCase):
    """Base class for export tests."""

    def test_export(self, rows, expected_pofiles):
        """Export a set of rows and compare the generated PO files to expected
        values.

        Each member of expected_pofiles is a list of lines (without
        terminating newlines).
        """

        pofiles = []

        def test_pofile_output(potemplate, language, variant, pofile):
            pofiles.append(pofile)

        export_rows(rows, test_pofile_output)

        self.assertEqual(len(expected_pofiles), len(pofiles))

        for i in range(len(expected_pofiles)):
            lines = pofiles[i].split('\n')

            self.assertEqual(expected_pofiles[i], lines,
                "Output doesn't match:\n\n" +
                test_diff(expected_pofiles[i], lines))

class BasicExportTest(ExportTest):
    """Test exporting various basic cases."""

    def runTest(self):
        prototype1 = TestRow(potemplate=TestPOTemplate(), language='es')

        prototype2 = TestRow(
            potemplate=TestPOTemplate(has_plural_message=True),
            language='cy',
            poheader=(prototype1.poheader +
                'Plural-Forms: nplurals=2; plural=(n!=1)\n'))

        rows = [
            # Simple PO file.
            prototype1.clone(potsequence=1, posequence=1, msgidpluralform=0,
                translationpluralform=0, msgid='ding', translation='es-DING'),
            prototype1.clone(potsequence=2, posequence=2, msgidpluralform=0,
                translationpluralform=0, msgid='dong', translation='es-DONG'),

            # Plural message. (Each (msgidpluralform, translationpluralform)
            # combination gets generated: (0, 0), (0, 1), (1, 0), (1, 1), where
            # (msgid, translation) vary in accordance with the plural form
            # indices.)
            prototype2.clone(potsequence=1, posequence=1, msgidpluralform=0,
                translationpluralform=0, msgid='foo', translation='cy-FOO1'),
            prototype2.clone(potsequence=1, posequence=1, msgidpluralform=1,
                translationpluralform=0, msgid='foos', translation='cy-FOO1'),
            prototype2.clone(potsequence=1, posequence=1, msgidpluralform=0,
                translationpluralform=1, msgid='foo', translation='cy-FOO2'),
            prototype2.clone(potsequence=1, posequence=1, msgidpluralform=1,
                translationpluralform=1, msgid='foos', translation='cy-FOO2'),

            # Fuzzy message.
            prototype2.clone(potsequence=2, posequence=2, msgidpluralform=0,
                translationpluralform=0, msgid='zig', translation='zag',
                isfuzzy=True),

            # Obsolete message.
            prototype2.clone(potsequence=0, posequence=3, msgidpluralform=0,
                translationpluralform=0, msgid='zot', translation='zat'),

            # A c-format message.
            prototype2.clone(potsequence=4, posequence=4, msgidpluralform=0,
                translationpluralform=0, msgid='zip', translation='zap',
                flagscomment=', c-format'),

            # A message with various commenty things.
            prototype2.clone(potsequence=5, posequence=5, msgidpluralform=0,
                translationpluralform=0, msgid='zog', translation='zug',
                pocommenttext='tove\n', sourcecomment='borogove\n',
                filereferences='rath\n'),
        ]

        expected_pofiles = []

        expected_pofiles.append([
            'msgid ""',
            'msgstr "Content-Type: text/plain; charset=UTF-8\\n"',
            '',
            'msgid "ding"',
            'msgstr "es-DING"',
            '',
            'msgid "dong"',
            'msgstr "es-DONG"',
        ])

        expected_pofiles.append([
            'msgid ""',
            'msgstr ""',
            '"Content-Type: text/plain; charset=UTF-8\\n"',
            '"Plural-Forms: nplurals=2; plural=(n!=1)\\n"',
            '',
            'msgid "foo"',
            'msgid_plural "foos"',
            'msgstr[0] "cy-FOO1"',
            'msgstr[1] "cy-FOO2"',
            '',
            '#, fuzzy',
            'msgid "zig"',
            'msgstr "zag"',
            '',
            '#, c-format',
            'msgid "zip"',
            'msgstr "zap"',
            '',
            '#tove',
            '#. borogove',
            '#: rath',
            'msgid "zog"',
            'msgstr "zug"',
            '',
            '#~ msgid "zot"',
            '#~ msgstr "zat"',
        ])

        self.test_export(rows, expected_pofiles)

class EncodingExportTest(ExportTest):
    """Test that PO headers specifying character sets are respected."""

    def runTest(self):
        # This is the word 'Japanese' in Japanese, in Unicode.

        nihongo_unicode = u'\u65e5\u672c\u8a9e'

        # Rows representing the same PO file three times. Each is identical
        # except for the charset declaration in the header.

        prototype1 = TestRow(language='ja', potsequence=1, posequence=1,
            msgidpluralform=0, translationpluralform=0, msgid="Japanese",
            translation=nihongo_unicode, potemplate=TestPOTemplate())

        rows = [
            prototype1.clone(potemplate=TestPOTemplate(),
                poheader='Content-Type: text/plain; charset=UTF-8\n'),
            prototype1.clone(potemplate=TestPOTemplate(),
                poheader='Content-Type: text/plain; charset=Shift-JIS\n'),
            prototype1.clone(potemplate=TestPOTemplate(),
                poheader='Content-Type: text/plain; charset=EUC-JP\n'),
        ]

        expected_pofiles = []

        expected_pofiles.append([
            'msgid ""',
            'msgstr "Content-Type: text/plain; charset=UTF-8\\n"',
            '',
            'msgid "Japanese"',
            'msgstr "\xe6\x97\xa5\xe6\x9c\xac\xe8\xaa\x9e"',
        ])

        expected_pofiles.append([
            'msgid ""',
            'msgstr "Content-Type: text/plain; charset=Shift-JIS\\n"',
            '',
            'msgid "Japanese"',
            'msgstr "\x93\xfa\x96\x7b\x8c\xea"',
        ])

        expected_pofiles.append([
            'msgid ""',
            'msgstr "Content-Type: text/plain; charset=EUC-JP\\n"',
            '',
            'msgid "Japanese"',
            'msgstr "\xc6\xfc\xcb\xdc\xb8\xec"',
        ])

        self.test_export(rows, expected_pofiles)

class IncompletePluralMessageTest(ExportTest):
    """Test that plural message sets which are missing some translations are
    correctly exported.
    """

    def runTest(self):
        prototype = TestRow(
            potemplate=TestPOTemplate(has_plural_message=True),
            language='es',
            popluralforms=3,
            poheader=(
                'Content-Type: text/plain; charset=UTF-8\n'
                'Plural-Forms: nplurals=3; plural=(n==0)?0:(n==1)?1:2\n'))

        rows = [
            prototype.clone(potsequence=1, posequence=1, msgidpluralform=0,
                translationpluralform=0, msgid="1 dead horse",
                translation=u"ning\u00fan caballo muerto"),
            prototype.clone(potsequence=1, posequence=1, msgidpluralform=1,
                translationpluralform=0, msgid="%d dead horses",
                translation="no tengo caballos muertos"),
            prototype.clone(potsequence=1, posequence=1, msgidpluralform=0,
                translationpluralform=2, msgid="1 dead horse",
                translation="%d caballos muertos"),
            ]

        expected_pofiles = [[
            'msgid ""',
            'msgstr ""',
            '"Content-Type: text/plain; charset=UTF-8\\n"',
            '"Plural-Forms: nplurals=3; plural=(n==0)?0:(n==1)?1:2\\n"',
            '',
            'msgid "1 dead horse"',
            'msgid_plural "%d dead horses"',
            'msgstr[0] "ning\xc3\xban caballo muerto"',
            'msgstr[1] ""',
            'msgstr[2] "%d caballos muertos"'
        ]]

        self.test_export(rows, expected_pofiles)

class InactiveTranslationTest(ExportTest):
    """Test that inactive translations do not get exported."""

    def runTest(self):
        prototype = TestRow(
            potemplate=TestPOTemplate(),
            language='es',
            msgidpluralform=0,
            translationpluralform=0)

        rows = [
            prototype.clone(potsequence=1, posequence=1, msgid="one",
                translation="uno"),
            prototype.clone(potsequence=2, posequence=2, msgid="two",
                translation="dos", activesubmission=None),
            prototype.clone(potsequence=3, posequence=3, msgid="three",
                translation="tres"),
        ]

        expected_pofiles = [[
            'msgid ""',
            'msgstr "Content-Type: text/plain; charset=UTF-8\\n"',
            '',
            'msgid "one"',
            'msgstr "uno"',
            '',
            'msgid "two"',
            'msgstr ""',
            '',
            'msgid "three"',
            'msgstr "tres"',
        ]]

        self.test_export(rows, expected_pofiles)

class HeaderUpdateTest(ExportTest):
    """Test that headers get updated properly."""

    def runTest(self):
        # Create a mock PO file with a mock last submission with a mock person
        # with a mock email address.

        class Mock:
            def __init__(self, **kw):
                self.__dict__.update(kw)

        mock_email = Mock(
            email='kk@pleasure-dome.com')
        mock_person = Mock(
            browsername='Kubla Kahn',
            preferredemail=mock_email,
            isTeam=lambda: False)
        mock_submission = Mock(
            person=mock_person,
            datecreated = datetime.fromtimestamp(
                1000000000, pytz.timezone('UTC')))
        mock_pofile = Mock(
            latestsubmission=mock_submission)

        # The existing header has both fields that should be preserved,
        # fields that need updating and the plural form entry that should not
        # be exported.

        test_row = TestRow(
            potemplate=TestPOTemplate(),
            potsequence=1,
            posequence=1,
            language='es',
            msgid='foo',
            translation='bar',
            msgidpluralform=0,
            translationpluralform=0,
            pofile=mock_pofile,
            poheader=(
                'Project-Id-Version: foo\n'
                'Content-Type: text/plain; charset=UTF-8\n'
                'Last-Translator: Aleister Crowley <crowley@golden-dawn.org>\n'
                'PO-Revision-Date: 1947-12-01 20:21+0100\n'
                'Language-Team: Spanish <es@li.org>\n'
                'Plural-Forms: nplurals=2; plural=(n!=1)\n'))

        expected_pofiles = [[
            'msgid ""',
            'msgstr ""',
            '"Project-Id-Version: foo\\n"',
            '"Content-Type: text/plain; charset=UTF-8\\n"',
            '"Last-Translator: Kubla Kahn <kk@pleasure-dome.com>\\n"',
            '"PO-Revision-Date: 2001-09-09 01:46+0000\\n"',
            '"Language-Team: Spanish <es@li.org>\\n"',
            '',
            'msgid "foo"',
            'msgstr "bar"',
        ]]

        self.test_export([test_row], expected_pofiles)

class DomainHeaderUpdateTest(ExportTest):
    """Test that the Domain header gets copied into the PO file when it's
    present in the PO template.
    """

    def runTest(self):
        test_row = TestRow(
            potemplate=TestPOTemplate(),
            potsequence=1,
            posequence=1,
            language='es',
            msgid='foo',
            translation='bar',
            msgidpluralform=0,
            translationpluralform=0,
            potheader=(
                'Domain: blahdomain\n'),
            poheader=(
                'Project-Id-Version: foo\n'
                'Content-Type: text/plain; charset=UTF-8\n'
                'Language-Team: Spanish <es@li.org>\n'))

        expected_pofiles = [[
            'msgid ""',
            'msgstr ""',
            '"Project-Id-Version: foo\\n"',
            '"Content-Type: text/plain; charset=UTF-8\\n"',
            '"Language-Team: Spanish <es@li.org>\\n"',
            '"Domain: blahdomain\\n"',
            '',
            'msgid "foo"',
            'msgstr "bar"',
        ]]

        self.test_export([test_row], expected_pofiles)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(BasicExportTest())
    suite.addTest(EncodingExportTest())
    suite.addTest(IncompletePluralMessageTest())
    suite.addTest(InactiveTranslationTest())
    suite.addTest(HeaderUpdateTest())
    suite.addTest(DomainHeaderUpdateTest())
    return suite

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(test_suite())

