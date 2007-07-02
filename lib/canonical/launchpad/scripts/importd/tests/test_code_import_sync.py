# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test cases for canonical.launchpad.scripts.importd.code_import_sync."""

__metaclass__ = type
__all__ = ['test_suite']


import logging
import unittest

from zope.component import getUtility

from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.database import CodeImport, ProductSeries
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.interfaces import (
    IBranchSet, IProductSet)
from canonical.launchpad.scripts.importd.code_import_sync import CodeImportSync
from canonical.launchpad.utilities import LaunchpadCelebrities
from canonical.lp.dbschema import ImportStatus, RevisionControlSystems

class TestCodeImportSync(LaunchpadZopelessTestCase):

    def setUp(self):
        self.cleanUpSampleData()
        self.code_import_sync = CodeImportSync(logging, self.layer.txn)

    def cleanUpSampleData(self):
        """Clear out the sample data that would affect tests."""
        all_import_series = ProductSeries.select("importstatus IS NOT NULL")
        for import_series in all_import_series:
            import_series.deleteImport()
        all_code_imports = CodeImport.select()
        for code_import in all_code_imports:
            code_import.destroySelf()

    def createTestingSeries(self, product, name):
        """Create an import series in with TESTING importstatus."""
        series = product.newSeries(product.owner, name, name)
        series.importstatus = ImportStatus.TESTING
        series.rcstype = RevisionControlSystems.SVN
        series.svnrepository = 'svn://example.com/' + name
        return series

    def createImportBranch(self, series):
        """Create an import branch and associate it to an import series."""
        vcs_imports = LaunchpadCelebrities().vcs_imports
        branch = getUtility(IBranchSet).new(
            series.name, vcs_imports, series.product, None)
        series.import_branch = branch
        return branch

    def testGetImportSeriesEmpty(self):
        # If there is no series with importstatus set, getImportSeries gives an
        # empty iterable. This would never happen in real life.
        self.assertEqual(list(self.code_import_sync.getImportSeries()), [])

    def testGetImportSeries(self):
        # getImportSeries should select all ProductSeries whose importstatus is
        # TESTING, AUTOTESTED, PROCESSING, SYNCING or STOPPED. ProductSeries
        # whose status is DONTSYNC or TESTFAILED are ignored.
        firefox = getUtility(IProductSet).getByName('firefox')

        # Create a series with importstatus = TESTING
        testing = self.createTestingSeries(firefox, 'testing')

        # Create a series with importstatus = TESTFAILED
        testfailed = self.createTestingSeries(firefox, 'testfailed')
        testfailed.markTestFailed()

        # Create a series with importstatus = AUTOTESTED
        autotested = self.createTestingSeries(firefox, 'autotested')
        autotested.importstatus = ImportStatus.AUTOTESTED

        # Create a series with importstatus = DONTSYNC
        dontsync = self.createTestingSeries(firefox, 'dontsync')
        dontsync.markDontSync()

        # Create a series with importstatus = PROCESSING
        processing = self.createTestingSeries(firefox, 'processing')
        processing.certifyForSync()

        # Create a series with importstatus = SYNCING
        syncing = self.createTestingSeries(firefox, 'syncing')
        syncing.certifyForSync()
        syncing.enableAutoSync()
        syncing_branch = self.createImportBranch(syncing)

        # Create a series with importstatus = STOPPED
        stopped = self.createTestingSeries(firefox, 'stopped')
        stopped.certifyForSync()
        stopped.enableAutoSync()
        stopped_branch = self.createImportBranch(stopped)
        stopped.importstatus = ImportStatus.STOPPED


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
