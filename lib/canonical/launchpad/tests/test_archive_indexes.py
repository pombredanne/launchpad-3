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

    def getPubSource(self, sourcename='foo', version='666', builddepends='',
                     builddependsindep='', architecturehintlist='',
                     dsc_standards_version='3.6.2', dsc_format='1.0',
                     dsc_binaries_hint='foo-bin',
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
            changelog='',
            dsc='',
            dscsigningkey=self.signingkey,
            manifest=None,
            dsc_maintainer_rfc822=dsc_maintainer_rfc822,
            dsc_standards_version=dsc_standards_version,
            dsc_format=dsc_format,
            dsc_binaries_hint=dsc_binaries_hint
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
                     description='Well, it does nothing, though', shlibdep='',
                     depends='', recommends='', suggests='', conflicts='',
                     replaces='', provides=''):
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
        """Check just-created source publication Index stanza."""
        pub_source = self.getPubSource()
        self.assertEqual(
            [u'',
             u'Package: foo',
             u'Binary: foo-bin',
             u'Version: 666',
             u'Maintainer: Foo Bar <foo@bar.com>',
             u'Build-Depends: ',
             u'Architecture: ',
             u'Standards-Version: 3.6.2',
             u'Format: 1.0',
             u'Directory: pool/main/f/foo',
             u'Files:',
             u' 3e47b75000b0924b6c9ba5759a7cf15d 7 foo.dsc',
             u''],
            pub_source.index_stanza().splitlines())

    def testBinaryStanza(self):
        """Check just-created binary publication Index stanza."""
        pub_binary = self.getPubBinary()
        self.assertEqual(
            [u'',
             u'Package: foo-bin',
             u'Priority: Standard',
             u'Section: base',
             u'Installed-Size: 100',
             u'Maintainer: Foo Bar <foo@bar.com>',
             u'Architecture: i386',
             u'Version: 666',
             u'Replaces: ',
             u'Depends: ',
             u'Conflicts: ',
             u'Filename: foo-bin.deb',
             u'Size: 18',
             u'MD5sum: 008409e7feb1c24a6ccab9f6a62d24c5',
             u'Description: Foo app is great',
             u'Well, it does nothing, though',
             u'Bugs: NDA',
             u'Origin: NDA',
             u'Task: NDA'],
            pub_binary.index_stanza().splitlines())


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
