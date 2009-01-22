# Copyright 2009 Canonical Ltd.  All rights reserved.
"""Test the expire-ppa-binaries.py script. """

import pytz
import unittest

from datetime import datetime, timedelta

from zope.component import getUtility

from canonical.launchpad.interfaces import IPersonSet
from canonical.launchpad.scripts import QuietFakeLogger
from canonical.launchpad.scripts.expire_ppa_binaries import PPABinaryExpirer
from canonical.launchpad.tests.test_publishing import SoyuzTestPublisher
from canonical.testing.layers import LaunchpadZopelessLayer


class TestPPABinaryExpiry(unittest.TestCase):
    """Test the expire-ppa-binaries.py script."""

    layer = LaunchpadZopelessLayer
    dbuser = "librariangc"

    def setUp(self):
        """Set up some test publications."""
        self.stp = SoyuzTestPublisher()
        self.stp.prepareBreezyAutotest()

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
        #
        # Set up publications that match each of these conditions.

        self.now = datetime.now(pytz.UTC)
        self.under_threshold_date = self.now + timedelta(days=29)
        self.over_threshold_date = self.now + timedelta(days=31)

        self.stp.getPubBinaries(
            binaryname="pkg2", dateremoved=self.under_threshold_date)

        self.stp.getPubBinaries(
            binaryname="pkg3", dateremoved=self.over_threshold_date)

        self.stp.getPubBinaries(
            binaryname="pkg4", dateremoved=self.over_threshold_date)
        self.stp.getPubBinaries(binaryname="pkg4", dateremoved=None)

        self.stp.getPubBinaries(
            binaryname="pkg5", dateremoved=self.over_threshold_date)
        self.stp.getPubBinaries(
            binaryname="pkg5",dateremoved=self.under_threshold_date)

        self.stp.getPubBinaries(
            binaryname="pkg6", dateremoved=self.over_threshold_date)
        self.stp.getPubBinaries(
            binaryname="pkg6",dateremoved=self.over_threshold_date)

    def getScript(self):
        """Return a PPABinaryExpirer instance."""
        script = PPABinaryExpirer("test expirer")
        script.logger = QuietFakeLogger()
        script.txn = self.layer.txn
        return script

    def testNoExpirationWithNoDateremoved(self):
        """Test that no expiring happens with no dateremoved set."""
        pkg1 = self.stp.getPubSource(
            sourcename="pkg1", architecturehintlist="i386")
        [pub] = self.stp.getPubBinaries(pub_source=pkg1, dateremoved=None)

        script = self.getScript()
        script.main()

        self.assertEqual(
            pub.binarypackagerelease.files[0].libraryfile.expires, None,
            "lfa.expires should be None, but it's not.")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
