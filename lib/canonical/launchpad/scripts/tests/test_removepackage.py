# Copyright 2007 Canonical Ltd.  All rights reserved.
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
from canonical.launchpad.database.publishing import (
    SecureSourcePackagePublishingHistory,
    SecureBinaryPackagePublishingHistory)
from canonical.launchpad.interfaces.distribution import IDistributionSet
from canonical.launchpad.interfaces.publishing import PackagePublishingStatus
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.scripts import FakeLogger
from canonical.launchpad.scripts.ftpmaster import (
    SoyuzScriptError, PackageRemover)
from canonical.launchpad.tests.test_publishing import SoyuzTestPublisher
from canonical.testing import LaunchpadZopelessLayer


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
            SecureSourcePackagePublishingHistory.selectBy(
                status=PackagePublishingStatus.DELETED).count())
        num_bin_deleted_before = (
            SecureBinaryPackagePublishingHistory.selectBy(
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

        num_src_deleted_after = SecureSourcePackagePublishingHistory.selectBy(
            status=PackagePublishingStatus.DELETED).count()
        num_bin_deleted_after = SecureBinaryPackagePublishingHistory.selectBy(
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
    user_name = 'sabdfl'
    removal_comment = 'fooooooo'

    def getRemover(self, name='mozilla-firefox', version=None,
                   suite='warty', distribution_name='ubuntu',
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
        remover.logger = FakeLogger()
        def message(self, prefix, *stuff, **kw):
            pass
        remover.logger.message = message
        remover.setupLocation()
        return remover

    def assertPublished(self, pub):
        """Check if the given publishing record is PUBLISHED.

        Published implies in:

         * PUBLISHED or PENDING status,
         * empty removed_by,
         * empty removal_comment.
        """
        self.assertTrue(pub.status.name in ['PUBLISHED', 'PENDING'])
        self.assertEqual(None, pub.removed_by)
        self.assertEqual(None, pub.removal_comment)

    def assertDeleted(self, pub):
        """Check if the given publishing record is DELETED.

        Deleted implies in:

         * DELETED status,
         * removed_by.name equal to self.user_name,
         * removal_comment equal to self.removal_comment.
        """
        self.assertEqual('DELETED', pub.status.name)
        self.assertEqual(self.user_name, pub.removed_by.name)
        self.assertEqual(self.removal_comment, pub.removal_comment)

    def getTestPublisher(self):
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        hoary = ubuntu.getSeries('hoary')
        test_publisher = SoyuzTestPublisher()
        test_publisher.setUpDefaultDistroSeries(hoary)
        test_publisher.addFakeChroots(hoary)
        return test_publisher

    def testRemoveSourceAndBinaries(self):
        """Check how PackageRemoval behaves on a successful removal.

        Default mode is 'remove source and binaries':
        `lp-remove-package.py foo`
        """
        test_publisher = self.getTestPublisher()

        removal_candidates = []
        source = test_publisher.getPubSource(sourcename='foo')
        binaries = test_publisher.getPubBinaries(pub_source=source)
        removal_candidates.append(source)
        removal_candidates.extend(binaries)

        remover = self.getRemover(name='foo', suite='hoary')
        removals = remover.mainTask()

        self.assertEqual(
            sorted([pub.id for pub in removals]),
            sorted([pub.id for pub in removal_candidates]))

        for pub in removal_candidates:
            self.assertDeleted(pub.secure_record)

    def testRemoveMultiplePackages(self):
        """Package remover accepts multiple non-option arguments.

        `lp-remove-packages` is capable of operating on multiple packages.
        """
        test_publisher = self.getTestPublisher()

        removal_candidates = []
        for name in ['foo', 'bar', 'baz']:
            source = test_publisher.getPubSource(sourcename=name)
            binaries = test_publisher.getPubBinaries(pub_source=source)
            removal_candidates.append(source)
            removal_candidates.extend(binaries)

        remover = self.getRemover(name='foo bar baz', suite='hoary')
        removals = remover.mainTask()

        self.assertEqual(
            sorted([pub.id for pub in removals]),
            sorted([pub.id for pub in removal_candidates]))

        for pub in removal_candidates:
            self.assertDeleted(pub.secure_record)

    def testRemoveSourceOnly(self):
        """Check how PackageRemoval behaves on source-only removals.

        `lp-remove-package.py foo -S`
        """
        test_publisher = self.getTestPublisher()

        removal_candidates = []
        source = test_publisher.getPubSource(sourcename='foo')
        binaries = test_publisher.getPubBinaries(pub_source=source)

        removal_candidates.append(source)

        remover = self.getRemover(
            name='foo', suite='hoary', source_only=True)
        removals = remover.mainTask()

        self.assertEqual(
            sorted([pub.id for pub in removals]),
            sorted([pub.id for pub in removal_candidates]))

        self.assertDeleted(source.secure_record)
        for pub in binaries:
            self.assertPublished(pub.secure_record)

    def testRemoveBinaryOnly(self):
        """Check how PackageRemoval behaves on binary-only removals.

        `lp-remove-package.py foo-bin -b`
        """
        test_publisher = self.getTestPublisher()
        source = test_publisher.getPubSource(sourcename='foo')

        builds = source.createMissingBuilds()
        binaries = []
        for build in builds:
            for binaryname in ['foo-bin', 'foo-data']:
                binarypackagerelease = test_publisher.uploadBinaryForBuild(
                    build, binaryname)
                binary = test_publisher.publishBinaryInArchive(
                    binarypackagerelease, source.archive)
                binaries.extend(binary)

        removal_candidates = [
            pub for pub in binaries
            if pub.binarypackagerelease.name == 'foo-bin']

        remover = self.getRemover(
            name='foo-bin', suite='hoary', binary_only=True)
        removals = remover.mainTask()

        self.assertEqual(
            sorted([pub.id for pub in removals]),
            sorted([pub.id for pub in removal_candidates]))

        self.assertPublished(source.secure_record)

        remained_binaries = [
            pub for pub in binaries
            if pub.binarypackagerelease.name != 'foo-bin']
        for pub in remained_binaries:
            self.assertPublished(pub.secure_record)

        for pub in removal_candidates:
            self.assertDeleted(pub.secure_record)

    def testRemoveBinaryOnlySpecificArch(self):
        """Check binary-only removals in a specific architecture.

        `lp-remove-package.py foo-bin -b -a i386`
        """
        test_publisher = self.getTestPublisher()
        source = test_publisher.getPubSource(sourcename='foo')
        binaries = test_publisher.getPubBinaries(pub_source=source)
        removal_candidates = [
            pub for pub in binaries
            if pub.distroarchseries.architecturetag == 'i386'
            ]

        # See the comment in testRemoveBinaryOnly.
        remover = self.getRemover(
            name='foo-bin', suite='hoary', binary_only=True, arch='i386')
        removals = remover.mainTask()

        self.assertEqual(
            sorted([pub.id for pub in removals]),
            sorted([pub.id for pub in removal_candidates]))

        self.assertPublished(source.secure_record)

        remained_binaries = [
            pub for pub in binaries
            if pub.distroarchseries.architecturetag != 'i386'
            ]
        for pub in remained_binaries:
            self.assertPublished(pub.secure_record)

        for pub in removal_candidates:
            self.assertDeleted(pub.secure_record)

    def testRemoveFromPartner(self):
        """Source and binary package removal for Partner archive."""
        test_publisher = self.getTestPublisher()
        ubuntu = test_publisher.distroseries.distribution
        partner_archive = ubuntu.getArchiveByComponent('partner')

        source = test_publisher.getPubSource(
            sourcename='foo', archive=partner_archive)
        binaries = test_publisher.getPubBinaries(
            pub_source=source, archive=partner_archive)
        removal_candidates = [source]
        removal_candidates.extend(binaries)

        remover = self.getRemover(
            name='foo', suite='hoary', partner=True)
        removals = remover.mainTask()

        self.assertEqual(
            sorted([pub.id for pub in removals]),
            sorted([pub.id for pub in removal_candidates]))

        for pub in removal_candidates:
            self.assertDeleted(pub.secure_record)

    def testRemoveFromPPA(self):
        """Source and binary package removal for PPAs."""
        cprov = getUtility(IPersonSet).getByName('cprov')
        test_publisher = self.getTestPublisher()
        source = test_publisher.getPubSource(
            sourcename='foo', archive=cprov.archive)
        binaries = test_publisher.getPubBinaries(
            pub_source=source, archive=cprov.archive)
        removal_candidates = [source]
        removal_candidates.extend(binaries)

        remover = self.getRemover(name='foo', suite='hoary', ppa='cprov')
        removals = remover.mainTask()

        self.assertEqual(
            sorted([pub.id for pub in removals]),
            sorted([pub.id for pub in removal_candidates]))

        for pub in removal_candidates:
            self.assertDeleted(pub.secure_record)

    def testRemoveComponentFilter(self):
        """Check the component filter behaviour.

        Filtering by component main ('-c main') will produce exactly
        the same result than not passing any component filter, because
        all test publications are in main component.
        """
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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
