# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.testing import LaunchpadZopelessLayer

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.adapters.packagelocation import PackageLocation
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuildSet
from lp.soyuz.interfaces.packagecloner import IPackageCloner
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.model.processor import ProcessorFamilySet
from lp.testing import TestCaseWithFactory


class PackageInfo:

    def __init__(self, name, version,
                 status=PackagePublishingStatus.PUBLISHED, component="main"):
        self.name = name
        self.version = version
        self.status = status
        self.component = component


class PackageClonerTests(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def checkCopiedSources(self, archive, distroseries, expected):
        """Check the sources published in an archive against an expected set.

        Given an archive and a target distroseries the sources published in
        that distroseries are checked against a set of PackageInfo to
        ensure that the correct package names and versions are published.
        """
        expected_set = set([(info.name, info.version) for info in expected])
        sources = archive.getPublishedSources(
            distroseries=distroseries,
            status=(PackagePublishingStatus.PENDING,
                PackagePublishingStatus.PUBLISHED))
        actual_set = set()
        for source in sources:
            source = removeSecurityProxy(source)
            actual_set.add(
                (source.source_package_name, source.source_package_version))
        self.assertEqual(expected_set, actual_set)

    def createSourceDistribution(self, package_infos):
        """Create a distribution to be the source of a copy archive."""
        distroseries = self.createSourceDistroSeries()
        self.createSourcePublications(package_infos, distroseries)
        return distroseries

    def createSourceDistroSeries(self):
        """Create a DistroSeries suitable for copying.

        Creates a distroseries with a DistroArchSeries and nominatedarchindep,
        which makes it suitable for copying because it will create some builds.
        """
        distro_name = "foobuntu"
        distro = self.factory.makeDistribution(name=distro_name)
        distroseries_name = "maudlin"
        distroseries = self.factory.makeDistroSeries(
            distribution=distro, name=distroseries_name)
        das = self.factory.makeDistroArchSeries(
            distroseries=distroseries, architecturetag="i386",
            processorfamily=ProcessorFamilySet().getByName("x86"),
            supports_virtualized=True)
        distroseries.nominatedarchindep = das
        return distroseries

    def getTargetArchive(self, distribution):
        """Get a target archive for copying in to."""
        return self.factory.makeArchive(
            name="test-copy-archive", purpose=ArchivePurpose.COPY,
            distribution=distribution)

    def createSourcePublication(self, info, distroseries):
        """Create a SourcePackagePublishingHistory based on a PackageInfo."""
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=self.factory.getOrMakeSourcePackageName(
                name=info.name),
            distroseries=distroseries, component=self.factory.makeComponent(
                info.component),
            version=info.version, architecturehintlist='any',
            archive=distroseries.distribution.main_archive,
            status=info.status, pocket=PackagePublishingPocket.RELEASE)

    def createSourcePublications(self, package_infos, distroseries):
        """Create a source publication for each item in package_infos."""
        for package_info in package_infos:
            self.createSourcePublication(package_info, distroseries)

    def makeCopyArchive(self, package_infos, component="main",
                        source_pocket=None, target_pocket=None):
        """Make a copy archive based on a new distribution."""
        distroseries = self.createSourceDistribution(package_infos)
        copy_archive = self.getTargetArchive(distroseries.distribution)
        to_component = getUtility(IComponentSet).ensure(component)
        cloner = self.copyArchive(
            copy_archive, distroseries, from_pocket=source_pocket,
            to_pocket=target_pocket, to_component=to_component)
        return (copy_archive, distroseries)

    def checkBuilds(self, archive, package_infos):
        """Check the build records pending in an archive.

        Given a set of PackageInfo objects check that each has a build
        created for it.
        """
        expected_builds = list(
            [(info.name, info.version) for info in package_infos])
        builds = list(
            getUtility(IBinaryPackageBuildSet).getBuildsForArchive(
            archive, status=BuildStatus.NEEDSBUILD))
        actual_builds = list()
        for build in builds:
            naked_build = removeSecurityProxy(build)
            spr = naked_build.source_package_release
            actual_builds.append((spr.name, spr.version))
        self.assertEqual(sorted(expected_builds), sorted(actual_builds))

    def copyArchive(self, to_archive, to_distroseries, from_archive=None,
                    from_distroseries=None, from_pocket=None, to_pocket=None,
                    to_component=None, distroarchseries_list=None,
                    packagesets=None):
        """Use a PackageCloner to copy an archive."""
        if from_distroseries is None:
           from_distroseries = to_distroseries
        if from_archive is None:
           from_archive = from_distroseries.distribution.main_archive
        if from_pocket is None:
           from_pocket = PackagePublishingPocket.RELEASE
        if to_pocket is None:
           to_pocket = PackagePublishingPocket.RELEASE
        if packagesets is None:
           packagesets = []
        origin = PackageLocation(
            from_archive, from_distroseries.distribution, from_distroseries,
            from_pocket)
        destination = PackageLocation(
            to_archive, to_distroseries.distribution, to_distroseries,
            to_pocket)
        origin.packagesets = packagesets
        if to_component is not None:
            destination.component = to_component
        cloner = getUtility(IPackageCloner)
        cloner.clonePackages(origin, destination, distroarchseries_list=None)
        return cloner

    def testCreateCopiesPublished(self):
        """Test that PUBLISHED sources are copied."""
        package_info = PackageInfo(
            "bzr", "2.1", status=PackagePublishingStatus.PUBLISHED)
        copy_archive, distroseries = self.makeCopyArchive([package_info])
        self.checkCopiedSources(
            copy_archive, distroseries, [package_info])

    def testCreateCopiesPending(self):
        """Test that PENDING sources are copied."""
        package_info = PackageInfo(
            "bzr", "2.1", status=PackagePublishingStatus.PENDING)
        copy_archive, distroseries = self.makeCopyArchive([package_info])
        self.checkCopiedSources(
            copy_archive, distroseries, [package_info])

    def testCreateDoesntCopySuperseded(self):
        """Test that SUPERSEDED sources are not copied."""
        package_info = PackageInfo(
            "bzr", "2.1", status=PackagePublishingStatus.SUPERSEDED)
        copy_archive, distroseries = self.makeCopyArchive([package_info])
        self.checkCopiedSources(
            copy_archive, distroseries, [])

    def testCreateDoesntCopyDeleted(self):
        """Test that DELETED sources are not copied."""
        package_info = PackageInfo(
            "bzr", "2.1", status=PackagePublishingStatus.DELETED)
        copy_archive, distroseries = self.makeCopyArchive([package_info])
        self.checkCopiedSources(
            copy_archive, distroseries, [])

    def testCreateDoesntCopyObsolete(self):
        """Test that OBSOLETE sources are not copied."""
        package_info = PackageInfo(
            "bzr", "2.1", status=PackagePublishingStatus.OBSOLETE)
        copy_archive, distroseries = self.makeCopyArchive([package_info])
        self.checkCopiedSources(
            copy_archive, distroseries, [])

    def testCopyArchiveCopiesAllComponents(self):
        """Test that packages from all components are copied.

        When copying you specify a component, but that component doesn't
        limit the packages copied. We create a source in main and one in
        universe, and then copy with --component main, and expect to see
        both sources in the copy.
        """
        package_infos = [
            PackageInfo(
                "bzr", "2.1", status=PackagePublishingStatus.PUBLISHED,
                component="universe"),
            PackageInfo(
                "apt", "2.2", status=PackagePublishingStatus.PUBLISHED,
                component="main")]
        copy_archive, distroseries = self.makeCopyArchive(package_infos,
            component="main")
        self.checkCopiedSources(copy_archive, distroseries, package_infos)

    def testCopyArchiveSubsetsBasedOnPackageset(self):
        """Test that --package-set limits the sources copied."""
        package_infos = [
            PackageInfo(
                "bzr", "2.1", status=PackagePublishingStatus.PUBLISHED),
            PackageInfo(
                "apt", "2.2", status=PackagePublishingStatus.PUBLISHED),
            ]
        distroseries = self.createSourceDistribution(package_infos)
        spn = self.factory.getOrMakeSourcePackageName(name="apt")
        packageset = self.factory.makePackageset(
            distroseries=distroseries, packages=(spn,))
        copy_archive = self.getTargetArchive(distroseries.distribution)
        self.copyArchive(copy_archive, distroseries, packagesets=[packageset])
        self.checkCopiedSources(
            copy_archive, distroseries, [package_infos[1]])

    def testCopyArchiveUnionsPackagesets(self):
        """Test that package sets are unioned when copying archives."""
        package_infos = [
            PackageInfo(
                "bzr", "2.1", status=PackagePublishingStatus.PUBLISHED),
            PackageInfo(
                "apt", "2.2", status=PackagePublishingStatus.PUBLISHED),
            PackageInfo(
                "gcc", "4.5", status=PackagePublishingStatus.PUBLISHED),
            ]
        distroseries = self.createSourceDistribution(package_infos)
        apt_spn = self.factory.getOrMakeSourcePackageName(name="apt")
        gcc_spn = self.factory.getOrMakeSourcePackageName(name="gcc")
        apt_packageset = self.factory.makePackageset(
            distroseries=distroseries, packages=(apt_spn,))
        gcc_packageset = self.factory.makePackageset(
            distroseries=distroseries, packages=(gcc_spn,))
        copy_archive = self.getTargetArchive(distroseries.distribution)
        self.copyArchive(
            copy_archive, distroseries,
            packagesets=[apt_packageset, gcc_packageset])
        self.checkCopiedSources(
            copy_archive, distroseries, package_infos[1:])

    def testCopyArchiveRecursivelyCopiesPackagesets(self):
        """Test that package set copies include subsets."""
        package_infos = [
            PackageInfo(
                "bzr", "2.1", status=PackagePublishingStatus.PUBLISHED),
            PackageInfo(
                "apt", "2.2", status=PackagePublishingStatus.PUBLISHED),
            PackageInfo(
                "gcc", "4.5", status=PackagePublishingStatus.PUBLISHED),
            ]
        distroseries = self.createSourceDistribution(package_infos)
        apt_spn = self.factory.getOrMakeSourcePackageName(name="apt")
        gcc_spn = self.factory.getOrMakeSourcePackageName(name="gcc")
        apt_packageset = self.factory.makePackageset(
            distroseries=distroseries, packages=(apt_spn,))
        gcc_packageset = self.factory.makePackageset(
            distroseries=distroseries, packages=(gcc_spn,))
        apt_packageset.add((gcc_packageset,))
        copy_archive = self.getTargetArchive(distroseries.distribution)
        self.copyArchive(
            copy_archive, distroseries, packagesets=[apt_packageset])
        self.checkCopiedSources(
            copy_archive, distroseries, package_infos[1:])

    def testCopyFromPPA(self):
        """Test we can create a copy archive with a PPA as the source."""
        distroseries = self.createSourceDistroSeries()
        ppa = self.factory.makeArchive(
            purpose=ArchivePurpose.PPA,
            distribution=distroseries.distribution)
        package_info = PackageInfo(
                "bzr", "2.1", status=PackagePublishingStatus.PUBLISHED,
                component="universe")
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=self.factory.getOrMakeSourcePackageName(
                name=package_info.name),
            distroseries=distroseries, component=self.factory.makeComponent(
                package_info.component),
            version=package_info.version, archive=ppa,
            status=package_info.status, architecturehintlist='any',
            pocket=PackagePublishingPocket.RELEASE)
        copy_archive = self.getTargetArchive(distroseries.distribution)
        self.copyArchive(copy_archive, distroseries, from_archive=ppa)
        self.checkCopiedSources(
            copy_archive, distroseries, [package_info])
