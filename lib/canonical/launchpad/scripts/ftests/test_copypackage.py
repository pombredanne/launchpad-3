# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os
import subprocess
import sys
import unittest

from canonical.config import config
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.scripts.ftpmaster import (
    PackageCopyError, CopyPackageHelper)

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
        returncode, out, err = self.runCopyPackage(
            extra_args=['-s', 'warty', 'mozilla-firefox',
                        '--to-suite', 'hoary', '-b'])
        self.assertEqual(0, returncode)


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

    def getCopyHelper(self, sourcename='mozilla-firefox', sourceversion=None,
                      from_suite='warty', to_suite='hoary',
                      from_distribution_name='ubuntu',
                      to_distribution_name='ubuntu',
                      confirm_all=True, comment='42', include_binaries=True):
        """Return an CopyHelper instance.

        Allow tests to use a set of default options and pass a inactive logger
        to CopyHelper.
        """
        logger = QuietLogger()
        return CopyPackageHelper(
            sourcename, sourceversion, from_suite, to_suite,
            from_distribution_name, to_distribution_name,
            confirm_all, comment, include_binaries, logger)

    def testSimpleAction(self):
        """Check how CopyPackageHelper behaves on a successful copy."""
        copy_helper = self.getCopyHelper()

        # Check default values.  This ensures we know that they are invalid
        # to start with and expect them to get re-populated after the copy.
        self.assertEqual(copy_helper.synced, False)
        self.assertEqual(bool(copy_helper.copied_source), False)
        self.assertEqual(len(copy_helper.copied_binaries), 0)

        copy_helper.performCopy()

        # Check locations.  They should be the same as the defaults defined
        # in the getCopyHelper method.
        self.assertEqual(
            str(copy_helper.from_location), 'ubuntu/warty/RELEASE')
        self.assertEqual(
            str(copy_helper.to_location), 'ubuntu/hoary/RELEASE')

        # Check target source title - this should be the package name in
        # the sample data for our source package.
        self.assertEqual(
            copy_helper.target_source.title,
            u'mozilla-firefox 0.9 (source) in ubuntu warty')

        # Check target binaries.  The default source we're using 
        # (mozilla-firefox) only has one binary and we're checking its title
        # to be as expected.
        target_binary = copy_helper.target_binaries[0]
        self.assertEqual(
            target_binary.title,
            u'Binary Package "mozilla-firefox" in The Warty Warthog '
            'Release for i386 (x86)')

        # Check stored results.  The data should be "synced" (written to the
        # database, the copied_source should be valid and the number of binaries
        # copied should be one.
        self.assertEqual(copy_helper.synced, True)
        self.assertEqual(bool(copy_helper.copied_source), True)
        self.assertEqual(len(copy_helper.copied_binaries), 1)

        # Inspect copied source, its title should be the same as the original
        # source.
        self.assertEqual(
            copy_helper.copied_source.title,
            u'mozilla-firefox 0.9 (source) in ubuntu hoary')

        # Inspect copied binary, its title should be the same as the original
        # binary.
        copied_binary = copy_helper.copied_binaries[0]
        self.assertEqual(
            copied_binary.title,
            u'mozilla-firefox 0.9 (i386 binary) in ubuntu hoary')

    def assertRaisesWithContent(self, 
                                exception, exception_content, func, *args):
        """Check if the given exception is raised with given content.

        If the expection isn't raised or the exception_content doesn't match
        what was raised an AssertionError is raised.
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
        copy_helper = self.getCopyHelper(sourcename='zaphod')

        self.assertRaisesWithContent(
            PackageCopyError,
            "Could not find any version of 'zaphod' in ubuntu/warty/RELEASE",
            copy_helper.performCopy)

    def testBadDistro(self):
        """Check if it raises if the distro is invalid."""
        copy_helper = self.getCopyHelper(from_distribution_name="beeblebrox")

        self.assertRaisesWithContent(
            PackageCopyError,
            "Could not find distribution 'beeblebrox'",
            copy_helper.performCopy)

    def testBadSuite(self):
        """Check that it fails when specifying a bad distro release."""
        copy_helper = self.getCopyHelper(from_suite="slatibartfast")

        self.assertRaisesWithContent(
            PackageCopyError,
            "Could not find suite 'slatibartfast'",
            copy_helper.performCopy)

    def testFailIfSameLocations(self):
        """Check that it fails if the source and destination package locations
        are the same."""
        copy_helper = self.getCopyHelper(from_suite='warty', to_suite='warty')

        self.assertRaisesWithContent(
            PackageCopyError, 
            "Can not sync between the same locations: 'ubuntu/warty/RELEASE' to 'ubuntu/warty/RELEASE'",
            copy_helper.performCopy)

    def testFailIfValidPackageButNotInSpecifiedSuite(self):
        """Check that we fail if the package is valid but does not exist in the
        specified distro release."""
        copy_helper = self.getCopyHelper(from_suite="breezy-autotest")

        self.assertRaisesWithContent(
            PackageCopyError,
            "Could not find 'mozilla-firefox/None' in ubuntu/breezy-autotest/RELEASE",
            copy_helper.performCopy)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
