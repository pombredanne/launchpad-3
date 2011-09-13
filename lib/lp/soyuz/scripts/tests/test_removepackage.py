# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Functional Tests for PackageRemover script class.

This file performs tests on the PackageRemover script class and on the script
file itself.
"""

__metaclass__ = type

import os
import subprocess
import sys
import unittest

from zope.component import getUtility

from canonical.config import config
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.services.log.logger import DevNullLogger
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.interfaces.publishing import (
    active_publishing_status,
    )
from lp.soyuz.model.publishing import (
    BinaryPackagePublishingHistory,
    SourcePackagePublishingHistory,
    )
from lp.soyuz.scripts.ftpmaster import (
    PackageRemover,
    SoyuzScriptError,
    )
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher


class TestRemovePackageScript(unittest.TestCase):
    """Test invokation of the remove-package.py script.

    Uses subprocess to invoke the script file with usual arguments and
    probe the expected results in the database.
    """
    layer = LaunchpadZopelessLayer

    def runRemovePackage(self, extra_args=None):
        """Run lp-remove-package.py, returning the result and output.

        Returns a tuple of the process's return code, stdout output and
        stderr output.
        """
        script = os.path.join(
            config.root, "scripts", "ftpmaster-tools", "lp-remove-package.py")
        args = [sys.executable, script, '-y']
        if extra_args is not None:
            args.extend(extra_args)
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return (process.returncode, stdout, stderr)

    def testSimpleRun(self):
        """Try a simple lp-remove-package.py run.

        Uses the default case, remove mozilla-firefox source and binaries
        from warty.
        """
        # Count the DELETED records in SSPPH and SBPPH to check later
        # that they increased according to the script action.
        num_src_deleted_before = (
            SourcePackagePublishingHistory.selectBy(
                status=PackagePublishingStatus.DELETED).count())
        num_bin_deleted_before = (
            BinaryPackagePublishingHistory.selectBy(
                status=PackagePublishingStatus.DELETED).count())

        returncode, out, err = self.runRemovePackage(
            extra_args=['-s', 'warty', 'mozilla-firefox', '-u', 'cprov',
                        '-m', 'bogus...'])
        # Need to print these or you can't see what happened if the
        # return code is bad:
        if returncode != 0:
            print "\nStdout:\n%s\nStderr\n%s\n" % (out, err)
        self.assertEqual(0, returncode)

        # Test that the database has been modified.  We're only checking
        # that the number of rows has increased; content checks are done
        # in other tests.
        self.layer.txn.abort()

        num_src_deleted_after = SourcePackagePublishingHistory.selectBy(
            status=PackagePublishingStatus.DELETED).count()
        num_bin_deleted_after = BinaryPackagePublishingHistory.selectBy(
            status=PackagePublishingStatus.DELETED).count()

        self.assertEqual(num_src_deleted_before + 1, num_src_deleted_after)
        # 'mozilla-firefox' source produced 2 binaries for each warty
        # architecture (i386, hppa).
        self.assertEqual(num_bin_deleted_before + 4, num_bin_deleted_after)


class TestPackageRemover(unittest.TestCase):
    """Test the PackageRemover class.

    Perform tests directly on the script class.
    """
    layer = LaunchpadZopelessLayer
    user_name = 'mark'
    removal_comment = 'fooooooo'

    def getRemover(self, name='foo', version=None,
                   suite='hoary', distribution_name='ubuntu',
                   component=None, arch=None, partner=False, ppa=None,
                   user_name=None, removal_comment=None,
                   binary_only=False, source_only=False):
        """Return a PackageRemover instance.

        Allow tests to use a set of default options and pass an
        inactive logger to PackageRemover.
        """
        test_args = ['-s', suite,
                     '-d', distribution_name]

        # Always operate with 'confirm_all' activated. Input requests are
        # very unlikely to be useful inside tests.
        test_args.append('-y')

        if binary_only:
            test_args.append('-b')

        if source_only:
            test_args.append('-S')

        if version is not None:
            test_args.extend(['-e', version])

        if arch is not None:
            test_args.extend(['-a', arch])

        if ppa is not None:
            test_args.extend(['-p', ppa])

        if partner:
            test_args.append('-j')

        if component is not None:
            test_args.extend(['-c', component])

        if user_name is None:
            test_args.extend(['-u', self.user_name])
        else:
            test_args.extend(['-u', user_name])

        if removal_comment is None:
            test_args.extend(['-m', self.removal_comment])
        else:
            test_args.extend(['-m', removal_comment])

        test_args.extend(name.split())

        remover = PackageRemover(
            name='lp-remove-package', test_args=test_args)
        # Swallowing all log messages.
        remover.logger = DevNullLogger()
        remover.setupLocation()
        return remover

    def assertPublished(self, pub):
        """Check if the given publishing record is PUBLISHED.

        Published implies in:

         * PUBLISHED or PENDING status,
         * empty removed_by,
         * empty removal_comment.
        """
        self.assertTrue(pub.status in active_publishing_status)
        self.assertEqual(None, pub.removed_by)
        self.assertEqual(None, pub.removal_comment)

    def assertDeleted(self, pub):
        """Check if the given publishing record is DELETED.

        Deleted implies in:

         * DELETED status,
         * removed_by.name equal to self.user_name,
         * removal_comment equal to self.removal_comment.
        """
        self.assertEqual(pub.status, PackagePublishingStatus.DELETED)
        self.assertEqual(self.user_name, pub.removed_by.name)
        self.assertEqual(self.removal_comment, pub.removal_comment)

    def compareRemovals(self, removed, expected):
        """Check if the removed set contains the expected data.

        :param removed: a list of `SourcePackagePublishingHistory` or
            `BinaryPackagePublishingHistory` returned by the
            `PackageRemover` instance.
        :param expected: a list of `SourcePackagePublishingHistory` or
            `BinaryPackagePublishingHistory` usually assembled at the call
            site with the records expected to be DELETED.

        :raises AssertionError: if the `removed` set does not match the
            `expected` one or if the removals are not properly 'deleted'
            (see `assertDeleted`).
        """
        self.assertEqual(
            sorted([pub.id for pub in removed]),
            sorted([pub.id for pub in expected]))

        for pub in expected:
            self.assertDeleted(pub)

    def getTestPublisher(self):
        """Return a initialized `SoyuzTestPublisher` object.

        The object will be configured to published sources and binaries
        for ubuntu/hoary on i386 and hppa architectures.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        hoary = ubuntu.getSeries('hoary')
        test_publisher = SoyuzTestPublisher()
        test_publisher.setUpDefaultDistroSeries(hoary)
        test_publisher.addFakeChroots(hoary)
        return test_publisher

    def setUp(self):
        """Instantiate a `SoyuzTestPublisher`."""
        self.test_publisher = self.getTestPublisher()

    def testRemoveSourceAndBinaries(self):
        """Check how PackageRemoval behaves on a successful removal.

        Default mode is 'remove source and binaries':
        `lp-remove-package.py foo`
        """
        # Create 'foo' source and its 'foo-bin' binary publications in
        # hoary i386 and hppa.
        source = self.test_publisher.getPubSource(sourcename='foo')
        binaries = self.test_publisher.getPubBinaries(pub_source=source)

        # All the created publishing records should be deleted.
        removal_candidates = []
        removal_candidates.append(source)
        removal_candidates.extend(binaries)

        remover = self.getRemover()
        removals = remover.mainTask()
        self.compareRemovals(removals, removal_candidates)

    def testRemoveMultiplePackages(self):
        """Package remover accepts multiple non-option arguments.

        `lp-remove-packages` is capable of operating on multiple packages.
        """
        # Create multiple source and binaries to be removed.
        removal_candidates = []
        for name in ['foo', 'bar', 'baz']:
            source = self.test_publisher.getPubSource(sourcename=name)
            binaries = self.test_publisher.getPubBinaries(pub_source=source)
            removal_candidates.append(source)
            removal_candidates.extend(binaries)

        remover = self.getRemover(name='foo bar baz')
        removals = remover.mainTask()
        self.compareRemovals(removals, removal_candidates)

    def testRemoveSourceOnly(self):
        """Check how PackageRemoval behaves on source-only removals.

        `lp-remove-package.py foo -S`
        """
        # Create source and binaries, but expect only the source to be
        # removed.
        source = self.test_publisher.getPubSource(sourcename='foo')
        binaries = self.test_publisher.getPubBinaries(pub_source=source)
        removal_candidates = [source]

        remover = self.getRemover(source_only=True)
        removals = remover.mainTask()
        self.compareRemovals(removals, removal_candidates)

        # Binaries remained published.
        for pub in binaries:
            self.assertPublished(pub)

    def testRemoveBinaryOnly(self):
        """Check how PackageRemoval behaves on binary-only removals.

        `lp-remove-package.py foo-bin -b`
        """
        # Create a source ('foo') with multiple binaries ('foo-bin' and
        # 'foo-data').
        source = self.test_publisher.getPubSource(sourcename='foo')
        builds = source.createMissingBuilds()
        binaries = []
        for build in builds:
            for binaryname in ['foo-bin', 'foo-data']:
                binarypackagerelease = (
                    self.test_publisher.uploadBinaryForBuild(
                        build, binaryname))
                binary = self.test_publisher.publishBinaryInArchive(
                    binarypackagerelease, source.archive)
                binaries.extend(binary)

        # Only 'foo-bin' will be removed across all architectures.
        removal_candidates = [
            pub for pub in binaries
            if pub.binarypackagerelease.name == 'foo-bin']

        remover = self.getRemover(name='foo-bin', binary_only=True)
        removals = remover.mainTask()
        self.compareRemovals(removals, removal_candidates)

        # Source and other binaries than 'foo-bin' remained published
        self.assertPublished(source)
        remained_binaries = [
            pub for pub in binaries
            if pub.binarypackagerelease.name != 'foo-bin']
        for pub in remained_binaries:
            self.assertPublished(pub)

    def testRemoveBinaryOnlySpecificArch(self):
        """Check binary-only removals in a specific architecture.

        `lp-remove-package.py foo-bin -b -a i386`
        """
        # Create source ('foo') and a binary ('foo-bin') for i386 and
        # hppa architectures.
        source = self.test_publisher.getPubSource(sourcename='foo')
        binaries = self.test_publisher.getPubBinaries(pub_source=source)

        # Only the 'foo-bin' on i386 will be removed.
        removal_candidates = [
            pub for pub in binaries
            if pub.distroarchseries.architecturetag == 'i386']

        # See the comment in testRemoveBinaryOnly.
        remover = self.getRemover(
            name='foo-bin', binary_only=True, arch='i386')
        removals = remover.mainTask()
        self.compareRemovals(removals, removal_candidates)

        # Source and non-i386 binaries remained published.
        self.assertPublished(source)
        remained_binaries = [
            pub for pub in binaries
            if pub.distroarchseries.architecturetag != 'i386']
        for pub in remained_binaries:
            self.assertPublished(pub)

    def testRemoveFromPartner(self):
        """Source and binary package removal for Partner archive."""
        # Retrieve the ubuntu PARTNER archives.
        ubuntu = self.test_publisher.distroseries.distribution
        partner_archive = ubuntu.getArchiveByComponent('partner')

        # Create source and a binary publication in the PARTNER archive.
        source = self.test_publisher.getPubSource(
            sourcename='foo', archive=partner_archive)
        binaries = self.test_publisher.getPubBinaries(
            pub_source=source, archive=partner_archive)

        # Expect all created publishing records to be removed.
        removal_candidates = [source]
        removal_candidates.extend(binaries)

        remover = self.getRemover(partner=True)
        removals = remover.mainTask()
        self.compareRemovals(removals, removal_candidates)

    def testRemoveFromPPA(self):
        """Source and binary package removal for PPAs."""
        # Create source and a binary for Celso's PPA>
        cprov = getUtility(IPersonSet).getByName('cprov')
        source = self.test_publisher.getPubSource(
            sourcename='foo', archive=cprov.archive)
        binaries = self.test_publisher.getPubBinaries(
            pub_source=source, archive=cprov.archive)

        # Expect all created publishing records to be removed.
        removal_candidates = [source]
        removal_candidates.extend(binaries)

        remover = self.getRemover(ppa='cprov')
        removals = remover.mainTask()
        self.compareRemovals(removals, removal_candidates)

    def testRemoveComponentFilter(self):
        """Check the component filter behaviour.

        Filtering by component main ('-c main') will produce exactly
        the same result than not passing any component filter, because
        all test publications are in main component.
        """
        source = self.test_publisher.getPubSource(sourcename='foo')

        self.layer.commit()

        remover = self.getRemover()
        removals_without_component = remover.mainTask()

        self.layer.abort()

        remover = self.getRemover(component='main')
        removals_with_main_component = remover.mainTask()

        self.assertEqual(
            len(removals_without_component),
            len(removals_with_main_component))

    def testRemoveComponentFilterError(self):
        """Check a component filter error.

        Filtering by component multiverse ('-c multiverse') will raise
        `SoyuzScriptError` because the selected publications are in main
        component.
        """
        source = self.test_publisher.getPubSource(sourcename='foo')

        remover = self.getRemover(component='multiverse')
        self.assertRaises(SoyuzScriptError, remover.mainTask)

    def testUnknownRemover(self):
        """Check if the script raises on unknown user_name."""
        remover = self.getRemover(user_name='slatitbartfast')
        self.assertRaises(SoyuzScriptError, remover.mainTask)

    def testRemovalCommentNotGiven(self):
        """Check if the script raises if removal comment is not passed"""
        remover = self.getRemover()
        remover.options.removal_comment = None
        self.assertRaises(SoyuzScriptError, remover.mainTask)

    def testPackageNameNotGiven(self):
        """Check if the script raises if package name is not passed"""
        remover = self.getRemover()
        remover.args = []
        self.assertRaises(SoyuzScriptError, remover.mainTask)
