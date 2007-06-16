# Copyright 2007 Canonical Ltd. All rights reserved.

__metaclass__ = type

import unittest

from canonical.launchpad.translationformat.mozilla_xpi_importer import DtdFile
from canonical.launchpad.interfaces import TranslationFormatInvalidInputError


class DtdFormatTestCase(unittest.TestCase):
    """Test class for dtd file format."""

    def test_UTF8DtdFileTest(self):
        """This test makes sure that we handle UTF-8 encoding files."""

        content = (
            '<!ENTITY utf8.message "\xc2\xbfQuieres? \xc2\xa1S\xc3\xad!">')

        dtd_file = DtdFile('test.dtd', content)

        count = 0
        for message in dtd_file.messages:
            if message.msgid == u'utf8.message':
                self.assertEqual(
                    message.translations, [u'\xbfQuieres? \xa1S\xed!'])
                count += 1

        # Validate that we actually found the string so the test is really
        # passing.
        self.assertEqual(count, 1)


    def test_Latin1DtdFileTest(self):
        """This test makes sure that we detect bad encodings."""

        content = '<!ENTITY latin1.message "\xbfQuieres? \xa1S\xed!">\n'

        detected = False
        try:
            dtd_file = DtdFile('test.dtd', content)
        except TranslationFormatInvalidInputError:
            detected = True

        # Whether the unsupported encoding was detected.
        self.assertEqual(detected, True)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DtdFormatTestCase))
    return suite
