# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Test native archive index generation for Soyuz."""

import apt_pkg
import os
import tempfile
from unittest import TestLoader

from canonical.launchpad.tests.test_publishing import TestNativePublishingBase

class TestNativeArchiveIndexes(TestNativePublishingBase):

    def setUp(self):
        """Setup global attributes."""
        TestNativePublishingBase.setUp(self)
        apt_pkg.InitSystem()

    def testSourceStanza(self):
        """Check just-created source publication Index stanza.

        The so-called 'stanza' method return a chunk of text which
        corresponds to the APT index reference.

        It contains specific package attributes, like: name of the source,
        maintainer identification, DSC format and standards version, etc

        Also contains the paths and checksums for the files included in
        the package in question.
        """
        pub_source = self.getPubSource()

        self.assertEqual(
            [u'Package: foo',
             u'Binary: foo-bin',
             u'Version: 666',
             u'Maintainer: Foo Bar <foo@bar.com>',
             u'Architecture: all',
             u'Standards-Version: 3.6.2',
             u'Format: 1.0',
             u'Directory: pool/main/f/foo',
             u'Files:',
             u' 5913c3ad52c14a62e6ae7eef51f9ef42 28 foo.dsc'],
            pub_source.getIndexStanza().splitlines())

    def testBinaryStanza(self):
        """Check just-created binary publication Index stanza.

        See also testSourceStanza, it must present something similar for
        binary packages.
        """
        pub_binary = self.getPubBinaries()[0]
        self.assertEqual(
            [u'Package: foo-bin',
             u'Priority: standard',
             u'Section: base',
             u'Installed-Size: 100',
             u'Maintainer: Foo Bar <foo@bar.com>',
             u'Architecture: all',
             u'Version: 666',
             u'Filename: pool/main/f/foo/foo-bin_all.deb',
             u'Size: 18',
             u'MD5sum: 008409e7feb1c24a6ccab9f6a62d24c5',
             u'Description: Foo app is great',
             u' Well ...',
             u' it does nothing, though'],
            pub_binary.getIndexStanza().splitlines())

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
            [u'Package: foo-bin',
             u'Priority: standard',
             u'Section: base',
             u'Installed-Size: 100',
             u'Maintainer: Foo Bar <foo@bar.com>',
             u'Architecture: all',
             u'Version: 666',
             u'Filename: pool/main/f/foo/foo-bin_all.deb',
             u'Size: 18',
             u'MD5sum: 008409e7feb1c24a6ccab9f6a62d24c5',
             u'Description: Foo app is great',
             u' Normal',
             u' Normal',
             u' .',
             u' .',
             u' .',
             u' %s' % ('x' * 100)
             ],
            pub_binary.getIndexStanza().splitlines())

    def testBinaryStanzaWithNonAscii(self):
        """Check how will be a stanza with non-ascii content

        Only 'Maintainer' (IPerson.displayname) and 'Description'
        (IBinaryPackageRelease.{summary, description}) can possibly
        contain non-ascii stuff.
        The encoding should be preserved and able to be encoded in
        'utf-8' for disk writing.
        """
        description = u'Using non-ascii as: \xe7\xe3\xe9\xf3'
        pub_binary = self.getPubBinaries(
            description=description)[0]

        self.assertEqual(
            [u'Package: foo-bin',
             u'Priority: standard',
             u'Section: base',
             u'Installed-Size: 100',
             u'Maintainer: Foo Bar <foo@bar.com>',
             u'Architecture: all',
             u'Version: 666',
             u'Filename: pool/main/f/foo/foo-bin_all.deb',
             u'Size: 18',
             u'MD5sum: 008409e7feb1c24a6ccab9f6a62d24c5',
             u'Description: Foo app is great',
             u' Using non-ascii as: \xe7\xe3\xe9\xf3',
             ],
            pub_binary.getIndexStanza().splitlines())

    def testBinaryStanzaWithApt(self):
        """Check a binary stanza with APT parser."""
        pub_binary = self.getPubBinaries()[0]

        index_filename = tempfile.mktemp()
        index_file = open(index_filename, 'w')
        index_file.write(pub_binary.getIndexStanza().encode('utf-8'))
        index_file.close()

        parser = apt_pkg.ParseTagFile(open(index_filename))

        parser.Step()

        self.assertEqual(parser.Section.get('Package'), 'foo-bin')
        self.assertEqual(
            parser.Section.get('Description').splitlines(),
            ['Foo app is great', ' Well ...', ' it does nothing, though'])

        os.remove(index_filename)

    def testSourceStanzaWithApt(self):
        """Check a source stanza with APT parser."""
        pub_source = self.getPubSource()

        index_filename = tempfile.mktemp()
        index_file = open(index_filename, 'w')
        index_file.write(pub_source.getIndexStanza().encode('utf-8'))
        index_file.close()

        parser = apt_pkg.ParseTagFile(open(index_filename))

        parser.Step()

        self.assertEqual(parser.Section.get('Package'), 'foo')
        self.assertEqual(
            parser.Section.get('Maintainer'), 'Foo Bar <foo@bar.com>')

        os.remove(index_filename)

    def testIndexStanzaFields(self):
        """Check how this auxiliary class works...

        This class provides simple FIFO API for aggregating fields
        (name & values) in a ordered way.

        Provides an method to format the option in a ready-to-use string.
        """
        from canonical.launchpad.database.publishing import IndexStanzaFields

        fields = IndexStanzaFields()
        fields.append('breakfast', 'coffee')
        fields.append('lunch', 'beef')
        fields.append('dinner', 'fish')

        self.assertEqual(3, len(fields.fields))
        self.assertTrue(('dinner', 'fish') in fields.fields)
        self.assertEqual(
            ['breakfast: coffee', 'lunch: beef', 'dinner: fish',
             ], fields.makeOutput().splitlines())

        fields = IndexStanzaFields()
        fields.append('one', 'um')
        fields.append('three', 'tres')
        fields.append('two', 'dois')

        self.assertEqual(
            ['one: um', 'three: tres', 'two: dois',
             ], fields.makeOutput().splitlines())

        # Special treatment for field named 'Files'
        # do not add a space between <name>:<value>
        # <value> will always start with a new line.
        fields = IndexStanzaFields()
        fields.append('one', 'um')
        fields.append('Files', '<no_sep>')

        self.assertEqual(
            ['one: um', 'Files:<no_sep>'], fields.makeOutput().splitlines())


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
