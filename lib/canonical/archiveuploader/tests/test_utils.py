#!/usr/bin/python2.4

# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: 90e6eb79-83a2-47e8-9f8b-3c687079c923

import unittest
import sys
import shutil
from canonical.archiveuploader.tests import datadir


class TestUtilities(unittest.TestCase):

    def testImport(self):
        """canonical.archiveuploader.utils should be importable"""
        import canonical.archiveuploader.utils

    def testPrefixMultilineString(self):
        """canonical.archiveuploader.utils.prefix_multi_line_string should work"""
        from canonical.archiveuploader.utils import prefix_multi_line_string
        self.assertEquals("A:foo\nA:bar",
                          prefix_multi_line_string("foo\nbar", "A:"))
        self.assertEquals("A:foo\nA:bar",
                          prefix_multi_line_string("foo\n\nbar", "A:"))
        self.assertEquals("A:foo\nA:\nA:bar",
                          prefix_multi_line_string("foo\n\nbar", "A:", 1))

    def testExtractComponent(self):
        """canonical.archiveuploader.utils.extract_component_from_section should work
        """
        from canonical.archiveuploader.utils import extract_component_from_section

        (sect, comp) = extract_component_from_section("libs")
        self.assertEquals(sect, "libs")
        self.assertEquals(comp, "main")

        (sect, comp) = extract_component_from_section("restricted/libs")
        self.assertEquals(sect, "libs")
        self.assertEquals(comp, "restricted")

        (sect, comp) = extract_component_from_section("libs", "multiverse")
        self.assertEquals(sect, "libs")
        self.assertEquals(comp, "multiverse")

        (sect, comp) = extract_component_from_section("restricted/libs",
                                                      "multiverse")
        self.assertEquals(sect, "libs")
        self.assertEquals(comp, "restricted")

    def testBuildFileListFromChanges(self):
        """canonical.archiveuploader.utils.build_file_list should be capable of
           reading changes files
        """
        from canonical.archiveuploader.utils import build_file_list
        from canonical.archiveuploader.tagfiles import parse_tagfile

        ch = parse_tagfile(datadir("good-signed-changes"))
        fl = build_file_list(ch)
        self.assertEquals("abiword_2.0.10-1.2_mips.deb" in fl, True)

    def testFixMaintainerOkay(self):
        """canonical.archiveuploader.utils.fix_maintainer should parse correct values
        """
        from canonical.archiveuploader.utils import fix_maintainer
        cases = (
            ("No\xc3\xa8l K\xc3\xb6the <noel@debian.org>",
             "No\xc3\xa8l K\xc3\xb6the <noel@debian.org>",
             "=?utf-8?b?Tm/DqGwgS8O2dGhl?= <noel@debian.org>",
             "No\xc3\xa8l K\xc3\xb6the",
             "noel@debian.org"),

            ("No\xe8l K\xf6the <noel@debian.org>",
             "No\xc3\xa8l K\xc3\xb6the <noel@debian.org>",
             "=?iso-8859-1?q?No=E8l_K=F6the?= <noel@debian.org>",
             "No\xc3\xa8l K\xc3\xb6the",
             "noel@debian.org"),

            ("James Troup <james@nocrew.org>",
             "James Troup <james@nocrew.org>",
             "James Troup <james@nocrew.org>",
             "James Troup",
             "james@nocrew.org"),

            ("James J. Troup <james@nocrew.org>",
             "james@nocrew.org (James J. Troup)",
             "james@nocrew.org (James J. Troup)",
             "James J. Troup",
             "james@nocrew.org"),

            ("James J, Troup <james@nocrew.org>",
             "james@nocrew.org (James J, Troup)",
             "james@nocrew.org (James J, Troup)",
             "James J, Troup",
             "james@nocrew.org"),

            ("james@nocrew.org",
             " <james@nocrew.org>",
             " <james@nocrew.org>",
             "",
             "james@nocrew.org"),

            ("<james@nocrew.org>",
             " <james@nocrew.org>",
             " <james@nocrew.org>",
             "",
             "james@nocrew.org"),

            ("Cris van Pelt <\"Cris van Pelt\"@tribe.eu.org>",
             "Cris van Pelt <\"Cris van Pelt\"@tribe.eu.org>",
             "Cris van Pelt <\"Cris van Pelt\"@tribe.eu.org>",
             "Cris van Pelt",
             "\"Cris van Pelt\"@tribe.eu.org"),

            ("Zak B. Elep <zakame@ubuntu.com>",
             "zakame@ubuntu.com (Zak B. Elep)",
             "zakame@ubuntu.com (Zak B. Elep)",
             "Zak B. Elep",
             "zakame@ubuntu.com"),

            ("zakame@ubuntu.com (Zak B. Elep)",
             " <zakame@ubuntu.com (Zak B. Elep)>",
             " <zakame@ubuntu.com (Zak B. Elep)>",
             "",
             "zakame@ubuntu.com (Zak B. Elep)")
             )

        for case in cases:
            (a, b, c, d) = fix_maintainer(case[0])
            self.assertEquals(case[1], a)
            self.assertEquals(case[2], b)
            self.assertEquals(case[3], c)
            self.assertEquals(case[4], d)

    def testFixMaintainerRaises(self):
        """canonical.archiveuploader.utils.fix_maintainer should raise on incorrect
           values
        """
        from canonical.archiveuploader.utils import fix_maintainer, ParseMaintError
        cases = (
            "James Troup",
            "James Troup <james>",
            "James Troup <james@nocrew.org")
        for case in cases:
            try:
                fix_maintainer(case)
                self.assertNotReached()
            except ParseMaintError:
                pass

def test_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestUtilities))
    return suite

def main(argv):
    suite = test_suite()
    runner = unittest.TextTestRunner(verbosity = 2)
    if not runner.run(suite).wasSuccessful():
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

