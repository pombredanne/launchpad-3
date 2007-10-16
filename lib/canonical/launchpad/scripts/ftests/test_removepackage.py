# Copyright 2007 Canonical Ltd.  All rights reserved.

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
from canonical.launchpad.scripts.ftpmaster import (
    SoyuzScriptError, PackageRemover)
from canonical.lp.dbschema import PackagePublishingStatus


class TestRemovePackageScript(LaunchpadZopelessTestCase):
    """Test the remove-package.py script."""

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

        Uses the default case, remove mozilla-firefox source with binaries
        from warty.
        """
        # Count the DELETED records in SSPPH and SBPPH to check later
        # that they increased according to the script action.
        num_src_deleted_pub = SecureSourcePackagePublishingHistory.selectBy(
            status=PackagePublishingStatus.DELETED).count()
        num_bin_deleted_pub = SecureBinaryPackagePublishingHistory.selectBy(
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
        # that the number of rows has increase; content checks are done
        # in other tests.
        self.layer.txn.abort()

        num_src_deleted_after = SecureSourcePackagePublishingHistory.selectBy(
            status=PackagePublishingStatus.DELETED).count()
        num_bin_deleted_after = SecureBinaryPackagePublishingHistory.selectBy(
            status=PackagePublishingStatus.DELETED).count()

        self.assertEqual(num_src_deleted_pub + 1, num_src_deleted_after)
        # 'mozilla-firefox' source produced 2 binaries for each warty
        # architecture (i386, hppa).
        self.assertEqual(num_bin_deleted_pub + 4, num_bin_deleted_after)


class TestPackageRemover(LaunchpadZopelessTestCase):
    """Test the PackageRemover class."""

    user_name = 'sabdfl'
    removal_comment = 'fooooooo'

    class QuietLogger:
        """A logger that doesn't log anything.

        Useful where you need to provide a logger object but don't actually
        want any output.
        """
        def debug(self, args):
            self.log(args)
        def info(self, args):
            self.log(args)
        def warn(self, args):
            self.log(args)
        def error(self, args):
            self.log(args)

        def log(self, args):
            #print args
            pass

    def getRemover(self, name='mozilla-firefox', version=None,
                   suite='warty', distribution_name='ubuntu',
                   component=None, arch=None,
                   user_name=None, removal_comment=None,
                   binary_only=False, source_only=False, confirm_all=True):
        """Return a PackageRemover instance.

        Allow tests to use a set of default options and pass an
        inactive logger to PackageRemover.
        """
        test_args=['-s', suite,
                   '-d', distribution_name ]

        if confirm_all:
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

        remover = PackageRemover(name='lp-remove-package', test_args=test_args)
        remover.logger = self.QuietLogger()
        remover.setupLocation()
        return remover

    def _getPubIDs(self):
        """ """
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

    def assertPublished(self, pub):
        """ """
        self.assertEqual('PUBLISHED', pub.status.name)
        self.assertEqual(None, pub.removed_by)
        self.assertEqual(None, pub.removal_comment)


    def assertDeleted(self, pub):
        """ """
        self.assertEqual('DELETED', pub.status.name)
        self.assertEqual(self.user_name, pub.removed_by.name)
        self.assertEqual(self.removal_comment, pub.removal_comment)

    def testRemoveSourceAndBinaries(self):
        """Check how PackageRemoval behaves on a successful removals.

        Default mode is 'remove source and binaries':
        `lp-remove-package.py mozilla-firefox`
        """
        mozilla_src_pub_id, mozilla_bin_pub_ids = self._getPubIDs()
        removal_candidates = [mozilla_src_pub_id]
        removal_candidates.extend(mozilla_bin_pub_ids)

        remover = self.getRemover()
        removals = remover.mainTask()

        self.assertEqual(len(removals), 5)

        self.assertEqual(
            sorted([pub.id for pub in removals]), sorted(removal_candidates))

        src_pub = SecureSourcePackagePublishingHistory.get(
            mozilla_src_pub_id)
        self.assertDeleted(src_pub)

        for pub_bin_id in mozilla_bin_pub_ids:
            bin_pub = SecureBinaryPackagePublishingHistory.get(pub_bin_id)
            self.assertDeleted(bin_pub)

    def testRemoveSourceOnly(self):
        """Check how PackageRemoval behaves on source-only removals.

        `lp-remove-package.py mozilla-firefox -S`
        """
        mozilla_src_pub_id, mozilla_bin_pub_ids = self._getPubIDs()
        removal_candidates = [mozilla_src_pub_id]

        remover = self.getRemover(source_only=True)
        removals = remover.mainTask()

        self.assertEqual(len(removals), 1)

        self.assertEqual(
            sorted([pub.id for pub in removals]), sorted(removal_candidates))

        src_pub = SecureSourcePackagePublishingHistory.get(
            mozilla_src_pub_id)
        self.assertDeleted(src_pub)

        for pub_bin_id in mozilla_bin_pub_ids:
            bin_pub = SecureBinaryPackagePublishingHistory.get(pub_bin_id)
            self.assertPublished(bin_pub)

    def testRemoveBinaryOnly(self):
        """Check how PackageRemoval behaves on binary-only removals.

        `lp-remove-package.py mozilla-firefox -b`
        """
        mozilla_src_pub_id, mozilla_bin_pub_ids = self._getPubIDs()
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

        self.assertEqual(len(removals), 2)

        self.assertEqual(
            sorted([pub.id for pub in removals]), sorted(removal_candidates))

        src_pub = SecureSourcePackagePublishingHistory.get(
            mozilla_src_pub_id)
        self.assertPublished(src_pub)

        for pub_bin_id in other_bin_pub_ids:
            bin_pub = SecureBinaryPackagePublishingHistory.get(pub_bin_id)
            self.assertPublished(bin_pub)

        for pub_bin_id in mozilla_firefox_bin_pub_ids:
            bin_pub = SecureBinaryPackagePublishingHistory.get(pub_bin_id)
            self.assertDeleted(bin_pub)

    def testRemoveBinaryOnlySpecificArch(self):
        """Check binary-only removals in a specific architecture.

        `lp-remove-package.py mozilla-firefox -b -a i386`
        """
        mozilla_src_pub_id, mozilla_bin_pub_ids = self._getPubIDs()
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

        # XXX cprov 20071002: see the comment in testRemoveBinaryOnly.
        remover = self.getRemover(binary_only=True, version='0.9', arch='i386')
        removals = remover.mainTask()

        self.assertEqual(len(removals), 1)

        self.assertEqual(
            sorted([pub.id for pub in removals]), sorted(removal_candidates))

        src_pub = SecureSourcePackagePublishingHistory.get(
            mozilla_src_pub_id)
        self.assertPublished(src_pub)

        for pub_bin_id in other_bin_pub_ids:
            bin_pub = SecureBinaryPackagePublishingHistory.get(pub_bin_id)
            self.assertPublished(bin_pub)

        for pub_bin_id in mozilla_firefox_bin_pub_ids:
            bin_pub = SecureBinaryPackagePublishingHistory.get(pub_bin_id)
            self.assertDeleted(bin_pub)

    def testRemoveComponentFilter(self):
        """Check the component filter.

        `lp-remove-package.py mozilla-firefox` -> 5 removals
        `lp-remove-package.py mozilla-firefox -c main` -> 5 removals
        `lp-remove-package.py mozilla-firefox -c multiverse` -> raises
            SoyuzScriptError.
        """
        remover = self.getRemover()
        removals = remover.mainTask()
        self.assertEqual(len(removals), 5)

        self.layer.abort()

        remover = self.getRemover(component='main')
        removals = remover.mainTask()
        self.assertEqual(len(removals), 5)

        self.layer.abort()

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
