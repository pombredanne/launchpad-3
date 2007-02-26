# Copyright 2004-2005 Canonical Ltd. All rights reserved.

__metaclass__ = type

import pytz
import unittest
from StringIO import StringIO
from datetime import datetime

from canonical.launchpad.components.poexport import export_rows
from canonical.launchpad.helpers import test_diff

class TestPOTemplate:
    """Pretend to be a potemplate for testing purposes."""

    def __init__(self, has_plural_message=False):
        self.has_plural_message = has_plural_message

    def hasPluralMessage(self):
        return self.has_plural_message


class FakeSQLObjectClass:
    """Help class to let us create a fake POFile class."""
    def __init__(self, **kw):
        self.__dict__.update(kw)


class TestPOFile:
    """Pretend to be a pofile for testing purposes."""

    def __init__(self, language_code='es', pluralforms=2,
                 pluralexpression='n != 1'):
        mock_email = FakeSQLObjectClass(
            email='kk@pleasure-dome.com')
        mock_person = FakeSQLObjectClass(
            browsername='Kubla Kahn',
            preferredemail=mock_email,
            isTeam=lambda: False)
        self.latestsubmission = FakeSQLObjectClass(
            person=mock_person,
            datecreated = datetime.fromtimestamp(
                1000000000, pytz.timezone('UTC')))
        self.language = FakeSQLObjectClass(
            code=language_code,
            pluralforms=pluralforms,
            pluralexpression=pluralexpression)

pofile_cy = TestPOFile(language_code='cy', pluralforms=4,
    pluralexpression='n==1 ? 0 : n==2 ? 1 : (n != 8 || n != 11) ? 2 : 3')
pofile_es = TestPOFile(language_code='es', pluralforms=2,
    pluralexpression='n != 1')
pofile_ja = TestPOFile(
    language_code='ja', pluralforms=1, pluralexpression='0')


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
            # Remove X-Rosetta-Export-Date line to prevent time bombs in
            # tests.
            lines = [line for line in pofiles[i].split('\n')
                     if not line.startswith('"X-Rosetta-Export-Date:')]
            for j in range(len(lines)):
                if expected_pofiles[i][j] != lines[j]:
                    # The output is different.
                    raise AssertionError, (
                        "Output doesn't match:\n\n %s" % test_diff(
                            expected_pofiles[i], lines))


class BasicExportTest(ExportTest):
    """Test exporting various basic cases."""

    def runTest(self):
        prototype1 = TestRow(
            potemplate=TestPOTemplate(), pofile=pofile_es,
            language='es')

        prototype2 = TestRow(
            potemplate=TestPOTemplate(has_plural_message=True),
            pofile=pofile_cy,
            language='cy',
            poheader=(prototype1.poheader +
                'Plural-Forms: nplurals=2; plural=(n!=1);\n'))

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
            'msgstr ""',
            '"Content-Type: text/plain; charset=UTF-8\\n"',
            '"Last-Translator: Kubla Kahn <kk@pleasure-dome.com>\\n"',
            '"PO-Revision-Date: 2001-09-09 01:46+0000\\n"',
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
            '"Plural-Forms: nplurals=4; plural=(n==1 ? 0 : n==2 ? 1 : (n != 8 || n != 11) "',
            '"? 2 : 3);\\n"',
            '"Last-Translator: Kubla Kahn <kk@pleasure-dome.com>\\n"',
            '"PO-Revision-Date: 2001-09-09 01:46+0000\\n"',
            '',
            'msgid "foo"',
            'msgid_plural "foos"',
            'msgstr[0] "cy-FOO1"',
            'msgstr[1] "cy-FOO2"',
            'msgstr[2] ""',
            'msgstr[3] ""',
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
            translation=nihongo_unicode, potemplate=TestPOTemplate(),
            pofile=pofile_ja)

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
            'msgstr ""',
            '"Content-Type: text/plain; charset=UTF-8\\n"',
            '"Last-Translator: Kubla Kahn <kk@pleasure-dome.com>\\n"',
            '"PO-Revision-Date: 2001-09-09 01:46+0000\\n"',
            '',
            'msgid "Japanese"',
            'msgstr "\xe6\x97\xa5\xe6\x9c\xac\xe8\xaa\x9e"',
        ])

        expected_pofiles.append([
            'msgid ""',
            'msgstr ""',
            '"Content-Type: text/plain; charset=Shift-JIS\\n"',
            '"Last-Translator: Kubla Kahn <kk@pleasure-dome.com>\\n"',
            '"PO-Revision-Date: 2001-09-09 01:46+0000\\n"',
            '',
            'msgid "Japanese"',
            'msgstr "\x93\xfa\x96\x7b\x8c\xea"',
        ])

        expected_pofiles.append([
            'msgid ""',
            'msgstr ""',
            '"Content-Type: text/plain; charset=EUC-JP\\n"',
            '"Last-Translator: Kubla Kahn <kk@pleasure-dome.com>\\n"',
            '"PO-Revision-Date: 2001-09-09 01:46+0000\\n"',
            '',
            'msgid "Japanese"',
            'msgstr "\xc6\xfc\xcb\xdc\xb8\xec"',
        ])

        self.test_export(rows, expected_pofiles)

