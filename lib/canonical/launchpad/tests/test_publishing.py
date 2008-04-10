# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Test native publication workflow for Soyuz. """

import datetime
import operator
import os
import shutil
from StringIO import StringIO
import tempfile
import unittest

import pytz
from zope.component import getUtility

from canonical.archivepublisher.config import Config
from canonical.archivepublisher.diskpool import DiskPool
from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.launchpad.database.publishing import (
    SourcePackagePublishingHistory, SecureSourcePackagePublishingHistory,
    BinaryPackagePublishingHistory, SecureBinaryPackagePublishingHistory)
from canonical.launchpad.database.processor import ProcessorFamily
from canonical.launchpad.interfaces import (
    BinaryPackageFormat, IBinaryPackageNameSet, IComponentSet,
    IDistributionSet, ILibraryFileAliasSet, IPersonSet, ISectionSet,
    ISourcePackageNameSet, PackagePublishingPocket, PackagePublishingPriority,
    PackagePublishingStatus, SourcePackageUrgency)
from canonical.launchpad.scripts import FakeLogger
from canonical.librarian.client import LibrarianClient
from canonical.testing import LaunchpadZopelessLayer


class SoyuzTestPublisher:
    """Helper class able to publish coherent source and binaries in Soyuz."""

    def prepareBreezyAutotest(self):
        """Prepare ubuntutest/breezy-autotest for publications.

        It's also called during the normal test-case setUp.
        """
        self.ubuntutest = getUtility(IDistributionSet)['ubuntutest']
        self.breezy_autotest = self.ubuntutest['breezy-autotest']
        self.person = getUtility(IPersonSet).getByName('name16')
        self.breezy_autotest_i386 = self.breezy_autotest.newArch(
            'i386', ProcessorFamily.get(1), False, self.person,
            ppa_supported=True)
        self.breezy_autotest_hppa = self.breezy_autotest.newArch(
            'hppa', ProcessorFamily.get(4), False, self.person)
        self.breezy_autotest.nominatedarchindep = self.breezy_autotest_i386
        self.breezy_autotest_i386.ppa_supported = True
        self.breezy_autotest_hppa.ppa_supported = True

    def addMockFile(self, filename, filecontent='nothing'):
        """Add a mock file in Librarian.

        Returns a ILibraryFileAlias corresponding to the file uploaded.
        """
        library = LibrarianClient()
        alias_id = library.addFile(
            filename, len(filecontent), StringIO(filecontent),
            'application/text')
        return getUtility(ILibraryFileAliasSet)[alias_id]

    def getPubSource(self, sourcename='foo', version='666', component='main',
                     filename=None, section='base',
                     filecontent='I do not care about sources.',
                     status=PackagePublishingStatus.PENDING,
                     pocket=PackagePublishingPocket.RELEASE,
                     urgency=SourcePackageUrgency.LOW,
                     scheduleddeletiondate=None, dateremoved=None,
                     distroseries=None, archive=None, builddepends=None,
                     builddependsindep=None, architecturehintlist='all',
                     dsc_standards_version='3.6.2', dsc_format='1.0',
                     dsc_binaries='foo-bin', build_conflicts=None,
                     build_conflicts_indep=None,
                     dsc_maintainer_rfc822='Foo Bar <foo@bar.com>'):
        """Return a mock source publishing record."""
        spn = getUtility(ISourcePackageNameSet).getOrCreateByName(sourcename)

        component = getUtility(IComponentSet)[component]
        section = getUtility(ISectionSet)[section]

        if distroseries is None:
            distroseries = self.breezy_autotest
        if archive is None:
            archive = self.breezy_autotest.main_archive

        spr = distroseries.createUploadedSourcePackageRelease(
            sourcepackagename=spn,
            maintainer=self.person,
            creator=self.person,
            component=component,
            section=section,
            urgency=urgency,
            version=version,
            builddepends=builddepends,
            builddependsindep=builddependsindep,
            build_conflicts=build_conflicts,
            build_conflicts_indep=build_conflicts_indep,
            architecturehintlist=architecturehintlist,
            changelog_entry=None,
            dsc=None,
            copyright='placeholder ...',
            dscsigningkey=self.person.gpgkeys[0],
            dsc_maintainer_rfc822=dsc_maintainer_rfc822,
            dsc_standards_version=dsc_standards_version,
            dsc_format=dsc_format,
            dsc_binaries=dsc_binaries,
            archive=archive)

        if filename is None:
            filename = "%s.dsc" % sourcename
        alias = self.addMockFile(filename, filecontent)
        spr.addFile(alias)

        sspph = SecureSourcePackagePublishingHistory(
            distroseries=distroseries,
            sourcepackagerelease=spr,
            component=spr.component,
            section=spr.section,
            status=status,
            datecreated=UTC_NOW,
            dateremoved=dateremoved,
            scheduleddeletiondate=scheduleddeletiondate,
            pocket=pocket,
            embargo=False,
            archive=archive)

        # SPPH and SSPPH IDs are the same, since they are SPPH is a SQLVIEW
        # of SSPPH and other useful attributes.
        return SourcePackagePublishingHistory.get(sspph.id)

    def getPubBinaries(self, binaryname='foo-bin', summary='Foo app is great',
                       description='Well ...\nit does nothing, though',
                       shlibdep=None, depends=None, recommends=None,
                       suggests=None, conflicts=None, replaces=None,
                       provides=None, pre_depends=None, enhances=None,
                       breaks=None, filecontent='bbbiiinnnaaarrryyy',
                       status=PackagePublishingStatus.PENDING,
                       pocket=PackagePublishingPocket.RELEASE,
                       scheduleddeletiondate=None, dateremoved=None,
                       distroseries=None,
                       archive=None,
                       pub_source=None):
        """Return a list of binary publishing records."""
        if distroseries is None:
            distroseries = self.breezy_autotest
        sourcename = "%s" % binaryname.split('-')[0]
        if pub_source is None:
            pub_source = self.getPubSource(
                sourcename=sourcename, status=status, pocket=pocket,
                archive=archive)

        builds = pub_source.createBuilds(ignore_pas=True)
        published_binaries = []
        for build in builds:
            pub_binaries = self._buildAndPublishBinaryForSource(
                archive, build, status, pocket, scheduleddeletiondate,
                dateremoved, filecontent, binaryname, summary, description,
                shlibdep, depends, recommends, suggests, conflicts, replaces,
                provides, pre_depends, enhances, breaks)
            published_binaries.extend(pub_binaries)

        return sorted(
            published_binaries, key=operator.attrgetter('id'), reverse=True)

    def _buildAndPublishBinaryForSource(
        self, archive, build, status, pocket, scheduleddeletiondate,
        dateremoved, filecontent, binaryname, summary, description,
        shlibdep, depends, recommends, suggests, conflicts, replaces,
        provides, pre_depends, enhances, breaks):
        """Return the corresponding BinaryPackagePublishingHistory."""
        sourcepackagerelease = build.sourcepackagerelease
        distroarchseries = build.distroarchseries
        if archive is None:
            archive = build.archive

        # Create a BinaryPackageRelease
        bpn = getUtility(IBinaryPackageNameSet).getOrCreateByName(binaryname)
        architecturespecific = (
            not sourcepackagerelease.architecturehintlist == 'all')
        bpr = build.createBinaryPackageRelease(
            version=sourcepackagerelease.version,
            component=sourcepackagerelease.component.id,
            section=sourcepackagerelease.section.id,
            binarypackagename=bpn.id,
            summary=summary,
            description=description,
            shlibdeps=shlibdep,
            depends=depends,
            recommends=recommends,
            suggests=suggests,
            conflicts=conflicts,
            replaces=replaces,
            provides=provides,
            pre_depends=pre_depends,
            enhances=enhances,
            breaks=breaks,
            essential=False,
            installedsize=100,
            architecturespecific=architecturespecific,
            binpackageformat=BinaryPackageFormat.DEB,
            priority=PackagePublishingPriority.STANDARD)

        # Create the corresponding DEB file.
        if architecturespecific:
            filearchtag = distroarchseries.architecturetag
        else:
            filearchtag = 'all'
        filename = '%s_%s.deb' % (binaryname, filearchtag)
        alias = self.addMockFile(filename, filecontent=filecontent)
        bpr.addFile(alias)

        # Publish the binary.
        if architecturespecific:
            archs = [distroarchseries]
        else:
            archs = distroarchseries.distroseries.architectures

        secure_pub_binaries = []
        for arch in archs:
            pub = SecureBinaryPackagePublishingHistory(
                distroarchseries=arch,
                binarypackagerelease=bpr,
                component=bpr.component,
                section=bpr.section,
                priority=bpr.priority,
                status=status,
                scheduleddeletiondate=scheduleddeletiondate,
                dateremoved=dateremoved,
                datecreated=UTC_NOW,
                pocket=pocket,
                embargo=False,
                archive=archive)
            secure_pub_binaries.append(pub)

        return [BinaryPackagePublishingHistory.get(pub.id)
                for pub in secure_pub_binaries]


