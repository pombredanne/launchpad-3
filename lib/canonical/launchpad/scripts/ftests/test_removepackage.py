# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os
import subprocess
import sys
import unittest

from canonical.config import config
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.database.publishing import (
    SecureSourcePackagePublishingHistory,
    SecureBinaryPackagePublishingHistory)
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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
