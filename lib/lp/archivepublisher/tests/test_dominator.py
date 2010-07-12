# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for domination.py."""

__metaclass__ = type

import datetime
import unittest

from zope.component import getUtility

from lp.archivepublisher.domination import Dominator
from lp.archivepublisher.publishing import Publisher
from canonical.database.sqlbase import flush_database_updates
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.tests.test_publishing import TestNativePublishingBase


class TestDominator(TestNativePublishingBase):
    """Test Dominator class."""

    def createSimpleDominationContext(self):
        """Create simple domination context.

        Creates source and binary publications for:

         * Dominated: foo_1.0 & foo-bin_1.0_i386
         * Dominant: foo_1.1 & foo-bin_1.1_i386

        Return the corresponding publication records as a 4-tuple:

         (dominant_source, dominant_binary, dominated_source,
          dominated_binary)

        Note that as an optimization the binaries list is already unpacked.
        """
        foo_10_source = self.getPubSource(
            version='1.0', architecturehintlist='i386',
            status=PackagePublishingStatus.PUBLISHED)
        foo_10_binaries = self.getPubBinaries(
            pub_source=foo_10_source,
            status=PackagePublishingStatus.PUBLISHED)

        foo_11_source = self.getPubSource(
            version='1.1', architecturehintlist='i386',
            status=PackagePublishingStatus.PUBLISHED)
        foo_11_binaries = self.getPubBinaries(
            pub_source=foo_11_source,
            status=PackagePublishingStatus.PUBLISHED)

        dominant_source = foo_11_source
        dominant_binaries = [pub for pub in foo_11_binaries]

        dominated_source = foo_10_source
        dominated_binaries = [pub for pub in foo_10_binaries]

        return (dominant_source, dominant_binaries[0],
                dominated_source, dominated_binaries[0])

    def testSourceDomination(self):
        """Test source domination procedure."""
        dominator = Dominator(self.logger, self.ubuntutest.main_archive)

        [dominant_source, dominant_binary, dominated_source,
         dominated_binary] = self.createSimpleDominationContext()

        # The _dominate* test methods require a dictionary where the source
        # package name is the key. The key's value is a list of
        # source or binary packages representing dominant, the first element
        # and dominated, the subsequents.
        source_input = {'foo': [dominant_source, dominated_source]}

        dominator._dominatePublications(source_input)
        flush_database_updates()

        # The dominant version remains correctly published.
        dominant  = self.checkSourcePublication(
            dominant_source, PackagePublishingStatus.PUBLISHED)
        self.assertTrue(dominant.supersededby is None)
        self.assertTrue(dominant.datesuperseded is None)

        # The dominated version is correctly dominated.
        dominated  = self.checkSourcePublication(
            dominated_source, PackagePublishingStatus.SUPERSEDED)
        self.assertEqual(
            dominated.supersededby, dominant.sourcepackagerelease)
        self.checkPastDate(dominated.datesuperseded)

    def testEmptyDomination(self):
        """Domination asserts for not empty input list."""
        dominator = Dominator(self.logger, self.ubuntutest.main_archive)
        pubs = {'foo': []}
        self.assertRaises(
            AssertionError, dominator._dominatePublications, pubs)

    def testBinariesDomination(self):
        """Test overall binary domination procedure."""
        dominator = Dominator(self.logger, self.ubuntutest.main_archive)

        [dominant_source, dominant, dominated_source,
         dominated] = self.createSimpleDominationContext()

        # See comment about domination input format and ordering above.
        binary_input = {'foo-bin': [dominant, dominated]}

        dominator._dominatePublications(binary_input)
        flush_database_updates()

        # Dominant version remains correctly published.
        dominant  = self.checkBinaryPublication(
            dominant, PackagePublishingStatus.PUBLISHED)
        self.assertTrue(dominant.supersededby is None)
        self.assertTrue(dominant.datesuperseded is None)

        # Dominated version is correctly dominated.
        dominated  = self.checkBinaryPublication(
            dominated, PackagePublishingStatus.SUPERSEDED)
        self.assertEqual(
            dominated.supersededby, dominant.binarypackagerelease.build)
        self.checkPastDate(dominated.datesuperseded)


class TestDomination(TestNativePublishingBase):
    """Test overall domination procedure."""

    def testCarefulDomination(self):
        """Test the careful domination procedure.

        Check if it works on a development series.
        A SUPERSEDED, DELETED or OBSOLETE published source should
        have its scheduleddeletiondate set.
        """
        publisher = Publisher(
            self.logger, self.config, self.disk_pool,
            self.ubuntutest.main_archive)

        superseded_source = self.getPubSource(
            status=PackagePublishingStatus.SUPERSEDED)
        self.assertTrue(superseded_source.scheduleddeletiondate is None)
        deleted_source = self.getPubSource(
            status=PackagePublishingStatus.DELETED)
        self.assertTrue(deleted_source.scheduleddeletiondate is None)
        obsoleted_source = self.getPubSource(
            status=PackagePublishingStatus.OBSOLETE)
        self.assertTrue(obsoleted_source.scheduleddeletiondate is None)

        # Ensure the stay of execution is 5 days.  This is so that we
        # can do a sensible check later (see comment below).
        publisher._config.stayofexecution = 5

        publisher.B_dominate(True)

        # The publishing records will be scheduled for removal.
        # DELETED and OBSOLETED publications are set to be deleted
        # immediately, whereas SUPERSEDED ones get a stay of execution
        # according to the configuration.
        deleted_source = self.checkSourcePublication(
            deleted_source, PackagePublishingStatus.DELETED)
        self.checkPastDate(deleted_source.scheduleddeletiondate)

        obsoleted_source = self.checkSourcePublication(
            obsoleted_source, PackagePublishingStatus.OBSOLETE)
        self.checkPastDate(deleted_source.scheduleddeletiondate)

        superseded_source = self.checkSourcePublication(
            superseded_source, PackagePublishingStatus.SUPERSEDED)
        self.checkPastDate(
            superseded_source.scheduleddeletiondate,
            lag=datetime.timedelta(days=publisher._config.stayofexecution))


class TestDominationOfObsoletedSeries(TestDomination):
    """Replay domination tests upon a OBSOLETED distroseries."""

    def setUp(self):
        TestDomination.setUp(self)
        self.ubuntutest['breezy-autotest'].status = (
            SeriesStatus.OBSOLETE)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
