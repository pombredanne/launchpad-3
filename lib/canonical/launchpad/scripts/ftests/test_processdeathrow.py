# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functional tests for process-death-row.py script.

See lib/canonical/launchpad/doc/deathrow.txt for more detailed tests
of the module functionality; here we just aim to test that the script
processes its arguments and handles dry-run correctly.

"""

__metaclass__ = type

import datetime
import os
import shutil
import subprocess
import sys
from tempfile import mkdtemp
from unittest import TestCase, TestLoader

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.database import SecureSourcePackagePublishingHistory
from canonical.launchpad.interfaces import IDistributionSet
from canonical.lp.dbschema import PackagePublishingStatus
from canonical.testing import LaunchpadZopelessLayer

class TestProcessDeathRow(TestCase):
    """Test the process-death-row.py script works properly."""

    layer = LaunchpadZopelessLayer

    def runDeathRow(self, extra_args, distribution="ubuntutest"):
        """Run process-death-row.py, returning the result and output."""
        script = os.path.join(config.root, "scripts", "process-death-row.py")
        args = [sys.executable, script, "-v", "-d", "ubuntutest",
                "-p", self.test_folder]
        args.extend(extra_args)
        process = subprocess.Popen(args,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return (process.returncode, stdout, stderr)

    def setUp(self):
        """Set up for a test death row run."""
        # Set up our archive folder, and put a fake source package file in it.
        self.test_folder = mkdtemp()
        package_folder = os.path.join(
            self.test_folder, "main", "a", "alsa-utils")
        os.makedirs(package_folder)
        self.package_path = os.path.join(
            package_folder, "alsa-utils_1.0.9a-4.dsc")
        f = open(self.package_path, "w")
        f.write("This is some test file contents")
        f.close()

        # Set up the related publishing records so that death row processing
        # will want to delete the file. We do this by locating all publishing
        # records for our package in ubuntutest and setting them all to
        # PENDINGREMOVAL.
        ubuntutest = getUtility(IDistributionSet)["ubuntutest"]
        ut_alsautils = ubuntutest.getSourcePackage("alsa-utils")
        ut_alsautils_109a4 = ut_alsautils.getVersion("1.0.9a-4")
        pubrecs = ut_alsautils_109a4.publishing_history

        # We remember which records we put into pending removal, so
        # we can later check whether or not they were changed.
        self.pubrec_ids = []

        for pubrec in pubrecs:
            # These are spph (view) records, we need to grab the matching
            # sspphs (actual table) records in order to update them.
            sspph = SecureSourcePackagePublishingHistory.get(pubrec.id)
            sspph.status = PackagePublishingStatus.PENDINGREMOVAL
            sspph.dateremoved = None
            sspph.scheduledremovaldate = datetime.datetime(1999, 1, 1)

            self.pubrec_ids.append(pubrec.id)

        # Commit so script can see our publishing record changes.
        self.layer.txn.commit()

    def tearDown(self):
        """Clean up after ourselves."""
        shutil.rmtree(self.test_folder)

    def testDryRun(self):
        """Test we don't delete the file or change the db in dry run mode."""
        self.runDeathRow(["-n"])
        self.assertTrue(os.path.exists(self.package_path))
        for pubrec_id in self.pubrec_ids:
            sspph = SecureSourcePackagePublishingHistory.get(pubrec_id)
            self.assertEqual(
                sspph.status, PackagePublishingStatus.PENDINGREMOVAL)

    def testWetRun(self):
        """Test we do delete the file and change the db in wet run mode."""
        self.runDeathRow([])
        self.assertFalse(os.path.exists(self.package_path))
        for pubrec_id in self.pubrec_ids:
            sspph = SecureSourcePackagePublishingHistory.get(pubrec_id)
            self.assertEqual(
                sspph.status, PackagePublishingStatus.REMOVED)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
