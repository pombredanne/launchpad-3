# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the ppa-add-missing-builds.py script. """

import os
import subprocess
import sys
import unittest

from zope.component import getUtility

from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.scripts.expire_ppa_binaries import PPABinaryExpirer
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory

from canonical.config import config
from canonical.database.sqlbase import (
    flush_database_updates, clear_current_connection_cache, cursor)
from canonical.launchpad.scripts import QuietFakeLogger
from canonical.testing.layers import LaunchpadZopelessLayer


class TestPPAAddMissingBuilds(TestCaseWithFactory):
    """Test the ppa-add-missing-builds.py script. """

    layer = LaunchpadZopelessLayer
    dbuser = config.builddmaster.dbuser

    def setUp(self):
        """Make a PPA and publish some sources that need builds."""
        TestCaseWithFactory.setUp(self)
        self.stp = SoyuzTestPublisher()
        self.stp.prepareBreezyAutotest()

        # i386 and hppa are enabled by STP but we need to mark hppa as
        # PPA-enabled.
        self.stp.breezy_autotest_hppa.supports_virtualized = True

        # Create an arch-any and an arch-all source in a PPA.
        self.ppa = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
        self.all = self.stp.getPubSource(
            sourcename="all", architecturehintlist="all", archive=self.ppa)
        self.any = self.stp.getPubSource(
            sourcename="any", architecturehintlist="any", archive=self.ppa)

    def runScript(self, test_args=None):
        """Run the script itself, returning the result and output.

        Return a tuple of the process's return code, stdout output and
        stderr output.
        """
        if test_args is None:
            test_args = []
        script = os.path.join(
            config.root, "scripts", "ppa-add-missing-builds.py")
        args = [sys.executable, script]
        args.extend(test_args)
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return (process.returncode, stdout, stderr)

    def testSimpleRun(self):
        """Try a simple script run.

        This test ensures that the script starts up and runs.
        It should create some missing builds.
        """
        # Commit the changes made in setUp()
        self.layer.txn.commit()

        args = [
            "-d", "ubuntutest",
            "-s", "breezy-autotest",
            "-a", "i386",
            "-a", "hppa",
            "--owner", "%s" % self.ppa.owner.name,
            ]
        code, stdout, stderr = self.runScript(args)
        self.assertEqual(
            code, 0,
            "The script returned with a non zero exit code: %s\n%s\n%s"  % (
                code, stdout, stderr))

        # Sync database changes made.
        flush_database_updates()
        clear_current_connection_cache()

        any_build_i386 = self.any.sourcepackagerelease.getBuildByArch(
            self.stp.breezy_autotest_i386, self.ppa)
        any_build_hppa = self.any.sourcepackagerelease.getBuildByArch(
            self.stp.breezy_autotest_hppa, self.ppa)
        self.assertIsNot(any_build_i386, None)
        self.assertIsNot(any_build_hppa, None)
