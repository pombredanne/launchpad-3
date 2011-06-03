# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the initialise_distroseries script machinery."""

__metaclass__ = type

import os
import subprocess
import sys

from testtools.content import Content
from testtools.content_type import UTF8_TEXT
import transaction
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.distroseriesparent import IDistroSeriesParentSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.enums import SourcePackageFormat
from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.packageset import (
    IPackagesetSet,
    NoSuchPackageSet,
    )
from lp.soyuz.interfaces.processor import IProcessorFamilySet
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

    def setupParent(self, packages=None):
        parent = self.factory.makeDistroSeries()
        pf = getUtility(IProcessorFamilySet).getByName('x86')
        if pf is None:
            pf = self.factory.makeProcessorFamily(name='x86')
            pf.addProcessor('x86', '', '')
        parent_das = self.factory.makeDistroArchSeries(
            distroseries=parent, processorfamily=pf)
        lf = self.factory.makeLibraryFileAlias()
        transaction.commit()
        parent_das.addOrUpdateChroot(lf)
        parent_das.supports_virtualized = True
        parent.nominatedarchindep = parent_das
        getUtility(ISourcePackageFormatSelectionSet).add(
            parent, SourcePackageFormat.FORMAT_1_0)
        parent.backports_not_automatic = True
        self._populate_parent(parent, parent_das, packages)
        return parent, parent_das

    def _populate_parent(self, parent, parent_das, packages=None):
        if packages is None:
            packages = {'udev': '0.1-1', 'libc6': '2.8-1',
                'postgresql': '9.0-1', 'chromium': '3.6'}
        for package in packages.keys():
            spn = self.factory.getOrMakeSourcePackageName(package)
            spph = self.factory.makeSourcePackagePublishingHistory(
                sourcepackagename=spn, version=packages[package],
                distroseries=parent,
                pocket=PackagePublishingPocket.RELEASE,
                status=PackagePublishingStatus.PUBLISHED)
            status = BuildStatus.FULLYBUILT
            if package is 'chromium':
                status = BuildStatus.FAILEDTOBUILD
            bpn = self.factory.getOrMakeBinaryPackageName(package)
            build = self.factory.makeBinaryPackageBuild(
                source_package_release=spph.sourcepackagerelease,
                distroarchseries=parent_das,
                status=status)
            bpr = self.factory.makeBinaryPackageRelease(
                binarypackagename=bpn, build=build,
                version=packages[package])
            if package is not 'chromium':
                self.factory.makeBinaryPackagePublishingHistory(
                    binarypackagerelease=bpr,
                    distroarchseries=parent_das,
                    pocket=PackagePublishingPocket.RELEASE,
                    status=PackagePublishingStatus.PUBLISHED)

    def test_failure_for_already_released_distroseries(self):
        # Initialising a distro series that has already been used will
        # error.
        self.parent, self.parent_das = self.setupParent()
        child = self.factory.makeDistroSeries()
        self.factory.makeDistroArchSeries(distroseries=child)
        ids = InitialiseDistroSeries(child, [self.parent.id])
        self.assertRaisesWithContent(
            InitialisationError,
            "Can not copy distroarchseries from parent, there are already "
            "distroarchseries(s) initialised for this series.", ids.check)

    def test_failure_with_pending_builds(self):
        # If the parent series has pending builds, and the child is a series
        # of the same distribution (which means they share an archive), we
        # can't initialise.
        self.parent, self.parent_das = self.setupParent()
        source = self.factory.makeSourcePackagePublishingHistory(
            distroseries=self.parent,
            pocket=PackagePublishingPocket.RELEASE)
        source.createMissingBuilds()
        child = self.factory.makeDistroSeries(
            distribution=self.parent.parent)
        ids = InitialiseDistroSeries(child, [self.parent.id])
        self.assertRaisesWithContent(
            InitialisationError, "Parent series has pending builds.",
            ids.check)

    def test_success_with_pending_builds(self):
        # If the parent series has pending builds, and the child's
        # distribution is different, we can initialise.
        self.parent, self.parent_das = self.setupParent()
        source = self.factory.makeSourcePackagePublishingHistory(
            distroseries=self.parent,
            pocket=PackagePublishingPocket.RELEASE)
        source.createMissingBuilds()
        child = self._full_initialise(self.parent)
        self.assertDistroSeriesInitialisedCorrectly(
            child, self.parent, self.parent_das)

    def test_failure_with_queue_items(self):
        # If the parent series has items in its queues, such as NEW and
        # UNAPPROVED, we can't initialise.
        self.parent, self.parent_das = self.setupParent()
        self.parent.createQueueEntry(
            PackagePublishingPocket.RELEASE,
            'foo.changes', 'bar', self.parent.main_archive)
        child = self.factory.makeDistroSeries()
        ids = InitialiseDistroSeries(child, [self.parent.id])
        self.assertRaisesWithContent(
            InitialisationError, "Parent series queues are not empty.",
            ids.check)

    def assertDistroSeriesInitialisedCorrectly(self, child, parent,
                                               parent_das):
        # Check that 'udev' has been copied correctly.
        parent_udev_pubs = parent.getPublishedSources('udev')
        child_udev_pubs = child.getPublishedSources('udev')
        self.assertEqual(
            parent_udev_pubs.count(), child_udev_pubs.count())
        parent_arch_udev_pubs = parent[
            parent_das.architecturetag].getReleasedPackages('udev')
        child_arch_udev_pubs = child[
            parent_das.architecturetag].getReleasedPackages('udev')
        self.assertEqual(
            len(parent_arch_udev_pubs), len(child_arch_udev_pubs))
        # And the binary package, and linked source package look fine too.
        udev_bin = child_arch_udev_pubs[0].binarypackagerelease
        self.assertEqual(udev_bin.title, u'udev-0.1-1')
        self.assertEqual(
            udev_bin.build.title,
            u'%s build of udev 0.1-1 in %s %s RELEASE' % (
                parent_das.architecturetag, parent.parent.name,
                parent.name))
        udev_src = udev_bin.build.source_package_release
        self.assertEqual(udev_src.title, u'udev - 0.1-1')
        # The build of udev 0.1-1 has been copied across.
        child_udev = udev_src.getBuildByArch(
            child[parent_das.architecturetag], child.main_archive)
        parent_udev = udev_src.getBuildByArch(
            parent[parent_das.architecturetag],
            parent.main_archive)
        self.assertEqual(parent_udev.id, child_udev.id)
        # We also inherit the permitted source formats from our parent.
        self.assertTrue(
            child.isSourcePackageFormatPermitted(
            SourcePackageFormat.FORMAT_1_0))
        # Other configuration bits are copied too.
        self.assertTrue(child.backports_not_automatic)

    def _full_initialise(self, parent, child=None, arches=(), packagesets=(),
                         rebuild=False, distribution=None, overlays=(),
                         overlay_pockets=(), overlay_components=()):
        if child is None:
            child = self.factory.makeDistroSeries(distribution=distribution)
        ids = InitialiseDistroSeries(
            child, [parent.id], arches, packagesets, rebuild, overlays,
            overlay_pockets, overlay_components)
        ids.check()
        ids.initialise()
        return child

    def test_initialise(self):
        # Test a full initialise with no errors.
        self.parent, self.parent_das = self.setupParent()
        child = self._full_initialise(self.parent)
        self.assertDistroSeriesInitialisedCorrectly(
            child, self.parent, self.parent_das)

    def test_initialise_only_one_das(self):
        # Test a full initialise with no errors, but only copy i386 to
        # the child.
        self.parent, self.parent_das = self.setupParent()
        self.factory.makeDistroArchSeries(distroseries=self.parent)
        child = self._full_initialise(
            self.parent,
            arches=[self.parent_das.architecturetag])
        self.assertDistroSeriesInitialisedCorrectly(
            child, self.parent, self.parent_das)
        das = list(IStore(DistroArchSeries).find(
            DistroArchSeries, distroseries=child))
        self.assertEqual(len(das), 1)
        self.assertEqual(
            das[0].architecturetag, self.parent_das.architecturetag)

    def test_copying_packagesets(self):
        # If a parent series has packagesets, we should copy them.
        self.parent, self.parent_das = self.setupParent()
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
        child = self._full_initialise(self.parent)
        # We can fetch the copied sets from the child.
        child_test1 = getUtility(IPackagesetSet).getByName(
            u'test1', distroseries=child)
        child_test2 = getUtility(IPackagesetSet).getByName(
            u'test2', distroseries=child)
        child_test3 = getUtility(IPackagesetSet).getByName(
            u'test3', distroseries=child)
        # And we can see they are exact copies, with the related_set for the
        # copies pointing to the packageset in the parent.
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

    def test_packageset_owner_preserved_within_distro(self):
        # When initialising a new series within a distro, the copied
        # packagesets have ownership preserved.
        self.parent, self.parent_das = self.setupParent()
        ps_owner = self.factory.makePerson()
        getUtility(IPackagesetSet).new(
            u'ps', u'packageset', ps_owner, distroseries=self.parent)
        child = self._full_initialise(
            self.parent, distribution=self.parent.distribution)
        child_ps = getUtility(IPackagesetSet).getByName(
            u'ps', distroseries=child)
        self.assertEqual(ps_owner, child_ps.owner)

    def test_packageset_owner_not_preserved_cross_distro(self):
        # In the case of a cross-distro initialisation, the new
        # packagesets are owned by the new distro owner.
        self.parent, self.parent_das = self.setupParent()
        getUtility(IPackagesetSet).new(
            u'ps', u'packageset', self.factory.makePerson(),
            distroseries=self.parent)
        child = self._full_initialise(self.parent)
        child_ps = getUtility(IPackagesetSet).getByName(
            u'ps', distroseries=child)
        self.assertEqual(child.owner, child_ps.owner)

    def test_copy_limit_packagesets(self):
        # If a parent series has packagesets, we can decide which ones we
        # want to copy.
        self.parent, self.parent_das = self.setupParent()
        test1 = getUtility(IPackagesetSet).new(
            u'test1', u'test 1 packageset', self.parent.owner,
            distroseries=self.parent)
        getUtility(IPackagesetSet).new(
            u'test2', u'test 2 packageset', self.parent.owner,
            distroseries=self.parent)
        packages = ('udev', 'chromium', 'libc6')
        for pkg in packages:
            test1.addSources(pkg)
        packageset1 = getUtility(IPackagesetSet).getByName(
            u'test1', distroseries=self.parent)
        child = self._full_initialise(
            self.parent, packagesets=(str(packageset1.id),))
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
        self.assertEqual(child.binarycount, 2)  # Chromium is FTBFS

    def test_rebuild_flag(self):
        # No binaries will get copied if we specify rebuild=True.
        self.parent, self.parent_das = self.setupParent()
        self.parent.updatePackageCount()
        child = self._full_initialise(self.parent, rebuild=True)
        child.updatePackageCount()
        builds = child.getBuildRecords(
            build_state=BuildStatus.NEEDSBUILD,
            pocket=PackagePublishingPocket.RELEASE)
        self.assertEqual(self.parent.sourcecount, child.sourcecount)
        self.assertEqual(child.binarycount, 0)
        self.assertEqual(builds.count(), self.parent.sourcecount)

    def test_limit_packagesets_rebuild_and_one_das(self):
        # We can limit the source packages copied, and only builds
        # for the copied source will be created.
        self.parent, self.parent_das = self.setupParent()
        test1 = getUtility(IPackagesetSet).new(
            u'test1', u'test 1 packageset', self.parent.owner,
            distroseries=self.parent)
        getUtility(IPackagesetSet).new(
            u'test2', u'test 2 packageset', self.parent.owner,
            distroseries=self.parent)
        packages = ('udev', 'chromium')
        for pkg in packages:
            test1.addSources(pkg)
        self.factory.makeDistroArchSeries(distroseries=self.parent)
        child = self._full_initialise(
            self.parent,
            arches=[self.parent_das.architecturetag],
            packagesets=(str(test1.id),), rebuild=True)
        child.updatePackageCount()
        builds = child.getBuildRecords(
            build_state=BuildStatus.NEEDSBUILD,
            pocket=PackagePublishingPocket.RELEASE)
        self.assertEqual(child.sourcecount, len(packages))
        self.assertEqual(child.binarycount, 0)
        self.assertEqual(builds.count(), len(packages))
        das = list(IStore(DistroArchSeries).find(
            DistroArchSeries, distroseries=child))
        self.assertEqual(len(das), 1)
        self.assertEqual(
            das[0].architecturetag, self.parent_das.architecturetag)

    def test_do_not_copy_disabled_dases(self):
        # DASes that are disabled in the parent will not be copied.
        self.parent, self.parent_das = self.setupParent()
        ppc_das = self.factory.makeDistroArchSeries(
            distroseries=self.parent)
        ppc_das.enabled = False
        child = self._full_initialise(self.parent)
        das = list(IStore(DistroArchSeries).find(
            DistroArchSeries, distroseries=child))
        self.assertEqual(len(das), 1)
        self.assertEqual(
            das[0].architecturetag, self.parent_das.architecturetag)

    def test_script(self):
        # Do an end-to-end test using the command-line tool.
        self.parent, self.parent_das = self.setupParent()
        uploader = self.factory.makePerson()
        test1 = getUtility(IPackagesetSet).new(
            u'test1', u'test 1 packageset', self.parent.owner,
            distroseries=self.parent)
        test1.addSources('udev')
        getUtility(IArchivePermissionSet).newPackagesetUploader(
            self.parent.main_archive, uploader, test1)
        # The child must have a parent series because initialise-from-parent
        # expects it; this script supports the old-style derivation of
        # distribution series where the parent series is specified at the time
        # of adding the series. New-style derivation leaves the specification
        # of the parent series until later.
        child = self.factory.makeDistroSeries(previous_series=self.parent)
        transaction.commit()
        ifp = os.path.join(
            config.root, 'scripts', 'ftpmaster-tools',
            'initialise-from-parent.py')
        process = subprocess.Popen(
            [sys.executable, ifp, "-vv", "-d", child.parent.name,
            child.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        self.addDetail("stdout", Content(UTF8_TEXT, lambda: stdout))
        self.addDetail("stderr", Content(UTF8_TEXT, lambda: stderr))
        self.assertEqual(process.returncode, 0)
        self.assertTrue(
            "DEBUG   Committing transaction." in stderr.split('\n'))
        transaction.commit()
        self.assertDistroSeriesInitialisedCorrectly(
            child, self.parent, self.parent_das)

    def test_is_initialized(self):
        # At the end of the initialisation, the distroseriesparent is marked
        # as 'initialised'.
        self.parent, self.parent_das = self.setupParent()
        child = self._full_initialise(self.parent, rebuild=True, overlays=())
        dsp_set = getUtility(IDistroSeriesParentSet)
        distroseriesparent = dsp_set.getByDerivedAndParentSeries(
            child, self.parent)

        self.assertTrue(distroseriesparent.initialized)

    def test_no_overlays(self):
        # Without the overlay parameter, no overlays are created.
        self.parent, self.parent_das = self.setupParent()
        child = self._full_initialise(self.parent, rebuild=True, overlays=[])
        dsp_set = getUtility(IDistroSeriesParentSet)
        distroseriesparent = dsp_set.getByDerivedAndParentSeries(
            child, self.parent)

        self.assertFalse(distroseriesparent.is_overlay)

    def test_setup_overlays(self):
        # If the overlay parameter is passed, overlays are properly setup.
        self.parent, self.parent_das = self.setupParent()
        child = self.factory.makeDistroSeries()
        overlays = [True]
        overlay_pockets = ['Updates']
        overlay_components = ['universe']
        child = self._full_initialise(
            self.parent, child=child, rebuild=True, overlays=overlays,
            overlay_pockets=overlay_pockets,
            overlay_components=overlay_components)
        dsp_set = getUtility(IDistroSeriesParentSet)
        distroseriesparent = dsp_set.getByDerivedAndParentSeries(
            child, self.parent)

        self.assertTrue(distroseriesparent.is_overlay)
        self.assertEqual(
            getUtility(IComponentSet)['universe'],
            distroseriesparent.component)
        self.assertEqual(
            PackagePublishingPocket.UPDATES, distroseriesparent.pocket)


class TestInitialiseDistroSeriesMultipleParents(TestInitialiseDistroSeries):

    layer = LaunchpadZopelessLayer

    def _fullInitialise(self, parents, child=None, arches=(), packagesets=(),
                        rebuild=False, distribution=None, overlays=(),
                        overlay_pockets=(), overlay_components=()):
        if child is None:
            child = self.factory.makeDistroSeries(distribution=distribution)
        ids = InitialiseDistroSeries(
            child, [parent.id for parent in parents], arches, packagesets,
            rebuild, overlays, overlay_pockets, overlay_components)
        ids.check()
        ids.initialise()
        return child

    def test_multiple_parents(self):
        self.parent, self.parent_das = self.setupParent()
        self.parent2, self.parent_das2 = self.setupParent()
        self._fullInitialise([self.parent, self.parent2])
