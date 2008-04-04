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

        expected = {u'default-first-title-mac': [u'Introducci\xf3n'],
                    u'default-last-title-mac': [u'Conclusi\xf3n']}
        parsed = dict([(message.msgid_singular, message.translations)
                   for message in property_file.messages])
        self.assertEquals(expected, parsed)

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
        self.assertRaises(
            TranslationFormatInvalidInputError, PropertyFile,
            'test.properties', content)

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

        expected = {u'default-first-title-mac': [u'Introducci\xf3n']}
        parsed = dict([(message.msgid_singular, message.translations)
                   for message in property_file.messages])
        self.assertEquals(expected, parsed)

    def test_EscapedQuotesPropertyFileTest(self):
        """Test whether escaped quotes are well handled.

        Escaped quotes must be stored unescaped.
        """
        content = 'default-first-title-mac = \\\'Something\\\' \\\"more\\\"'

        property_file = PropertyFile('test.properties', dedent(content))

        expected = {u'default-first-title-mac': [u'\'Something\' \"more\"']}
        parsed = dict([(message.msgid_singular, message.translations)
                   for message in property_file.messages])
        self.assertEquals(expected, parsed)

    def test_WholeLineCommentPropertyFileTest(self):
        """Test whether whole line comments are well handled."""
        content = '''
            # Foo bar comment.
            default-first-title-mac = blah

            # This comment should be ignored.

            foo = bar
            '''

        property_file = PropertyFile('test.properties', dedent(content))
        expected = {u'default-first-title-mac': u'Foo bar comment.\n',
                    u'foo': None}
        parsed = dict([(message.msgid_singular, message.source_comment)
                   for message in property_file.messages])
        self.assertEquals(expected, parsed)

    def test_EndOfLineCommentPropertyFileTest(self):
        """Test whether end of line comments are well handled."""

        content = '''
            default-first-title-mac = blah // Foo bar comment.

            # This comment should be ignored.
            foo = bar // Something
            '''

        property_file = PropertyFile('test.properties', dedent(content))
        expected_comments = {
            u'default-first-title-mac': u'Foo bar comment.\n',
            u'foo': u'Something\n'
            }
        parsed_comments = dict(
            [(message.msgid_singular, message.source_comment)
             for message in property_file.messages])

        self.assertEquals(expected_comments, parsed_comments)

        expected_translations = {
            u'default-first-title-mac': [u'blah'],
            u'foo': [u'bar']
            }
        parsed_translations = dict([(message.msgid_singular,
                                     message.translations)
                   for message in property_file.messages])

        self.assertEquals(expected_translations, parsed_translations)

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
        expected = {
            u'default-first-title-mac': u' single line comment \n',
            u'foo': u" Multi line comment\n   yeah, it's multiple! \n",
            u'long_comment': (
                u' Even with nested comment tags, we handle this as' +
                u' multiline comment:\n# fooo\nfoos = bar\n' +
                u'something = else // Comment me!\n')
            }
        parsed = dict([(message.msgid_singular, message.source_comment)
                   for message in property_file.messages])
        self.assertEquals(expected, parsed)

    def test_InvalidLinePropertyFileTest(self):
        """Test whether an invalid line is ignored."""
        content = '''
            # Foo bar comment.
            default-first-title-mac = blah

            # This comment should be ignored.
            crappy-contnet
            foo = bar
            '''

        property_file = PropertyFile('test.properties', dedent(content))
        expected = {u'default-first-title-mac': u'Foo bar comment.\n',
                    u'foo': None}
        parsed = dict([(message.msgid_singular, message.source_comment)
                   for message in property_file.messages])
        self.assertEquals(expected, parsed)

    def test_MultilinePropertyFileTest(self):
        """Test parsing of multiline entries."""
        content = (
            'multiline-key = This is the first one\\nThis is the second one.')
        property_file = PropertyFile('test.properties', content)
        expected = {
            u'multiline-key': (
                [u'This is the first one\nThis is the second one.'])
            }
        parsed = dict([(message.msgid_singular, message.translations)
                   for message in property_file.messages])
        self.assertEquals(expected, parsed)


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
