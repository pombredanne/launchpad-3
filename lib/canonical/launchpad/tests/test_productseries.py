# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test methods of the ProductSeries content class."""

import datetime
import pytz
import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.database.productseries import (
    DatePublishedSyncError, ProductSeries, NoImportBranchError)
from canonical.launchpad.ftests import login
from canonical.launchpad.interfaces import (
    IProductSeriesSet, IProductSet, ImportStatus, RevisionControlSystems)
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.testing import LaunchpadZopelessLayer, LaunchpadFunctionalLayer


class ImportdTestCase(unittest.TestCase):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        LaunchpadZopelessLayer.switchDbUser(config.importd.dbuser)


class TestDeleteImport(unittest.TestCase):

    layer = LaunchpadFunctionalLayer

    def testClearLastPublishedSync(self):
        """ProductSeries.deleteImport must clear datepublishedsync."""
        # We need to be a members of vcs-imports or admin to use deleteImport.
        login('david.allouche@canonical.com')

        # evolution/trunk is a commonly used series in unit tests of the code
        # import system.
        series = getUtility(IProductSet)['evolution'].getSeries('trunk')
        self.failIf(series.importstatus is None)

        # Ideally, we woud implement a realistic scenario to set this
        # attribute, but it would be too complicated for the purpose of this
        # simple test.
        removeSecurityProxy(series).datepublishedsync = UTC_NOW

        series.deleteImport()
        self.failUnless(series.datepublishedsync is None,
            'series.datepublishesync is %r' % (series.datepublishedsync))


class TestImportUpdated(ImportdTestCase):
    """Test ProductSeries.importUpdated.

    This method updates the datelastsynced and datepublishedsync timestamps.
    """

    def series(self):
        """Return the ProductSeries for the Evolution import."""
        series_id = 3
        return ProductSeries.get(series_id)

    def testNoBranchError(self):
        # setDateLastSynced must raise an exception if the series does not
        # have its import_branch set.
        #
        # The import_branch attribute is set when the import branch is pushed
        # to the internal server. The setDateLastSynced method is only called
        # for successful production jobs, so there must always be an
        # internally published import branch at this point.
        self.series().import_branch = None
        self.assertRaises(NoImportBranchError,
            self.series().importUpdated)

    def testDatePublishedSyncError(self):
        # If import_branch.last_mirrorred is None, the initial mirroring has
        # not yet completed. The datepublishedsync should be NULL because we
        # have not published anything yet.
        assert self.series().import_branch.last_mirrored is None
        self.series().datepublishedsync = UTC_NOW
        self.assertRaises(DatePublishedSyncError,
            self.series().importUpdated)

    # WARNING: RACE CONDITION if the mirroring starts after the branch has
    # been published internally, but before importUpdated is called. The
    # supermirror will be up-to-date with the latest import when mirroring
    # completes, but importUpdated will see that the branch is out of date,
    # and will not update datepublishedsync. When the mirroring completes,
    # import_branch.last_mirrored will be older than datelastsynced, because
    # it records the date when mirroring started, so Launchpad will believe
    # that the branch is out of date. Since this fails on the pessimistic
    # side, this is acceptable -- DavidAllouche 2006-12-12.

    # XXX DavidAllouche 2006-12-21: This race condition can be avoided if the
    # branch puller only runs for vcs-imports branches when
    # importd_branch.last_mirrored < datelastsynced.

    # XXX DavidAllouche 2006-12-21: The race can be resolved if we record
    # revision ids along with the datelastsynced and datepublishedsync
    # timestamps. That will be easier to do when the status reporting is done
    # from the importd slaves.

    def testLastMirroredIsNone(self):
        # If import_branch.last_mirrored is None, importUpdated sets
        # datelastsynced and import_branch.next_mirror_time to UTC_NOW.
        series = self.series()
        series.import_branch.last_mirrored = None
        series.datelastsynced = None
        series.importUpdated()
        # use str() to work around sqlobject lazy evaluation
        self.assertEqual(str(series.datepublishedsync), str(None))
        self.assertEqual(str(series.datelastsynced), str(UTC_NOW))
        self.assertEqual(
            str(series.import_branch.next_mirror_time), str(UTC_NOW))

    def testLastSyncedIsNone(self):
        # Make sure that importUpdated() still work when encountering the
        # transition case where datelastsynced is None while a previous branch
        # was successfully mirrored.
        series = self.series()
        series.datelastsynced = None
        UTC = pytz.timezone('UTC')
        series.import_branch.last_mirrored = datetime.datetime(
            2000, 1, 2, tzinfo=UTC)
        # In this situation, datepublishedsync SHOULD be None, but let's make
        # sure it is cleared, just to be safe..
        series.datepublishedsync = datetime.datetime(
            2000, 1, 1, tzinfo=UTC)
        series.importUpdated()
        # use str() to work around sqlobject lazy evaluation
        self.assertEqual(str(series.datelastsynced), str(UTC_NOW))
        self.assertEqual(str(series.datepublishedsync), str(None))

    def testLastMirroredBeforeLastSync(self):
        # If import_branch.last_mirrored is older than datelastsynced, the
        # previous sync has not been mirrored yet. The date of the currently
        # published sync should be already recorded in datepublishedsync.
        # Then importUpdated just updates datelastsynced.

        # XXX DavidAllouche 2006-12-13: 
        # If datepublishedsync is None, this means:
        # * last_mirrored was None the last time importUpdated was called
        # * the last mirror started before the last call to importUpdated
        #
        # This means the race condition occured on the initial import. In this
        # case we do not really know what has been mirrored, and the import
        # should be treated as not-mirrored. So this case does not need to be
        # treated specially.
        series = self.series()
        UTC = pytz.timezone('UTC')
        datepublishedsync = datetime.datetime(2000, 1, 1, tzinfo=UTC)
        series.datepublishedsync = datepublishedsync
        series.import_branch.last_mirrored = datetime.datetime(
            2001, 1, 1, tzinfo=UTC)
        series.datelastsynced = datetime.datetime(2002, 1, 1, tzinfo=UTC)
        series.importUpdated()
        self.assertEqual(
            str(series.datepublishedsync), str(datepublishedsync))
        self.assertEqual(str(series.datelastsynced), str(UTC_NOW))

    def testLastSyncWasMirrored(self):
        # If import_branch.last_mirrored is newer than datelastsynced, the
        # previous sync has been mirrored. So we save datelastsynced, the date
        # of the currently published sync, to datepublishedsync, and update
        # datelastsynced.
        series = self.series()
        UTC = pytz.timezone('UTC')
        series.datepublishedsync = datetime.datetime(2000, 1, 1, tzinfo=UTC)
        date_previous_sync = datetime.datetime(2001, 1, 1, tzinfo=UTC)
        series.datelastsynced = date_previous_sync
        series.import_branch.last_mirrored = datetime.datetime(
            2002, 1, 1, tzinfo=UTC)
        series.importUpdated()
        self.assertEqual(
            str(series.datepublishedsync), str(date_previous_sync))
        self.assertEqual(str(series.datelastsynced), str(UTC_NOW))


