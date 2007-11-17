# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os
import subprocess
import sys
import unittest

from canonical.config import config
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.scripts import FakeLogger
from canonical.launchpad.scripts.ftpmaster import (
    PackageLocationError, PackageCopier, SoyuzScriptError)
from canonical.launchpad.database.publishing import (
    SecureSourcePackagePublishingHistory,
    SecureBinaryPackagePublishingHistory)
from canonical.launchpad.interfaces import PackagePublishingStatus


class TestCopyPackageScript(LaunchpadZopelessTestCase):
    """Test the copy-package.py script."""

    def runCopyPackage(self, extra_args=None):
        """Run copy-package.py, returning the result and output.
        Returns a tuple of the process's return code, stdout output and
        stderr output."""
        if extra_args is None:
            extra_args = []
        script = os.path.join(
            config.root, "scripts", "ftpmaster-tools", "copy-package.py")
        args = [sys.executable, script, '-y']
        args.extend(extra_args)
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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


class TestCopyPackage(LaunchpadZopelessTestCase):
    """Test the CopyPackageHelper class."""

    def setUp(self):
        """Anotate pending publishing records provided in the sampledata.

        The records annotated will be excluded during the operation checks,
        see checkCopies().
        """
        LaunchpadZopelessTestCase.setUp(self)

        pending_sources = SecureSourcePackagePublishingHistory.selectBy(
            status=PackagePublishingStatus.PENDING)
        self.sources_pending_ids = [pub.id for pub in pending_sources]
        pending_binaries = SecureBinaryPackagePublishingHistory.selectBy(
            status=PackagePublishingStatus.PENDING)
        self.binaries_pending_ids = [pub.id for pub in pending_binaries]

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
        test_args=['-s', from_suite,
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
        # Swallowing all log messages.
        copier.logger = FakeLogger()
        def message(self, prefix, *stuff, **kw):
            pass
        copier.logger.message = message
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

        # We have to compare IDs because the copied list is actually a
        # list of Secure*PublishingHistory records and the lookups are
        # the records from the correspondent DB view *PackagePublishingHistory.
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

    def testCopyAcrossPartner(self):
        """Check the copy operation across PARTNER archive.

        This operation is required to propagate partner uploads across several
        suites, avoiding to build (and modify) the package multiple times to
        have it available for all supported suites independent of the the
        time they were released.
        """
        copy_helper = self.getCopier(
            sourcename='commercialpackage', from_partner=True, to_partner=True,
            from_suite='breezy-autotest', to_suite='hoary')
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

    def testCopyFromPPA(self):
        """Check the copy operation from PPA to PRIMARY Archive.

        That's the preliminary workflow for 'syncing' sources from PPA to
        the ubuntu PRIMARY archive. Note that copying binaries it not allowed,
        see testBinaryCopyFromPpaToPrimaryIsDenied.
        """
        copy_helper = self.getCopier(
            sourcename='iceweasel', from_ppa='cprov',
            from_suite='warty', to_suite='hoary', include_binaries=False)
        copied = copy_helper.mainTask()

        self.assertEqual(
            str(copy_helper.location),
            'PPA for Celso Providelo: warty-RELEASE')
        self.assertEqual(
            str(copy_helper.destination),
            'Primary Archive for Ubuntu Linux: hoary-RELEASE')

        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 1)

    def testCopyAcrossPPAs(self):
        """Check the copy operation across PPAs.

        This operation is useful to propagate deependencies accross
        colaborative PPAs without requiring new uploads. Ideally, it
        should be possible to perform such operation via the Launchpad UI.
        """
        copy_helper = self.getCopier(
            sourcename='iceweasel', from_ppa='cprov',
            from_suite='warty', to_suite='hoary', to_ppa='sabdfl')
        copied = copy_helper.mainTask()

        self.assertEqual(
            str(copy_helper.location),
            'PPA for Celso Providelo: warty-RELEASE')
        self.assertEqual(
            str(copy_helper.destination),
            'PPA for Mark Shuttleworth: hoary-RELEASE')

        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 2)

    def assertRaisesWithContent(self, exception, exception_content,
                                func, *args):
        """Check if the given exception is raised with given content.

        If the expection isn't raised or the exception_content doesn't
        match what was raised an AssertionError is raised.
        """
        exception_name = str(exception).split('.')[-1]

        try:
            func(*args)
        except exception, err:
            self.assertEqual(str(err), exception_content)
        else:
            raise AssertionError(
                "'%s' was not raised" % exception_name)

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
            "Could not find a PPA for slatibartfast",
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

    def testBinaryCopyFromPpaToPrimaryIsDenied(self):
        """Check if copying binaries from PPA to PRIMARY archive is denied.

        SoyuzScriptError is raised if the user tries to copy binaries from
        a PPA to PRIMARY archive.
        """
        copy_helper = self.getCopier(
            sourcename='iceweasel', from_ppa='cprov',
            from_suite='warty', to_suite='hoary')

        self.assertRaisesWithContent(
            SoyuzScriptError,
            "Cannot copy binaries from PPA to PRIMARY archive.",
            copy_helper.mainTask)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
