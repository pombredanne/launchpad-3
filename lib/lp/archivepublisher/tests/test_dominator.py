# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for domination.py."""

__metaclass__ = type

import datetime

from canonical.database.sqlbase import flush_database_updates
from lp.archivepublisher.domination import Dominator, STAY_OF_EXECUTION
from lp.archivepublisher.publishing import Publisher
from lp.registry.interfaces.series import SeriesStatus
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.tests.test_publishing import TestNativePublishingBase


class TestDominator(TestNativePublishingBase):
    """Test Dominator class."""

    def createSourceAndBinaries(self, version, with_debug=False,
                                archive=None):
        """Create a source and binaries with the given version."""
        source = self.getPubSource(
            version=version, archive=archive,
            status=PackagePublishingStatus.PUBLISHED)
        binaries = self.getPubBinaries(
            pub_source=source, with_debug=with_debug,
            status=PackagePublishingStatus.PUBLISHED)
        return (source, binaries)

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
        foo_10_source, foo_10_binaries = self.createSourceAndBinaries('1.0')
        foo_11_source, foo_11_binaries = self.createSourceAndBinaries('1.1')
        return (foo_11_source, foo_11_binaries[0],
                foo_10_source, foo_10_binaries[0])

    def dominateAndCheck(self, dominant, dominated, supersededby):
        dominator = Dominator(self.logger, self.ubuntutest.main_archive)

        # The _dominate* test methods require a dictionary where the
        # package name is the key. The key's value is a list of
        # source or binary packages representing dominant, the first element
        # and dominated, the subsequents.
        pubs = {'foo': [dominant, dominated]}

        dominator._dominatePublications(pubs)
        flush_database_updates()

        # The dominant version remains correctly published.
        self.checkPublication(dominant, PackagePublishingStatus.PUBLISHED)
        self.assertTrue(dominant.supersededby is None)
        self.assertTrue(dominant.datesuperseded is None)

        # The dominated version is correctly dominated.
        self.checkPublication(dominated, PackagePublishingStatus.SUPERSEDED)
        self.assertEqual(dominated.supersededby, supersededby)
        self.checkPastDate(dominated.datesuperseded)

    def testManualSourceDomination(self):
        """Test source domination procedure."""
        [dominant_source, dominant_binary, dominated_source,
         dominated_binary] = self.createSimpleDominationContext()

        self.dominateAndCheck(
            dominant_source, dominated_source,
            dominant_source.sourcepackagerelease)

    def testManualBinaryDomination(self):
        """Test binary domination procedure."""
        [dominant_source, dominant, dominated_source,
         dominated] = self.createSimpleDominationContext()

        self.dominateAndCheck(
            dominant, dominated, dominant.binarypackagerelease.build)

    def testJudgeAndDominate(self):
        """Verify that judgeAndDominate correctly dominates everything."""
        foo_10_source, foo_10_binaries = self.createSourceAndBinaries('1.0')
        foo_11_source, foo_11_binaries = self.createSourceAndBinaries('1.1')
        foo_12_source, foo_12_binaries = self.createSourceAndBinaries('1.2')

        dominator = Dominator(self.logger, foo_10_source.archive)
        dominator.judgeAndDominate(
            foo_10_source.distroseries, foo_10_source.pocket)

        self.checkPublications(
            [foo_12_source] + foo_12_binaries,
            PackagePublishingStatus.PUBLISHED)
        self.checkPublications(
            [foo_11_source] + foo_11_binaries,
            PackagePublishingStatus.SUPERSEDED)
        self.checkPublications(
            [foo_10_source] + foo_10_binaries,
            PackagePublishingStatus.SUPERSEDED)

    def testJudgeAndDominateWithDDEBs(self):
        """Verify that judgeAndDominate ignores DDEBs correctly.

        DDEBs are superseded by their corresponding DEB publications, so they
        are forbidden from superseding publications (an attempt would result
        in an AssertionError), and shouldn't be directly considered for
        superseding either.
        """
        ppa = self.factory.makeArchive()
        foo_10_source, foo_10_binaries = self.createSourceAndBinaries(
            '1.0', with_debug=True, archive=ppa)
        foo_11_source, foo_11_binaries = self.createSourceAndBinaries(
            '1.1', with_debug=True, archive=ppa)
        foo_12_source, foo_12_binaries = self.createSourceAndBinaries(
            '1.2', with_debug=True, archive=ppa)

        dominator = Dominator(self.logger, ppa)
        dominator.judgeAndDominate(
            foo_10_source.distroseries, foo_10_source.pocket)

        self.checkPublications(
            [foo_12_source] + foo_12_binaries,
            PackagePublishingStatus.PUBLISHED)
        self.checkPublications(
            [foo_11_source] + foo_11_binaries,
            PackagePublishingStatus.SUPERSEDED)
        self.checkPublications(
            [foo_10_source] + foo_10_binaries,
            PackagePublishingStatus.SUPERSEDED)

    def testEmptyDomination(self):
        """Domination asserts for not empty input list."""
        dominator = Dominator(self.logger, self.ubuntutest.main_archive)
        pubs = {'foo': []}
        # This isn't a really good exception. It should probably be
        # something more indicative of bad input.
        self.assertRaises(
            AssertionError, dominator._dominatePublications, pubs)


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

        publisher.B_dominate(True)

        # The publishing records will be scheduled for removal.
        # DELETED and OBSOLETED publications are set to be deleted
        # immediately, whereas SUPERSEDED ones get a stay of execution
        # according to the configuration.
        self.checkPublication(
            deleted_source, PackagePublishingStatus.DELETED)
        self.checkPastDate(deleted_source.scheduleddeletiondate)

        self.checkPublication(
            obsoleted_source, PackagePublishingStatus.OBSOLETE)
        self.checkPastDate(deleted_source.scheduleddeletiondate)

        self.checkPublication(
            superseded_source, PackagePublishingStatus.SUPERSEDED)
        self.checkPastDate(
            superseded_source.scheduleddeletiondate,
            lag=datetime.timedelta(days=STAY_OF_EXECUTION))


class TestDominationOfObsoletedSeries(TestDomination):
    """Replay domination tests upon a OBSOLETED distroseries."""

    def setUp(self):
        TestDomination.setUp(self)
        self.ubuntutest['breezy-autotest'].status = (
            SeriesStatus.OBSOLETE)
