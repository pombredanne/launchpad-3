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

        # There is a single message.
        self.assertEquals(len(dtd_file.messages), 1)
        message = dtd_file.messages[0]

        self.assertEquals(
            [u'\xbfQuieres? \xa1S\xed!'], message.translations)

    def test_Latin1DtdFileTest(self):
        """This test makes sure that we detect bad encodings."""

        content = '<!ENTITY latin1.message "\xbfQuieres? \xa1S\xed!">\n'

        self.assertRaises(TranslationFormatInvalidInputError, DtdFile, 'test.dtd', content)


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
