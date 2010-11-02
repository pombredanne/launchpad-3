#!/usr/bin/python
#
# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# arch-tag: 52e0c871-49a3-4186-beb8-9817d02d5465

import unittest

import apt_pkg

from lp.archiveuploader.tagfiles import (
    parse_tagfile,
    TagFile,
    TagFileParseError,
    )
from lp.archiveuploader.tests import datadir


class Testtagfiles(unittest.TestCase):

    def testTagFileOnSingular(self):
        """lp.archiveuploader.tagfiles.TagFile should parse a singular stanza
        """
        f = TagFile(file(datadir("singular-stanza"), "r"))
        seenone = False
        for stanza in f:
            self.assertEquals(seenone, False)
            seenone = True
            self.assertEquals("Format" in stanza, True)
            self.assertEquals("Source" in stanza, True)
            self.assertEquals("FooBar" in stanza, False)

    def testTagFileOnSeveral(self):
        """TagFile should parse multiple stanzas."""
        f = TagFile(file(datadir("multiple-stanzas"), "r"))
        seen = 0
        for stanza in f:
            seen += 1
            self.assertEquals("Format" in stanza, True)
            self.assertEquals("Source" in stanza, True)
            self.assertEquals("FooBar" in stanza, False)
        self.assertEquals(seen > 1, True)

    def testCheckParseChangesOkay(self):
        """lp.archiveuploader.tagfiles.parse_tagfile should work on a good
           changes file
        """
        p = parse_tagfile(datadir("good-signed-changes"))

    def testCheckParseBadChangesRaises(self):
        """lp.archiveuploader.tagfiles.parse_chantges should raise
           TagFileParseError on failure
        """
        self.assertRaises(TagFileParseError,
                          parse_tagfile, datadir("badformat-changes"), 1)

    def testCheckParseEmptyChangesRaises(self):
        """lp.archiveuploader.tagfiles.parse_chantges should raise
           TagFileParseError on empty
        """
        self.assertRaises(TagFileParseError,
                          parse_tagfile, datadir("empty-file"), 1)

    def testCheckParseMalformedSigRaises(self):
        """lp.archiveuploader.tagfiles.parse_chantges should raise
           TagFileParseError on malformed signatures
        """
        self.assertRaises(TagFileParseError,
                          parse_tagfile, datadir("malformed-sig-changes"), 1)

    def testCheckParseMalformedMultilineRaises(self):
        """lp.archiveuploader.tagfiles.parse_chantges should raise
           TagFileParseError on malformed continuation lines"""
        self.assertRaises(TagFileParseError,
                          parse_tagfile, datadir("bad-multiline-changes"), 1)

    def testCheckParseUnterminatedSigRaises(self):
        """lp.archiveuploader.tagfiles.parse_changes should raise
           TagFileParseError on unterminated signatures
        """
        self.assertRaises(TagFileParseError,
                          parse_tagfile,
                          datadir("unterminated-sig-changes"),
                          1)

    def testParseChangesNotVulnerableToArchExploit(self):
        """lp.archiveuploader.tagfiles.parse_tagfile should not be vulnerable
           to tags outside of the signed portion
        """
        tf = parse_tagfile(datadir("changes-with-exploit-top"))
        self.assertRaises(KeyError, tf.__getitem__, "you")
        tf = parse_tagfile(datadir("changes-with-exploit-bottom"))
        self.assertRaises(KeyError, tf.__getitem__, "you")


class TestTagFileDebianPolicyCompat(unittest.TestCase):

    def setUp(self):
        """Parse the test file using apt_pkg for comparison."""

        tagfile_path = datadir("test436182_0.1_source.changes")
        tagfile = open(tagfile_path)
        self.apt_pkg_parsed_version = apt_pkg.ParseTagFile(tagfile)
        self.apt_pkg_parsed_version.Step()

        self.parse_tagfile_version = parse_tagfile(
            tagfile_path, allow_unsigned = True)

    def test_parse_tagfile_with_multiline_values(self):
        """parse_tagfile should not leave trailing '\n' on multiline values.

        This is a regression test for bug 436182.
        Previously we,
          1. Stripped leading space/tab from subsequent lines of multiline
             values, and
          2. appended a trailing '\n' to the end of the value.
        """

        expected_text = (
            'test75874 anotherbinary\n'
            ' andanother andonemore\n'
            '\tlastone')

        self.assertEqual(
            expected_text,
            self.apt_pkg_parsed_version.Section['Binary'])

        self.assertEqual(
            expected_text,
            self.parse_tagfile_version['Binary'])

    def test_parse_tagfile_with_newline_delimited_field(self):
        """parse_tagfile should not leave leading or tailing '\n' when
        parsing newline delimited fields.

        Newline-delimited fields should be parsed to match
        apt_pkg.ParseTageFile.

        Note: in the past, our parse_tagfile function left the leading
        '\n' in the parsed value, whereas it should not have.

        For an example,
        see http://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-Files
        """

        expected_text = (
            'f26bb9b29b1108e53139da3584a4dc92 1511 test75874_0.1.tar.gz\n '
            '29c955ff520cea32ab3e0316306d0ac1 393742 '
                'pmount_0.9.7.orig.tar.gz\n'
            ' 91a8f46d372c406fadcb57c6ff7016f3 5302 '
                'pmount_0.9.7-2ubuntu2.diff.gz')

        self.assertEqual(
            expected_text,
            self.apt_pkg_parsed_version.Section['Files'])

        self.assertEqual(
            expected_text,
            self.parse_tagfile_version['Files'])

    def test_parse_description_field(self):
        """Apt-pkg preserves the blank-line indicator and does not strip
        leading spaces.

        See http://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-Description
        """
        expected_text = (
            "Here's the single-line synopsis.\n"
            " Then there is the extended description which can\n"
            " span multiple lines, and even include blank-lines like this:\n"
            " .\n"
            " There you go. If a line starts with two or more spaces,\n"
            " it will be displayed verbatim. Like this one:\n"
            "  Example verbatim line.\n"
            "    Another verbatim line.\n"
            " OK, back to normal.")

        self.assertEqual(
            expected_text,
            self.apt_pkg_parsed_version.Section['Description'])

        # In the past our parse_tagfile function replaced blank-line
        # indicators in the description (' .\n') with new lines ('\n'),
        # but it is now compatible with ParseTagFiles (and ready to be
        # replaced by ParseTagFiles).
        self.assertEqual(
            expected_text,
            self.parse_tagfile_version['Description'])