class TestNativePublishingBase(unittest.TestCase, SoyuzTestPublisher):
    layer = LaunchpadZopelessLayer
    dbuser = config.archivepublisher.dbuser

    def setUp(self):
        """Setup a pool dir, the librarian, and instantiate the DiskPool."""
        self.layer.switchDbUser(config.archivepublisher.dbuser)
        self.prepareBreezyAutotest()
        self.config = Config(self.ubuntutest)
        self.config.setupArchiveDirs()
        self.pool_dir = self.config.poolroot
        self.temp_dir = self.config.temproot
        self.logger = FakeLogger()
        def message(self, prefix, *stuff, **kw):
            pass
        self.logger.message = message
        self.disk_pool = DiskPool(self.pool_dir, self.temp_dir, self.logger)

    def tearDown(self):
        """Tear down blows the pool dir away."""
        shutil.rmtree(self.config.distroroot)

    def getPubSource(self, *args, **kwargs):
        """Overrides `SoyuzTestPublisher.getPubSource`.

        Commits the transaction before returning, this way the rest of
        the test will immediately notice the just-created records.
        """
        source = SoyuzTestPublisher.getPubSource(self, *args, **kwargs)
        self.layer.commit()
        return source

    def getPubBinaries(self, *args, **kwargs):
        """Overrides `SoyuzTestPublisher.getPubBinaries`.

        Commits the transaction before returning, this way the rest of
        the test will immediately notice the just-created records.
        """
        binaries = SoyuzTestPublisher.getPubBinaries(self, *args, **kwargs)
        self.layer.commit()
        return binaries

    def checkSourcePublication(self, source, status):
        """Assert the source publications has the given status.

        Retrieve an up-to-date record corresponding to the given publication,
        check and return it.
        """
        fresh_source = SourcePackagePublishingHistory.get(source.id)
        self.assertEqual(
            fresh_source.status, status, "%s is not %s (%s)" % (
            fresh_source.displayname, status.name, source.status.name))
        return fresh_source

    def checkBinaryPublication(self, binary, status):
        """Assert the binary publication has the given status.

        Retrieve an up-to-date record corresponding to the given publication,
        check and return it.
        """
        fresh_binary = BinaryPackagePublishingHistory.get(binary.id)
        self.assertEqual(
            fresh_binary.status, status, "%s is not %s (%s)" % (
            fresh_binary.displayname, status.name, fresh_binary.status.name))
        return fresh_binary

    def checkBinaryPublications(self, binaries, status):
        """Assert the binary publications have the given status.

        See `checkBinaryPublication`.
        """
        fresh_binaries = []
        for bin in binaries:
            bin = self.checkBinaryPublication(bin, status)
            fresh_binaries.append(bin)
        return fresh_binaries

    def checkPublications(self, source, binaries, status):
        """Assert source and binary publications have in the given status.

        See `checkSourcePublication` and `checkBinaryPublications`.
        """
        self.checkSourcePublication(source, status)
        self.checkBinaryPublications(binaries, status)

    def getSecureSource(self, source):
        """Return the corresponding SecureSourcePackagePublishingHistory."""
        return SecureSourcePackagePublishingHistory.get(source.id)

    def getSecureBinary(self, binary):
        """Return the corresponding SecureBinaryPackagePublishingHistory."""
        return SecureBinaryPackagePublishingHistory.get(binary.id)

    def checkPastDate(self, date, lag=None):
        """Assert given date is older than 'now'.

        Optionally the user can pass a 'lag' which will be added to 'now'
        before comparing.
        """
        UTC = pytz.timezone("UTC")
        limit = datetime.datetime.now(UTC)
        if lag is not None:
            limit = limit + lag
        self.assertTrue(date < limit, "%s >= %s" % (date, limit))


