# Copyright 2009 Canonical Ltd.  All rights reserved.
"""Test the expire-ppa-binaries.py script. """

import pytz
import unittest

from datetime import datetime, timedelta

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces import IDistributionSet, IPersonSet
from canonical.launchpad.scripts import QuietFakeLogger
from canonical.launchpad.scripts.expire_ppa_binaries import PPABinaryExpirer
from canonical.launchpad.tests.test_publishing import SoyuzTestPublisher
from canonical.testing.layers import LaunchpadZopelessLayer


class TestPPABinaryExpiry(unittest.TestCase):
    """Test the expire-ppa-binaries.py script."""

    layer = LaunchpadZopelessLayer
    dbuser = config.binaryfile_expire.dbuser

    # We need to test several cases are handled properly:
    #  - publications with no "dateremoved" are not expired
    #  - publications with dateremoved <= 30 days ago are not expired
    #  - publications with dateremoved > 30 days ago are expired
    #  - publications with dateremoved > 30 days ago but refer to a
    #     binary published elsewhere with no dateremoved are not
    #     expired
    #  - publications with dateremoved > 30 days ago but refer to a
    #    binary published elsewhere with dateremoved <= 30 days ago
    #    are not expired
    #  - publications with dateremoved > 30 days ago but refer to a
    #    binary published elsewhere with dateremoved > 30 days ago
    #    are expired.

    def setUp(self):
        """Set up some test publications."""
        # Configure the test publisher.
        self.layer.switchDbUser("launchpad")
        self.stp = SoyuzTestPublisher()
        self.stp.prepareBreezyAutotest()

        # Prepare some date properties for the tests to use.
        self.now = datetime.now(pytz.UTC)
        self.under_threshold_date = self.now - timedelta(days=29)
        self.over_threshold_date = self.now - timedelta(days=31)

        # Prepare two PPAs for the tests to use.
        cprov = getUtility(IPersonSet).getByName('cprov')
        self.ppa = cprov.archive
        sabdfl = getUtility(IPersonSet).getByName('sabdfl')
        self.ppa2 = sabdfl.archive

    def getScript(self, test_args=None):
        """Return a PPABinaryExpirer instance."""
        if test_args is None:
            test_args = []
        script = PPABinaryExpirer("test expirer", test_args=test_args)
        script.logger = QuietFakeLogger()
        script.txn = self.layer.txn
        return script

    def runScript(self):
        """Run the expiry script and return."""
        script = self.getScript()
        self.layer.txn.commit()
        self.layer.switchDbUser(self.dbuser)
        script.main()

    def assertExpired(self, publication):
        self.assertNotEqual(
            publication.binarypackagerelease.files[0].libraryfile.expires,
            None,
            "lfa.expires should be set, but it's not.")

    def assertNotExpired(self, publication):
        self.assertEqual(
            publication.binarypackagerelease.files[0].libraryfile.expires,
            None,
            "lfa.expires should be None, but it's not.")

    def testNoExpirationWithNoDateremoved(self):
        """Test that no expiring happens if no dateremoved set."""
        pkg1 = self.stp.getPubSource(
            sourcename="pkg1", architecturehintlist="i386", archive=self.ppa)
        [pub] = self.stp.getPubBinaries(
            pub_source=pkg1, dateremoved=None, archive=self.ppa)

        self.runScript()
        self.assertNotExpired(pub)

    def testNoExpirationWithDateUnderThreshold(self):
        """Test no expiring if dateremoved too recent."""
        pkg2 = self.stp.getPubSource(
            sourcename="pkg2", architecturehintlist="i386", archive=self.ppa)
        [pub] = self.stp.getPubBinaries(
            pub_source=pkg2, dateremoved=self.under_threshold_date,
            archive=self.ppa)

        self.runScript()
        self.assertNotExpired(pub)

    def testExpirationWithDateOverThreshold(self):
        """Test expiring works if dateremoved old enough."""
        pkg3 = self.stp.getPubSource(
            sourcename="pkg3", architecturehintlist="i386", archive=self.ppa)
        [pub] = self.stp.getPubBinaries(
            pub_source=pkg3, dateremoved=self.over_threshold_date,
            archive=self.ppa)

        self.runScript()
        self.assertExpired(pub)

    def testNoExpirationWithDateOverThresholdAndOtherValidPublication(self):
        """Test no expiry if dateremoved old enough but other publication."""
        pkg4 = self.stp.getPubSource(
            sourcename="pkg4", architecturehintlist="i386", archive=self.ppa)
        [pub] = self.stp.getPubBinaries(
            pub_source=pkg4, dateremoved=self.over_threshold_date,
            archive=self.ppa)
        [other_binary] = pub.copyTo(
            pub.distroarchseries.distroseries, pub.pocket, self.ppa2)
        other_binary.secure_record.dateremoved = None

        self.runScript()
        self.assertNotExpired(pub)

    def testNoExpirationWithDateOverThresholdAndOtherPubUnderThreshold(self):
        """Test no expiring.
        
        Test no expiring if dateremoved old enough but other publication
        not over date threshold.
        """
        pkg5 = self.stp.getPubSource(
            sourcename="pkg5", architecturehintlist="i386", archive=self.ppa)
        [pub] = self.stp.getPubBinaries(
            pub_source=pkg5, dateremoved=self.over_threshold_date,
            archive=self.ppa)
        [other_binary] = pub.copyTo(
            pub.distroarchseries.distroseries, pub.pocket, self.ppa2)
        other_binary.secure_record.dateremoved = self.under_threshold_date

        self.runScript()
        self.assertNotExpired(pub)

    def _setUpExpirablePublications(self, archive=None):
        """Helper to set up two publications that are both expirable."""
        if archive is None:
            archive = self.ppa
        pkg5 = self.stp.getPubSource(
            sourcename="pkg5", architecturehintlist="i386", archive=archive)
        [pub] = self.stp.getPubBinaries(
            pub_source=pkg5, dateremoved=self.over_threshold_date,
            archive=archive)
        [other_binary] = pub.copyTo(
            pub.distroarchseries.distroseries, pub.pocket, self.ppa2)
        other_binary.secure_record.dateremoved = self.over_threshold_date
        return pub

    def testNoExpirationWithDateOverThresholdAndOtherPubOverThreshold(self):
        """Test expiring works.
        
        Test expiring works if dateremoved old enough and other publication
        is over date threshold.
        """
        pub = self._setUpExpirablePublications()
        self.runScript()
        self.assertExpired(pub)

    def testBlacklistingWorks(self):
        """Test that blacklisted PPAs are not expired."""
        pub = self._setUpExpirablePublications()
        script = self.getScript()
        script.blacklist = ["cprov",]
        self.layer.txn.commit()
        self.layer.switchDbUser(self.dbuser)
        script.main()
        self.assertNotExpired(pub)

    def testPrivatePPAsNotExpired(self):
        """Test that private PPAs are not expired."""
        self.ppa.private = True
        self.ppa.buildd_secret = "foo"
        pub = self._setUpExpirablePublications()
        self.runScript()
        self.assertNotExpired(pub)

    def testDryRun(self):
        """Test that when dryrun is specified, nothing is expired."""
        pub = self._setUpExpirablePublications()
        # We have to commit here otherwise when the script aborts it
        # will remove the test publications we just created.
        self.layer.txn.commit()
        script = self.getScript(['--dry-run'])
        self.layer.switchDbUser(self.dbuser)
        script.main()
        self.assertNotExpired(pub)

    def testDoesNotAffectNonPPA(self):
        """Test that expiry does not happen for non-PPA publications."""
        ubuntu_archive = getUtility(IDistributionSet)['ubuntu'].main_archive
        pub = self._setUpExpirablePublications(ubuntu_archive)
        self.runScript()
        self.assertNotExpired(pub)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