class SyncIntervalTestCase(unittest.TestCase):
    """When a VCS import is approved, we set the syncinterval column
    to indicate how often the import should be updated.  Imports from
    different revision control systems get different rates by default.
    """
    layer = LaunchpadZopelessLayer

    def getSampleSeries(self):
        """Get a sample product series without any source details."""
        product = getUtility(IProductSet).getByName('gnome-terminal')
        series = product.getSeries('trunk')
        self.assert_(series.rcstype is None)
        return series

    def testSyncIntervalForSvn(self):
        """Our policy is imports from subversion should be updated
        every 6 hours by default.
        """
        series = self.getSampleSeries()
        series.rcstype = RevisionControlSystems.SVN
        series.svnrepository = 'http://svn.example.com/hello/trunk'
        series.certifyForSync()
        self.assertEquals(series.syncinterval, datetime.timedelta(hours=6))

    def testSyncIntervalForCvs(self):
        """Our policy is imports from CVS should be updated
        every 12 hours by default.
        """
        series = self.getSampleSeries()
        series.rcstype = RevisionControlSystems.CVS
        series.cvsroot = ':pserver:anonymous@cvs.example.com:/cvsroot'
        series.cvsmodule = 'hello'
        series.cvsbranch = 'MAIN'
        series.certifyForSync()
        self.assertEquals(series.syncinterval, datetime.timedelta(hours=12))


