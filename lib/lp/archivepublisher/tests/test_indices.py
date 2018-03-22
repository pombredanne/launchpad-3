# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test native archive index generation for Soyuz."""

from __future__ import absolute_import, print_function, unicode_literals

import os
import tempfile
import unittest

import apt_pkg

from lp.archivepublisher.indices import (
    build_binary_stanza_fields,
    build_source_stanza_fields,
    IndexStanzaFields,
    )
from lp.soyuz.tests.test_publishing import TestNativePublishingBase


def build_bpph_stanza(bpph):
    return build_binary_stanza_fields(
        bpph.binarypackagerelease, bpph.component, bpph.section,
        bpph.priority, bpph.phased_update_percentage,
        False)


def build_spph_stanza(spph):
    return build_source_stanza_fields(
        spph.sourcepackagerelease, spph.component,
        spph.section)


def get_field(stanza_fields, name):
    return dict(stanza_fields.fields).get(name)


class TestNativeArchiveIndexes(TestNativePublishingBase):

    deb_md5 = '008409e7feb1c24a6ccab9f6a62d24c5'
    deb_sha1 = '30b7b4e583fa380772c5a40e428434628faef8cf'
    deb_sha256 = (
        '006ca0f356f54b1916c24c282e6fd19961f4356441401f4b0966f2a00bb3e945')
    dsc_md5 = '5913c3ad52c14a62e6ae7eef51f9ef42'
    dsc_sha1 = 'e35e29b2ea94bbaa831882e11d1f456690f04e69'
    dsc_sha256 = (
        'ac512102db9724bee18f26945efeeb82fdab89819e64e120fbfda755ca50c2c6')

    def setUp(self):
        """Setup global attributes."""
        TestNativePublishingBase.setUp(self)
        apt_pkg.init_system()

    def testSourceStanza(self):
        """Check just-created source publication Index stanza.

        The so-called 'stanza' method return a chunk of text which
        corresponds to the APT index reference.

        It contains specific package attributes, like: name of the source,
        maintainer identification, DSC format and standards version, etc

        Also contains the paths and checksums for the files included in
        the package in question.
        """
        pub_source = self.getPubSource(
            builddepends='fooish', builddependsindep='pyfoo',
            build_conflicts='bar', build_conflicts_indep='pybar',
            user_defined_fields=[
                ("Build-Depends-Arch", "libfoo-dev"),
                ("Build-Conflicts-Arch", "libbar-dev")])

        self.assertEqual(
            ['Package: foo',
             'Binary: foo-bin',
             'Version: 666',
             'Section: base',
             'Maintainer: Foo Bar <foo@bar.com>',
             'Build-Depends: fooish',
             'Build-Depends-Indep: pyfoo',
             'Build-Depends-Arch: libfoo-dev',
             'Build-Conflicts: bar',
             'Build-Conflicts-Indep: pybar',
             'Build-Conflicts-Arch: libbar-dev',
             'Architecture: all',
             'Standards-Version: 3.6.2',
             'Format: 1.0',
             'Directory: pool/main/f/foo',
             'Files:',
             ' %s 28 foo_666.dsc' % self.dsc_md5,
             'Checksums-Sha1:',
             ' %s 28 foo_666.dsc' % self.dsc_sha1,
             'Checksums-Sha256:',
             ' %s 28 foo_666.dsc' % self.dsc_sha256,
             ],
            build_spph_stanza(pub_source).makeOutput().splitlines())

    def testSourceStanzaCustomFields(self):
        """Check just-created source publication Index stanza
        with custom fields (Python-Version).

        A field is excluded if its key case-insensitively matches one that's
        already there. This mostly affects sources that were uploaded before
        Homepage, Checksums-Sha1 or Checksums-Sha256 were excluded.
        """
        pub_source = self.getPubSource(
            builddepends='fooish', builddependsindep='pyfoo',
            build_conflicts='bar', build_conflicts_indep='pybar',
            user_defined_fields=[
                ("Python-Version", "< 1.5"),
                ("CHECKSUMS-SHA1", "BLAH"),
                ("Build-Depends-Arch", "libfoo-dev"),
                ("Build-Conflicts-Arch", "libbar-dev")])

        self.assertEqual(
            ['Package: foo',
             'Binary: foo-bin',
             'Version: 666',
             'Section: base',
             'Maintainer: Foo Bar <foo@bar.com>',
             'Build-Depends: fooish',
             'Build-Depends-Indep: pyfoo',
             'Build-Depends-Arch: libfoo-dev',
             'Build-Conflicts: bar',
             'Build-Conflicts-Indep: pybar',
             'Build-Conflicts-Arch: libbar-dev',
             'Architecture: all',
             'Standards-Version: 3.6.2',
             'Format: 1.0',
             'Directory: pool/main/f/foo',
             'Files:',
             ' %s 28 foo_666.dsc' % self.dsc_md5,
             'Checksums-Sha1:',
             ' %s 28 foo_666.dsc' % self.dsc_sha1,
             'Checksums-Sha256:',
             ' %s 28 foo_666.dsc' % self.dsc_sha256,
             'Python-Version: < 1.5'],
            build_spph_stanza(pub_source).makeOutput().splitlines())

    def testBinaryStanza(self):
        """Check just-created binary publication Index stanza.

        See also testSourceStanza, it must present something similar for
        binary packages.
        """
        pub_binaries = self.getPubBinaries(
            depends='biscuit', recommends='foo-dev', suggests='pyfoo',
            conflicts='old-foo', replaces='old-foo', provides='foo-master',
            pre_depends='master-foo', enhances='foo-super', breaks='old-foo',
            phased_update_percentage=50)
        pub_binary = pub_binaries[0]
        self.assertEqual(
            ['Package: foo-bin',
             'Source: foo',
             'Priority: standard',
             'Section: base',
             'Installed-Size: 100',
             'Maintainer: Foo Bar <foo@bar.com>',
             'Architecture: all',
             'Version: 666',
             'Recommends: foo-dev',
             'Replaces: old-foo',
             'Suggests: pyfoo',
             'Provides: foo-master',
             'Depends: biscuit',
             'Conflicts: old-foo',
             'Pre-Depends: master-foo',
             'Enhances: foo-super',
             'Breaks: old-foo',
             'Filename: pool/main/f/foo/foo-bin_666_all.deb',
             'Size: 18',
             'MD5sum: ' + self.deb_md5,
             'SHA1: ' + self.deb_sha1,
             'SHA256: ' + self.deb_sha256,
             'Phased-Update-Percentage: 50',
             'Description: Foo app is great',
             ' Well ...',
             ' it does nothing, though'],
            build_bpph_stanza(pub_binary).makeOutput().splitlines())

    def testBinaryStanzaWithCustomFields(self):
        """Check just-created binary publication Index stanza with
        custom fields (Python-Version).

        """
        pub_binaries = self.getPubBinaries(
            depends='biscuit', recommends='foo-dev', suggests='pyfoo',
            conflicts='old-foo', replaces='old-foo', provides='foo-master',
            pre_depends='master-foo', enhances='foo-super', breaks='old-foo',
            user_defined_fields=[("Python-Version", ">= 2.4")])
        pub_binary = pub_binaries[0]
        self.assertEqual(
            ['Package: foo-bin',
             'Source: foo',
             'Priority: standard',
             'Section: base',
             'Installed-Size: 100',
             'Maintainer: Foo Bar <foo@bar.com>',
             'Architecture: all',
             'Version: 666',
             'Recommends: foo-dev',
             'Replaces: old-foo',
             'Suggests: pyfoo',
             'Provides: foo-master',
             'Depends: biscuit',
             'Conflicts: old-foo',
             'Pre-Depends: master-foo',
             'Enhances: foo-super',
             'Breaks: old-foo',
             'Filename: pool/main/f/foo/foo-bin_666_all.deb',
             'Size: 18',
             'MD5sum: ' + self.deb_md5,
             'SHA1: ' + self.deb_sha1,
             'SHA256: ' + self.deb_sha256,
             'Description: Foo app is great',
             ' Well ...',
             ' it does nothing, though',
             'Python-Version: >= 2.4'],
            build_bpph_stanza(pub_binary).makeOutput().splitlines())

    def testBinaryStanzaDescription(self):
        """ Check the description field.

        The description field should formated as:

        Description: <single line synopsis>
         <extended description over several lines>

        The extended description should allow the following formatting
        actions supported by the dpkg-friend tools:

         * lines to be wraped should start with a space.
         * lines to be preserved empty should start with single space followed
           by a single full stop (DOT).
         * lines to be presented in Verbatim should start with two or
           more spaces.

        We just want to check if the original description uploaded and stored
        in the system is preserved when we build the archive index.
        """
        description = (
            "Normal\nNormal"
            "\n.\n.\n."
            "\n %s" % ('x' * 100))
        pub_binary = self.getPubBinaries(
            description=description)[0]

        self.assertEqual(
            ['Package: foo-bin',
             'Source: foo',
             'Priority: standard',
             'Section: base',
             'Installed-Size: 100',
             'Maintainer: Foo Bar <foo@bar.com>',
             'Architecture: all',
             'Version: 666',
             'Filename: pool/main/f/foo/foo-bin_666_all.deb',
             'Size: 18',
             'MD5sum: ' + self.deb_md5,
             'SHA1: ' + self.deb_sha1,
             'SHA256: ' + self.deb_sha256,
             'Description: Foo app is great',
             ' Normal',
             ' Normal',
             ' .',
             ' .',
             ' .',
             ' %s' % ('x' * 100),
             ],
            build_bpph_stanza(pub_binary).makeOutput().splitlines())

    def testBinaryStanzaWithNonAscii(self):
        """Check how will be a stanza with non-ascii content

        Only 'Maintainer' (IPerson.displayname) and 'Description'
        (IBinaryPackageRelease.{summary, description}) can possibly
        contain non-ascii stuff.
        The encoding should be preserved and able to be encoded in
        'utf-8' for disk writing.
        """
        description = 'Using non-ascii as: \xe7\xe3\xe9\xf3'
        pub_binary = self.getPubBinaries(
            description=description)[0]

        self.assertEqual(
            ['Package: foo-bin',
             'Source: foo',
             'Priority: standard',
             'Section: base',
             'Installed-Size: 100',
             'Maintainer: Foo Bar <foo@bar.com>',
             'Architecture: all',
             'Version: 666',
             'Filename: pool/main/f/foo/foo-bin_666_all.deb',
             'Size: 18',
             'MD5sum: ' + self.deb_md5,
             'SHA1: ' + self.deb_sha1,
             'SHA256: ' + self.deb_sha256,
             'Description: Foo app is great',
             ' Using non-ascii as: \xe7\xe3\xe9\xf3',
             ],
            build_bpph_stanza(pub_binary).makeOutput().splitlines())

    def testBinaryOmitsIdenticalSourceName(self):
        # Binaries omit the Source field if it identical to Package.
        pub_source = self.getPubSource(sourcename='foo')
        pub_binary = self.getPubBinaries(
            binaryname='foo', pub_source=pub_source)[0]
        self.assertIs(
            None,
            get_field(build_bpph_stanza(pub_binary), 'Source'))

    def testBinaryIncludesDifferingSourceName(self):
        # Binaries include a Source field if their name differs.
        pub_source = self.getPubSource(sourcename='foo')
        pub_binary = self.getPubBinaries(
            binaryname='foo-bin', pub_source=pub_source)[0]
        self.assertEqual(
            'foo',
            get_field(build_bpph_stanza(pub_binary), 'Source'))

    def testBinaryIncludesDifferingSourceVersion(self):
        # Binaries also include a Source field if their versions differ.
        pub_source = self.getPubSource(sourcename='foo', version='666')
        pub_binary = self.getPubBinaries(
            binaryname='foo', version='999', pub_source=pub_source)[0]
        self.assertEqual(
            'foo (666)',
            get_field(build_bpph_stanza(pub_binary), 'Source'))


