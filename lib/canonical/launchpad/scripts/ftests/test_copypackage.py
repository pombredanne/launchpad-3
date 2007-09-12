# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os
import subprocess
import sys
import unittest

from canonical.config import config
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.scripts.ftpmaster import (
    PackageLocationError, PackageCopyError, PackageCopier)
from canonical.launchpad.database.publishing import (
    SecureSourcePackagePublishingHistory,
    SecureBinaryPackagePublishingHistory)


class TestCopyPackageScript(LaunchpadZopelessTestCase):
    """Test the copy-package.py script."""

    def runCopyPackage(self, extra_args=[]):
        """Run copy-package.py, returning the result and output.
        Returns a tuple of the process's return code, stdout output and
        stderr output."""
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
                        '--to-suite', 'breezy-autotest', '-b'])
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
        # 'mozilla-firefox' source produced 2 binaries.
        self.assertEqual(num_bin_pub + 2, num_bin_pub_after)


class TestCopyPackage(LaunchpadZopelessTestCase):
    """Test the CopyPackageHelper class."""

    class QuietLogger:
        """A logger that doesn't log anything.  Useful where you need to
        provide a logger object but don't actually want any output."""
        def debug(self, args):
            pass
        def info(self, args):
            pass
        def error(self, args):
            pass

    def getCopier(self, sourcename='mozilla-firefox', sourceversion=None,
                  from_suite='warty', to_suite='hoary',
                  from_distribution_name='ubuntu',
                  confirm_all=True, include_binaries=True):
        """Return a PackageCopier instance.

        Allow tests to use a set of default options and pass an
        inactive logger to PackageCopier.
        """
        test_args=['-s', from_suite,
                   '--to-suite', to_suite,
                   '-d', from_distribution_name ]
        if confirm_all:
            test_args.append('-y')
        if include_binaries:
            test_args.append('-b')
        if sourceversion is not None:
            test_args.extend(['-e', sourceversion])

        test_args.append(sourcename)

        copier = PackageCopier(name='copy-package', test_args=test_args)
        copier.logger = self.QuietLogger()
        return copier

    def testSimpleAction(self):
        """Check how CopyPackageHelper behaves on a successful copy."""
        copy_helper = self.getCopier()

        (from_location, to_location, from_source, from_binaries,
            copied_source, copied_binaries) = copy_helper.doCopy()

        # Check locations.  They should be the same as the defaults defined
        # in the getCopier method.
        self.assertEqual(str(from_location), 'ubuntu/warty/RELEASE')
        self.assertEqual(str(to_location), 'ubuntu/hoary/RELEASE')

        # Check target source title - this should be the package name in
        # the sample data for our source package.
        self.assertEqual(from_source.title,
            u'mozilla-firefox 0.9 (source) in ubuntu warty')

        # Check target binaries.  The default source we're using
        # (mozilla-firefox) only has one binary and we're checking its title
        # to be as expected.
        target_binary = from_binaries[0]
        self.assertEqual(
            target_binary.title,
            u'mozilla-firefox 0.9 (i386 binary) in ubuntu warty')

        # Check stored results.  The copied_source should be valid and
        # the number of binaries copied should be four (2 binaries in 2
        # architectures).
        self.assertEqual(bool(copied_source), True)
        self.assertEqual(len(copied_binaries), 4)

        # Inspect copied source, its title should be the same as the original
        # source.
        self.assertEqual(
            copied_source.title,
            u'mozilla-firefox 0.9 (source) in ubuntu hoary')

        # Inspect copied binary, its title should be the same as the original
        # binary.
        copied_binary = copied_binaries[0]
        self.assertEqual(
            copied_binary.title,
            u'mozilla-firefox 0.9 (i386 binary) in ubuntu hoary')

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
        """Check if it raises when the target source can't be found."""
        copy_helper = self.getCopier(sourcename='zaphod')

        self.assertRaisesWithContent(
            PackageCopyError,
            "Could not find any version of 'zaphod' in ubuntu/warty/RELEASE",
            copy_helper.doCopy)

    def testBadDistro(self):
        """Check if it raises if the distro is invalid."""
        copy_helper = self.getCopier(from_distribution_name="beeblebrox")

        self.assertRaisesWithContent(
            PackageLocationError,
            "Could not find distribution 'beeblebrox'",
            copy_helper.doCopy)

    def testBadSuite(self):
        """Check that it fails when specifying a bad distro release."""
        copy_helper = self.getCopier(from_suite="slatibartfast")

        self.assertRaisesWithContent(
            PackageLocationError,
            "Could not find suite 'slatibartfast'",
            copy_helper.doCopy)

    def testFailIfSameLocations(self):
        """It fails if the source and destination locations are the same."""
        copy_helper = self.getCopier(from_suite='warty', to_suite='warty')

        self.assertRaisesWithContent(
            PackageCopyError,
            "Can not sync between the same locations: 'ubuntu/warty/RELEASE'"
            " to 'ubuntu/warty/RELEASE'",
            copy_helper.doCopy)

    def testFailIfValidPackageButNotInSpecifiedSuite(self):
        """It fails if the package is not published in the source location."""
        copy_helper = self.getCopier(from_suite="breezy-autotest")

        self.assertRaisesWithContent(
            PackageCopyError,
            "Could not find 'mozilla-firefox/None' in"
            " ubuntu/breezy-autotest/RELEASE",
            copy_helper.doCopy)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
