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
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.database.publishing import (
    SecureSourcePackagePublishingHistory,
    SecureBinaryPackagePublishingHistory)
from canonical.launchpad.interfaces import IDistributionSet
from canonical.launchpad.scripts import FakeLogger
from canonical.launchpad.scripts.ftpmaster import (
    SoyuzScriptError, PackageRemover)
from canonical.lp.dbschema import PackagePublishingStatus


class TestRemovePackageScript(LaunchpadZopelessTestCase):
    """Test invokation of the remove-package.py script.

    Uses subprocess to invoke the script file with usual arguments and
    probe the expected results in the database.
    """

    def runRemovePackage(self, extra_args=[]):
        """Run lp-remove-package.py, returning the result and output.

        Returns a tuple of the process's return code, stdout output and
        stderr output.
        """
        script = os.path.join(
            config.root, "scripts", "ftpmaster-tools", "lp-remove-package.py")
        args = [sys.executable, script, '-y']
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
        num_src_deleted_before = SecureSourcePackagePublishingHistory.selectBy(
            status=PackagePublishingStatus.DELETED).count()
        num_bin_deleted_before = SecureBinaryPackagePublishingHistory.selectBy(
            status=PackagePublishingStatus.DELETED).count()

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


class TestPackageRemover(LaunchpadZopelessTestCase):
    """Test the PackageRemover class.

    Perform tests directly on the script class.
    """

    user_name = 'sabdfl'
    removal_comment = 'fooooooo'

    def getRemover(self, name='mozilla-firefox', version=None,
                   suite='warty', distribution_name='ubuntu',
                   component=None, arch=None,
                   user_name=None, removal_comment=None,
                   binary_only=False, source_only=False):
        """Return a PackageRemover instance.

        Allow tests to use a set of default options and pass an
        inactive logger to PackageRemover.
        """
        test_args=['-s', suite,
                   '-d', distribution_name ]

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

        test_args.append(name)

        remover = PackageRemover(
            name='lp-remove-package', test_args=test_args)
        # Swallowing all log messages.
        remover.logger = FakeLogger()
        def message(self, prefix, *stuff, **kw):
            pass
        remover.logger.message = message
        remover.setupLocation()
        return remover

    def _getPublicationIDs(self):
        """Return the publication IDs for the mozilla-firefox release.

        Return the publication IDs for the sources and binaries of the current
        mozilla-firefox release in warty (warty-i386, warty-hppa).

        We return IDs instead of the records because they won't be useful in
        callsites without a `flush_database_updates`.
        """
        ubuntu = getUtility(IDistributionSet)['ubuntu']
        warty = ubuntu['warty']
        warty_i386 = warty['i386']
        warty_hppa = warty['hppa']

        mozilla_sp = warty.getSourcePackage('mozilla-firefox')
        mozilla_src_pub = mozilla_sp.currentrelease.current_published
        mozilla_bin_pub_ids = [
            bin.current_publishing_record.id
            for bin in mozilla_sp.currentrelease.published_binaries]

        return (mozilla_src_pub.id, mozilla_bin_pub_ids)

    def _preparePublicationIDs(self, pub_ids, source=True):
        """Prepare the given publication ID list for checks.

        Ensure that 'pub_ids' is a list and find the correct database
        'getter' (`SourcePackagePublishingHistory` or
        `BinaryPackagePublishingHistory`).

        Return a tuple (pub_ids, getter).
        """
        if not isinstance(pub_ids, list):
            pub_ids = [pub_ids]

        if source:
            getter = SecureSourcePackagePublishingHistory
        else:
            getter = SecureBinaryPackagePublishingHistory

        return pub_ids, getter

    def assertPublished(self, pub_ids, source):
        """Check if the given pub_ids list items are PUBLISHED.

        `pub_ids` can be a list of publishing records IDs or a single ID.

        Performs a lookup on publishing table and checks each entry for:

         * PUBLISHED status,
         * empty removed_by,
         * empty removal_comment.

        The 'source' flag indicates if the lookup should be in the source or
        binary tables.
        """
        pub_ids, getter = self._preparePublicationIDs(pub_ids, source)
        for pub_id in pub_ids:
            pub = getter.get(pub_id)
            self.assertEqual('PUBLISHED', pub.status.name)
            self.assertEqual(None, pub.removed_by)
            self.assertEqual(None, pub.removal_comment)

    def assertDeleted(self, pub_ids, source):
        """Check if the given pub_ids list items are DELETED.

        `pub_ids` can be a list of publishing records IDs or a single ID.

        Performs a lookup on publishing table and checks each entry for:
         * DELETED status,
         * removed_by.name equal to self.user_name,
         * removal_comment equal to self.removal_comment.

        The 'source' flag indicates if the lookup should be in the source or
        binary tables.
        """
        pub_ids, getter = self._preparePublicationIDs(pub_ids, source)
        for pub_id in pub_ids:
            pub = getter.get(pub_id)
            self.assertEqual('DELETED', pub.status.name)
            self.assertEqual(self.user_name, pub.removed_by.name)
            self.assertEqual(self.removal_comment, pub.removal_comment)

    def testRemoveSourceAndBinaries(self):
        """Check how PackageRemoval behaves on a successful removal.

        Default mode is 'remove source and binaries':
        `lp-remove-package.py mozilla-firefox`
        """
        mozilla_src_pub_id, mozilla_bin_pub_ids = self._getPublicationIDs()
        removal_candidates = [mozilla_src_pub_id]
        removal_candidates.extend(mozilla_bin_pub_ids)

        remover = self.getRemover()
        removals = remover.mainTask()

        self.assertEqual(
            sorted([pub.id for pub in removals]), sorted(removal_candidates))

        self.assertDeleted(mozilla_src_pub_id, source=True)
        self.assertDeleted(mozilla_bin_pub_ids, source=False)

    def testRemoveSourceOnly(self):
        """Check how PackageRemoval behaves on source-only removals.

        `lp-remove-package.py mozilla-firefox -S`
        """
        mozilla_src_pub_id, mozilla_bin_pub_ids = self._getPublicationIDs()
        removal_candidates = [mozilla_src_pub_id]

        remover = self.getRemover(source_only=True)
        removals = remover.mainTask()

        self.assertEqual(len(removals), 1)

        self.assertEqual(
            sorted([pub.id for pub in removals]), sorted(removal_candidates))

        self.assertDeleted(mozilla_src_pub_id, source=True)
        self.assertPublished(mozilla_bin_pub_ids, source=False)

    def testRemoveBinaryOnly(self):
        """Check how PackageRemoval behaves on binary-only removals.

        `lp-remove-package.py mozilla-firefox -b`
        """
        mozilla_src_pub_id, mozilla_bin_pub_ids = self._getPublicationIDs()
        removal_candidates = []

        # Extract only binaries named 'mozilla-firefox'
        mozilla_firefox_bin_pub_ids = []
        other_bin_pub_ids = []
        for pub_bin_id in mozilla_bin_pub_ids:
            bin_pub = SecureBinaryPackagePublishingHistory.get(pub_bin_id)
            if bin_pub.binarypackagerelease.name == 'mozilla-firefox':
                mozilla_firefox_bin_pub_ids.append(bin_pub.id)
            else:
                other_bin_pub_ids.append(bin_pub.id)

        removal_candidates.extend(mozilla_firefox_bin_pub_ids)

        # XXX cprov 20071002: use a specific version because the
        # binary mozilla-firefox_0.9 in warty i386 is going to be
        # superseded in sampledata by the 1.0 version.
        remover = self.getRemover(binary_only=True, version='0.9')
        removals = remover.mainTask()

        self.assertEqual(
            sorted([pub.id for pub in removals]), sorted(removal_candidates))

        self.assertPublished(mozilla_src_pub_id, source=True)
        self.assertPublished(other_bin_pub_ids, source=False)
        self.assertDeleted(mozilla_firefox_bin_pub_ids, source=False)

    def testRemoveBinaryOnlySpecificArch(self):
        """Check binary-only removals in a specific architecture.

        `lp-remove-package.py mozilla-firefox -b -a i386`
        """
        mozilla_src_pub_id, mozilla_bin_pub_ids = self._getPublicationIDs()
        removal_candidates = []

        # Extract only binaries named 'mozilla-firefox' published in
        # 'i386' architecture
        mozilla_firefox_bin_pub_ids = []
        other_bin_pub_ids = []
        for pub_bin_id in mozilla_bin_pub_ids:
            bin_pub = SecureBinaryPackagePublishingHistory.get(pub_bin_id)
            if bin_pub.binarypackagerelease.name == 'mozilla-firefox':
                if bin_pub.distroarchseries.architecturetag == 'i386':
                    mozilla_firefox_bin_pub_ids.append(bin_pub.id)
                else:
                    other_bin_pub_ids.append(bin_pub.id)
            else:
                other_bin_pub_ids.append(bin_pub.id)

        removal_candidates.extend(mozilla_firefox_bin_pub_ids)

        # See the comment in testRemoveBinaryOnly.
        remover = self.getRemover(binary_only=True, version='0.9', arch='i386')
        removals = remover.mainTask()

        self.assertEqual(
            sorted([pub.id for pub in removals]), sorted(removal_candidates))

        self.assertPublished(mozilla_src_pub_id, source=True)
        self.assertPublished(other_bin_pub_ids, source=False)
        self.assertDeleted(mozilla_firefox_bin_pub_ids, source=False)

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
            len(removals_without_component), len(removals_with_main_component))

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
