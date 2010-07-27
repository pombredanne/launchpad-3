#!/usr/bin/python
#
# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# arch-tag: 90e6eb79-83a2-47e8-9f8b-3c687079c923

import unittest
import sys

from lp.registry.interfaces.sourcepackage import SourcePackageFileType
from lp.soyuz.interfaces.binarypackagerelease import BinaryPackageFileType
from lp.archiveuploader.tests import datadir


class TestUtilities(unittest.TestCase):

    def testImport(self):
        """lp.archiveuploader.utils should be importable"""
        import lp.archiveuploader.utils

    def test_determine_source_file_type(self):
        """lp.archiveuploader.utils.determine_source_file_type should work."""
        from lp.archiveuploader.utils import determine_source_file_type

        # .dsc -> DSC
        self.assertEquals(
            determine_source_file_type('foo_1.0-1.dsc'),
            SourcePackageFileType.DSC)

        # .diff.gz -> DIFF
        self.assertEquals(
            determine_source_file_type('foo_1.0-1.diff.gz'),
            SourcePackageFileType.DIFF)

        # DIFFs can only be gzipped.
        self.assertEquals(
            determine_source_file_type('foo_1.0.diff.bz2'), None)

        # Plain original tarballs can be gzipped or bzip2ed.
        self.assertEquals(
            determine_source_file_type('foo_1.0.orig.tar.gz'),
            SourcePackageFileType.ORIG_TARBALL)
        self.assertEquals(
            determine_source_file_type('foo_1.0.orig.tar.bz2'),
            SourcePackageFileType.ORIG_TARBALL)

        # Component original tarballs too.
        self.assertEquals(
            determine_source_file_type('foo_1.0.orig-foo.tar.gz'),
            SourcePackageFileType.COMPONENT_ORIG_TARBALL)
        self.assertEquals(
            determine_source_file_type('foo_1.0.orig-bar.tar.bz2'),
            SourcePackageFileType.COMPONENT_ORIG_TARBALL)

        # And Debian tarballs...
        self.assertEquals(
            determine_source_file_type('foo_1.0-1.debian.tar.gz'),
            SourcePackageFileType.DEBIAN_TARBALL)
        self.assertEquals(
            determine_source_file_type('foo_1.0-2.debian.tar.bz2'),
            SourcePackageFileType.DEBIAN_TARBALL)

        # And even native tarballs!
        self.assertEquals(
            determine_source_file_type('foo_1.0.tar.gz'),
            SourcePackageFileType.NATIVE_TARBALL)
        self.assertEquals(
            determine_source_file_type('foo_1.0.tar.bz2'),
            SourcePackageFileType.NATIVE_TARBALL)

        self.assertEquals(None, determine_source_file_type('foo_1.0'))
        self.assertEquals(None, determine_source_file_type('foo_1.0.blah.gz'))

    def test_determine_binary_file_type(self):
        """lp.archiveuploader.utils.determine_binary_file_type should work."""
        from lp.archiveuploader.utils import determine_binary_file_type

        # .deb -> DEB
        self.assertEquals(
            determine_binary_file_type('foo_1.0-1_all.deb'),
            BinaryPackageFileType.DEB)

        # .udeb -> UDEB
        self.assertEquals(
            determine_binary_file_type('foo_1.0-1_all.udeb'),
            BinaryPackageFileType.UDEB)

        self.assertEquals(determine_binary_file_type('foo_1.0'), None)
        self.assertEquals(determine_binary_file_type('foo_1.0.notdeb'), None)

    def testPrefixMultilineString(self):
        """lp.archiveuploader.utils.prefix_multi_line_string should work"""
        from lp.archiveuploader.utils import prefix_multi_line_string
        self.assertEquals("A:foo\nA:bar",
                          prefix_multi_line_string("foo\nbar", "A:"))
        self.assertEquals("A:foo\nA:bar",
                          prefix_multi_line_string("foo\n\nbar", "A:"))
        self.assertEquals("A:foo\nA:\nA:bar",
                          prefix_multi_line_string("foo\n\nbar", "A:", 1))

    def testExtractComponent(self):
        """lp.archiveuploader.utils.extract_component_from_section should work
        """
        from lp.archiveuploader.utils import extract_component_from_section

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
        """lp.archiveuploader.utils.build_file_list should be capable of
           reading changes files
        """
        from lp.archiveuploader.utils import build_file_list
        from lp.archiveuploader.tagfiles import parse_tagfile

        ch = parse_tagfile(datadir("good-signed-changes"))
        fl = build_file_list(ch)
        self.assertEquals("abiword_2.0.10-1.2_mips.deb" in fl, True)

    def testFixMaintainerOkay(self):
        """lp.archiveuploader.utils.fix_maintainer should parse correct values
        """
        from lp.archiveuploader.utils import fix_maintainer
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
             "zakame@ubuntu.com (Zak B. Elep)"),
             )

        for case in cases:
            (a, b, c, d) = fix_maintainer(case[0])
            self.assertEquals(case[1], a)
            self.assertEquals(case[2], b)
            self.assertEquals(case[3], c)
            self.assertEquals(case[4], d)

    def testFixMaintainerRaises(self):
        """lp.archiveuploader.utils.fix_maintainer should raise on incorrect
           values
        """
        from lp.archiveuploader.utils import fix_maintainer, ParseMaintError
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