class TestNativeArchiveIndexesReparsing(TestNativePublishingBase):
    """Tests for ensuring the native archive indexes that we publish
    can be parsed correctly by apt_pkg.TagFile.
    """

    def setUp(self):
        """Setup global attributes."""
        TestNativePublishingBase.setUp(self)
        apt_pkg.init_system()

    def write_stanza_and_reparse(self, stanza):
        """Helper method to return the apt_pkg parser for the stanza."""
        index_filename = tempfile.mktemp()
        index_file = open(index_filename, 'w')
        index_file.write(stanza.makeOutput().encode('utf-8'))
        index_file.close()

        parser = apt_pkg.TagFile(open(index_filename))

        # We're only interested in one stanza, so we'll parse it and remove
        # the tmp file again.
        section = next(parser)
        os.remove(index_filename)

        return section

    def test_binary_stanza(self):
        """Check a binary stanza with APT parser."""
        pub_binary = self.getPubBinaries()[0]

        section = self.write_stanza_and_reparse(build_bpph_stanza(pub_binary))

        self.assertEqual(section.get('Package'), 'foo-bin')
        self.assertEqual(
            section.get('Description').splitlines(),
            ['Foo app is great', ' Well ...', ' it does nothing, though'])

    def test_source_stanza(self):
        """Check a source stanza with APT parser."""
        pub_source = self.getPubSource()

        section = self.write_stanza_and_reparse(build_spph_stanza(pub_source))

        self.assertEqual(section.get('Package'), 'foo')
        self.assertEqual(section.get('Maintainer'), 'Foo Bar <foo@bar.com>')

    def test_source_with_corrupt_dsc_binaries(self):
        """Ensure corrupt binary fields are written correctly to indexes.

        This is a regression test for bug 436182.

        During upload, our custom parser at:
          lp.archiveuploader.tagfiles.parse_tagfile_lines
        strips leading spaces from subsequent lines of fields with values
        spanning multiple lines, such as the binary field, and in addition
        leaves a trailing '\n' (which results in a blank line after the
        Binary field).

        The second issue causes apt_pkg.TagFile() to error during
        germination when it attempts to parse the generated Sources index.
        But the first issue will also cause apt_pkg.TagFile to skip each
        newline of a multiline field that is not preceded with a space.

        This test ensures that binary fields saved as such will continue
        to be written correctly to index files.

        This test can be removed if the parser is fixed and the corrupt
        data has been cleaned.
        """
        pub_source = self.getPubSource()

        # An example of a corrupt dsc_binaries field. We need to ensure
        # that the corruption is not carried over into the index stanza.
        pub_source.sourcepackagerelease.dsc_binaries = (
            'foo_bin,\nbar_bin,\nzed_bin')

        section = self.write_stanza_and_reparse(build_spph_stanza(pub_source))

        self.assertEqual('foo', section['Package'])

        # Without the fix, this raises a key-error due to apt-pkg not
        # being able to parse the file.
        self.assertEqual(
            '666', section['Version'],
            'The Version field should be parsed correctly.')

        # Without the fix, the second binary would not be parsed at all.
        self.assertEqual('foo_bin,\n bar_bin,\n zed_bin', section['Binary'])

    def test_source_with_correct_dsc_binaries(self):
        """Ensure correct binary fields are written correctly to indexes.

        During upload, our custom parser at:
          lp.archiveuploader.tagfiles.parse_tagfile_lines
        strips leading spaces from subsequent lines of fields with values
        spanning multiple lines, such as the binary field, and in addition
        leaves a trailing '\n' (which results in a blank line after the
        Binary field).

        This test ensures that when our parser is updated to store the
        binary field in the same way that apt_pkg.TagFile would, that it
        will continue to be written correctly to index files.
        """
        pub_source = self.getPubSource()

        # An example of a corrupt dsc_binaries field. We need to ensure
        # that the corruption is not carried over into the index stanza.
        pub_source.sourcepackagerelease.dsc_binaries = (
            'foo_bin,\n bar_bin,\n zed_bin')

        section = self.write_stanza_and_reparse(build_spph_stanza(pub_source))

        self.assertEqual('foo', section['Package'])

        # Without the fix, this raises a key-error due to apt-pkg not
        # being able to parse the file.
        self.assertEqual(
            '666', section['Version'],
            'The Version field should be parsed correctly.')

        # Without the fix, the second binary would not be parsed at all.
        self.assertEqual('foo_bin,\n bar_bin,\n zed_bin', section['Binary'])


