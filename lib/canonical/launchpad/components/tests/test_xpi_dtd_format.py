# Copyright 2007 Canonical Ltd. All rights reserved.

__metaclass__ = type

import unittest
from textwrap import dedent

from canonical.launchpad.components.translationformats.mozilla_xpi_importer import (
    DtdFile, UnsupportedEncoding)


class UTF8DtdFileTest(unittest.TestCase):
    """Test class for dtd file format.

    This test makes sure that we handle UTF-8 encoding files.
    """

    content = '<!ENTITY utf8.message "\xc2\xbfQuieres? \xc2\xa1S\xc3\xad!">'


    def runTest(self):
        dtd_file = DtdFile('test.dtd', self.content)

        count = 0
        for message in dtd_file._data:
            if message['msgid'] == u'utf8.message':
                self.assertEqual(
                    message['content'], u'\xbfQuieres? \xa1S\xed!')
                count += 1

        # Validate that we actually found the string so the test is really
        # passing.
        self.assertEqual(count, 1)


class Latin1DtdFileTest(unittest.TestCase):
    """Test class for dtd file format.

    This test makes sure that we detect bad encodings.
    """

    content = '<!ENTITY latin1.message "\xbfQuieres? \xa1S\xed!">\n'

    def runTest(self):
        detected = False
        try:
            dtd_file = DtdFile('test.dtd', self.content)
        except UnsupportedEncoding:
            detected = True

        # Whether the unsupported encoding was detected.
        self.assertEqual(detected, True)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(UTF8DtdFileTest())
    suite.addTest(Latin1DtdFileTest())
    return suite

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(test_suite())