class TestNativePublishing(TestNativePublishingBase):

    def testPublish(self):
        """Test publishOne in normal conditions (new file)."""
        pub_source = self.getPubSource(filecontent='Hello world')
        pub_source.publish(self.disk_pool, self.logger)
        self.layer.commit()

        pub_source.sync()
        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)
        foo_name = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertEqual(open(foo_name).read().strip(), 'Hello world')

    def testPublishingOverwriteFileInPool(self):
        """Test if publishOne refuses to overwrite a file in pool.

        Check if it also keeps the original file content.
        It's done by publishing 'foo' by-hand and ensuring it
        has a special content, then publish 'foo' again, via publisher,
        and finally check one of the 'foo' files content.
        """
        foo_path = os.path.join(self.pool_dir, 'main', 'f', 'foo')
        os.makedirs(foo_path)
        foo_dsc_path = os.path.join(foo_path, 'foo.dsc')
        foo_dsc = open(foo_dsc_path, 'w')
        foo_dsc.write('Hello world')
        foo_dsc.close()

        pub_source = self.getPubSource(filecontent="Something")
        pub_source.publish(self.disk_pool, self.logger)
        self.layer.commit()
        self.assertEqual(
            pub_source.status,PackagePublishingStatus.PENDING)
        self.assertEqual(open(foo_dsc_path).read().strip(), 'Hello world')

    def testPublishingDifferentContents(self):
        """Test if publishOne refuses to overwrite its own publication."""
        pub_source = self.getPubSource(filecontent='foo is happy')
        pub_source.publish(self.disk_pool, self.logger)
        self.layer.commit()

        foo_name = "%s/main/f/foo/foo.dsc" % self.pool_dir
        pub_source.sync()
        self.assertEqual(
            pub_source.status, PackagePublishingStatus.PUBLISHED)
        self.assertEqual(open(foo_name).read().strip(), 'foo is happy')

        # try to publish 'foo' again with a different content, it
        # raises internally and keeps the files with the original
        # content.
        pub_source2 = self.getPubSource(filecontent='foo is depressing')
        pub_source2.publish(self.disk_pool, self.logger)
        self.layer.commit()

        pub_source2.sync()
        self.assertEqual(
            pub_source2.status, PackagePublishingStatus.PENDING)
        self.assertEqual(open(foo_name).read().strip(), 'foo is happy')

    def testPublishingAlreadyInPool(self):
        """Test if publishOne works if file is already in Pool.

        It should identify that the file has the same content and
        mark it as PUBLISHED.
        """
        pub_source = self.getPubSource(
            sourcename='bar', filecontent='bar is good')
        pub_source.publish(self.disk_pool, self.logger)
        self.layer.commit()
        bar_name = "%s/main/b/bar/bar.dsc" % self.pool_dir
        self.assertEqual(open(bar_name).read().strip(), 'bar is good')
        pub_source.sync()
        self.assertEqual(
            pub_source.status, PackagePublishingStatus.PUBLISHED)

        pub_source2 = self.getPubSource(
            sourcename='bar', filecontent='bar is good')
        pub_source2.publish(self.disk_pool, self.logger)
        self.layer.commit()
        pub_source2.sync()
        self.assertEqual(
            pub_source2.status, PackagePublishingStatus.PUBLISHED)

    def testPublishingSymlink(self):
        """Test if publishOne moving publication between components.

        After check if the pool file contents as the same, it should
        create a symlink in the new pointing to the original file.
        """
        content = 'am I a file or a symbolic link ?'
        # publish sim.dsc in main and re-publish in universe
        pub_source = self.getPubSource(
            sourcename='sim', filecontent=content)
        pub_source2 = self.getPubSource(
            sourcename='sim', component='universe', filecontent=content)
        pub_source.publish(self.disk_pool, self.logger)
        pub_source2.publish(self.disk_pool, self.logger)
        self.layer.commit()

        pub_source.sync()
        pub_source2.sync()
        self.assertEqual(
            pub_source.status, PackagePublishingStatus.PUBLISHED)
        self.assertEqual(
            pub_source2.status, PackagePublishingStatus.PUBLISHED)

        # check the resulted symbolic link
        sim_universe = "%s/universe/s/sim/sim.dsc" % self.pool_dir
        self.assertEqual(
            os.readlink(sim_universe), '../../../main/s/sim/sim.dsc')

        # if the contexts don't match it raises, so the publication
        # remains pending.
        pub_source3 = self.getPubSource(
            sourcename='sim', component='restricted',
            filecontent='It is all my fault')
        pub_source3.publish(self.disk_pool, self.logger)
        self.layer.commit()

        pub_source3.sync()
        self.assertEqual(
            pub_source3.status, PackagePublishingStatus.PENDING)

    def testPublishInAnotherArchive(self):
        """Publication in another archive

        Basically test if publishing records target to other archive
        than Distribution.main_archive work as expected
        """
        cprov = getUtility(IPersonSet).getByName('cprov')
        test_pool_dir = tempfile.mkdtemp()
        test_temp_dir = tempfile.mkdtemp()
        test_disk_pool = DiskPool(test_pool_dir, test_temp_dir, self.logger)

        pub_source = self.getPubSource(
            sourcename="foo", filename="foo.dsc",
            filecontent='Am I a PPA Record ?',
            archive=cprov.archive)
        pub_source.publish(test_disk_pool, self.logger)
        self.layer.commit()

        pub_source.sync()
        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)
        self.assertEqual(pub_source.sourcepackagerelease.upload_archive,
                         cprov.archive)
        foo_name = "%s/main/f/foo/foo.dsc" % test_pool_dir
        self.assertEqual(open(foo_name).read().strip(), 'Am I a PPA Record ?')

        # Remove locally created dir.
        shutil.rmtree(test_pool_dir)
        shutil.rmtree(test_temp_dir)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