class TestIndexStanzaFieldsHelper(unittest.TestCase):
    """Check how this auxiliary class works...

    This class provides simple FIFO API for aggregating fields
    (name & values) in a ordered way.

    Provides an method to format the option in a ready-to-use string.
    """

    def test_simple(self):
        fields = IndexStanzaFields()
        fields.append('breakfast', 'coffee')
        fields.append('lunch', 'beef')
        fields.append('dinner', 'fish')

        self.assertEqual(3, len(fields.fields))
        self.assertTrue(('dinner', 'fish') in fields.fields)
        self.assertEqual(
            ['breakfast: coffee', 'lunch: beef', 'dinner: fish',
             ], fields.makeOutput().splitlines())

    def test_preserves_order(self):
        fields = IndexStanzaFields()
        fields.append('one', 'um')
        fields.append('three', 'tres')
        fields.append('two', 'dois')

        self.assertEqual(
            ['one: um', 'three: tres', 'two: dois',
             ], fields.makeOutput().splitlines())

    def test_files(self):
        # Special treatment for field named 'Files'
        # do not add a space between <name>:<value>
        # <value> will always start with a new line.
        fields = IndexStanzaFields()
        fields.append('one', 'um')
        fields.append('Files', '<no_sep>')

        self.assertEqual(
            ['one: um', 'Files:<no_sep>'], fields.makeOutput().splitlines())

    def test_extend(self):
        fields = IndexStanzaFields()
        fields.append('one', 'um')
        fields.extend([('three', 'tres'), ['four', 'five']])

        self.assertEqual(
            ['one: um', 'three: tres', 'four: five',
             ], fields.makeOutput().splitlines())
