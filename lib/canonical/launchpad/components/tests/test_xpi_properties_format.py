# Copyright 2007 Canonical Ltd. All rights reserved.

__metaclass__ = type

import unittest
from textwrap import dedent

from canonical.launchpad.components.translationformats.mozilla_xpi_importer import (
    PropertyFile, UnsupportedEncoding, PropertySyntaxError)

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


class EscapedQuotesPropertyFileTest(unittest.TestCase):
    """Test class for property file format with escaped quotes.

    Escaped quotes must be stored unescaped.
    """

    content = 'default-first-title-mac = \\\'Something\\\' \\\"more\\\"'

    def runTest(self):
        property_file = PropertyFile('test.properties', dedent(self.content))

        count = 0
        for message in property_file._data:
            if message['msgid'] == u'default-first-title-mac':
                self.assertEqual(
                    message['content'], u'\'Something\' \"more\"')
                count += 1

        # Validate that we actually found the strings so the test is really
        # passing.
        self.assertEqual(count, 1)


class WholeLineCommentPropertyFileTest(unittest.TestCase):
    """Test class for property file format with whole line comment."""

    content = '''
        # Foo bar comment.
        default-first-title-mac = blah

        # This comment should be ignored.

        foo = bar
        '''

    def runTest(self):
        property_file = PropertyFile('test.properties', dedent(self.content))

        count = 0
        for message in property_file._data:
            if message['msgid'] == u'default-first-title-mac':
                self.assertEqual(
                    message['comment'], u'Foo bar comment.')
                count += 1
            if message['msgid'] == u'foo':
                self.assertEqual(
                    message['comment'], None)
                count += 1

        # Validate that we actually found the strings so the test is really
        # passing.
        self.assertEqual(count, 2)


class EndOfLineCommentPropertyFileTest(unittest.TestCase):
    """Test class for property file format with end of line comment."""

    content = '''
        default-first-title-mac = blah // Foo bar comment.

        # This comment should be ignored.
        foo = bar // Something
        '''

    def runTest(self):
        property_file = PropertyFile('test.properties', dedent(self.content))

        count = 0
        for message in property_file._data:
            if message['msgid'] == u'default-first-title-mac':
                self.assertEqual(
                    message['comment'], u'Foo bar comment.')
                # Also, the content should be only the text before the comment
                # tag.
                self.assertEqual(
                    message['content'], u'blah')
                count += 1
            if message['msgid'] == u'foo':
                self.assertEqual(
                    message['comment'], u'Something')
                # Also, the content should be only the text before the comment
                # tag.
                self.assertEqual(
                    message['content'], u'bar')
                count += 1

        # Validate that we actually found the strings so the test is really
        # passing.
        self.assertEqual(count, 2)


class MultiLineCommentPropertyFileTest(unittest.TestCase):
    """Test class for property file format with end of line comment."""

    content = '''
        /* single line comment */
        default-first-title-mac = blah

        /* Multi line comment
           yeah, it's multiple! */
        foo = bar

        /* Even with nested comment tags, we handle this as multiline comment:
        # fooo
        foos = bar
        something = else // Comment me!
        */
        long_comment = foo
        '''

    def runTest(self):
        property_file = PropertyFile('test.properties', dedent(self.content))

        count = 0
        for message in property_file._data:
            if message['msgid'] == u'default-first-title-mac':
                self.assertEqual(
                    message['comment'], u' single line comment ')
                count += 1
            if message['msgid'] == u'foo':
                self.assertEqual(
                    message['comment'],
                    u" Multi line comment\n   yeah, it's multiple! ")
                count += 1
            if message['msgid'] == u'long_comment':
                self.assertEqual(
                    message['comment'],
                    u' Even with nested comment tags, we handle this as' +
                        u' multiline comment:\n# fooo\nfoos = bar\n' +
                        u'something = else // Comment me!')
                count += 1

        # Validate that we actually found the strings so the test is really
        # passing.
        self.assertEqual(count, 3)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(UTF8PropertyFileTest())
    suite.addTest(UnicodeEscapedPropertyFileTest())
    suite.addTest(Latin1PropertyFileTest())
    suite.addTest(TrailingBackslashPropertyFileTest())
    suite.addTest(EscapedQuotesPropertyFileTest())
    suite.addTest(WholeLineCommentPropertyFileTest())
    suite.addTest(EndOfLineCommentPropertyFileTest())
    suite.addTest(MultiLineCommentPropertyFileTest())
    return suite

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(test_suite())
