# Copyright 2007 Canonical Ltd. All rights reserved.

__metaclass__ = type

import unittest
from textwrap import dedent

from canonical.launchpad.components.rosettaformats.mozilla_xpi import (
    PropertyFile, UnsupportedEncoding)

class BaseEncodingPropertyFileTest(unittest.TestCase):
    """Test class for property file format.

    This is a base class to check different encodings.

    Child class should define self.content like the following example, but
    using the encoding that is being tested:

    content = '''
        default-first-title-mac=Introducci\u00F3n
        default-last-title-mac=Conclusi\u00F3n
        '''
    """


    def runTest(self):
        property_file = PropertyFile('test.properties', dedent(self.content))

        count = 0
        for message in property_file._data:
            if message['msgid'] == u'default-first-title-mac':
                self.assertEqual(message['content'], u'Introducci\xf3n')
                count += 1
            elif message['msgid'] == u'default-last-title-mac':
                self.assertEqual(message['content'], u'Conclusi\xf3n')
                count += 1

        # Validate that we actually found the strings so the test is really
        # passing.
        self.assertEqual(count, 2)


class UTF8PropertyFileTest(BaseEncodingPropertyFileTest):
    """Test class for utf-8 property file format.

    This test makes sure that we handle UTF-8 encoding files.
    """

    content = '''
        default-first-title-mac = Introducci\xc3\xb3n
        default-last-title-mac = Conclusi\xc3\xb3n
        '''


class UnicodeEscapedPropertyFileTest(BaseEncodingPropertyFileTest):
    """Test class for unicode-escaped property file format.

    This test makes sure that we handle unicode escaped files.
    """

    content = '''
        default-first-title-mac=Introducci\u00F3n
        default-last-title-mac=Conclusi\u00F3n
        '''


class Latin1PropertyFileTest(unittest.TestCase):
    """Test class for latin1 property file format.

    This test makes sure that we detect bad encodings.
    """

    content = '''
        default-first-title-mac = Introducci\xf3n
        default-last-title-mac = Conclusi\xf3n
        '''

    def runTest(self):
        detected = False
        try:
            property_file = PropertyFile(
                'test.properties', dedent(self.content))
        except UnsupportedEncoding:
            detected = True

        # Whether the unsupported encoding was detected.
        self.assertEqual(detected, True)


class TrailingBackslashPropertyFileTest(unittest.TestCase):
    """Test class for property file format with trailing backslash.

    A trailing backslash as last char in the line continue the string in the
    following document line.
    """

    content = '''
default-first-title-mac=Introd\
ucci\u00F3n
'''

    def runTest(self):
        property_file = PropertyFile('test.properties', dedent(self.content))

        count = 0
        for message in property_file._data:
            if message['msgid'] == u'default-first-title-mac':
                self.assertEqual(message['content'], u'Introducci\xf3n')
                count += 1

        # Validate that we actually found the strings so the test is really
        # passing.
        self.assertEqual(count, 1)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(UTF8PropertyFileTest())
    suite.addTest(UnicodeEscapedPropertyFileTest())
    suite.addTest(Latin1PropertyFileTest())
    suite.addTest(TrailingBackslashPropertyFileTest())
    return suite

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(test_suite())
