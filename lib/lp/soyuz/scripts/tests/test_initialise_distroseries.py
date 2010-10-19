# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the initialise_distroseries script machinery."""

__metaclass__ = type

import os
import subprocess
import sys

import transaction
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.enums import SourcePackageFormat
from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet
from lp.soyuz.interfaces.packageset import (
    IPackagesetSet,
    NoSuchPackageSet,
    )
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.interfaces.sourcepackageformat import (
    ISourcePackageFormatSelectionSet,
    )
from lp.soyuz.model.distroarchseries import DistroArchSeries
from lp.soyuz.scripts.initialise_distroseries import (
    InitialisationError,
    InitialiseDistroSeries,
    )
from lp.testing import TestCaseWithFactory


class TestInitialiseDistroSeries(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestInitialiseDistroSeries, self).setUp()
        self.parent = self.factory.makeDistroSeries()
        pf = self.factory.makeProcessorFamily()
        pf.addProcessor('x86', '', '')
        self.parent_das = self.factory.makeDistroArchSeries(
            distroseries=self.parent, processorfamily=pf)
        lf = self.factory.makeLibraryFileAlias()
        transaction.commit()
        self.parent_das.addOrUpdateChroot(lf)
        self.parent_das.supports_virtualized = True
        self.parent.nominatedarchindep = self.parent_das
        getUtility(ISourcePackageFormatSelectionSet).add(
            self.parent, SourcePackageFormat.FORMAT_1_0)
        self._populate_parent()

    def _populate_parent(self):
        packages = {'udev': '0.1-1', 'libc6': '2.8-1',
            'postgresql': '9.0-1', 'chromium': '3.6'}
        for package in packages.keys():
            spn = self.factory.makeSourcePackageName(package)
            spph = self.factory.makeSourcePackagePublishingHistory(
                sourcepackagename=spn, version=packages[package],
                distroseries=self.parent,
                pocket=PackagePublishingPocket.RELEASE,
                status=PackagePublishingStatus.PUBLISHED)
            status = BuildStatus.FULLYBUILT
            if package is 'chromium':
                status = BuildStatus.FAILEDTOBUILD
            bpn = self.factory.makeBinaryPackageName(package)
            build = self.factory.makeBinaryPackageBuild(
                source_package_release=spph.sourcepackagerelease,
                distroarchseries=self.parent_das,
                status=status)
            bpr = self.factory.makeBinaryPackageRelease(
                binarypackagename=bpn, build=build,
                version=packages[package])
            if package is not 'chromium':
                self.factory.makeBinaryPackagePublishingHistory(
                    binarypackagerelease=bpr,
                    distroarchseries=self.parent_das,
                    pocket=PackagePublishingPocket.RELEASE,
                    status=PackagePublishingStatus.PUBLISHED)

    def test_failure_with_no_parent_series(self):
        # Initialising a new distro series requires a parent series to be set
        ids = InitialiseDistroSeries(self.factory.makeDistroSeries())
        self.assertRaisesWithContent(
            InitialisationError, "Parent series required.", ids.check)

    def test_failure_for_already_released_distroseries(self):
        # Initialising a distro series that has already been used will error
        child = self.factory.makeDistroSeries(parent_series=self.parent)
        self.factory.makeDistroArchSeries(distroseries=child)
        ids = InitialiseDistroSeries(child)
        self.assertRaisesWithContent(
            InitialisationError,
            "Can not copy distroarchseries from parent, there are already "
            "distroarchseries(s) initialised for this series.", ids.check)

    def test_failure_with_pending_builds(self):
        # If the parent series has pending builds, we can't initialise
        source = self.factory.makeSourcePackagePublishingHistory(
            distroseries=self.parent,
            pocket=PackagePublishingPocket.RELEASE)
        source.createMissingBuilds()
        child = self.factory.makeDistroSeries(
            parent_series=self.parent)
        ids = InitialiseDistroSeries(child)
        self.assertRaisesWithContent(
            InitialisationError, "Parent series has pending builds.",
            ids.check)

    def test_failure_with_queue_items(self):
        # If the parent series has items in its queues, such as NEW and
        # UNAPPROVED, we can't initialise
        self.parent.createQueueEntry(
            PackagePublishingPocket.RELEASE,
            'foo.changes', 'bar', self.parent.main_archive)
        child = self.factory.makeDistroSeries(parent_series=self.parent)
        ids = InitialiseDistroSeries(child)
        self.assertRaisesWithContent(
            InitialisationError, "Parent series queues are not empty.",
            ids.check)

    def assertDistroSeriesInitialisedCorrectly(self, child):
        # Check that 'udev' has been copied correctly
        parent_udev_pubs = self.parent.getPublishedSources('udev')
        child_udev_pubs = child.getPublishedSources('udev')
        self.assertEqual(
            parent_udev_pubs.count(), child_udev_pubs.count())
        parent_arch_udev_pubs = self.parent[
            self.parent_das.architecturetag].getReleasedPackages('udev')
        child_arch_udev_pubs = child[
            self.parent_das.architecturetag].getReleasedPackages('udev')
        self.assertEqual(
            len(parent_arch_udev_pubs), len(child_arch_udev_pubs))
        # And the binary package, and linked source package look fine too
        udev_bin = child_arch_udev_pubs[0].binarypackagerelease
        self.assertEqual(udev_bin.title, u'udev-0.1-1')
        self.assertEqual(
            udev_bin.build.title,
            u'%s build of udev 0.1-1 in %s %s RELEASE' % (
                self.parent_das.architecturetag, self.parent.parent.name,
                self.parent.name))
        udev_src = udev_bin.build.source_package_release
        self.assertEqual(udev_src.title, u'udev - 0.1-1')
        # The build of udev 0.1-1 has been copied across.
        child_udev = udev_src.getBuildByArch(
            child[self.parent_das.architecturetag], child.main_archive)
        parent_udev = udev_src.getBuildByArch(
            self.parent[self.parent_das.architecturetag],
            self.parent.main_archive)
        self.assertEqual(parent_udev.id, child_udev.id)
        # We also inherient the permitted source formats from our parent
        self.assertTrue(
            child.isSourcePackageFormatPermitted(
            SourcePackageFormat.FORMAT_1_0))

    def _full_initialise(self, arches=(), packagesets=(), rebuild=False):
        child = self.factory.makeDistroSeries(parent_series=self.parent)
        ids = InitialiseDistroSeries(child, arches, packagesets, rebuild)
        ids.check()
        ids.initialise()
        return child

    def test_initialise(self):
        # Test a full initialise with no errors
        child = self._full_initialise()
        self.assertDistroSeriesInitialisedCorrectly(child)

    def test_initialise_only_one_das(self):
        # Test a full initialise with no errors, but only copy i386 to
        # the child
        self.factory.makeDistroArchSeries(distroseries=self.parent)
        child = self._full_initialise(
            arches=[self.parent_das.architecturetag])
        self.assertDistroSeriesInitialisedCorrectly(child)
        das = list(IStore(DistroArchSeries).find(
            DistroArchSeries, distroseries = child))
        self.assertEqual(len(das), 1)
        self.assertEqual(
            das[0].architecturetag, self.parent_das.architecturetag)

    def test_copying_packagesets(self):
        # If a parent series has packagesets, we should copy them
        uploader = self.factory.makePerson()
        test1 = getUtility(IPackagesetSet).new(
            u'test1', u'test 1 packageset', self.parent.owner,
            distroseries=self.parent)
        test2 = getUtility(IPackagesetSet).new(
            u'test2', u'test 2 packageset', self.parent.owner,
            distroseries=self.parent)
        test3 = getUtility(IPackagesetSet).new(
            u'test3', u'test 3 packageset', self.parent.owner,
            distroseries=self.parent, related_set=test2)
        test1.addSources('udev')
        getUtility(IArchivePermissionSet).newPackagesetUploader(
            self.parent.main_archive, uploader, test1)
        child = self._full_initialise()
        # We can fetch the copied sets from the child
        child_test1 = getUtility(IPackagesetSet).getByName(
            u'test1', distroseries=child)
        child_test2 = getUtility(IPackagesetSet).getByName(
            u'test2', distroseries=child)
        child_test3 = getUtility(IPackagesetSet).getByName(
            u'test3', distroseries=child)
        # And we can see they are exact copies, with the related_set for the
        # copies pointing to the packageset in the parent
        self.assertEqual(test1.description, child_test1.description)
        self.assertEqual(test2.description, child_test2.description)
        self.assertEqual(test3.description, child_test3.description)
        self.assertEqual(child_test1.relatedSets().one(), test1)
        self.assertEqual(
            list(child_test2.relatedSets()),
            [test2, test3, child_test3])
        self.assertEqual(
            list(child_test3.relatedSets()),
            [test2, child_test2, test3])
        # The contents of the packagesets will have been copied.
        child_srcs = child_test1.getSourcesIncluded(
            direct_inclusion=True)
        parent_srcs = test1.getSourcesIncluded(direct_inclusion=True)
        self.assertEqual(parent_srcs, child_srcs)
        # The uploader can also upload to the new distroseries.
        self.assertTrue(
            getUtility(IArchivePermissionSet).isSourceUploadAllowed(
                self.parent.main_archive, 'udev', uploader,
                distroseries=self.parent))
        self.assertTrue(
            getUtility(IArchivePermissionSet).isSourceUploadAllowed(
                child.main_archive, 'udev', uploader,
                distroseries=child))

    def test_copy_limit_packagesets(self):
        # If a parent series has packagesets, we can decide which ones we
        # want to copy
        test1 = getUtility(IPackagesetSet).new(
            u'test1', u'test 1 packageset', self.parent.owner,
            distroseries=self.parent)
        test2 = getUtility(IPackagesetSet).new(
            u'test2', u'test 2 packageset', self.parent.owner,
            distroseries=self.parent)
        packages = ('udev', 'chromium', 'libc6')
        for pkg in packages:
            test1.addSources(pkg)
        child = self._full_initialise(packagesets=('test1',))
        child_test1 = getUtility(IPackagesetSet).getByName(
            u'test1', distroseries=child)
        self.assertEqual(test1.description, child_test1.description)
        self.assertRaises(
            NoSuchPackageSet, getUtility(IPackagesetSet).getByName,
                u'test2', distroseries=child)
        parent_srcs = test1.getSourcesIncluded(direct_inclusion=True)
        child_srcs = child_test1.getSourcesIncluded(
            direct_inclusion=True)
        self.assertEqual(parent_srcs, child_srcs)
        child.updatePackageCount()
        self.assertEqual(child.sourcecount, len(packages))
        self.assertEqual(child.binarycount, 2) # Chromium is FTBFS

    def test_rebuild_flag(self):
        # No binaries will get copied if we specify rebuild=True
        self.parent.updatePackageCount()
        child = self._full_initialise(rebuild=True)
        child.updatePackageCount()
        builds = child.getBuildRecords(
            build_state=BuildStatus.NEEDSBUILD,
            pocket=PackagePublishingPocket.RELEASE)
        self.assertEqual(self.parent.sourcecount, child.sourcecount)
        self.assertEqual(child.binarycount, 0)
        self.assertEqual(builds.count(), self.parent.sourcecount)

    def test_limit_packagesets_rebuild_and_one_das(self):
        # We can limit the source packages copied, and only builds
        # for the copied source will be created
        test1 = getUtility(IPackagesetSet).new(
            u'test1', u'test 1 packageset', self.parent.owner,
            distroseries=self.parent)
        test2 = getUtility(IPackagesetSet).new(
            u'test2', u'test 2 packageset', self.parent.owner,
            distroseries=self.parent)
        packages = ('udev', 'chromium')
        for pkg in packages:
            test1.addSources(pkg)
        self.factory.makeDistroArchSeries(distroseries=self.parent)
        child = self._full_initialise(
            arches=[self.parent_das.architecturetag],
            packagesets=('test1',), rebuild=True)
        child.updatePackageCount()
        builds = child.getBuildRecords(
            build_state=BuildStatus.NEEDSBUILD,
            pocket=PackagePublishingPocket.RELEASE)
        self.assertEqual(child.sourcecount, len(packages))
        self.assertEqual(child.binarycount, 0)
        self.assertEqual(builds.count(), len(packages))
        das = list(IStore(DistroArchSeries).find(
            DistroArchSeries, distroseries = child))
        self.assertEqual(len(das), 1)
        self.assertEqual(
            das[0].architecturetag, self.parent_das.architecturetag)

    def test_do_not_copy_disabled_dases(self):
        # DASes that are disabled in the parent will not be copied
        ppc_das = self.factory.makeDistroArchSeries(
            distroseries=self.parent)
        ppc_das.enabled = False
        child = self._full_initialise()
        das = list(IStore(DistroArchSeries).find(
            DistroArchSeries, distroseries = child))
        self.assertEqual(len(das), 1)
        self.assertEqual(
            das[0].architecturetag, self.parent_das.architecturetag)

    def test_script(self):
        # Do an end-to-end test using the command-line tool
        uploader = self.factory.makePerson()
        test1 = getUtility(IPackagesetSet).new(
            u'test1', u'test 1 packageset', self.parent.owner,
            distroseries=self.parent)
        test1.addSources('udev')
        getUtility(IArchivePermissionSet).newPackagesetUploader(
            self.parent.main_archive, uploader, test1)
        child = self.factory.makeDistroSeries(parent_series=self.parent)
        transaction.commit()
        ifp = os.path.join(
            config.root, 'scripts', 'ftpmaster-tools',
            'initialise-from-parent.py')
        process = subprocess.Popen(
            [sys.executable, ifp, "-vv", "-d", child.parent.name,
            child.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        self.assertEqual(process.returncode, 0)
        self.assertTrue(
            "DEBUG   Committing transaction." in stderr.split('\n'))
        self.assertDistroSeriesInitialisedCorrectly(child)