class BrokenEncodingExportTest(ExportTest):
    """Test what happens when the content and the encoding don't agree.

    If an IPOFile fails to encode using the character set specified in the
    header, the header should be changed to specify to UTF-8 and the IPOFile
    exported accordingly.
    """

    def runTest(self):
        prototype1 = TestRow(language='es', potsequence=1, posequence=1,
            msgidpluralform=0, translationpluralform=0, msgid="a",
            translation=u'\u00e1', potemplate=TestPOTemplate(),
            pofile=pofile_es)

        rows = [
            prototype1.clone(potemplate=TestPOTemplate(),
                poheader='Content-Type: text/plain; charset=ASCII\n'),
        ]

        expected_pofiles = [[
            'msgid ""',
            'msgstr ""',
            '"Content-Type: text/plain; charset=UTF-8\\n"',
            '"Last-Translator: Kubla Kahn <kk@pleasure-dome.com>\\n"',
            '"PO-Revision-Date: 2001-09-09 01:46+0000\\n"',
            '',
            'msgid "a"',
            'msgstr "\xc3\xa1"',
        ]]

        self.test_export(rows, expected_pofiles)


class IncompletePluralMessageTest(ExportTest):
    """Test that plural message sets which are missing some translations are
    correctly exported.
    """

    def runTest(self):
        prototype = TestRow(
            potemplate=TestPOTemplate(has_plural_message=True),
            pofile=pofile_es,
            language='es',
            poheader=(
                'Content-Type: text/plain; charset=UTF-8\n'))

        rows = [
            prototype.clone(potsequence=1, posequence=1, msgidpluralform=0,
                translationpluralform=0, msgid="1 dead horse",
                translation=u"ning\u00fan caballo muerto"),
            prototype.clone(potsequence=1, posequence=1, msgidpluralform=1,
                translationpluralform=0, msgid="%d dead horses",
                translation="no tengo caballos muertos"),
            ]

        expected_pofiles = [[
            'msgid ""',
            'msgstr ""',
            '"Content-Type: text/plain; charset=UTF-8\\n"',
            '"Last-Translator: Kubla Kahn <kk@pleasure-dome.com>\\n"',
            '"PO-Revision-Date: 2001-09-09 01:46+0000\\n"',
            '"Plural-Forms: nplurals=2; plural=(n != 1);\\n"',
            '',
            'msgid "1 dead horse"',
            'msgid_plural "%d dead horses"',
            'msgstr[0] "ning\xc3\xban caballo muerto"',
            'msgstr[1] ""'
        ]]

        self.test_export(rows, expected_pofiles)

class InactiveTranslationTest(ExportTest):
    """Test that inactive translations do not get exported."""

    def runTest(self):
        prototype = TestRow(
            potemplate=TestPOTemplate(),
            pofile=pofile_es,
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
            'msgstr ""',
            '"Content-Type: text/plain; charset=UTF-8\\n"',
            '"Last-Translator: Kubla Kahn <kk@pleasure-dome.com>\\n"',
            '"PO-Revision-Date: 2001-09-09 01:46+0000\\n"',
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
            pofile=pofile_es,
            poheader=(
                'Project-Id-Version: foo\n'
                'Content-Type: text/plain; charset=UTF-8\n'
                'Last-Translator: Aleister Crowley <crowley@golden-dawn.org>\n'
                'PO-Revision-Date: 1947-12-01 20:21+0100\n'
                'Language-Team: Spanish <es@li.org>\n'
                'Plural-Forms: nplurals=2; plural=(n!=1);\n'))

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
            pofile=pofile_es,
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
            '"Last-Translator: Kubla Kahn <kk@pleasure-dome.com>\\n"',
            '"PO-Revision-Date: 2001-09-09 01:46+0000\\n"',
            '',
            'msgid "foo"',
            'msgstr "bar"',
        ]]

        self.test_export([test_row], expected_pofiles)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(BasicExportTest())
    suite.addTest(EncodingExportTest())
    suite.addTest(BrokenEncodingExportTest())
    suite.addTest(IncompletePluralMessageTest())
    suite.addTest(InactiveTranslationTest())
    suite.addTest(HeaderUpdateTest())
    suite.addTest(DomainHeaderUpdateTest())
    return suite

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(test_suite())