class TestProductSeriesSearchImports(unittest.TestCase):
    """Tests for ProductSeriesSet.searchImports()."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Prepare by deleting all the import data in the sample data.

        This means that the tests only have to care about the ProductSeries
        they touch.
        """
        for series in ProductSeries.select():
            series.deleteImport()
        flush_database_updates()
        self.factory = LaunchpadObjectFactory()

    def makeSeries(self, project_name=None, product_name=None,
                   series_name=None):
        """Make a new ProductSeries for a new Product, mabye in a new Project.
        """
        if project_name is not None:
            project = self.factory.makeProject(name=project_name)
        else:
            project = None
        product = self.factory.makeProduct(name=product_name, project=project)
        return self.factory.makeSeries(product=product, name=series_name)

    def addImportDetailsToSeries(self, series, module_name='hello'):
        """Add import data to the provided series.

        'importstatus' will be set to SYNCING, arbitrarily.
        """
        series.rcstype = RevisionControlSystems.CVS
        series.cvsroot = ':pserver:anonymous@cvs.example.com:/cvsroot'
        series.cvsmodule = module_name
        series.cvsbranch = 'MAIN'
        series.importstatus = ImportStatus.SYNCING
        flush_database_updates()

    def testEmpty(self):
        # We start out with no series with import data, so searchImports()
        # returns no results.
        results = getUtility(IProductSeriesSet).searchImports()
        self.assertEquals(list(results), [])

    def testOneSeries(self):
        # When there is one series with import data, it is returned.
        series = self.makeSeries()
        self.addImportDetailsToSeries(series)
        results = getUtility(IProductSeriesSet).searchImports()
        self.assertEquals(list(results), [series])

    def testOneSeriesWithProject(self):
        # Series for products with a project should be returned too.
        series = self.makeSeries(project_name="whatever")
        self.addImportDetailsToSeries(series)
        results = getUtility(IProductSeriesSet).searchImports()
        self.assertEquals(list(results), [series])

    def testExcludeDeactivatedProducts(self):
        # Deactivating a product means that series associated to it are no
        # longer returned.
        series = self.factory.makeSeries()
        self.addImportDetailsToSeries(series)
        self.failUnless(series.product.active)
        results = getUtility(IProductSeriesSet).searchImports()
        self.assertEquals(list(results), [series])
        series.product.active = False
        flush_database_updates()
        results = getUtility(IProductSeriesSet).searchImports()
        self.assertEquals(list(results), [])

    def testExcludeDeactivatedProjects(self):
        # Deactivating a project means that series associated to products in
        # it are no longer returned.
        series = self.makeSeries(project_name="whatever")
        self.addImportDetailsToSeries(series)
        self.failUnless(series.product.project.active)
        results = getUtility(IProductSeriesSet).searchImports()
        self.assertEquals(list(results), [series])
        series.product.project.active = False
        flush_database_updates()
        results = getUtility(IProductSeriesSet).searchImports()
        self.assertEquals(list(results), [])

    def testSearchByStatus(self):
        # If passed a status, searchImports only returns series with that
        # status.
        series = self.makeSeries()
        self.addImportDetailsToSeries(series)
        results = getUtility(IProductSeriesSet).searchImports(
            importstatus=ImportStatus.SYNCING)
        self.assertEquals(list(results), [series])
        results = getUtility(IProductSeriesSet).searchImports(
            importstatus=ImportStatus.PROCESSING)
        self.assertEquals(list(results), [])

    def testSorting(self):
        # Returned series are sorted by product name, then series name.
        product1_a = self.makeSeries(product_name='product1', series_name='a')
        product2_a = self.makeSeries(product_name='product2', series_name='a')
        product1_b = self.factory.makeSeries(
            product=product1_a.product, name='b')
        self.addImportDetailsToSeries(product1_a, 'a')
        self.addImportDetailsToSeries(product1_b, 'b')
        self.addImportDetailsToSeries(product2_a, 'c')
        results = getUtility(IProductSeriesSet).searchImports()
        self.assertEquals(
            list(results), [product1_a, product1_b, product2_a])

    def testSearchByProduct(self):
        # Searching can filter by product name and other texts.
        series = self.makeSeries(product_name='product')
        self.addImportDetailsToSeries(series)
        results = getUtility(IProductSeriesSet).searchImports(
            text='product')
        self.assertEquals(
            list(results), [series])

    def testSearchByProductWithProject(self):
        # Searching can filter by product name and other texts, and returns
        # matching products even if the product is in a project which does not
        # match.
        series = self.makeSeries(
            project_name='whatever', product_name='product')
        self.addImportDetailsToSeries(series)
        results = getUtility(IProductSeriesSet).searchImports(
            text='product')
        self.assertEquals(
            list(results), [series])

    def testSearchByProject(self):
        # Searching can filter by project name and other texts.
        series = self.makeSeries(
            project_name='project', product_name='product')
        self.addImportDetailsToSeries(series)
        results = getUtility(IProductSeriesSet).searchImports(
            text='project')
        self.assertEquals(
            list(results), [series])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
