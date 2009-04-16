# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os
import subprocess
import sys
import unittest

from zope.component import getUtility

from canonical.archiveuploader.tests.test_uploadprocessor import (
    MockLogger as TestLogger)
from canonical.config import config
from canonical.launchpad.components.packagelocation import (
    PackageLocationError)
from canonical.launchpad.database.processor import ProcessorFamily
from canonical.launchpad.database.publishing import (
    SecureSourcePackagePublishingHistory,
    SecureBinaryPackagePublishingHistory)
from canonical.launchpad.interfaces.bug import (
    CreateBugParams, IBugSet)
from canonical.launchpad.interfaces.bugtask import BugTaskStatus
from canonical.launchpad.interfaces.build import BuildStatus
from canonical.launchpad.interfaces.component import IComponentSet
from lp.registry.interfaces.distribution import IDistributionSet
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from lp.registry.interfaces.person import IPersonSet
from canonical.launchpad.interfaces.publishing import (
    IBinaryPackagePublishingHistory, ISourcePackagePublishingHistory,
    PackagePublishingPocket, PackagePublishingStatus,
    active_publishing_status)
from canonical.launchpad.scripts import QuietFakeLogger
from canonical.launchpad.scripts.ftpmasterbase import SoyuzScriptError
from canonical.launchpad.scripts.packagecopier import (
    PackageCopier, UnembargoSecurityPackage)
from canonical.launchpad.testing import TestCase
from canonical.launchpad.tests.test_publishing import SoyuzTestPublisher
from canonical.testing import DatabaseLayer, LaunchpadZopelessLayer


class TestCopyPackageScript(unittest.TestCase):
    """Test the copy-package.py script."""
    layer = LaunchpadZopelessLayer

    def runCopyPackage(self, extra_args=None):
        """Run copy-package.py, returning the result and output.

        Returns a tuple of the process's return code, stdout output and
        stderr output.
        """
        if extra_args is None:
            extra_args = []
        script = os.path.join(
            config.root, "scripts", "ftpmaster-tools", "copy-package.py")
        args = [sys.executable, script, '-y']
        args.extend(extra_args)
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # The subprocess commits to the database so we need to tell the layer
        # to fully tear down and restore the testing database.
        DatabaseLayer.force_dirty_database()
        stdout, stderr = process.communicate()
        return (process.returncode, stdout, stderr)

    def testSimpleRun(self):
        """Try a simple copy-package.py run.

        Uses the default case, copy mozilla-firefox source with binaries
        from warty to hoary.
        """
        # Count the records in SSPPH and SBPPH to check later that they
        # increased by one each.
        num_source_pub = SecureSourcePackagePublishingHistory.select(
            "True").count()
        num_bin_pub = SecureBinaryPackagePublishingHistory.select(
            "True").count()

        returncode, out, err = self.runCopyPackage(
            extra_args=['-s', 'warty', 'mozilla-firefox',
                        '--to-suite', 'hoary', '-b'])
        # Need to print these or you can't see what happened if the
        # return code is bad:
        if returncode != 0:
            print "\nStdout:\n%s\nStderr\n%s\n" % (out, err)
        self.assertEqual(0, returncode)

        # Test that the database has been modified.  We're only checking
        # that the number of rows has increase; content checks are done
        # in other tests.
        self.layer.txn.abort()

        num_source_pub_after = SecureSourcePackagePublishingHistory.select(
            "True").count()
        num_bin_pub_after = SecureBinaryPackagePublishingHistory.select(
            "True").count()

        self.assertEqual(num_source_pub + 1, num_source_pub_after)
        # 'mozilla-firefox' source produced 4 binaries.
        self.assertEqual(num_bin_pub + 4, num_bin_pub_after)


