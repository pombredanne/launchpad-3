#!/usr/bin/env python

# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: 52e0c871-49a3-4186-beb8-9817d02d5465

import unittest
import sys
import shutil
from canonical.lucille.tests import datadir

class TestTagFiles(unittest.TestCase):

    def testImport(self):
        """canonical.lucille.TagFiles should be importable"""
        from canonical.lucille.TagFiles import TagFile
        from canonical.lucille.TagFiles import TagFileParseError
        from canonical.lucille.TagFiles import parse_tagfile

    def testTagFileOnSingular(self):
        """canonical.lucille.TagFiles.TagFile should parse a singular stanza
        """
        from canonical.lucille.TagFiles import TagFile
        f = TagFile(file(datadir("singular-stanza"), "r"))
        seenone = False
        for stanza in f:
            self.assertEquals(seenone, False)
            seenone = True
            self.assertEquals("Format" in stanza, True)
            self.assertEquals("Source" in stanza, True)
            self.assertEquals("FooBar" in stanza, False)

    def testTagFileOnSeveral(self):
        """canonical.lucille.TagFiles.TagFile should parse multiple stanzas"""
        from canonical.lucille.TagFiles import TagFile
        f = TagFile(file(datadir("multiple-stanzas"), "r"))
        seen = 0
        for stanza in f:
            seen += 1
            self.assertEquals("Format" in stanza, True)
            self.assertEquals("Source" in stanza, True)
            self.assertEquals("FooBar" in stanza, False)
        self.assertEquals(seen > 1, True)

    def testCheckParseChangesOkay(self):
        """canonical.lucille.TagFiles.parse_tagfile should work on a good
           changes file
        """
        from canonical.lucille.TagFiles import parse_tagfile
        p = parse_tagfile(datadir("good-signed-changes"))

    def testCheckParseBadChangesRaises(self):
        """canonical.lucille.TagFiles.parse_chantges should raise
           TagFileParseError on failure
        """
        from canonical.lucille.TagFiles import parse_tagfile
        from canonical.lucille.TagFiles import TagFileParseError
        self.assertRaises(TagFileParseError,
                          parse_tagfile, datadir("badformat-changes"), 1)

    def testCheckParseEmptyChangesRaises(self):
        """canonical.lucille.TagFiles.parse_chantges should raise
           TagFileParseError on empty
        """
        from canonical.lucille.TagFiles import parse_tagfile
        from canonical.lucille.TagFiles import TagFileParseError
        self.assertRaises(TagFileParseError,
                          parse_tagfile, datadir("empty-file"), 1)

    def testCheckParseMalformedSigRaises(self):
        """canonical.lucille.TagFiles.parse_chantges should raise
           TagFileParseError on malformed signatures
        """
        from canonical.lucille.TagFiles import parse_tagfile
        from canonical.lucille.TagFiles import TagFileParseError
        self.assertRaises(TagFileParseError,
                          parse_tagfile, datadir("malformed-sig-changes"), 1)

    def testCheckParseMalformedMultilineRaises(self):
        """canonical.lucille.TagFiles.parse_chantges should raise
           TagFileParseError on malformed continuation lines"""
        from canonical.lucille.TagFiles import parse_tagfile
        from canonical.lucille.TagFiles import TagFileParseError
        self.assertRaises(TagFileParseError,
                          parse_tagfile, datadir("bad-multiline-changes"), 1)

    def testCheckParseUnterminatedSigRaises(self):
        """canonical.lucille.TagFiles.parse_chantges should raise
           TagFileParseError on unterminated signatures
        """
        from canonical.lucille.TagFiles import parse_tagfile
        from canonical.lucille.TagFiles import TagFileParseError
        self.assertRaises(TagFileParseError,
                          parse_tagfile,
                          datadir("unterminated-sig-changes"),
                          1)

    def testParseChangesNotVulnerableToArchExploit(self):
        """canonical.lucille.TagFiles.parse_tagfile should not be vulnerable
           to tags outside of the signed portion
        """
        from canonical.lucille.TagFiles import parse_tagfile
        tf = parse_tagfile(datadir("changes-with-exploit-top"))
        self.assertRaises(KeyError, tf.__getitem__, "you")
        tf = parse_tagfile(datadir("changes-with-exploit-bottom"))
        self.assertRaises(KeyError, tf.__getitem__, "you")

def test_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestTagFiles))
    return suite

def main(argv):
    suite = test_suite()
    runner = unittest.TextTestRunner(verbosity = 2)
    if not runner.run(suite).wasSuccessful():
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

