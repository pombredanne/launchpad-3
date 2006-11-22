# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Test native archive index generation for Soyuz."""

from unittest import TestLoader
import os
import shutil
from StringIO import StringIO

from zope.component import getUtility

from canonical.database.constants import UTC_NOW

from canonical.launchpad.ftests.harness import (
    LaunchpadZopelessTestCase, LaunchpadZopelessTestSetup)
from canonical.launchpad.database.processor import ProcessorFamily
from canonical.launchpad.database.publishing import (
    SourcePackagePublishingHistory, SecureSourcePackagePublishingHistory,
    BinaryPackagePublishingHistory, SecureBinaryPackagePublishingHistory)
from canonical.launchpad.interfaces import (
    ILibraryFileAliasSet, IDistributionSet, IPersonSet, ISectionSet,
    IComponentSet, ISourcePackageNameSet, IBinaryPackageNameSet, IGPGKeySet)

from canonical.librarian.client import LibrarianClient

from canonical.lp.dbschema import (
    PackagePublishingStatus, PackagePublishingPocket, SourcePackageUrgency,
    BinaryPackageFormat, PackagePublishingPriority)


class TestNativeArchiveIndexes(LaunchpadZopelessTestCase):

    dbuser = 'lucille'

    def setUp(self):
        """Setup global attributes."""
        LaunchpadZopelessTestCase.setUp(self)
        self.library = LibrarianClient()
        self.ubuntutest = getUtility(IDistributionSet)['ubuntutest']
        self.breezy_autotest = self.ubuntutest['breezy-autotest']
        self.person = getUtility(IPersonSet).getByName('sabdfl')
        self.breezy_autotest_i386 = self.breezy_autotest.newArch(
            'i386', ProcessorFamily.get(1), False, self.person)
        self.signingkey = getUtility(IGPGKeySet).get(1)
        self.section = getUtility(ISectionSet)['base']
        self.component = getUtility(IComponentSet)['main']

    def addMockFile(self, filename, content='nothing'):
        """Add a mock file in Librarian.

        Returns a ILibraryFileAlias corresponding to the file uploaded.
        """
        alias_id = self.library.addFile(
            filename, len(content), StringIO(content), 'application/text')
        LaunchpadZopelessTestSetup.txn.commit()
        return getUtility(ILibraryFileAliasSet)[alias_id]

    def getPubSource(self, sourcename='foo', version='666', builddepends=None,
                     builddependsindep=None, architecturehintlist='all',
                     dsc_standards_version='3.6.2', dsc_format='1.0',
                     dsc_binaries='foo-bin',
                     dsc_maintainer_rfc822='Foo Bar <foo@bar.com>'):
        """Return a mock source publishing record."""
        spn = getUtility(ISourcePackageNameSet).getOrCreateByName(sourcename)

        spr = self.breezy_autotest.createUploadedSourcePackageRelease(
            sourcepackagename=spn,
            maintainer=self.person,
            creator=self.person,
            component=self.component,
            section=self.section,
            urgency=SourcePackageUrgency.LOW,
            dateuploaded=UTC_NOW,
            version=version,
            builddepends=builddepends,
            builddependsindep=builddependsindep,
            architecturehintlist=architecturehintlist,
            changelog=None,
            dsc=None,
            dscsigningkey=self.signingkey,
            manifest=None,
            dsc_maintainer_rfc822=dsc_maintainer_rfc822,
            dsc_standards_version=dsc_standards_version,
            dsc_format=dsc_format,
            dsc_binaries=dsc_binaries
            )

        filename = '%s.dsc' % sourcename
        alias = self.addMockFile(filename)
        spr.addFile(alias)

        sspph = SecureSourcePackagePublishingHistory(
            distrorelease=self.breezy_autotest,
            sourcepackagerelease=spr,
            component=spr.component,
            section=spr.section,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            pocket=PackagePublishingPocket.RELEASE,
            embargo=False
            )

        # SPPH and SSPPH IDs are the same, since they are SPPH is a SQLVIEW
        # of SSPPH and other useful attributes.
        return SourcePackagePublishingHistory.get(sspph.id)

    def getPubBinary(self, binaryname='foo-bin', summary='Foo app is great',
                     description='Well ...\nit does nothing, though',
                     shlibdep=None, depends=None, recommends=None,
                     suggests=None, conflicts=None, replaces=None,
                     provides=None):
        """Return a mock binary publishing record."""
        sourcename = "%s" % binaryname.split('-')[0]
        pub_source = self.getPubSource(sourcename)
        spr = pub_source.sourcepackagerelease
        build = spr.createBuild(
            self.breezy_autotest_i386, pocket=PackagePublishingPocket.RELEASE)

        bpn = getUtility(IBinaryPackageNameSet).getOrCreateByName(binaryname)

        bpr = build.createBinaryPackageRelease(
            binarypackagename=bpn.id,
            version=spr.version,
            summary=summary,
            description=description,
            binpackageformat=BinaryPackageFormat.DEB,
            component=spr.component.id,
            section=spr.section.id,
            priority=PackagePublishingPriority.STANDARD,
            shlibdeps=shlibdep,
            depends=depends,
            recommends=recommends,
            suggests=suggests,
            conflicts=conflicts,
            replaces=replaces,
            provides=provides,
            essential=False,
            installedsize=100,
            copyright='Foo Foundation',
            licence='RMS will not like this',
            architecturespecific=False
            )

        filename = '%s.deb' % binaryname
        alias = self.addMockFile(filename, content='bbbiiinnnaaarrryyy')
        bpr.addFile(alias)

        sbpph = SecureBinaryPackagePublishingHistory(
            distroarchrelease=self.breezy_autotest_i386,
            binarypackagerelease=bpr,
            component=bpr.component,
            section=bpr.section,
            priority=bpr.priority,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            pocket=PackagePublishingPocket.RELEASE,
            embargo=False
            )

        return BinaryPackagePublishingHistory.get(sbpph.id)

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
             u' 3e47b75000b0924b6c9ba5759a7cf15d 7 foo.dsc'],
            pub_source.getIndexStanza().splitlines())

    def testBinaryStanza(self):
        """Check just-created binary publication Index stanza.

        See also testSourceStanza, it must present something similar for
        binary packages.
        """
        pub_binary = self.getPubBinary()
        self.assertEqual(
            [u'Package: foo-bin',
             u'Priority: Standard',
             u'Section: base',
             u'Installed-Size: 100',
             u'Maintainer: Foo Bar <foo@bar.com>',
             u'Architecture: i386',
             u'Version: 666',
             u'Filename: foo-bin.deb',
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
            "\n xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
            "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        pub_binary = self.getPubBinary(
            description=description)

        self.assertEqual(
            [u'Package: foo-bin',
             u'Priority: Standard',
             u'Section: base',
             u'Installed-Size: 100',
             u'Maintainer: Foo Bar <foo@bar.com>',
             u'Architecture: i386',
             u'Version: 666',
             u'Filename: foo-bin.deb',
             u'Size: 18',
             u'MD5sum: 008409e7feb1c24a6ccab9f6a62d24c5',
             u'Description: Foo app is great',
             u' Normal',
             u' Normal',
             u' .',
             u' .',
             u' .',
             (u'  xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
              u'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
             ],
            pub_binary.getIndexStanza().splitlines())

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

        # special treatment for field named 'Files'
        # do not add a space between <name>:<value>
        # <value> will always start with a new line.
        fields = IndexStanzaFields()
        fields.append('one', 'um')
        fields.append('Files', '<no_sep>')

        self.assertEqual(
            ['one: um', 'Files:<no_sep>'], fields.makeOutput().splitlines())


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