class TestCopyPackage(TestCase):
    """Test the CopyPackageHelper class."""
    layer = LaunchpadZopelessLayer
    dbuser = config.archivepublisher.dbuser

    def setUp(self):
        """Anotate pending publishing records provided in the sampledata.

        The records annotated will be excluded during the operation checks,
        see checkCopies().
        """
        pending_sources = SecureSourcePackagePublishingHistory.selectBy(
            status=PackagePublishingStatus.PENDING)
        self.sources_pending_ids = [pub.id for pub in pending_sources]
        pending_binaries = SecureBinaryPackagePublishingHistory.selectBy(
            status=PackagePublishingStatus.PENDING)
        self.binaries_pending_ids = [pub.id for pub in pending_binaries]

        # Run test cases in the production context.
        self.layer.switchDbUser(self.dbuser)

    def getCopier(self, sourcename='mozilla-firefox', sourceversion=None,
                  from_distribution='ubuntu', from_suite='warty',
                  to_distribution='ubuntu', to_suite='hoary',
                  component=None, from_ppa=None, to_ppa=None,
                  from_partner=False, to_partner=False,
                  confirm_all=True, include_binaries=True):
        """Return a PackageCopier instance.

        Allow tests to use a set of default options and pass an
        inactive logger to PackageCopier.
        """
        test_args = ['-s', from_suite,
                     '-d', from_distribution,
                     '--to-suite', to_suite,
                     '--to-distribution', to_distribution]

        if confirm_all:
            test_args.append('-y')

        if include_binaries:
            test_args.append('-b')

        if sourceversion is not None:
            test_args.extend(['-e', sourceversion])

        if component is not None:
            test_args.extend(['-c', component])

        if from_partner:
            test_args.append('-j')

        if to_partner:
            test_args.append('--to-partner')

        if from_ppa is not None:
            test_args.extend(['-p', from_ppa])

        if to_ppa is not None:
            test_args.extend(['--to-ppa', to_ppa])

        test_args.append(sourcename)

        copier = PackageCopier(name='copy-package', test_args=test_args)
        copier.logger = QuietFakeLogger()
        copier.setupLocation()
        return copier

    def checkCopies(self, copied, target_archive, size):
        """Perform overall checks in the copied records list.

         * check if the size is expected,
         * check if all copied records are PENDING,
         * check if the list copied matches the list of PENDING records
           retrieved from the target_archive.
        """
        self.assertEqual(len(copied), size)

        for candidate in copied:
            self.assertEqual(
                candidate.status, PackagePublishingStatus.PENDING)

        def excludeOlds(found, old_pending_ids):
            return [pub.id for pub in found if pub.id not in old_pending_ids]

        sources_pending = target_archive.getPublishedSources(
            status=PackagePublishingStatus.PENDING)
        sources_pending_ids = excludeOlds(
            sources_pending, self.sources_pending_ids)

        binaries_pending = target_archive.getAllPublishedBinaries(
            status=PackagePublishingStatus.PENDING)
        binaries_pending_ids = excludeOlds(
            binaries_pending, self.binaries_pending_ids)

        copied_ids = [pub.id for pub in copied]
        pending_ids = sources_pending_ids + binaries_pending_ids

        self.assertEqual(
            sorted(copied_ids), sorted(pending_ids),
            "The copy did not succeed.\nExpected IDs: %s\nFound IDs: %s" % (
                sorted(copied_ids), sorted(pending_ids))
            )

    def testCopyBetweenDistroSeries(self):
        """Check the copy operation between distroseries."""
        copy_helper = self.getCopier()
        copied = copy_helper.mainTask()

        # Check locations.  They should be the same as the defaults defined
        # in the getCopier method.
        self.assertEqual(str(copy_helper.location),
                         'Primary Archive for Ubuntu Linux: warty-RELEASE')
        self.assertEqual(str(copy_helper.destination),
                         'Primary Archive for Ubuntu Linux: hoary-RELEASE')

        # Check stored results. The number of copies should be 5
        # (1 source and 2 binaries in 2 architectures).
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 5)

    def testCopyBetweenPockets(self):
        """Check the copy operation between pockets.

        That's normally how SECURITY publications get propagated to UPDATES
        in order to reduce the burden on ubuntu servers.
        """
        copy_helper = self.getCopier(
            from_suite='warty', to_suite='warty-updates')
        copied = copy_helper.mainTask()

        self.assertEqual(str(copy_helper.location),
                         'Primary Archive for Ubuntu Linux: warty-RELEASE')
        self.assertEqual(str(copy_helper.destination),
                         'Primary Archive for Ubuntu Linux: warty-UPDATES')

        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 5)

    def testCopyAncestryLookup(self):
        """Check the ancestry lookup used in copy-package.

        This test case exercises the 'ancestry lookup' mechanism used to
        verify if the copy candidate version is higher than the currently
        published version of the same source/binary in the destination
        context.

        We emulate a conflict with a pre-existing version of 'firefox-3.0'
        in hardy-updates, a version of 'firefox' present in hardy and a copy
        copy candidate 'firefox' from hardy-security.

        As described in bug #245416, the ancestry lookup was erroneously
        considering the 'firefox-3.0' as an ancestor to the 'firefox' copy
        candidate. It was caused because the lookup was not restricted to
        'exact_match' names. See `scripts/packagecopier.py`.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        hoary = ubuntu.getSeries('hoary')
        test_publisher = self.getTestPublisher(hoary)

        # Create the described publishing scenario.
        ancestry_source = test_publisher.getPubSource(
            sourcename='firefox', version='1.0',
            archive=ubuntu.main_archive, distroseries=hoary,
            pocket=PackagePublishingPocket.RELEASE,
            status=PackagePublishingStatus.PUBLISHED)

        noise_source = test_publisher.getPubSource(
            sourcename='firefox-3.0', version='1.2',
            archive=ubuntu.main_archive, distroseries=hoary,
            pocket=PackagePublishingPocket.UPDATES,
            status=PackagePublishingStatus.PUBLISHED)

        candidate_source = test_publisher.getPubSource(
            sourcename='firefox', version='1.1',
            archive=ubuntu.main_archive, distroseries=hoary,
            pocket=PackagePublishingPocket.SECURITY,
            status=PackagePublishingStatus.PUBLISHED)

        # Commit to ensure librarian files are written.
        self.layer.txn.commit()

        # Perform the copy.
        copy_helper = self.getCopier(
            sourcename='firefox', include_binaries=False,
            from_suite='hoary-security', to_suite='hoary-updates')
        copied = copy_helper.mainTask()

        # Check if the copy was performed as expected.
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 1)

        # Verify the resulting publishing scenario.
        [updates, security,
         release] = ubuntu.main_archive.getPublishedSources(
            name='firefox', exact_match=True)

        # Context publications remain the same.
        self.assertEqual(release, ancestry_source)
        self.assertEqual(security, candidate_source)

        # The copied source is published in the 'updates' pocket as expected.
        self.assertEqual(updates.displayname, 'firefox 1.1 in hoary')
        self.assertEqual(updates.pocket, PackagePublishingPocket.UPDATES)
        self.assertEqual(len(updates.getBuilds()), 1)

    def testWillNotCopyTwice(self):
        """When invoked twice, the script doesn't repeat the copy.

        As reported in bug #237353, duplicates are generally cruft and may
        cause problems when they include architecture-independent binaries.

        That's why PackageCopier refuses to copy publications with versions
        older or equal the ones already present in the destination.
        """
        copy_helper = self.getCopier(
            from_suite='warty', to_suite='warty-updates')
        copied = copy_helper.mainTask()
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 5)

        copy_helper = self.getCopier(
            from_suite='warty', to_suite='warty-updates')

        # Use a TestLogger object to store log messages issued during
        # the copy.
        copy_helper.logger = TestLogger()

        copied = copy_helper.mainTask()
        self.assertEqual(len(copied), 0)

        # The script output informs the user that no packages were copied.
        self.assertEqual(
            copy_helper.logger.lines[-1], 'No packages copied.')

    def testCopyAcrossPartner(self):
        """Check the copy operation across PARTNER archive.

        This operation is required to propagate partner uploads across several
        suites, avoiding to build (and modify) the package multiple times to
        have it available for all supported suites independent of the
        time they were released.
        """
        copy_helper = self.getCopier(
            sourcename='commercialpackage', from_partner=True,
            to_partner=True, from_suite='breezy-autotest', to_suite='hoary')
        copied = copy_helper.mainTask()

        self.assertEqual(
            str(copy_helper.location),
            'Partner Archive for Ubuntu Linux: breezy-autotest-RELEASE')
        self.assertEqual(
            str(copy_helper.destination),
            'Partner Archive for Ubuntu Linux: hoary-RELEASE')

        # 'commercialpackage' has only one binary built for i386.
        # The source and the binary got copied.
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 2)

    def getTestPublisher(self, distroseries):
        """Return a initialised `SoyuzTestPublisher` object.

        Setup a i386 chroot for the given distroseries, so it can build
        and publish binaries.
        """
        fake_chroot = getUtility(ILibraryFileAliasSet)[1]
        distroseries['i386'].addOrUpdateChroot(fake_chroot)
        test_publisher = SoyuzTestPublisher()
        test_publisher.setUpDefaultDistroSeries(distroseries)
        test_publisher.person = getUtility(IPersonSet).getByName("name16")
        return test_publisher

    def testCopySourceFromPPA(self):
        """Check the copy source operation from PPA to PRIMARY Archive.

        A source package can get copied from PPA to the PRIMARY archive,
        which will immediately result in a build record in the destination
        context.

        That's the preliminary workflow for 'syncing' sources from PPA to
        the ubuntu PRIMARY archive.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        hoary = ubuntu.getSeries('hoary')
        test_publisher = self.getTestPublisher(hoary)

        cprov = getUtility(IPersonSet).getByName("cprov")
        ppa_source = test_publisher.getPubSource(
            archive=cprov.archive, version='1.0', distroseries=hoary,
            status=PackagePublishingStatus.PUBLISHED)
        ppa_binaries = test_publisher.getPubBinaries(
            pub_source=ppa_source, distroseries=hoary,
            status=PackagePublishingStatus.PUBLISHED)
        # Commit to ensure librarian files are written.
        self.layer.txn.commit()

        copy_helper = self.getCopier(
            sourcename='foo', from_ppa='cprov', include_binaries=False,
            from_suite='hoary', to_suite='hoary')
        copied = copy_helper.mainTask()

        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 1)

        [copy] = copied
        self.assertEqual(copy.displayname, 'foo 1.0 in hoary')
        self.assertEqual(len(copy.getPublishedBinaries()), 0)
        self.assertEqual(len(copy.getBuilds()), 1)

    def testCopySourceAndBinariesFromPPA(self):
        """Check the copy operation from PPA to PRIMARY Archive.

        Source and binaries can be copied from PPA to the PRIMARY archive.

        This action is typically used to copy invariant/harmless packages
        built in PPA context, as language-packs.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        hoary = ubuntu.getSeries('hoary')
        test_publisher = self.getTestPublisher(hoary)

        # There are no sources named 'boing' in ubuntu primary archive.
        existing_sources = ubuntu.main_archive.getPublishedSources(
            name='boing')
        self.assertEqual(existing_sources.count(), 0)

        cprov = getUtility(IPersonSet).getByName("cprov")
        ppa_source = test_publisher.getPubSource(
            sourcename='boing', version='1.0',
            archive=cprov.archive, distroseries=hoary,
            status=PackagePublishingStatus.PENDING)
        ppa_binaries = test_publisher.getPubBinaries(
            pub_source=ppa_source, distroseries=hoary,
            status=PackagePublishingStatus.PENDING)
        # Commit to ensure librarian files are written.
        self.layer.txn.commit()

        copy_helper = self.getCopier(
            sourcename='boing', from_ppa='cprov', include_binaries=True,
            from_suite='hoary', to_suite='hoary')
        copied = copy_helper.mainTask()

        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 3)

        [copied_source] = ubuntu.main_archive.getPublishedSources(
            name='boing')
        self.assertEqual(copied_source.displayname, 'boing 1.0 in hoary')
        self.assertEqual(len(copied_source.getPublishedBinaries()), 2)
        self.assertEqual(len(copied_source.getBuilds()), 0)

    def _setupArchitectureGrowingScenario(self, architecturehintlist="all"):
        """Prepare distroseries with different sets of architectures.

        Ubuntu/warty has i386 and hppa, but only i386 is supported.
        Ubuntu/hoary has i386 and hppa and both are supported.

        Also create source and binary(ies) publication set called 'boing'
        according to the given 'architecturehintlist'.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')

        # Ubuntu/warty only supports i386.
        warty = ubuntu.getSeries('warty')
        test_publisher = self.getTestPublisher(warty)
        active_warty_architectures = [
            arch.architecturetag for arch in warty.architectures
            if arch.getChroot()]
        self.assertEqual(
            active_warty_architectures, ['i386'])

        # Setup ubuntu/hoary supporting i386 and hppa architetures.
        hoary = ubuntu.getSeries('hoary')
        test_publisher.addFakeChroots(hoary)
        active_hoary_architectures = [
            arch.architecturetag for arch in hoary.architectures]
        self.assertEqual(
            sorted(active_hoary_architectures), ['hppa', 'i386'])

        # We will create an architecture-specific source and its binaries
        # for i386 in ubuntu/warty. They will be copied over.
        ppa_source = test_publisher.getPubSource(
            sourcename='boing', version='1.0', distroseries=warty,
            architecturehintlist=architecturehintlist,
            status=PackagePublishingStatus.PUBLISHED)
        ppa_binaries = test_publisher.getPubBinaries(
            pub_source=ppa_source, distroseries=warty,
            status=PackagePublishingStatus.PUBLISHED)
        # Commit to ensure librarian files are written.
        self.layer.txn.commit()

    def testCopyArchitectureIndependentBinaries(self):
        """Architecture independent binaries are propagated in the detination.

        In the case when the destination distroseries supports more
        architectures than the source (distroseries), `copy-package`
        correctly identifies it and propagates architecture independent
        binaries to the new architectures.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')

        self._setupArchitectureGrowingScenario()

        # In terms of supported architectures, both warty & hoary supports
        # i386 and hppa. We will create hoary/amd64 so we can verify if
        # architecture independent binaries copied from warty will also
        # end up in the new architecture.
        amd64_family = ProcessorFamily.selectOneBy(name='amd64')
        hoary = ubuntu.getSeries('hoary')
        hoary_amd64 = hoary.newArch('amd64', amd64_family, True, hoary.owner)

        # Copy the source and binaries from warty to hoary.
        copy_helper = self.getCopier(
            sourcename='boing', include_binaries=True,
            from_suite='warty', to_suite='hoary')
        copied = copy_helper.mainTask()

        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 4)

        # The source and the only existing binary were correctly copied.
        # No build was created, but the architecture independent binary
        # was propagated to the new architecture (hoary/amd64).
        [copied_source] = ubuntu.main_archive.getPublishedSources(
            name='boing', distroseries=hoary)
        self.assertEqual(copied_source.displayname, 'boing 1.0 in hoary')

        self.assertEqual(len(copied_source.getBuilds()), 0)

        architectures_with_binaries = [
            binary.distroarchseries.architecturetag
            for binary in copied_source.getPublishedBinaries()]
        self.assertEqual(
            architectures_with_binaries, ['amd64', 'hppa', 'i386'])

    def testCopyCreatesMissingBuilds(self):
        """Copying source and binaries also create missing builds.

        When source and binaries are copied to a distroseries which supports
        more architectures than the one where they were built, copy-package
        should create builds for the new architectures.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')

        self._setupArchitectureGrowingScenario(architecturehintlist="any")

        copy_helper = self.getCopier(
            sourcename='boing', include_binaries=True,
            from_suite='warty', to_suite='hoary')
        copied = copy_helper.mainTask()

        # Copy the source and the i386 binary from warty to hoary.
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 2)

        # The source and the only existing binary were correctly copied.
        hoary = ubuntu.getSeries('hoary')
        [copied_source] = ubuntu.main_archive.getPublishedSources(
            name='boing', distroseries=hoary)
        self.assertEqual(copied_source.displayname, 'boing 1.0 in hoary')

        [copied_binary] = copied_source.getPublishedBinaries()
        self.assertEqual(
            copied_binary.displayname, 'foo-bin 1.0 in hoary i386')

        # A new build was created in the hoary context for the *extra*
        # architecture (hppa).
        [new_build] = copied_source.getBuilds()
        self.assertEqual(
            new_build.title,
            'hppa build of boing 1.0 in ubuntu hoary RELEASE')

    def testVersionConflictInDifferentPockets(self):
        """Copy-package stops copies conflicting in different pocket.

        Copy candidates are checks against all occurrences of the same
        name and version in the destination archive, regardless the series
        and pocket. In practical terms, it denies copies that will end up
        'unpublishable' due to conflicts in the repository filesystem.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        warty = ubuntu.getSeries('warty')
        test_publisher = self.getTestPublisher(warty)

        # Create a 'probe - 1.1' with a binary in warty-proposed suite
        # in the ubuntu primary archive.
        proposed_source = test_publisher.getPubSource(
            sourcename='probe', version='1.1',
            pocket=PackagePublishingPocket.PROPOSED)
        proposed_binaries = test_publisher.getPubBinaries(
            pub_source=proposed_source,
            pocket=PackagePublishingPocket.PROPOSED)

        # Create a different 'probe - 1.1' in Celso's PPA.
        cprov = getUtility(IPersonSet).getByName("cprov")
        candidate_source = test_publisher.getPubSource(
            sourcename='probe', version='1.1', archive=cprov.archive)
        candidate_binaries = test_publisher.getPubBinaries(
            pub_source=candidate_source, archive=cprov.archive)

        # Perform the copy from the 'probe - 1.1' version from Celso's PPA
        # to the warty-updates in the ubuntu primary archive.
        copy_helper = self.getCopier(
            sourcename='probe', from_ppa='cprov', include_binaries=True,
            from_suite='warty', to_suite='warty-updates')
        copy_helper.logger = TestLogger()
        copied = copy_helper.mainTask()

        # The copy request was denied and the error message is clear about
        # why it happened.
        self.assertEqual(0, len(copied))
        self.assertEqual(
            'probe 1.1 in warty (a different source with the same version '
            'is published in the destination archive)',
            copy_helper.logger.lines[-1])

    def _setupSecurityPropagationContext(self, sourcename):
        """Setup a security propagation publishing context.

        Assert there is no previous publication with the given sourcename
        in the Ubuntu archive.

        Publish a corresponding source in hoary-security context with
        builds for i386 and hppa. Only one i386 binary is published, so the
        hppa build will remain NEEDSBUILD.

        Return the initialized instance of `SoyuzTestPublisher` and the
        security source publication.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')

        # There are no previous source publications for the given
        # sourcename.
        existing_sources = ubuntu.main_archive.getPublishedSources(
            name=sourcename, exact_match=True)
        self.assertEqual(existing_sources.count(), 0)

        # Build a SoyuzTestPublisher for ubuntu/hoary and also enable
        # it to build hppa binaries.
        hoary = ubuntu.getSeries('hoary')
        fake_chroot = getUtility(ILibraryFileAliasSet)[1]
        hoary['hppa'].addOrUpdateChroot(fake_chroot)
        test_publisher = self.getTestPublisher(hoary)

        # Ensure hoary/i386 is official and hoary/hppa unofficial before
        # continuing with the test.
        self.assertTrue(hoary['i386'].official)
        self.assertFalse(hoary['hppa'].official)

        # Publish the requested architecture-specific source in
        # ubuntu/hoary-security.
        security_source = test_publisher.getPubSource(
            sourcename=sourcename, version='1.0',
            architecturehintlist="any",
            archive=ubuntu.main_archive, distroseries=hoary,
            pocket=PackagePublishingPocket.SECURITY,
            status=PackagePublishingStatus.PUBLISHED)

        # Create builds and upload and publish one binary package
        # in the i386 architecture.
        [build_hppa, build_i386] = security_source.createMissingBuilds()
        lazy_bin = test_publisher.uploadBinaryForBuild(
            build_i386, 'lazy-bin')
        test_publisher.publishBinaryInArchive(
            lazy_bin, ubuntu.main_archive,
            pocket=PackagePublishingPocket.SECURITY,
            status=PackagePublishingStatus.PUBLISHED)

        # The i386 build is completed and the hppa one pending.
        self.assertEqual(build_hppa.buildstate, BuildStatus.NEEDSBUILD)
        self.assertEqual(build_i386.buildstate, BuildStatus.FULLYBUILT)

        # Commit to ensure librarian files are written.
        self.layer.txn.commit()

        return test_publisher, security_source

    def _checkSecurityPropagationContext(self, archive, sourcename):
        """Verify publishing context after propagating a security update.

        Check if both publications remain active, the newest in UPDATES and
        the oldest in SECURITY.

        Assert that no build was created during the copy, first because
        the copy was 'including binaries'.

        Additionally, check that no builds will be created in future runs of
        `buildd-queue-builder`, because a source version can only be built
        once in a distroarchseries, independent of its targeted pocket.
        """
        sources = archive.getPublishedSources(
            name=sourcename, exact_match=True,
            status=active_publishing_status)

        [copied_source, original_source] = sources

        self.assertEqual(
            copied_source.pocket, PackagePublishingPocket.UPDATES)
        self.assertEqual(
            original_source.pocket, PackagePublishingPocket.SECURITY)

        self.assertEqual(
            copied_source.getBuilds(), original_source.getBuilds())

        new_builds = copied_source.createMissingBuilds()
        self.assertEqual(len(new_builds), 0)

    def testPropagatingSecurityToUpdates(self):
        """Check if copy-packages copes with the ubuntu workflow.

        As mentioned in bug #251492, ubuntu distro-team uses copy-package
        to propagate security updates across the mirrors via the updates
        pocket and reduce the bottle-neck in the only security repository
        we have.

        This procedure should be executed as soon as the security updates are
        published; the sooner the copy happens, the lower will be the impact
        on the security repository.

        Having to wait for the unofficial builds (which are  usually slower
        than official architectures) before propagating security updates
        causes a severe and unaffordable load on the security repository.

        The copy-backend was modified to support 'incremental' copies, i.e.
        when copying a source (and its binaries) only the missing
        publications will be copied across. That fixes the symptoms of bad
        copies (publishing duplications) and avoid reaching the bug we have
        in the 'domination' component when operating on duplicated arch-indep
        binary publications.
        """
        sourcename = 'lazy-building'

        (test_publisher,
         security_source) = self._setupSecurityPropagationContext(sourcename)

        # Source and i386 binary(ies) can be propagated from security to
        # updates pocket.
        copy_helper = self.getCopier(
            sourcename=sourcename, include_binaries=True,
            from_suite='hoary-security', to_suite='hoary-updates')
        copied = copy_helper.mainTask()

        [source_copy, i386_copy] = copied
        self.assertEqual(
            source_copy.displayname, 'lazy-building 1.0 in hoary')
        self.assertEqual(i386_copy.displayname, 'lazy-bin 1.0 in hoary i386')

        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 2)

        self._checkSecurityPropagationContext(
            security_source.archive, sourcename)

        # Upload a hppa binary but keep it unpublished. When attempting
        # to repeat the copy of 'lazy-building' to -updates the copy
        # succeeds but nothing gets copied. Everything built and published
        # from this source is already copied.
        [build_hppa, build_i386] = security_source.getBuilds()
        lazy_bin_hppa = test_publisher.uploadBinaryForBuild(
            build_hppa, 'lazy-bin')

        copy_helper = self.getCopier(
            sourcename=sourcename, include_binaries=True,
            from_suite='hoary-security', to_suite='hoary-updates')
        nothing_copied = copy_helper.mainTask()
        self.assertEqual(len(nothing_copied), 0)

        # Publishing the hppa binary and re-issuing the full copy procedure
        # will copy only the new binary.
        test_publisher.publishBinaryInArchive(
            lazy_bin_hppa, security_source.archive,
            pocket=PackagePublishingPocket.SECURITY,
            status=PackagePublishingStatus.PUBLISHED)

        copy_helper = self.getCopier(
            sourcename=sourcename, include_binaries=True,
            from_suite='hoary-security', to_suite='hoary-updates')
        copied_increment = copy_helper.mainTask()

        [hppa_copy] = copied_increment
        self.assertEqual(hppa_copy.displayname, 'lazy-bin 1.0 in hoary hppa')

        # The source and its 2 binaries are now available in both
        # hoary-security and hoary-updates suites.
        currently_copied = copied + copied_increment
        self.checkCopies(currently_copied, target_archive, 3)

        self._checkSecurityPropagationContext(
            security_source.archive, sourcename)

        # At this point, trying to copy stuff from -security to -updates will
        # not copy anything again.
        copy_helper = self.getCopier(
            sourcename=sourcename, include_binaries=True,
            from_suite='hoary-security', to_suite='hoary-updates')
        nothing_copied = copy_helper.mainTask()
        self.assertEqual(len(nothing_copied), 0)

    def testCopyAcrossPPAs(self):
        """Check the copy operation across PPAs.

        This operation is useful to propagate dependencies across
        collaborative PPAs without requiring new uploads.
        """
        copy_helper = self.getCopier(
            sourcename='iceweasel', from_ppa='cprov',
            from_suite='warty', to_suite='hoary', to_ppa='sabdfl')
        copied = copy_helper.mainTask()

        self.assertEqual(
            str(copy_helper.location),
            'cprov: warty-RELEASE')
        self.assertEqual(
            str(copy_helper.destination),
            'sabdfl: hoary-RELEASE')

        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 2)

    def testSourceLookupFailure(self):
        """Check if it raises when the target source can't be found.

        SoyuzScriptError is raised when a lookup fails.
        """
        copy_helper = self.getCopier(sourcename='zaphod')

        self.assertRaisesWithContent(
            SoyuzScriptError,
            "Could not find source 'zaphod/None' in "
            "Primary Archive for Ubuntu Linux: warty-RELEASE",
            copy_helper.mainTask)

    def testFailIfValidPackageButNotInSpecifiedSuite(self):
        """It fails if the package is not published in the source location.

        SoyuzScriptError is raised when a lookup fails
        """
        copy_helper = self.getCopier(from_suite="breezy-autotest")

        self.assertRaisesWithContent(
            SoyuzScriptError,
            "Could not find source 'mozilla-firefox/None' in "
            "Primary Archive for Ubuntu Linux: breezy-autotest-RELEASE",
            copy_helper.mainTask)

    def testFailIfSameLocations(self):
        """It fails if the source and destination locations are the same.

        SoyuzScriptError is raise when the copy cannot be performed.
        """
        copy_helper = self.getCopier(from_suite='warty', to_suite='warty')

        self.assertRaisesWithContent(
            SoyuzScriptError,
            "Can not sync between the same locations: "
            "'Primary Archive for Ubuntu Linux: warty-RELEASE' to "
            "'Primary Archive for Ubuntu Linux: warty-RELEASE'",
            copy_helper.mainTask)

    def testBadDistributionDestination(self):
        """Check if it raises if the distribution is invalid.

        PackageLocationError is raised for unknown destination distribution.
        """
        copy_helper = self.getCopier(to_distribution="beeblebrox")

        self.assertRaisesWithContent(
            PackageLocationError,
            "Could not find distribution 'beeblebrox'",
            copy_helper.mainTask)

    def testBadSuiteDestination(self):
        """Check that it fails when specifying a bad distroseries.

        PackageLocationError is raised for unknown destination distroseries.
        """
        copy_helper = self.getCopier(to_suite="slatibartfast")

        self.assertRaisesWithContent(
            PackageLocationError,
            "Could not find suite 'slatibartfast'",
            copy_helper.mainTask)

    def testBadPPADestination(self):
        """Check that it fails when specifying a bad PPA destination.

        PackageLocationError is raised for unknown destination PPA.
        """
        copy_helper = self.getCopier(to_ppa="slatibartfast")

        self.assertRaisesWithContent(
            PackageLocationError,
            "Could not find a PPA for slatibartfast named ppa",
            copy_helper.mainTask)

    def testCrossPartnerCopiesFails(self):
        """Check that it fails when cross-PARTNER copies are requested.

        SoyuzScriptError is raised for cross-PARTNER copies, packages
        published in PARTNER archive can only be copied within PARTNER
        archive.
        """
        copy_helper = self.getCopier(from_partner=True)

        self.assertRaisesWithContent(
            SoyuzScriptError,
            "Cross-PARTNER copies are not allowed.",
            copy_helper.mainTask)

        copy_helper = self.getCopier(to_partner=True)

        self.assertRaisesWithContent(
            SoyuzScriptError,
            "Cross-PARTNER copies are not allowed.",
            copy_helper.mainTask)

    def testPpaPartnerInconsistentLocations(self):
        """Check if PARTNER and PPA inconsistent arguments are caught.

        SoyuzScriptError is raised for when inconsistences in the PARTNER
        and PPA location or destination are spotted.
        """
        copy_helper = self.getCopier(
            from_partner=True, from_ppa='cprov', to_partner=True)

        self.assertRaisesWithContent(
            SoyuzScriptError,
            "Cannot operate with location PARTNER and PPA simultaneously.",
            copy_helper.mainTask)

        copy_helper = self.getCopier(
            from_partner=True, to_ppa='cprov', to_partner=True)

        self.assertRaisesWithContent(
            SoyuzScriptError,
            "Cannot operate with destination PARTNER and PPA simultaneously.",
            copy_helper.mainTask)

    def testCopyFromPrivateToPublicPPAs(self):
        """Check if copying private sources into public archives is denied.

        Private source files can only be published in private archives,
        because builders do not have access to the restricted librarian.

        Builders only fetch the sources files from the repository itself
        for private PPAs. If we copy a restricted file into a public PPA
        builders will not be able to fetch it.
        """
        # Set up a private PPA.
        cprov = getUtility(IPersonSet).getByName("cprov")
        cprov.archive.buildd_secret = "secret"
        cprov.archive.private = True

        # Create a source and binary private publication.
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        hoary = ubuntu.getSeries('hoary')
        test_publisher = self.getTestPublisher(hoary)
        ppa_source = test_publisher.getPubSource(
            archive=cprov.archive, version='1.0', distroseries=hoary)
        ppa_binaries = test_publisher.getPubBinaries(
            pub_source=ppa_source, distroseries=hoary)

        # Run the copy package script storing the logged information.
        copy_helper = self.getCopier(
            sourcename='foo', from_ppa='cprov', include_binaries=True,
            from_suite='hoary', to_suite='hoary')
        copy_helper.logger = TestLogger()
        copied = copy_helper.mainTask()

        # Nothing was copied and an error message was printed explaining why.
        self.assertEqual(len(copied), 0)
        self.assertEqual(
            copy_helper.logger.lines[-1],
            'foo 1.0 in hoary '
            '(Cannot copy private source into public archives.)')

    def testUnembargoing(self):
        """Test UnembargoSecurityPackage, which wraps PackagerCopier."""
        # Set up a private PPA.
        cprov = getUtility(IPersonSet).getByName("cprov")
        cprov.archive.buildd_secret = "secret"
        cprov.archive.private = True

        # Setup a SoyuzTestPublisher object, so we can create publication
        # to be unembargoed.
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        warty = ubuntu.getSeries('warty')
        test_publisher = self.getTestPublisher(warty)

        # Create a source and binary pair to be unembargoed from the PPA.
        ppa_source = test_publisher.getPubSource(
            archive=cprov.archive, version='1.1',
            distroseries=warty,
            status=PackagePublishingStatus.PUBLISHED)
        other_source = test_publisher.getPubSource(
            archive=cprov.archive, version='1.1',
            sourcename="sourcefordiff", distroseries=warty,
            status=PackagePublishingStatus.PUBLISHED)
        test_publisher.addFakeChroots(warty)
        ppa_binaries = test_publisher.getPubBinaries(
            pub_source=ppa_source, distroseries=warty,
            status=PackagePublishingStatus.PUBLISHED)

        # Give the new source a private package diff.
        sourcepackagerelease = other_source.sourcepackagerelease
        diff_file = test_publisher.addMockFile("diff_file", restricted=True)
        package_diff = sourcepackagerelease.requestDiffTo(
            cprov, ppa_source.sourcepackagerelease)
        package_diff.diff_content = diff_file

        # Prepare a *restricted* buildlog file for the Build instances.
        fake_buildlog = test_publisher.addMockFile(
            'foo_source.buildlog', restricted=True)

        for build in ppa_source.getBuilds():
            build.buildlog = fake_buildlog

        # Create ancestry environment in the primary archive, so we can
        # test unembargoed overrides.
        ancestry_source = test_publisher.getPubSource(
            version='1.0', distroseries=warty,
            status=PackagePublishingStatus.PUBLISHED)
        ancestry_binaries = test_publisher.getPubBinaries(
            pub_source=ancestry_source, distroseries=warty,
            status=PackagePublishingStatus.SUPERSEDED)

        # Override the published ancestry source to 'universe'
        universe = getUtility(IComponentSet)['universe']
        ancestry_source.secure_record.component = universe

        # Override the copied binarypackagerelease to 'universe'.
        for binary in ppa_binaries:
            binary.binarypackagerelease.component = universe

        self.layer.txn.commit()

        # Now we can invoke the unembargo script and check its results.
        test_args = [
            "--ppa", "cprov",
            "--ppa-name", "ppa",
            "-s", "%s" % ppa_source.distroseries.name + "-security",
            "foo"
            ]

        script = UnembargoSecurityPackage(
            name='unembargo', test_args=test_args)
        script.logger = QuietFakeLogger()

        copied = script.mainTask()

        # Check the results.
        self.checkCopies(copied, script.destination.archive, 3)

        # Check that the librarian files are all unrestricted now.
        # We must commit the txn for SQL object to see the change.
        # Also check that the published records are in universe, which
        # shows that the ancestry override worked.
        self.layer.txn.commit()
        for published in copied:
            # This is cheating a bit but it's fine.  The script updates
            # the secure publishing record but this change does not
            # get reflected in SQLObject's cache on the object that comes
            # from the SQL View, the non-secure record.  No amount of
            # syncUpdate and flushing seems to want to make it update :(
            # So, I am checking the secure record in this test.
            self.assertEqual(
                published.secure_record.component.name, universe.name,
                "%s is in %s" % (published.displayname,
                                 published.component.name))
            for published_file in published.files:
                self.assertFalse(published_file.libraryfilealias.restricted)
            # Also check the sources' changesfiles.
            if ISourcePackagePublishingHistory.providedBy(published):
                queue = published.sourcepackagerelease.getQueueRecord(
                    distroseries=published.distroseries)
                self.assertFalse(queue.changesfile.restricted)
                # Check the source's package diff.
                [diff] = published.sourcepackagerelease.package_diffs
                self.assertFalse(diff.diff_content.restricted)
            # Check the binary changesfile and the buildlog.
            if IBinaryPackagePublishingHistory.providedBy(published):
                package = published.binarypackagerelease
                changesfile = package.build.changesfile
                self.assertFalse(changesfile.restricted)
                buildlog = package.build.buildlog
                self.assertFalse(buildlog.restricted)
            # Check that the pocket is -security as specified in the
            # script parameters.
            self.assertEqual(
                published.pocket.title, "Security",
                "Expected Security pocket, got %s" % published.pocket.title)

    def testUnembargoSuite(self):
        """Test that passing different suites works as expected."""
        test_args = [
            "--ppa", "cprov",
            "-s", "warty-backports",
            "foo"
            ]

        script = UnembargoSecurityPackage(
            name='unembargo', test_args=test_args)
        self.assertTrue(script.setUpCopierOptions())
        self.assertEqual(
            script.options.to_suite, "warty-backports",
            "Got %s, expected warty-backports")

        # Change the suite to one with the release pocket, it should
        # copy nothing as you're not allowed to unembargo into the
        # release pocket.
        test_args[3] = "hoary"
        script = UnembargoSecurityPackage(
            name='unembargo', test_args=test_args)
        script.logger = QuietFakeLogger()
        self.assertFalse(script.setUpCopierOptions())

    def testCopyClosesBugs(self):
        """Copying packages closes bugs.

        Package copies to primary archive automatically closes
        bugs referenced bugs when target to release, updates
        and security pockets.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        cprov = getUtility(IPersonSet).getByName("cprov")

        warty = ubuntu.getSeries('warty')
        test_publisher = self.getTestPublisher(warty)
        test_publisher.addFakeChroots(warty)

        hoary = ubuntu.getSeries('hoary')
        test_publisher.addFakeChroots(hoary)

        def create_source(version, archive, pocket, changes_file_content):
            source = test_publisher.getPubSource(
                sourcename='buggy-source', version=version,
                distroseries=warty, archive=archive, pocket=pocket,
                changes_file_content=changes_file_content,
                status=PackagePublishingStatus.PUBLISHED)
            source.sourcepackagerelease.changelog_entry = (
                "Required for close_bugs_for_sourcepublication")
            binaries = test_publisher.getPubBinaries(
                pub_source=source, distroseries=warty, archive=archive,
                pocket=pocket, status=PackagePublishingStatus.PUBLISHED)
            return source

        def create_bug(summary):
            buggy_in_ubuntu = ubuntu.getSourcePackage('buggy-source')
            bug_params = CreateBugParams(cprov, summary, "booo")
            bug = buggy_in_ubuntu.createBug(bug_params)
            [bug_task] = bug.bugtasks
            self.assertEqual(bug_task.status, BugTaskStatus.NEW)
            return bug.id

        def create_upload(pub_source, changesfilecontent):
            pub_source.sourcepackagerelease.changelog_entry = "Boing!"
            queue_item = warty.createQueueEntry(
                archive=pub_source.archive,
                changesfilename='foo_source.changes',
                pocket=pub_source.pocket,
                changesfilecontent=changesfilecontent)
            queue_item.addSource(pub_source.sourcepackagerelease)
            queue_item.setDone()
            self.layer.txn.commit()

        def publish_copies(copies):
            for pub in copies:
                pub.secure_record.status = PackagePublishingStatus.PUBLISHED

        changes_template = (
            "Format: 1.7\n"
            "Launchpad-bugs-fixed: %s\n")

        # Create a dummy first package version so we can file bugs on it.
        dummy_changesfile = "Format: 1.7\n"
        proposed_source = create_source(
            '666', warty.main_archive, PackagePublishingPocket.PROPOSED,
            dummy_changesfile)

        # Copies to -updates close bugs when they exist.
        updates_bug_id = create_bug('bug in -proposed')
        closing_bug_changesfile = changes_template % updates_bug_id
        proposed_source = create_source(
            '667', warty.main_archive, PackagePublishingPocket.PROPOSED,
            closing_bug_changesfile)
        self.layer.txn.commit()

        copy_helper = self.getCopier(
            sourcename='buggy-source', include_binaries=True,
            from_suite='warty-proposed', to_suite='warty-updates')
        copied = copy_helper.mainTask()
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 3)

        updates_bug = getUtility(IBugSet).get(updates_bug_id)
        [updates_bug_task] = updates_bug.bugtasks
        self.assertEqual(updates_bug_task.status, BugTaskStatus.FIXRELEASED)

        publish_copies(copied)

        # Copies to the development distroseries close bugs.
        dev_bug_id = create_bug('bug in development')
        closing_bug_changesfile = changes_template % dev_bug_id
        dev_source = create_source(
            '668', warty.main_archive, PackagePublishingPocket.UPDATES,
            closing_bug_changesfile)
        self.layer.txn.commit()

        copy_helper = self.getCopier(
            sourcename='buggy-source', include_binaries=True,
            from_suite='warty-updates', to_suite='hoary')
        copied = copy_helper.mainTask()
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 3)

        dev_bug = getUtility(IBugSet).get(dev_bug_id)
        [dev_bug_task] = dev_bug.bugtasks
        self.assertEqual(dev_bug_task.status, BugTaskStatus.FIXRELEASED)

        publish_copies(copied)

        # Copies to -proposed do not close bugs
        ppa_bug_id = create_bug('bug in PPA')
        closing_bug_changesfile = changes_template % ppa_bug_id
        ppa_source = create_source(
            '669', cprov.archive, PackagePublishingPocket.RELEASE,
            closing_bug_changesfile)
        self.layer.txn.commit()

        copy_helper = self.getCopier(
            sourcename='buggy-source', include_binaries=True,
            from_ppa='cprov', from_suite='warty', to_suite='warty-proposed')
        copied = copy_helper.mainTask()
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 3)

        ppa_bug = getUtility(IBugSet).get(ppa_bug_id)
        [ppa_bug_task] = ppa_bug.bugtasks
        self.assertEqual(ppa_bug_task.status, BugTaskStatus.NEW)

        publish_copies(copied)

        # Copies to PPA do not close bugs.
        proposed_bug_id = create_bug('bug in PPA')
        closing_bug_changesfile = changes_template % proposed_bug_id
        release_source = create_source(
            '670', warty.main_archive, PackagePublishingPocket.RELEASE,
            closing_bug_changesfile)
        self.layer.txn.commit()

        copy_helper = self.getCopier(
            sourcename='buggy-source', include_binaries=True,
            to_ppa='cprov', from_suite='warty', to_suite='warty')
        copied = copy_helper.mainTask()
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 3)

        proposed_bug = getUtility(IBugSet).get(proposed_bug_id)
        [proposed_bug_task] = proposed_bug.bugtasks
        self.assertEqual(proposed_bug_task.status, BugTaskStatus.NEW)

        publish_copies(copied)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
