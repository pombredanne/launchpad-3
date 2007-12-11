# Copyright 2004-2006 Canonical Ltd.  All rights reserved.
#
"""Tests for domination.py."""

__metaclass__ = type

import datetime
import pytz
import unittest

from canonical.archivepublisher.domination import Dominator
from canonical.archivepublisher.publishing import Publisher
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.interfaces import (
    DistroSeriesStatus, PackagePublishingStatus)
from canonical.launchpad.tests.test_publishing import TestNativePublishingBase


class TestDominator(TestNativePublishingBase):
    """Test Dominator class."""

    def createSimpleDominationContext(self):
        """Create simple domination context.

        Creates source and binary publications for:

         * Dominated: foo_1.0 & foo-bin_1.0_i386
         * Dominant: foo_1.1 & foo-bin_1.1_i386

        Return the corresponding 'secure' records as a 4-tuple:

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

        dominant_source = self.getSecureSource(foo_11_source)
        dominant_binaries = [self.getSecureBinary(pub)
                             for pub in foo_11_binaries]

        dominated_source = self.getSecureSource(foo_10_source)
        dominated_binaries = [self.getSecureBinary(pub)
                              for pub in foo_10_binaries]

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

        dominator._dominateSource(source_input)
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

    def testEmptySourceDomination(self):
        """Source domination asserts for not empty input list."""
        dominator = Dominator(self.logger, self.ubuntutest.main_archive)
        source_input = {'foo': []}
        self.assertRaises(
            AssertionError, dominator._dominateSource, source_input)

    def testBinariesDomination(self):
        """Test overall binary domination procedure."""
        dominator = Dominator(self.logger, self.ubuntutest.main_archive)

        [dominant_source, dominant, dominated_source,
         dominated] = self.createSimpleDominationContext()

        # See comment about domination input format and ordering above.
        binary_input = {'foo-bin': [dominant, dominated]}

        dominator._dominateBinaries(binary_input)
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

    def testEmptyBinaryDomination(self):
        """Binaries domination asserts not empty input list."""
        dominator = Dominator(self.logger, self.ubuntutest.main_archive)
        binary_input = {'foo-bin': []}
        self.assertRaises(
            AssertionError, dominator._dominateBinaries, binary_input)

    def testBinaryDomination(self):
        """Test binary domination unit procedure."""
        dominator = Dominator(self.logger, self.ubuntutest.main_archive)

        [dominant_source, dominant, dominated_source,
         dominated] = self.createSimpleDominationContext()

        dominator._dominateBinary(dominated, dominant)
        flush_database_updates()

        dominated  = self.checkBinaryPublication(
            dominated, PackagePublishingStatus.SUPERSEDED)
        self.assertEqual(
            dominated.supersededby, dominant.binarypackagerelease.build)
        self.checkPastDate(dominated.datesuperseded)

    def testBinaryDominationAssertsPendingOrPublished(self):
        """Test binary domination asserts coherent dominated status.

        Normally _dominateBinary only accepts domination candidates in
        PUBLISHED or PENDING status, a exception is opened for architecture
        independent binaries because during the iteration they might have
        been already SUPERSEDED with its first publication, when it happens
        the candidate is skipped, i.e. it's not dominated again.

        (remembering the architecture independent binaries get superseded
        atomically)
        """
        dominator = Dominator(self.logger, self.ubuntutest.main_archive)

        [dominant_source, dominant, dominated_source,
         dominated] = self.createSimpleDominationContext()

        # Let's modify the domination candidate, so it will look wrong to
        # _dominateBinary which will raise because it's a architecture
        # specific binary publication not in PENDING or PUBLISHED state.
        dominated.status = PackagePublishingStatus.SUPERSEDED
        manual_domination_date = datetime.datetime(
            2006, 12, 25, tzinfo=pytz.timezone("UTC"))
        dominated.datesuperseded = manual_domination_date
        flush_database_updates()

        # An error like that in production clearly indicates that something
        # is wrong in the Dominator look-up methods.
        self.assertRaises(
            AssertionError, dominator._dominateBinary, dominated, dominant)

        # The refused publishing record remains the same.
        dominated  = self.checkBinaryPublication(
            dominated, PackagePublishingStatus.SUPERSEDED)
        self.assertEqual(dominated.datesuperseded, manual_domination_date)

        # Let's make it a architecture independent binary, so the domination
        # can be executed, but the record will be skipped.
        dominated.binarypackagerelease.architecturespecific = False
        flush_database_updates()

        dominator._dominateBinary(dominated, dominant)
        flush_database_updates()
        dominated  = self.checkBinaryPublication(
            dominated, PackagePublishingStatus.SUPERSEDED)
        self.assertEqual(dominated.datesuperseded, manual_domination_date)

    def testOtherBinaryPublications(self):
        """Check the basis of architecture independent binary domination.

        We use _getOtherBinaryPublications to identify other publications of
        the same binarypackagerelease in other architectures (architecture
        independent binaries), they will be dominated during a single step.

        See overall details in `testDominationOfOldArchIndepBinaries`.
        """
        dominator = Dominator(self.logger, self.ubuntutest.main_archive)

        # Create architecture independent publications for foo-bin_1.0
        # in i386 & hppa.
        pub_source_archindep = self.getPubSource(
            version='1.0', status=PackagePublishingStatus.PUBLISHED,
            architecturehintlist='all')
        pub_binaries_archindep = self.getPubBinaries(
            pub_source=pub_source_archindep,
            status=PackagePublishingStatus.PUBLISHED)
        [hppa_pub, i386_pub] = pub_binaries_archindep

        # Manually supersede the hppa binary.
        secure_hppa_pub = self.getSecureBinary(hppa_pub)
        secure_hppa_pub.status = PackagePublishingStatus.SUPERSEDED
        flush_database_updates()

        # Check if we can reach the i386 publication using
        # _getOtherBinaryPublications over the hppa binary.
        [found] = list(dominator._getOtherBinaryPublications(secure_hppa_pub))
        self.assertEqual(self.getSecureBinary(i386_pub), found)

        # Create architecture specific publications for foo-bin_1.1 in
        # i386 & hppa.
        pub_source_archdep = self.getPubSource(
            version='1.1', status=PackagePublishingStatus.PUBLISHED,
            architecturehintlist='any')
        pub_binaries_archdep = self.getPubBinaries(
            pub_source=pub_source_archdep)
        [hppa_pub, i386_pub] = pub_binaries_archdep

        # Manually supersede the hppa publication.
        secure_hppa_pub = self.getSecureBinary(hppa_pub)
        secure_hppa_pub.status = PackagePublishingStatus.SUPERSEDED
        flush_database_updates()

        # Check if there is no other publication of the hppa binary package
        # release.
        self.assertEqual(
            dominator._getOtherBinaryPublications(secure_hppa_pub).count(),
            0)

    def testDominationOfOldArchIndepBinaries(self):
        """Check domination of architecture independent binaries.

        When a architecture independent binary is dominated it should also
        'carry' the same publications in other architectures independently
        of whether or not the new binary was successfully built to a specific
        architecture.

        See bug #48760 for further information about this aspect.
        """
        publisher = Publisher(
            self.logger, self.config, self.disk_pool,
            self.ubuntutest.main_archive)

        # Create published archindep context.
        pub_source_archindep = self.getPubSource(
            version='1.0', status=PackagePublishingStatus.PUBLISHED,
            architecturehintlist='all')
        pub_binaries_archindep = self.getPubBinaries(
            pub_source=pub_source_archindep,
            status=PackagePublishingStatus.PUBLISHED)

        # Emulated new publication of a archdep binary only on i386.
        pub_source_archdep = self.getPubSource(
            version='1.1', architecturehintlist='i386')
        pub_binaries_archdep = self.getPubBinaries(
            pub_source=pub_source_archdep)

        publisher.A_publish(False)
        publisher.B_dominate(False)

        # The latest architecture specific source and binary pair is
        # PUBLISHED.
        self.checkPublications(
            pub_source_archdep, pub_binaries_archdep,
            PackagePublishingStatus.PUBLISHED)

        # The oldest architecture independent source & binaries should
        # be SUPERSEDED, i.e., the fact that new source version wasn't
        # built for hppa should not hold the condemned architecture
        # independent binary.
        self.checkPublications(
            pub_source_archindep, pub_binaries_archindep,
            PackagePublishingStatus.SUPERSEDED)


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
            DistroSeriesStatus.OBSOLETE)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

