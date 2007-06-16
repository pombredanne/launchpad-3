# Copyright 2007 Canonical Ltd. All rights reserved.

__metaclass__ = type

import unittest
from textwrap import dedent

from canonical.launchpad.translationformat.mozilla_xpi_importer import (
    PropertyFile)
from canonical.launchpad.interfaces import TranslationFormatInvalidInputError

class PropertyFileFormatTestCase(unittest.TestCase):
    """Test class for property file format."""

    def _baseContentEncodingTest(self, content):
        """This is a base function to check different encodings."""
        property_file = PropertyFile('test.properties', dedent(content))

        count = 0
        for message in property_file.messages:
            if message.msgid == u'default-first-title-mac':
                self.assertEqual(message.translations, [u'Introducci\xf3n'])
                count += 1
            elif message.msgid == u'default-last-title-mac':
                self.assertEqual(message.translations, [u'Conclusi\xf3n'])
                count += 1

        # Validate that we actually found the strings so the test is really
        # passing.
        self.assertEqual(count, 2)

    def test_UTF8PropertyFileTest(self):
        """This test makes sure that we handle UTF-8 encoding files."""
        content = '''
            default-first-title-mac = Introducci\xc3\xb3n
            default-last-title-mac = Conclusi\xc3\xb3n
            '''
        self._baseContentEncodingTest(content)

    def test_UnicodeEscapedPropertyFileTest(self):
        """This test makes sure that we handle unicode escaped files."""
        content = '''
            default-first-title-mac=Introducci\u00F3n
            default-last-title-mac=Conclusi\u00F3n
            '''
        self._baseContentEncodingTest(content)

    def test_Latin1PropertyFileTest(self):
        """This test makes sure that we detect bad encodings."""
        content = '''
            default-first-title-mac = Introducci\xf3n
            default-last-title-mac = Conclusi\xf3n
            '''
        detected = False
        try:
            property_file = PropertyFile(
                'test.properties', dedent(content))
        except TranslationFormatInvalidInputError:
            detected = True

        # Whether the unsupported encoding was detected.
        self.assertEqual(detected, True)

    def test_TrailingBackslashPropertyFileTest(self):
        """Test whether trailing backslashes are well handled.

        A trailing backslash as last char in the line continue the string in
        the following document line.
        """
        content = '''
default-first-title-mac=Introd\
ucci\u00F3n
'''
        property_file = PropertyFile('test.properties', dedent(content))

        count = 0
        for message in property_file.messages:
            if message.msgid == u'default-first-title-mac':
                self.assertEqual(message.translations, [u'Introducci\xf3n'])
                count += 1

        # Validate that we actually found the strings so the test is really
        # passing.
        self.assertEqual(count, 1)

    def test_EscapedQuotesPropertyFileTest(self):
        """Test whether escaped quotes are well handled.

        Escaped quotes must be stored unescaped.
        """
        content = 'default-first-title-mac = \\\'Something\\\' \\\"more\\\"'

        property_file = PropertyFile('test.properties', dedent(content))

        count = 0
        for message in property_file.messages:
            if message.msgid == u'default-first-title-mac':
                self.assertEqual(
                    message.translations, [u'\'Something\' \"more\"'])
                count += 1

        # Validate that we actually found the strings so the test is really
        # passing.
        self.assertEqual(count, 1)

    def test_WholeLineCommentPropertyFileTest(self):
        """Test whether whole line comments are well handled."""
        content = '''
            # Foo bar comment.
            default-first-title-mac = blah

            # This comment should be ignored.

            foo = bar
            '''

        property_file = PropertyFile('test.properties', dedent(content))

        count = 0
        for message in property_file.messages:
            if message.msgid == u'default-first-title-mac':
                self.assertEqual(
                    message.source_comment, u'Foo bar comment.')
                count += 1
            if message.msgid == u'foo':
                self.assertEqual(
                    message.source_comment, None)
                count += 1

        # Validate that we actually found the strings so the test is really
        # passing.
        self.assertEqual(count, 2)

    def test_EndOfLineCommentPropertyFileTest(self):
        """Test whether end of line comments are well handled."""

        content = '''
            default-first-title-mac = blah // Foo bar comment.

            # This comment should be ignored.
            foo = bar // Something
            '''

        property_file = PropertyFile('test.properties', dedent(content))

        count = 0
        for message in property_file.messages:
            if message.msgid == u'default-first-title-mac':
                self.assertEqual(
                    message.source_comment, u'Foo bar comment.')
                # Also, the content should be only the text before the comment
                # tag.
                self.assertEqual(
                    message.translations, [u'blah'])
                count += 1
            if message.msgid == u'foo':
                self.assertEqual(
                    message.source_comment, u'Something')
                # Also, the content should be only the text before the comment
                # tag.
                self.assertEqual(
                    message.translations, [u'bar'])
                count += 1

        # Validate that we actually found the strings so the test is really
        # passing.
        self.assertEqual(count, 2)

    def test_MultiLineCommentPropertyFileTest(self):
        """Test whether multiline comments are well handled."""
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

        property_file = PropertyFile('test.properties', dedent(content))

        count = 0
        for message in property_file.messages:
            if message.msgid == u'default-first-title-mac':
                self.assertEqual(
                    message.source_comment, u' single line comment ')
                count += 1
            if message.msgid == u'foo':
                self.assertEqual(
                    message.source_comment,
                    u" Multi line comment\n   yeah, it's multiple! ")
                count += 1
            if message.msgid == u'long_comment':
                self.assertEqual(
                    message.source_comment,
                    u' Even with nested comment tags, we handle this as' +
                        u' multiline comment:\n# fooo\nfoos = bar\n' +
                        u'something = else // Comment me!')
                count += 1

        # Validate that we actually found the strings so the test is really
        # passing.
        self.assertEqual(count, 3)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PropertyFileFormatTestCase))
    return suite
