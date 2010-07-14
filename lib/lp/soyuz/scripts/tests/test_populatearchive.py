# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import datetime
import os
import subprocess
import sys
import time
import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.scripts import (
    BufferLogger, QuietFakeLogger)
from canonical.testing import LaunchpadZopelessLayer
from canonical.testing.layers import DatabaseLayer
from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.job.interfaces.job import JobStatus
from lp.soyuz.interfaces.archive import ArchivePurpose, IArchiveSet
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuildSet
from lp.soyuz.interfaces.packagecopyrequest import (
    IPackageCopyRequestSet, PackageCopyStatus)
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.model.processor import ProcessorFamilySet
from lp.soyuz.scripts.ftpmaster import PackageLocationError, SoyuzScriptError
from lp.soyuz.scripts.populate_archive import ArchivePopulator
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


def get_spn(build):
    """Return the SourcePackageName of the given Build."""
    pub = build.current_source_publication
    return pub.sourcepackagerelease.sourcepackagename


class PackageInfo:

    def __init__(self, name, version,
                 status=PackagePublishingStatus.PUBLISHED, component="main",
                 arch_hint=None):
        self.name = name
        self.version = version
        self.status = status
        self.component = component
        self.arch_hint = arch_hint


class TestPopulateArchiveScript(TestCaseWithFactory):
    """Test the copy-package.py script."""

    layer = LaunchpadZopelessLayer
    expected_build_spns = [
        u'alsa-utils', u'cnews', u'evolution', u'libstdc++',
        u'linux-source-2.6.15', u'netapplet']
    expected_src_names = [
        u'alsa-utils 1.0.9a-4ubuntu1 in hoary',
        u'cnews cr.g7-37 in hoary', u'evolution 1.0 in hoary',
        u'libstdc++ b8p in hoary',
        u'linux-source-2.6.15 2.6.15.3 in hoary',
        u'netapplet 1.0-1 in hoary', u'pmount 0.1-2 in hoary']
    pending_statuses = (
        PackagePublishingStatus.PENDING,
        PackagePublishingStatus.PUBLISHED)

    def runWrapperScript(self, extra_args=None):
        """Run populate-archive.py, returning the result and output.

        Runs the wrapper script using Popen(), returns a tuple of the
        process's return code, stdout output and stderr output."""
        if extra_args is None:
            extra_args = []
        script = os.path.join(
            config.root, "scripts", "populate-archive.py")
        args = [sys.executable, script, '-y']
        args.extend(extra_args)
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return (process.returncode, stdout, stderr)

    def testCopyArchiveCreation(self):
        """Start archive population, check data before and after.

        Use the hoary-RELEASE suite along with the main component.
        """
        # XXX: JamesWestby 2010-06-21 bug=596984: it is not clear
        # what this test is testing that is not covered in more
        # specific tests. It should be removed if there is nothing
        # else as it is fragile due to use of sampledata.
        DatabaseLayer.force_dirty_database()
        # Make sure a copy archive with the desired name does
        # not exist yet.
        distro_name = 'ubuntu'
        distro = getUtility(IDistributionSet).getByName(distro_name)

        archive_name = "msa%s" % int(time.time())
        copy_archive = getUtility(IArchiveSet).getByDistroPurpose(
            distro, ArchivePurpose.COPY, archive_name)
        # This is a sanity check: a copy archive with this name should not
        # exist yet.
        self.assertTrue(copy_archive is None)

        hoary = getUtility(IDistributionSet)[distro_name]['hoary']

        # Verify that we have the right source packages in the sample data.
        self._verifyPackagesInSampleData(hoary)

        # Command line arguments required for the invocation of the
        # 'populate-archive.py' script.
        extra_args = [
            '-a', '386',
            '--from-distribution', distro_name, '--from-suite', 'hoary',
            '--to-distribution', distro_name, '--to-suite', 'hoary',
            '--to-archive', archive_name, '--to-user', 'salgado', '--reason',
            '"copy archive from %s"' % datetime.ctime(datetime.utcnow()),
            ]

        # Start archive population now!
        (exitcode, out, err) = self.runWrapperScript(extra_args)
        # Check for zero exit code.
        self.assertEqual(
            exitcode, 0, "\n=> %s\n=> %s\n=> %s\n" % (exitcode, out, err))

        # Make sure the copy archive with the desired name was
        # created
        copy_archive = getUtility(IArchiveSet).getByDistroPurpose(
            distro, ArchivePurpose.COPY, archive_name)
        self.assertTrue(copy_archive is not None)

        # Make sure the right source packages were cloned.
        self._verifyClonedSourcePackages(copy_archive, hoary)

        # Now check that we have build records for the sources cloned.
        builds = list(getUtility(IBinaryPackageBuildSet).getBuildsForArchive(
            copy_archive, status=BuildStatus.NEEDSBUILD))

        # Please note: there will be no build for the pmount package
        # since it is architecture independent and the 'hoary'
        # DistroSeries in the sample data has no DistroArchSeries
        # with chroots set up.
        build_spns = [
            get_spn(removeSecurityProxy(build)).name for build in builds]

        self.assertEqual(build_spns, self.expected_build_spns)

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

    def createTargetOwner(self):
        """Create a person suitable to own a copy archive."""
        person_name = "copy-archive-owner"
        owner = self.factory.makePerson(name=person_name)
        return owner

    def getTargetArchiveName(self, distribution):
        """Get a suitable name for a copy archive.

        It also checks that the archive doesn't currently exist.
        """
        archive_name = "msa%s" % int(time.time())
        copy_archive = getUtility(IArchiveSet).getByDistroPurpose(
            distribution, ArchivePurpose.COPY, archive_name)
        # This is a sanity check: a copy archive with this name should not
        # exist yet.
        self.assertIs(None, copy_archive)
        return archive_name

    def createSourcePublication(self, info, distroseries):
        """Create a SourcePackagePublishingHistory based on a PackageInfo."""
        if info.arch_hint is None:
            arch_hint = "any"
        else:
            arch_hint = info.arch_hint

        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=self.factory.getOrMakeSourcePackageName(
                name=info.name),
            distroseries=distroseries, component=self.factory.makeComponent(
                info.component),
            version=info.version, architecturehintlist=arch_hint,
            archive=distroseries.distribution.main_archive,
            status=info.status, pocket=PackagePublishingPocket.RELEASE)

    def createSourcePublications(self, package_infos, distroseries):
        """Create a source publication for each item in package_infos."""
        for package_info in package_infos:
            self.createSourcePublication(package_info, distroseries)

    def getScript(self, test_args=None):
        """Return an ArchivePopulator instance."""
        if test_args is None:
            test_args = []
        script = ArchivePopulator("test copy archives", test_args=test_args)
        script.logger = QuietFakeLogger()
        script.txn = self.layer.txn
        return script

    def copyArchive(self, distroseries, archive_name, owner,
        architectures=None, component="main", from_user=None,
        from_archive=None, packageset_names=None, nonvirtualized=False):
        """Run the copy-archive script."""
        extra_args = [
            '--from-distribution', distroseries.distribution.name,
            '--from-suite', distroseries.name,
            '--to-distribution', distroseries.distribution.name,
            '--to-suite', distroseries.name,
            '--to-archive', archive_name,
            '--to-user', owner.name,
            '--reason',
            '"copy archive from %s"' % datetime.ctime(datetime.utcnow()),
            '--component', component,
            ]

        if from_user is not None:
            extra_args.extend(["--from-user", from_user])

        if from_archive is not None:
            extra_args.extend(["--from-archive", from_archive])

        if architectures is None:
            architectures = ["386"]

        if nonvirtualized:
            extra_args.extend(["--nonvirtualized"])

        for architecture in architectures:
            extra_args.extend(['-a', architecture])

        if packageset_names is None:
            packageset_names = []

        for packageset_name in packageset_names:
            extra_args.extend(['--package-set', packageset_name])

        script = self.getScript(test_args=extra_args)
        script.mainTask()

        # Make sure the copy archive with the desired name was
        # created
        copy_archive = getUtility(IArchiveSet).getByDistroPurpose(
            distroseries.distribution, ArchivePurpose.COPY, archive_name)
        self.assertTrue(copy_archive is not None)

        # Ascertain that the new copy archive was created with the 'enabled'
        # flag turned off.
        self.assertFalse(copy_archive.enabled)

        # Assert the virtualization is correct.
        virtual = not nonvirtualized
        self.assertEqual(copy_archive.require_virtualized, virtual)

        return copy_archive

    def checkCopiedSources(self, archive, distroseries, expected):
        """Check the sources published in an archive against an expected set.

        Given an archive and a target distroseries the sources published in
        that distroseries are checked against a set of PackageInfo to
        ensure that the correct package names and versions are published.
        """
        expected_set = set([(info.name, info.version) for info in expected])
        sources = archive.getPublishedSources(
            distroseries=distroseries, status=self.pending_statuses)
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

    def makeCopyArchive(self, package_infos, component="main",
                        nonvirtualized=False):
        """Make a copy archive based on a new distribution."""
        owner = self.createTargetOwner()
        distroseries = self.createSourceDistribution(package_infos)
        archive_name = self.getTargetArchiveName(distroseries.distribution)
        copy_archive = self.copyArchive(
            distroseries, archive_name, owner, component=component,
            nonvirtualized=nonvirtualized)
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

    def testCopyArchiveRunScript(self):
        """Check that we can exec the script to copy an archive."""
        package_info = PackageInfo(
            "bzr", "2.1", status=PackagePublishingStatus.PUBLISHED)
        owner = self.createTargetOwner()
        distroseries = self.createSourceDistribution([package_info])
        archive_name = self.getTargetArchiveName(distroseries.distribution)
        # We must commit as we are going to exec a script that will run
        # in a different transaction and must be able to see the
        # objects we just created.
        self.layer.commit()

        extra_args = [
            '--from-distribution', distroseries.distribution.name,
            '--from-suite', distroseries.name,
            '--to-distribution', distroseries.distribution.name,
            '--to-suite', distroseries.name,
            '--to-archive', archive_name,
            '--to-user', owner.name,
            '--reason',
            '"copy archive from %s"' % datetime.ctime(datetime.utcnow()),
            '--component', "main",
            '-a', '386',
            ]
        (exitcode, out, err) = self.runWrapperScript(extra_args)
        # Check for zero exit code.
        self.assertEqual(
            exitcode, 0, "\n=> %s\n=> %s\n=> %s\n" % (exitcode, out, err))
        # Make sure the copy archive with the desired name was
        # created
        copy_archive = getUtility(IArchiveSet).getByDistroPurpose(
            distroseries.distribution, ArchivePurpose.COPY, archive_name)
        self.assertTrue(copy_archive is not None)

        # Ascertain that the new copy archive was created with the 'enabled'
        # flag turned off.
        self.assertFalse(copy_archive.enabled)

        # Also, make sure that the builds for the new copy archive will be
        # carried out on non-virtual builders.
        self.assertTrue(copy_archive.require_virtualized)
        self.checkCopiedSources(
            copy_archive, distroseries, [package_info])

    def testCopyArchiveCreateCopiesPublished(self):
        """Test that PUBLISHED sources are copied."""
        package_info = PackageInfo(
            "bzr", "2.1", status=PackagePublishingStatus.PUBLISHED)
        copy_archive, distroseries = self.makeCopyArchive([package_info])
        self.checkCopiedSources(
            copy_archive, distroseries, [package_info])

    def testCopyArchiveCreateCopiesPending(self):
        """Test that PENDING sources are copied."""
        package_info = PackageInfo(
            "bzr", "2.1", status=PackagePublishingStatus.PENDING)
        copy_archive, distroseries = self.makeCopyArchive([package_info])
        self.checkCopiedSources(
            copy_archive, distroseries, [package_info])

    def testCopyArchiveCreateDoesntCopySuperseded(self):
        """Test that SUPERSEDED sources are not copied."""
        package_info = PackageInfo(
            "bzr", "2.1", status=PackagePublishingStatus.SUPERSEDED)
        copy_archive, distroseries = self.makeCopyArchive([package_info])
        self.checkCopiedSources(
            copy_archive, distroseries, [])

    def testCopyArchiveCreateDoesntCopyDeleted(self):
        """Test that DELETED sources are not copied."""
        package_info = PackageInfo(
            "bzr", "2.1", status=PackagePublishingStatus.DELETED)
        copy_archive, distroseries = self.makeCopyArchive([package_info])
        self.checkCopiedSources(
            copy_archive, distroseries, [])

    def testCopyArchiveCreateDoesntCopyObsolete(self):
        """Test that OBSOLETE sources are not copied."""
        package_info = PackageInfo(
            "bzr", "2.1", status=PackagePublishingStatus.OBSOLETE)
        copy_archive, distroseries = self.makeCopyArchive([package_info])
        self.checkCopiedSources(
            copy_archive, distroseries, [])

    def testCopyArchiveCreatesBuilds(self):
        """Test that a copy archive creates builds for the copied packages."""
        package_info = PackageInfo(
            "bzr", "2.1", status=PackagePublishingStatus.PUBLISHED)
        copy_archive, distroseries = self.makeCopyArchive([package_info])
        self.checkBuilds(copy_archive, [package_info])

    def testCopyArchiveArchTagNotAvailableInSource(self):
        """Test creating a copy archive for an arch not in the source.

        If we request a copy to an architecture that doesn't have
        a DistroArchSeries in the source then we won't get any builds
        created in the copy archive.
        """
        family = self.factory.makeProcessorFamily(name="armel")
        self.factory.makeProcessor(family=family, name="armel")
        package_info = PackageInfo(
            "bzr", "2.1", status=PackagePublishingStatus.PUBLISHED)
        owner = self.createTargetOwner()
        # Creates an archive with just x86
        distroseries = self.createSourceDistribution([package_info])
        archive_name = self.getTargetArchiveName(distroseries.distribution)
        # Different architecture, so there won't be any builds
        copy_archive = self.copyArchive(
            distroseries, archive_name, owner, architectures=["armel"])
        self.checkBuilds(copy_archive, [])

        # Also, make sure the package copy request status was updated.
        [pcr] = getUtility(
            IPackageCopyRequestSet).getByTargetArchive(copy_archive)
        self.assertTrue(pcr.status == PackageCopyStatus.COMPLETE)

        # This date is set when the copy request makes the transition to
        # the "in progress" state.
        self.assertTrue(pcr.date_started is not None)
        # This date is set when the copy request makes the transition to
        # the "completed" state.
        self.assertTrue(pcr.date_completed is not None)
        self.assertTrue(pcr.date_started <= pcr.date_completed)

    def testMultipleArchTagsWithSubsetInSource(self):
        """Try copy archive population with multiple architecture tags.

        The user may specify a number of given architecture tags on the
        command line.
        The script should create build records only for the specified
        architecture tags that are supported by the destination distro series.

        In this (test) case the script should create the build records for the
        '386' architecture.
        """
        family = self.factory.makeProcessorFamily(name="armel")
        self.factory.makeProcessor(family=family, name="armel")
        package_info = PackageInfo(
            "bzr", "2.1", status=PackagePublishingStatus.PUBLISHED)
        owner = self.createTargetOwner()
        # Creates an archive with just x86
        distroseries = self.createSourceDistribution([package_info])
        archive_name = self.getTargetArchiveName(distroseries.distribution)
        # There is only a DAS for i386, so armel won't produce any
        # builds
        copy_archive = self.copyArchive(
            distroseries, archive_name, owner,
            architectures=["386", "armel"])
        self.checkBuilds(copy_archive, [package_info])

    def testCopyArchiveCreatesSubsetOfBuilds(self):
        """Create a copy archive with a subset of the architectures.

        We copy from an archive with multiple architecture DistroArchSeries,
        but request only one of those architectures in the target,
        so we only get builds for that one architecture.
        """
        package_info = PackageInfo(
            "bzr", "2.1", status=PackagePublishingStatus.PUBLISHED)
        owner = self.createTargetOwner()
        distroseries = self.createSourceDistribution([package_info])
        self.factory.makeDistroArchSeries(
            distroseries=distroseries, architecturetag="amd64",
            processorfamily=ProcessorFamilySet().getByName("amd64"),
            supports_virtualized=True)
        archive_name = self.getTargetArchiveName(distroseries.distribution)
        copy_archive = self.copyArchive(
            distroseries, archive_name, owner,
            architectures=["386"])
        # We only get a single build, as we only requested 386, not
        # amd64 too
        self.checkBuilds(copy_archive, [package_info])

    def testNoBuildsForArchAll(self):
        # If we have a copy for an architecture that is not the
        # nominatedarchindep architecture, then we don't want to create
        # builds for arch-all packages, as they can't be built at all
        # and createMissingBuilds blows up when it checks that.
        package_info = PackageInfo(
            "bzr", "2.1", status=PackagePublishingStatus.PUBLISHED,
            arch_hint="all")
        owner = self.createTargetOwner()
        distroseries = self.createSourceDistribution([package_info])
        self.factory.makeDistroArchSeries(
            distroseries=distroseries, architecturetag="amd64",
            processorfamily=ProcessorFamilySet().getByName("amd64"),
            supports_virtualized=True)
        archive_name = self.getTargetArchiveName(distroseries.distribution)
        copy_archive = self.copyArchive(
            distroseries, archive_name, owner,
            architectures=["amd64"])
        # We don't get any builds since amd64 is not the
        # nomindatedarchindep, i386 is.
        self.assertEqual(
            distroseries.nominatedarchindep.architecturetag, "i386")
        self.checkBuilds(copy_archive, [])

    def testMultipleArchTags(self):
        """Test copying an archive with multiple architectures.

        We create a source with two architectures, and then request
        a copy of both, so we get a build for each of those architectures.
        """
        package_info = PackageInfo(
            "bzr", "2.1", status=PackagePublishingStatus.PUBLISHED)
        owner = self.createTargetOwner()
        distroseries = self.createSourceDistribution([package_info])
        self.factory.makeDistroArchSeries(
            distroseries=distroseries, architecturetag="amd64",
            processorfamily=ProcessorFamilySet().getByName("amd64"),
            supports_virtualized=True)
        archive_name = self.getTargetArchiveName(distroseries.distribution)
        copy_archive = self.copyArchive(
            distroseries, archive_name, owner,
            architectures=["386", "amd64"])
        self.checkBuilds(copy_archive, [package_info, package_info])

    def testCopyArchiveCopiesRightComponents(self):
        """Test that packages from the right components are copied.

        When copying you specify a component, that component should
        limit the packages copied. We create a source in main and one in
        universe, and then copy with --component main, and expect to see
        only main in the copy.
        """
        package_info_universe = PackageInfo(
                "bzr", "2.1", status=PackagePublishingStatus.PUBLISHED,
                component="universe")
        package_info_main = PackageInfo(
                "apt", "2.2", status=PackagePublishingStatus.PUBLISHED,
                component="main")
        package_infos_both = [package_info_universe, package_info_main]
        copy_archive, distroseries = self.makeCopyArchive(
            package_infos_both, component="main")
        self.checkBuilds(copy_archive, [package_info_main])

    def testCopyArchiveSubsetsBasedOnPackageset(self):
        """Test that --package-set limits the sources copied."""
        package_infos = [
            PackageInfo(
                "bzr", "2.1", status=PackagePublishingStatus.PUBLISHED),
            PackageInfo(
                "apt", "2.2", status=PackagePublishingStatus.PUBLISHED),
            ]
        owner = self.createTargetOwner()
        distroseries = self.createSourceDistribution(package_infos)
        packageset_name = u"apt-packageset"
        spn = self.factory.getOrMakeSourcePackageName(name="apt")
        self.factory.makePackageset(
            name=packageset_name, distroseries=distroseries, packages=(spn,))
        archive_name = self.getTargetArchiveName(distroseries.distribution)
        copy_archive = self.copyArchive(
            distroseries, archive_name, owner,
            packageset_names=[packageset_name])
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
        owner = self.createTargetOwner()
        distroseries = self.createSourceDistribution(package_infos)
        apt_packageset_name = u"apt-packageset"
        apt_spn = self.factory.getOrMakeSourcePackageName(name="apt")
        gcc_packageset_name = u"gcc-packageset"
        gcc_spn = self.factory.getOrMakeSourcePackageName(name="gcc")
        self.factory.makePackageset(
            name=apt_packageset_name, distroseries=distroseries,
            packages=(apt_spn,))
        self.factory.makePackageset(
            name=gcc_packageset_name, distroseries=distroseries,
            packages=(gcc_spn,))
        archive_name = self.getTargetArchiveName(distroseries.distribution)
        copy_archive = self.copyArchive(
            distroseries, archive_name, owner,
            packageset_names=[apt_packageset_name, gcc_packageset_name])
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
        owner = self.createTargetOwner()
        distroseries = self.createSourceDistribution(package_infos)
        apt_packageset_name = u"apt-packageset"
        apt_spn = self.factory.getOrMakeSourcePackageName(name="apt")
        gcc_packageset_name = u"gcc-packageset"
        gcc_spn = self.factory.getOrMakeSourcePackageName(name="gcc")
        apt_packageset = self.factory.makePackageset(
            name=apt_packageset_name, distroseries=distroseries,
            packages=(apt_spn,))
        gcc_packageset = self.factory.makePackageset(
            name=gcc_packageset_name, distroseries=distroseries,
            packages=(gcc_spn,))
        apt_packageset.add((gcc_packageset,))
        archive_name = self.getTargetArchiveName(distroseries.distribution)
        copy_archive = self.copyArchive(
            distroseries, archive_name, owner,
            packageset_names=[apt_packageset_name])
        self.checkCopiedSources(
            copy_archive, distroseries, package_infos[1:])

    def testCopyFromPPA(self):
        """Test we can create a copy archive with a PPA as the source."""
        ppa_owner_name = "ppa-owner"
        ppa_name = "ppa"
        ppa_owner = self.factory.makePerson(name=ppa_owner_name)
        distroseries = self.createSourceDistroSeries()
        ppa = self.factory.makeArchive(
            name=ppa_name, purpose=ArchivePurpose.PPA,
            distribution=distroseries.distribution, owner=ppa_owner)
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
        owner = self.createTargetOwner()
        archive_name = self.getTargetArchiveName(distroseries.distribution)
        copy_archive = self.copyArchive(
            distroseries, archive_name, owner, from_user=ppa_owner_name,
            from_archive=ppa_name, component=package_info.component)
        self.checkCopiedSources(
            copy_archive, distroseries, [package_info])

    def runScript(
        self, archive_name=None, suite='hoary', user='salgado',
        exists_before=None, exists_after=None, exception_type=None,
        exception_text=None, extra_args=None, copy_archive_name=None,
        reason=None, output_substr=None):
        """Run the script to test.

        :type archive_name: `str`
        :param archive_name: the name of the copy archive to create.
        :type suite: `str`
        :param suite: the name of the copy archive suite.
        :type user: `str`
        :param user: the name of the user creating the archive.
        :type exists_before: `bool`
        :param exists_before: copy archive with given name should
            already exist if True.
        :type exists_after: `True`
        :param exists_after: the copy archive is expected to exist
            after script invocation if True.
        :type exception_type: type
        :param exception_type: the type of exception expected in case
            of failure.
        :type exception_text: `str`
        :param exception_text: expected exception text prefix in case
            of failure.
        :type extra_args: list of strings
        :param extra_args: additional arguments to be passed to the
            script (if any).
        :type copy_archive_name: `IArchive`
        :param copy_archive_name: optional copy archive instance, used for
            merge copy testing.
        :param reason: if empty do not provide '--reason' cmd line arg to
            the script
        :param output_substr: this must be part of the script's output
        """
        class FakeZopeTransactionManager:
            def commit(self):
                pass
            def begin(self):
                pass

        if copy_archive_name is None:
            now = int(time.time())
            if archive_name is None:
                archive_name = "ra%s" % now
        else:
            archive_name = copy_archive_name

        distro_name = 'ubuntu'
        distro = getUtility(IDistributionSet).getByName(distro_name)

        copy_archive = getUtility(IArchiveSet).getByDistroPurpose(
            distro, ArchivePurpose.COPY, archive_name)

        # Enforce these assertions only if the 'exists_before' flag was
        # specified in first place.
        if exists_before is not None:
            if exists_before:
                self.assertTrue(copy_archive is not None)
            else:
                self.assertTrue(copy_archive is None)

        # Command line arguments required for the invocation of the
        # 'populate-archive.py' script.
        script_args = [
            '--from-distribution', distro_name, '--from-suite', suite,
            '--to-distribution', distro_name, '--to-suite', suite,
            '--to-archive', archive_name, '--to-user', user
            ]

        # Empty reason string indicates that the '--reason' command line
        # argument should be ommitted.
        if reason is not None and not reason.isspace():
            script_args.extend(['--reason', reason])
        elif reason is None:
            reason = "copy archive, %s" % datetime.ctime(datetime.utcnow())
            script_args.extend(['--reason', reason])

        if extra_args is not None:
            script_args.extend(extra_args)

        script = ArchivePopulator(
            'populate-archive', dbuser=config.uploader.dbuser,
            test_args=script_args)

        script.logger = BufferLogger()
        script.txn = FakeZopeTransactionManager()

        if exception_type is not None:
            self.assertRaisesWithContent(
                exception_type, exception_text, script.mainTask)
        else:
            script.mainTask()

        # Does the script's output contain the specified sub-string?
        if output_substr is not None and not output_substr.isspace():
            output = script.logger.buffer.getvalue()
            self.assertTrue(output_substr in output)

        copy_archive = getUtility(IArchiveSet).getByDistroPurpose(
            distro, ArchivePurpose.COPY, archive_name)

        # Enforce these assertions only if the 'exists_after' flag was
        # specified in first place.
        if exists_after is not None:
            if exists_after:
                self.assertTrue(copy_archive is not None)
            else:
                self.assertTrue(copy_archive is None)

        return copy_archive

    def testInvalidCopyArchiveName(self):
        """Try copy archive creation/population with an invalid archive name.

        When trying to create and populate a copy archive with an invalid name
        the script should fail with an appropriate error message.
        """
        now = int(time.time())
        # The slashes in the name make it invalid.
        invalid_name = "ra//%s" % now

        extra_args = ['-a', '386']
        self.runScript(
            extra_args=extra_args,
            archive_name=invalid_name,
            exception_type=SoyuzScriptError,
            exception_text=(
                "Invalid destination archive name: '%s'" % invalid_name))

    def testInvalidSuite(self):
        """Try copy archive creation/population with a non-existent suite.

        A suite is a combination of a distro series and pocket e.g.
        hoary-updates or hardy-security.
        In the case where a non-existent suite is specified the script should
        abort with an appropriate error message.
        """
        now = int(time.time())
        invalid_suite = "suite/:/%s" % now
        extra_args = ['-a', '386']
        self.runScript(
            extra_args=extra_args,
            suite=invalid_suite,
            exception_type=PackageLocationError,
            exception_text="Could not find suite '%s'" % invalid_suite)

    def testInvalidUserName(self):
        """Try copy archive population with an invalid user name.

        The destination/copy archive will be created for some Launchpad user.
        If the user name passed is invalid the script should abort with an
        appropriate error message.
        """
        now = int(time.time())
        invalid_user = "user//%s" % now
        extra_args = ['-a', '386']
        self.runScript(
            extra_args=extra_args,
            user=invalid_user,
            exception_type=SoyuzScriptError,
            exception_text="Invalid user name: '%s'" % invalid_user)

    def testUnknownPackagesetName(self):
        """Try copy archive population with an unknown packageset name.

        The caller can request copying specific packagesets. We test
        what happens if they request a packageset that doesn't exist.
        """
        unknown_packageset = "unknown"
        extra_args = ['-a', '386', "--package-set", unknown_packageset]
        self.runScript(
            extra_args=extra_args,
            exception_type=PackageLocationError,
            exception_text="Could not find packageset No such package set"
            " (in the specified distro series): '%s'." % unknown_packageset)

    def testPackagesetDelta(self):
        """Try to calculate the delta between two source package sets."""
        hoary = getUtility(IDistributionSet)['ubuntu']['hoary']

        # Verify that we have the right source packages in the sample data.
        self._verifyPackagesInSampleData(hoary)

        # Take a snapshot of ubuntu/hoary first.
        extra_args = ['-a', 'amd64']
        first_stage = self.runScript(
            extra_args=extra_args, exists_after=True,
            copy_archive_name='first-stage')
        self._verifyClonedSourcePackages(first_stage, hoary)

        # Now add a new package to ubuntu/hoary and update one.
        self._prepareMergeCopy()

        # Check which source packages are fresher or new in the second stage
        # archive.
        expected_output = (
            "INFO: Fresher packages: 1\n"
            "INFO: * alsa-utils (2.0 > 1.0.9a-4ubuntu1)\n"
            "INFO: New packages: 1\n"
            "INFO: * new-in-second-round (1.0)\n")

        extra_args = ['--package-set-delta']
        self.runScript(
            extra_args=extra_args, reason='', output_substr=expected_output,
            copy_archive_name=first_stage.name)

    def testMergeCopy(self):
        """Try repeated copy archive population (merge copy).

        In this (test) case an archive is populated twice and only fresher or
        new packages are copied to it.
        """
        hoary = getUtility(IDistributionSet)['ubuntu']['hoary']

        # Verify that we have the right source packages in the sample data.
        self._verifyPackagesInSampleData(hoary)

        # Take a snapshot of ubuntu/hoary first.
        extra_args = ['-a', 'amd64']
        first_stage = self.runScript(
            extra_args=extra_args, exists_after=True,
            copy_archive_name='first-stage')
        self._verifyClonedSourcePackages(first_stage, hoary)

        # Now add a new package to ubuntu/hoary and update one.
        self._prepareMergeCopy()

        # Take a snapshot of the modified ubuntu/hoary primary archive.
        second_stage = self.runScript(
            extra_args=extra_args, exists_after=True,
            copy_archive_name='second-stage')
        # Verify that the 2nd snapshot has the fresher and the new package.
        self._verifyClonedSourcePackages(
            second_stage, hoary,
            # The set of packages that were superseded in the target archive.
            obsolete=set(['alsa-utils 1.0.9a-4ubuntu1 in hoary']),
            # The set of packages that are new/fresher in the source archive.
            new=set(['alsa-utils 2.0 in hoary',
                     'new-in-second-round 1.0 in hoary'])
            )

        # Now populate a 3rd copy archive from the first ubuntu/hoary
        # snapshot.
        extra_args = ['-a', 'amd64', '--from-archive', first_stage.name]
        copy_archive = self.runScript(
            extra_args=extra_args, exists_after=True)
        self._verifyClonedSourcePackages(copy_archive, hoary)

        # Then populate the same copy archive from the 2nd snapshot.
        # This results in the copying of the fresher and of the new package.
        extra_args = [
            '--merge-copy', '--from-archive', second_stage.name]

        # We need to enable the copy archive before we can copy to it.
        copy_archive.enable()
        # An empty 'reason' string is passed to runScript() i.e. the latter
        # will not pass a '--reason' command line argument to the script which
        # is OK since this is a repeated population of an *existing* COPY
        # archive.
        copy_archive = self.runScript(
            extra_args=extra_args, copy_archive_name=copy_archive.name,
            reason='')
        self._verifyClonedSourcePackages(
            copy_archive, hoary,
            # The set of packages that were superseded in the target archive.
            obsolete=set(['alsa-utils 1.0.9a-4ubuntu1 in hoary']),
            # The set of packages that are new/fresher in the source archive.
            new=set(['alsa-utils 2.0 in hoary',
                     'new-in-second-round 1.0 in hoary'])
            )

    def testUnknownOriginArchive(self):
        """Try copy archive population with a unknown origin archive.

        This test should provoke a `SoyuzScriptError` exception.
        """
        extra_args = ['-a', 'amd64', '--from-archive', '9th-level-cache']
        self.runScript(
            extra_args=extra_args,
            exception_type=SoyuzScriptError,
            exception_text="Origin archive does not exist: '9th-level-cache'")

    def testUnknownOriginPPA(self):
        """Try copy archive population with an invalid PPA owner name.

        This test should provoke a `SoyuzScriptError` exception.
        """
        extra_args = ['-a', 'amd64', '--from-user', 'king-kong']
        self.runScript(
            extra_args=extra_args,
            exception_type=SoyuzScriptError,
            exception_text="No PPA for user: 'king-kong'")

    def testInvalidOriginArchiveName(self):
        """Try copy archive population with an invalid origin archive name.

        This test should provoke a `SoyuzScriptError` exception.
        """
        extra_args = [
            '-a', 'amd64', '--from-archive', '//']
        self.runScript(
            extra_args=extra_args,
            exception_type=SoyuzScriptError,
            exception_text="Invalid origin archive name: '//'")

    def testInvalidProcessorFamilyName(self):
        """Try copy archive population with an invalid architecture tag.

        This test should provoke a `SoyuzScriptError` exception.
        """
        extra_args = ['-a', 'wintel']
        self.runScript(
            extra_args=extra_args,
            exception_type=SoyuzScriptError,
            exception_text="Invalid architecture tag: 'wintel'")

    def testFamiliesForExistingArchives(self):
        """Try specifying processor family names for existing archive.

        The user is not supposed to specify processor families on the command
        line for existing copy archives. The processor families will be read
        from the database instead. Please see also the end of the
        testMultipleArchTags test.

        This test should provoke a `SoyuzScriptError` exception.
        """
        extra_args = ['-a', '386', '-a', 'amd64']
        copy_archive = self.runScript(
            extra_args=extra_args, exists_before=False)

        extra_args = ['--merge-copy', '-a', '386', '-a', 'amd64']
        self.runScript(
            extra_args=extra_args, copy_archive_name=copy_archive.name,
            exception_type=SoyuzScriptError,
            exception_text=(
                'error: cannot specify architecture tags for *existing* '
                'archive.'))

    def testMissingCreationReason(self):
        """Try copy archive population without a copy archive creation reason.

        This test should provoke a `SoyuzScriptError` exception because the
        copy archive does not exist yet and will need to be created.

        This is different from a merge copy scenario where the destination
        copy archive exists already and hence no archive creation reason is
        needed.
        """
        extra_args = ['-a', 'amd64']
        self.runScript(
            # Pass an empty reason parameter string to indicate that no
            # '--reason' command line argument is to be provided.
            extra_args=extra_args, reason='',
            exception_type=SoyuzScriptError,
            exception_text=(
                'error: reason for copy archive creation not specified.'))

    def testMergecopyToMissingArchive(self):
        """Try merge copy to non-existent archive.

        This test should provoke a `SoyuzScriptError` exception because the
        copy archive does not exist yet and we specified the '--merge-copy'
        command line option. The latter specifies the repeated population of
        *existing* archives.
        """
        extra_args = ['--merge-copy', '-a', 'amd64']
        self.runScript(
            extra_args=extra_args,
            exception_type=SoyuzScriptError,
            exception_text=(
                'error: merge copy requested for non-existing archive.'))

    def testArchiveNameClash(self):
        """Try creating an archive with same name and distribution twice.

        This test should provoke a `SoyuzScriptError` exception because there
        is a uniqueness constraint based on (distribution, name) for all
        non-PPA archives i.e. we do not allow the creation of a second archive
        with the same name and distribution.
        """
        extra_args = ['-a', 'amd64']
        self.runScript(
            extra_args=extra_args, exists_after=True,
            copy_archive_name='hello-1')
        extra_args = ['-a', 'amd64']
        self.runScript(
            extra_args=extra_args,
            copy_archive_name='hello-1', exception_type=SoyuzScriptError,
            exception_text=(
                "error: archive 'hello-1' already exists for 'ubuntu'."))

    def testMissingProcessorFamily(self):
        """Try copy archive population without a single architecture tag.

        This test should provoke a `SoyuzScriptError` exception.
        """
        self.runScript(
            exception_type=SoyuzScriptError,
            exception_text="error: architecture tags not specified.")

    def testBuildsPendingAndSuspended(self):
        """All builds in the new copy archive are pending and suspended."""
        def build_in_wrong_state(build):
            """True if the given build is not (pending and suspended)."""
            return not (
                build.status == BuildStatus.NEEDSBUILD and
                build.buildqueue_record.job.status == JobStatus.SUSPENDED)
        hoary = getUtility(IDistributionSet)['ubuntu']['hoary']

        # Verify that we have the right source packages in the sample data.
        self._verifyPackagesInSampleData(hoary)

        extra_args = ['-a', '386']
        archive = self.runScript(extra_args=extra_args, exists_after=True)

        # Make sure the right source packages were cloned.
        self._verifyClonedSourcePackages(archive, hoary)

        # Get the binary builds generated for the copy archive at hand.
        builds = list(getUtility(IBinaryPackageBuildSet).getBuildsForArchive(
            archive))
        # At least one binary build was generated for the target copy archive.
        self.assertTrue(len(builds) > 0)
        # Now check that the binary builds and their associated job records
        # are in the state expected:
        #   - binary build: pending
        #   - job: suspended
        builds_in_wrong_state = filter(build_in_wrong_state, builds)
        self.assertEqual (
            [], builds_in_wrong_state,
            "The binary builds generated for the target copy archive "
            "should all be pending and suspended. However, at least one of "
            "the builds is in the wrong state.")

    def testPrivateOriginArchive(self):
        """Try copying from a private archive.

        This test should provoke a `SoyuzScriptError` exception because
        presently copy archives can only be created as public archives.
        The copying of packages from private archives to public ones
        thus constitutes a security breach.
        """
        # We will make a private PPA and then attempt to copy from it.
        joe = self.factory.makePerson(name='joe')
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        self.factory.makeArchive(
            owner=joe, private=True, name="ppa", distribution=ubuntu)

        extra_args = ['--from-user', 'joe', '-a', 'amd64']
        self.runScript(
            extra_args=extra_args, exception_type=SoyuzScriptError,
            exception_text=(
                "Cannot copy from private archive ('joe/ppa')"))

    def testDisabledDestinationArchive(self):
        """Try copying to a disabled archive.

        This test should provoke a `SoyuzScriptError` exception because
        the destination archive is disabled.
        """
        # Create a copy archive, disable it and then attempt to copy to it.
        cprov = getUtility(IPersonSet).getByName('cprov')
        distro = getUtility(IDistributionSet).getByName('ubuntu')
        disabled_archive = getUtility(IArchiveSet).new(
            ArchivePurpose.COPY, cprov, name='disabled-copy-archive',
            distribution=distro, description='disabled-copy-archive test',
            enabled=False)

        extra_args = ['--from-user', 'cprov', '--merge-copy']
        self.runScript(
            copy_archive_name=disabled_archive.name, reason='',
            extra_args=extra_args, exception_type=SoyuzScriptError,
            exception_text='error: cannot copy to disabled archive')

    def _verifyClonedSourcePackages(
        self, copy_archive, series, obsolete=None, new=None):
        """Verify that the expected source packages have been cloned.

        The destination copy archive should be populated with the expected
        source packages.

        :type copy_archive: `Archive`
        :param copy_archive: the destination copy archive to check.
        :type series: `DistroSeries`
        :param series: the destination distro series.
        """
        # Make sure the source packages were cloned.
        target_set = set(self.expected_src_names)
        copy_src_names = self._getPendingPackageNames(copy_archive, series)
        if obsolete is not None:
            target_set -= obsolete
        if new is not None:
            target_set = target_set.union(new)
        self.assertEqual(copy_src_names, target_set)

    def _getPendingPackageNames(self, archive, series):
        sources = archive.getPublishedSources(
            distroseries=series, status=self.pending_statuses)
        return set(source.displayname for source in sources)

    def _prepareMergeCopy(self):
        """Add a fresher and a new package to ubuntu/hoary.

        This is used to test merge copy functionality."""
        test_publisher = SoyuzTestPublisher()
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        hoary = ubuntu.getSeries('hoary')
        test_publisher.addFakeChroots(hoary)
        test_publisher.setUpDefaultDistroSeries(hoary)
        test_publisher.getPubSource(
            sourcename="new-in-second-round", version="1.0",
            distroseries=hoary, archive=ubuntu.main_archive)
        test_publisher.getPubSource(
            sourcename="alsa-utils", version="2.0", distroseries=hoary,
            archive=ubuntu.main_archive)
        sources = ubuntu.main_archive.getPublishedSources(
            distroseries=hoary, status=self.pending_statuses,
            name='alsa-utils')
        for src in sources:
            if src.source_package_version != '2.0':
                src.supersede()
        LaunchpadZopelessLayer.txn.commit()

    def _verifyPackagesInSampleData(self, series, archive_name=None):
        """Verify that the expected source packages are in the sample data.

        :type series: `DistroSeries`
        :param series: the origin distro series.
        """
        if archive_name is None:
            archive = series.distribution.main_archive
        else:
            archive = getUtility(IArchiveSet).getByDistroPurpose(
                series.distribution, ArchivePurpose.COPY, archive)
        # These source packages will be copied to the copy archive.
        sources = archive.getPublishedSources(
            distroseries=series, status=self.pending_statuses)

        src_names = sorted(source.displayname for source in sources)
        # Make sure the source to be copied are the ones we expect (this
        # should break in case of a sample data change/corruption).
        self.assertEqual(src_names, self.expected_src_names)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
