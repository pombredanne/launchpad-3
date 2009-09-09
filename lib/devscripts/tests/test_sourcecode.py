# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type

from StringIO import StringIO
import unittest

from devscripts.sourcecode import interpret_config, parse_config_file


class TestParseConfigFile(unittest.TestCase):
    """Tests for the config file parser."""

    def makeFile(self, contents):
        return StringIO(contents)

    def test_empty(self):
        # Parsing an empty config file returns an empty sequence.
        empty_file = self.makeFile("")
        self.assertEqual([], list(parse_config_file(empty_file)))

    def test_single_value(self):
        # Parsing a file containing a single key=value pair returns a sequence
        # containing the (key, value) as a list.
        config_file = self.makeFile("key=value")
        self.assertEqual(
            [['key', 'value']], list(parse_config_file(config_file)))

    def test_comment_ignored(self):
        # If a line begins with a '#', then its a comment.
        comment_only = self.makeFile('# foo')
        self.assertEqual([], list(parse_config_file(comment_only)))

    def test_optional_value(self):
        # Lines in the config file can have a third optional entry.
        config_file = self.makeFile('key=value=optional')
        self.assertEqual(
            [['key', 'value', 'optional']],
            list(parse_config_file(config_file)))

    def test_whitespace_stripped(self):
        # Any whitespace around any of the tokens in the config file are
        # stripped out.
        config_file = self.makeFile('  key = value =  optional   ')
        self.assertEqual(
            [['key', 'value', 'optional']],
            list(parse_config_file(config_file)))


class TestInterpretConfiguration(unittest.TestCase):
    """Tests for the configuration interpreter."""

    def test_empty(self):
        # An empty configuration stream means no configuration.
        config = interpret_config([])
        self.assertEqual({}, config)

    def test_key_value(self):
        # A (key, value) pair without a third optional value is returned in
        # the configuration as a dictionary entry under 'key' with '(value,
        # False)' as its value.
        config = interpret_config([['key', 'value']])
        self.assertEqual({'key': ('value', False)}, config)

    def test_key_value_optional(self):
        # A (key, value, optional) entry is returned in the configuration as a
        # dictionary entry under 'key' with '(value, True)' as its value.
        config = interpret_config([['key', 'value', 'optional']])
        self.assertEqual({'key': ('value', True)}, config)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
