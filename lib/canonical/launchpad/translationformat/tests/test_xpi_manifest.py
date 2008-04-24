# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Functional tests for XPI manifests."""
__metaclass__ = type

import unittest

from canonical.launchpad.translationformat.xpi_manifest import XpiManifest
from canonical.testing import LaunchpadZopelessLayer


class XpiManifestTestCase(unittest.TestCase):
    """Test `XpiManifest`."""

    layer = LaunchpadZopelessLayer

    def test_TrivialParse(self):
        # Parse and use minimal manifest.
        manifest = XpiManifest("locale chromepath en-US directory/")
        chrome_path, locale = manifest.get_chrome_path_and_locale(
            'directory/file.dtd')
        self.failIf(chrome_path is None, "Failed to match simple path")
        self.assertEqual(
            chrome_path, "chromepath/file.dtd", "Bad chrome path")

    def test_NonMatch(self):
        # Failure to match path.
        manifest = XpiManifest("locale chromepath en-US directory/")
        chrome_path, locale = manifest.get_chrome_path_and_locale(
            'nonexistent/file')
        self.failIf(chrome_path is not None, "Unexpected path match.")
        self.failIf(locale is not None, "Got locale without a match.")

    def test_NoUsefulLines(self):
        # Parse manifest without useful data.  Lines that don't match what
        # we're looking for are ignored.
        manifest = XpiManifest("""
            There are no usable
            locale lines
            in this file.
            """)
        chrome_path, locale = manifest.get_chrome_path_and_locale('lines')
        self.failIf(chrome_path is not None, "Empty manifest matched a path.")
        chrome_path, locale = manifest.get_chrome_path_and_locale('')
        self.failIf(chrome_path is not None, "Matched empty path.")

    def test_MultipleLines(self):
        # Parse manifest file with multiple entries.
        manifest = XpiManifest("""
            locale foo en-US foodir/
            locale bar en-US bardir/
            locale ixx en-US ixxdir/
            locale gna en-US gnadir/
            """)
        for dir in ['gna', 'bar', 'ixx', 'foo']:
            path = "%sdir/file.html" % dir
            chrome_path, locale = manifest.get_chrome_path_and_locale(path)
            self.assertEqual(chrome_path, "%s/file.html" % dir,
                "Bad chrome path in multi-line parse.")
            self.assertEqual(
                locale, 'en-US', "Bad locale in multi-line parse.")

    def test_MultipleLocales(self):
        # Different locales.
        dirs = {
            'foo': 'en-US',
            'bar': 'es',
            'ixx': 'zh_CN',
            'zup': 'zh_TW',
            'gna': 'pt',
            'gnu': 'pt_BR'
            }
        manifest_text = '\n'.join([
            "locale %s %s %sdir/\n" % (dir, locale, dir)
            for dir, locale in dirs.iteritems()
            ])
        manifest = XpiManifest(manifest_text)
        for dir, dirlocale in dirs.iteritems():
            path = "%sdir/file.html" % dir
            chrome_path, locale = manifest.get_chrome_path_and_locale(path)
            self.assertEqual(chrome_path, "%s/file.html" % dir,
                "Bad chrome path in multi-line parse.")
            self.assertEqual(locale, dirlocale, "Locales got mixed up.")

    def test_IgnoredLines(self):
        # Ignored lines: anything that doesn't start with "locale" or doesn't
        # have the right number of arguments.  The one correct line is picked
        # out though.
        manifest = XpiManifest("""
            nonlocale obsolete fr foodir/
            anotherline

            #locale obsolete fr foodir/
            locale okay fr foodir/
            locale overlong fr foordir/ etc. etc. etc.
            locale incomplete fr
            """)
        chrome_path, locale = manifest.get_chrome_path_and_locale('foodir/x')
        self.failIf(chrome_path is None, "Garbage lines messed up match.")
        self.assertEqual(chrome_path, "okay/x", "Matched wrong line.")
        self.assertEqual(locale, "fr", "Inexplicably mismatched locale.")

    def _checkLookup(self, manifest, path, chrome_path, locale):
        """Helper: look up "path" in "manifest," expect given output."""
        found_chrome_path, found_locale = manifest.get_chrome_path_and_locale(
            path)
        self.failIf(found_chrome_path is None, "No match found for " + path)
        self.assertEqual(found_chrome_path, chrome_path)
        self.assertEqual(found_locale, locale)

    def test_Normalize(self):
        # These paths are all wrong for one reason or another.  So are most of
        # the paths we look up here, but they're broken in different ways.
        # Check that the normalization of paths renders those little
        # differences and imperfections irrelevant to path lookup.
        manifest = XpiManifest("""
            locale foo1 el /ploink/squit
            locale foo2 he /ploink/squittle
            locale foo3 ja hello///kitty////
            locale foo4 sux /deep/sumerian/file/path/
            """)
        self._checkLookup(manifest, 'ploink/squit/file', 'foo1/file', 'el')
        self._checkLookup(manifest, 'ploink///squit//file', 'foo1/file', 'el')
        self._checkLookup(
            manifest, '/ploink/squit/dir/file', 'foo1/dir/file', 'el')
        self._checkLookup(manifest, '/ploink/squittle/file', 'foo2/file', 'he')
        self._checkLookup(
            manifest, 'ploink/squittle/dir/file', 'foo2/dir/file', 'he')
        self._checkLookup(
            manifest, 'hello/kitty/how/are/you', 'foo3/how/are/you', 'ja')
        self._checkLookup(
            manifest, 'deep/sumerian/file/path/x', 'foo4/x', 'sux')


    def test_Overlap(self):
        # Path matching looks for longest prefix.  Make sure this works right,
        # even when nested directories are in "overlapping" manifest entries.
        manifest = XpiManifest("""
            locale foo1 ca a/
            locale foo2 ca a/b/
            locale foo3 ca a/b/c/x1
            locale foo4 ca a/b/c/x2
            """)
        self._checkLookup(manifest, 'a/bb', 'foo1/bb', 'ca')
        self._checkLookup(manifest, 'a/bb/c', 'foo1/bb/c', 'ca')
        self._checkLookup(manifest, 'a/b/y', 'foo2/y', 'ca')
        self._checkLookup(manifest, 'a/b/c/', 'foo2/c/', 'ca')
        self._checkLookup(manifest, 'a/b/c/x12', 'foo2/c/x12', 'ca')
        self._checkLookup(manifest, 'a/b/c/x1/y', 'foo3/y', 'ca')
        self._checkLookup(manifest, 'a/b/c/x2/y', 'foo4/y', 'ca')

    def test_JarLookup(self):
        # Correct lookup.
        manifest = XpiManifest("""
            locale foo en_GB jar:foo.jar!/dir/
            locale bar id jar:bar.jar!/
            """)
        self._checkLookup(
            manifest, 'jar:foo.jar!/dir/file', 'foo/file', 'en_GB')
        self._checkLookup(
            manifest, 'jar:bar.jar!/dir/file', 'bar/dir/file', 'id')

    def test_JarNormalization(self):
        # Various badly-formed paths and lookups.  All get normalized.
        manifest = XpiManifest("""
            locale foo pl foo.jar!contained/dir
            locale bar tr jar://bar.jar!//contained/dir
            locale splat id splat.jar!
            locale nojar hu splat.jar
            """)
        self._checkLookup(
            manifest, 'jar:foo.jar!/contained/dir/x', 'foo/x', 'pl')
        self._checkLookup(
            manifest, 'jar:/foo.jar!/contained/dir/x', 'foo/x', 'pl')
        self._checkLookup(
            manifest, 'jar:bar.jar!/contained/dir/x', 'bar/x', 'tr')
        self._checkLookup(manifest, 'jar:splat.jar!/x', 'splat/x', 'id')
        self._checkLookup(manifest, 'splat.jar/x', 'nojar/x', 'hu')

    def test_JarMixup(self):
        # Two locales mixed up in two jar files.
        manifest = XpiManifest("""
            locale serbian sr jar:translations.jar!/sr/
            locale croatian hr jar:translations.jar!/hr/
            locale docs sr jar:docs.jar!/sr/
            locale docs hr jar:docs.jar!/hr/
            """)
        self._checkLookup(
            manifest, 'jar:translations.jar!/sr/x', 'serbian/x', 'sr')
        self._checkLookup(
            manifest, 'jar:translations.jar!/hr/x', 'croatian/x', 'hr')
        self._checkLookup(manifest, 'jar:docs.jar!/sr/x', 'docs/x', 'sr')
        self._checkLookup(manifest, 'jar:docs.jar!/hr/x', 'docs/x', 'hr')

    def test_NestedJars(self):
        # Nested jar files.
        manifest = XpiManifest("""
            locale x it jar:dir/x.jar!/subdir/y.jar!/
            locale y it jar:dir/x.jar!/subdir/y.jar!/deep/
            locale z it jar:dir/x.jar!/subdir/z.jar!/
            """)
        self._checkLookup(
            manifest, 'jar:dir/x.jar!/subdir/y.jar!/foo', 'x/foo', 'it')
        self._checkLookup(
            manifest, 'jar:dir/x.jar!/subdir/y.jar!/deep/foo', 'y/foo', 'it')
        self._checkLookup(
            manifest, 'jar:dir/x.jar!/subdir/z.jar!/foo', 'z/foo', 'it')


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)

