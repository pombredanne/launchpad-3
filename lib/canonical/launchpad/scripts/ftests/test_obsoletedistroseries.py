# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os
import subprocess
import sys
import unittest

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.ftests.soyuz import SoyuzTestHelper
from canonical.launchpad.scripts import FakeLogger
from canonical.launchpad.scripts.ftpmaster import (
    PackageLocationError, ObsoleteDistroseries, SoyuzScriptError)
from canonical.launchpad.database.publishing import (
    SecureSourcePackagePublishingHistory,
    SecureBinaryPackagePublishingHistory)
from canonical.launchpad.interfaces import (
    DistroSeriesStatus, IDistributionSet, PackagePublishingStatus)


class TestObsoleteDistroseriesScript(LaunchpadZopelessTestCase):
    """Test the obsolete-distroseries.py script."""

    def runCopyPackage(self, extra_args=None):
        """Run obsolete-distroseries.py, returning the result and output.
        Returns a tuple of the process's return code, stdout output and
        stderr output."""
        if extra_args is None:
            extra_args = []
        script = os.path.join(
            config.root, "scripts", "ftpmaster-tools",
            "obsolete-distroseries.py")
        args = [sys.executable, script, '-y']
        args.extend(extra_args)
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return (process.returncode, stdout, stderr)

    def testSimpleRun(self):
        """Try a simple obsolete-distroseries.py run.

        This test purely ensures that the script starts up and runs.
        We'll try and obsolete a non-obsolete distroseries, so it will
        just exit without doing anything.
        """
        returncode, out, err = self.runCopyPackage(extra_args=['-s', 'warty'])
        # Need to print these or you can't see what happened if the
        # return code is bad:
        self.assertEqual(1, returncode)
        expected = "ERROR   warty is not at status OBSOLETE."
        assert expected in err, (
            "Expected %s, got %s" % (expected, err))


class TestObsoleteDistroseries(LaunchpadZopelessTestCase):
    """Test the ObsoleteDistroseries class."""

    def setUp(self):
        """Set up test data common to all test cases."""
        LaunchpadZopelessTestCase.setUp(self)

        self.warty = getUtility(IDistributionSet)['ubuntu']['warty']

        # Re-process the returned list otherwise it ends up being a list
        # of zope proxy objects that sqlvalues cannot deal with.
        self.main_archive_ids = [
            id for id in self.warty.distribution.all_distro_archive_ids]

        #self.setupBreezy()

    def setupBreezy(self):
        """Create a fresh distroseries in ubuntu.

        Use *initialiseFromParent* procedure to create 'breezy'
        on ubuntu based on the last 'breezy-autotest'.

        Also sets 'changeslist' and 'nominatedarchindep' properly.
        """
        self.ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        bat = self.ubuntu['breezy-autotest']
        self.breezy = getUtility(IDistroSeriesSet).new(
            self.ubuntu, 'breezy', 'Breezy Badger',
            'The Breezy Badger', 'Black and White', 'Someone',
            '5.10', bat, bat.owner)
        breezy_i386 = self.breezy.newArch(
            'i386', bat['i386'].processorfamily, True, self.breezy.owner)
        self.breezy.nominatedarchindep = breezy_i386
        self.breezy.initialiseFromParent()

    def getObsoleter(self, suite='warty', distribution='ubuntu',
                     confirm_all=True):
        """Return an ObsoleteDistroseries instance.

        Allow tests to use a set of default options and pass an
        inactive logger to ObsoleteDistroseries
        """
        test_args=['-s', suite,
                   '-d', distribution,
                  ]

        if confirm_all:
            test_args.append('-y')

        obsoleter = ObsoleteDistroseries(
            name='obsolete-distroseries', test_args=test_args)
        # Swallow all log messages.
        obsoleter.logger = FakeLogger()
        def message(self, prefix, *stuff, **kw):
            pass
        obsoleter.logger.message = message
        obsoleter.setupLocation()
        return obsoleter

    def testNonObsoleteDistroseries(self):
        """Test running over a non-obsolete distroseries."""
        # Default to warty, which is not obsolete.
        self.assertTrue(warty.status != PackagePublishingStatus.OBSOLETE)
        obsoleter = self.getObsoleter(suite='warty')
        self.assertRaises(SoyuzScriptError, obsoleter.mainTask)

    def testNothingToDoCase(self):
        """When there is nothing to, we expect an exception."""
        obsoleter = self.getObsoleter()
        self.warty.status = DistroSeriesStatus.OBSOLETE

        # Get all the published sources in warty.
        published_sources = SecureSourcePackagePublishingHistory.select("""
            distroseries = %s AND
            status = %s AND
            archive IN %s
            """ % sqlvalues(self.warty, PackagePublishingStatus.PUBLISHED,
                            self.main_archive_ids))
        published_binaries = SecureBinaryPackagePublishingHistory.select("""
            SecureBinaryPackagePublishingHistory.distroarchseries =
                DistroArchSeries.id AND
            DistroArchseries.DistroSeries = DistroSeries.id AND
            DistroSeries.id = %s AND
            SecureBinaryPackagePublishingHistory.status = %s AND
            SecureBinaryPackagePublishingHistory.archive IN %s
            """ % sqlvalues(self.warty, PackagePublishingStatus.PUBLISHED,
                            self.main_archive_ids),
            clauseTables=["DistroArchSeries", "DistroSeries"])

        # Reset their status to OBSOLETE.
        for package in published_sources:
            package.status = PackagePublishingStatus.OBSOLETE
        for package in published_binaries:
            package.status = PackagePublishingStatus.OBSOLETE

        # Call the script and ensure it does nothing.
        self.layer.txn.commit()
        self.assertRaises(SoyuzScriptError, obsoleter.mainTask)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
