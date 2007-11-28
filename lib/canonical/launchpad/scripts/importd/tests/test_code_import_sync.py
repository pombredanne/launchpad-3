# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test cases for canonical.launchpad.scripts.importd.code_import_sync."""

__metaclass__ = type
__all__ = ['test_suite']


import datetime
import os.path
import pytz
from subprocess import Popen, PIPE
from unittest import TestCase, TestLoader

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.database import CodeImport, ProductSeries, ProductSet
from canonical.testing import LaunchpadZopelessLayer
from canonical.launchpad.interfaces import (
    BranchType, CodeImportReviewStatus, IBranchSet, ICodeImportSet,
    ImportStatus, NotFoundError, RevisionControlSystems)
from canonical.launchpad.scripts.importd.code_import_sync import CodeImportSync
from canonical.launchpad.utilities import LaunchpadCelebrities
from canonical.launchpad.webapp import canonical_url


UTC = pytz.timezone('UTC')


class MockLogger:
    """Mock logger object for testing."""

    def __init__(self):
        self.warning_calls = []
        self.error_calls = []

    def debug(self, *args):
        pass

    def info(self, *args):
        pass

    def warning(self, *args):
        self.warning_calls.append(args)

    def error(self, *args):
        self.error_calls.append(args)


class CodeImportSyncTestCase(TestCase):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.cleanUpSampleData()
        self.firefox = ProductSet().getByName('firefox')
        logger = MockLogger()
        self.code_import_sync = CodeImportSync(logger, self.layer.txn)

    def cleanUpSampleData(self):
        """Clear out the sample data that would affect tests."""
        all_import_series = ProductSeries.select("importstatus IS NOT NULL")
        for import_series in all_import_series:
            import_series.deleteImport()
        all_code_imports = CodeImport.select()
        for code_import in all_code_imports:
            code_import.destroySelf()

    def createTestingSeries(self, name):
        """Create an import series in with TESTING importstatus."""
        product = self.firefox
        series = product.newSeries(product.owner, name, name)
        series.importstatus = ImportStatus.TESTING
        self.updateSeriesWithSubversion(series)
        # ProductSeries may have datelastsynced for any importstatus, but it
        # must only be copied to the CodeImport in some cases.
        series.datelastsynced = datetime.datetime(
            2000, 1, 1, 0, 0, 0, tzinfo=UTC)

        return series

    def updateSeriesWithCvs(self, series):
        """Update a productseries to use CVS details."""
        series.rcstype = RevisionControlSystems.CVS
        series.svnrepository = None
        series.cvsroot = ':pserver:anonymous@cvs.example.com/cvsroot'
        series.cvsmodule = series.name
        series.cvsbranch = 'MAIN'

    def updateSeriesWithSubversion(self, series):
        """Update a productseries to use Subversion details."""
        series.rcstype = RevisionControlSystems.SVN
        series.cvsroot = None
        series.cvsmodule = None
        series.cvsbranch = None
        series.svnrepository = 'svn://example.com/' + series.name

    def createImportBranch(self, series):
        """Create an import branch and associate it to an import series."""
        vcs_imports = LaunchpadCelebrities().vcs_imports
        branch = getUtility(IBranchSet).new(
            BranchType.IMPORTED,
            name=series.name, creator=vcs_imports, owner=vcs_imports,
            product=series.product, url=None)
        series.import_branch = branch
        return branch

    def assertImportMatchesSeries(self, code_import, series):
        """Fail if the CodeImport is not consistent with the ProductSeries."""
        # A CodeImport must have the same database id as its corresponding
        # series.
        self.assertEqual(code_import.id, series.id)

        # Since ProductSeries does not record who requested an import, all
        # CodeImports created by the sync script are recorded as registered by
        # the vcs-imports user.
        self.assertEqual(code_import.registrant.name, u'vcs-imports')

        # The VCS details must be identical.
        self.assertEqual(code_import.rcs_type, series.rcstype)
        self.assertEqual(code_import.svn_branch_url, series.svnrepository)
        self.assertEqual(code_import.cvs_root, series.cvsroot)
        self.assertEqual(code_import.cvs_module, series.cvsmodule)

        # dateLastSuccessfulFromProductSeries is carefully unit-testing in
        # TestDateLastSuccessfulFromProductSeries, so we can rely on it here.
        last_successful = \
            self.code_import_sync.dateLastSuccessfulFromProductSeries(series)
        self.assertEqual(code_import.date_last_successful, last_successful)

        # reviewStatusFromImportStatus is carefully unit-tested in
        # TestReviewStatusFromImportStatus, so we can rely on it here.
        review_status = self.code_import_sync.reviewStatusFromImportStatus(
            series.importstatus)
        self.assertEqual(code_import.review_status, review_status)

        # If series.import_branch is set, it should be the same as
        # code_import.branch.
        if series.import_branch is not None:
            self.assertEqual(code_import.branch, series.import_branch)


class TestGetImportSeries(CodeImportSyncTestCase):
    """Test that `CodeImportSync.getImportSeries` yields all the ProductSeries
    for which we want to have CodeImport, and nothing else.
    """

    def assertGetImportSeriesYields(self, expected_series):
        """Fail if getImportSeries does not yield a single item equal to
        `expected_series`.
        """
        flush_database_updates()
        series_list = list(self.code_import_sync.getImportSeries())
        self.assertEqual(len(series_list), 1)
        [series] = series_list
        self.assertEqual(series, expected_series)

    def assertGetImportSeriesYieldsNothing(self):
        """Fail if getImportSeries yield anything."""
        flush_database_updates()
        series_list = list(self.code_import_sync.getImportSeries())
        self.assertEqual(series_list, [])

    def testEmpty(self):
        # If there is no series with importstatus set, getImportSeries gives an
        # empty iterable. This would never happen in real life.
        self.assertGetImportSeriesYieldsNothing()

    def testDoncSync(self):
        # getImportSeries does not yield series with DONTSYNC import status.
        dontsync = self.createTestingSeries('dontsync')
        dontsync.markDontSync()
        self.assertEqual(dontsync.importstatus, ImportStatus.DONTSYNC)
        self.assertGetImportSeriesYieldsNothing()

    def testTesting(self):
        # getImportSeries yields series with TESTING import status.
        testing = self.createTestingSeries('testing')
        self.assertEqual(testing.importstatus, ImportStatus.TESTING)
        self.assertGetImportSeriesYields(testing)

    def testTestfailed(self):
        # getImportSeries does not yield series with TESTFAILED import status.
        testfailed = self.createTestingSeries('testfailed')
        testfailed.markTestFailed()
        self.assertEqual(testfailed.importstatus, ImportStatus.TESTFAILED)
        self.assertGetImportSeriesYieldsNothing()

    def testAutotested(self):
        # getImportSeries yields series with AUTOTESTED import status.
        autotested = self.createTestingSeries('autotested')
        autotested.importstatus = ImportStatus.AUTOTESTED
        self.assertGetImportSeriesYields(autotested)

    def testProcessing(self):
        # getImportSeries yields series with PROCESSING import status.
        processing = self.createTestingSeries('processing')
        processing.certifyForSync()
        self.assertEqual(processing.importstatus, ImportStatus.PROCESSING)
        self.assertGetImportSeriesYields(processing)

    def testSyncing(self):
        # getImportSeries yields series with SYNCING import status.
        syncing = self.createTestingSeries('syncing')
        syncing.certifyForSync()
        syncing.enableAutoSync()
        self.createImportBranch(syncing)
        self.assertEqual(syncing.importstatus, ImportStatus.SYNCING)
        self.assertGetImportSeriesYields(syncing)

    def testStopped(self):
        # getImportSeries yields series with STOPPED import status.
        stopped = self.createTestingSeries('stopped')
        stopped.certifyForSync()
        stopped.enableAutoSync()
        stopped_branch = self.createImportBranch(stopped)
        stopped.importstatus = ImportStatus.STOPPED
        self.assertGetImportSeriesYields(stopped)

    def testCvsNonMain(self):
        # getImportSeries should ignore series with a cvsbranch which is not
        # MAIN, regardless of the importstatus.
        testing = self.createTestingSeries('testing')
        self.updateSeriesWithCvs(testing)
        testing.cvsbranch = 'BRANCH-FOO'
        self.assertGetImportSeriesYieldsNothing()


class TestReviewStatusFromImportStatus(TestCase):
    """Test that reviewStatusFromImportStatus correctly maps ImportStatus to
    ReviewStatus.
    """

    def setUp(self):
        # reviewStatusFromImportStatus does not need database access.
        logger = MockLogger()
        self.code_import_sync = CodeImportSync(logger, None)

    def assertImportStatusTranslatesTo(self, import_status, expected):
        """Assert that reviewStatusFromImportStatus returns `expected`
        when passed `import_status`.
        """
        review_status = self.code_import_sync.reviewStatusFromImportStatus(
            import_status)
        self.assertEqual(review_status, expected)

    def assertImportStatusDoesNotTranslate(self, import_status):
        """Assert that reviewFromImportStatus raises AssertionError when passed
        `import_status`.
        """
        self.assertRaises(AssertionError,
            self.code_import_sync.reviewStatusFromImportStatus, import_status)

    def testDontsync(self):
        self.assertImportStatusDoesNotTranslate(ImportStatus.DONTSYNC)

    def testTesting(self):
        self.assertImportStatusTranslatesTo(
            ImportStatus.TESTING, CodeImportReviewStatus.NEW)

    def testTestfailed(self):
        self.assertImportStatusDoesNotTranslate(ImportStatus.TESTFAILED)

    def testAutotested(self):
        self.assertImportStatusTranslatesTo(
            ImportStatus.AUTOTESTED, CodeImportReviewStatus.NEW)

    def testProcessing(self):
        self.assertImportStatusTranslatesTo(
            ImportStatus.PROCESSING, CodeImportReviewStatus.REVIEWED)

    def testSyncing(self):
        self.assertImportStatusTranslatesTo(
            ImportStatus.SYNCING, CodeImportReviewStatus.REVIEWED)

    def testStopped(self):
        self.assertImportStatusTranslatesTo(
            ImportStatus.STOPPED, CodeImportReviewStatus.SUSPENDED)


class StubProductSeries:
    """Stub ProductSeries class used in unit tests."""


class TestDateLastSuccessfulFromProductSeries(TestCase):
    """Test that `CodeImportSync.dateLastSuccessfulFromProductSeries` gives the
    right date_last_successful for the associated CodeImport given an import
    ProductSeries.
    """

    def setUp(self):
        # dateLastSuccessfulFromProductSeries does not need database access.
        logger = MockLogger()
        self.code_import_sync = CodeImportSync(logger, None)

    def makeStubSeries(self, import_status):
        """Create a stub ProductSeries with a datelastsynced and the given
        import status.
        """
        series = StubProductSeries()
        series.importstatus = import_status
        series.datelastsynced = datetime.datetime(
            2000, 1, 1, 0, 0, 0, tzinfo=UTC)
        return series

    def assertDateLastSuccessfulIsReturned(self, import_status):
        """Assert that dateLastSuccessfulFromProductSeries returns
        datelastsynced for a ProductSeries with the given `import_status`.
        """
        series = self.makeStubSeries(import_status)
        date_last_successful = \
            self.code_import_sync.dateLastSuccessfulFromProductSeries(series)
        self.assertEqual(date_last_successful, series.datelastsynced)

    def assertNoneIsReturned(self, import_status):
        """Assert that dateLastSuccesfulFromProductSeries returns None for a
        ProductSeries with the given `import_status`.
        """
        series = self.makeStubSeries(import_status)
        date_last_successful = \
            self.code_import_sync.dateLastSuccessfulFromProductSeries(series)
        self.assertEqual(date_last_successful, None)

    def assertAssertionErrorRaised(self, import_status):
        """Assert that dateLastSuccessfulFromProductSeries raises an
        AssertionError for a ProductSeries with the given `import_status`.
        """
        series = self.makeStubSeries(import_status)
        self.assertRaises(AssertionError,
            self.code_import_sync.dateLastSuccessfulFromProductSeries, series)

    def testDontsync(self):
        self.assertAssertionErrorRaised(ImportStatus.DONTSYNC)

    def testTesting(self):
        self.assertNoneIsReturned(ImportStatus.TESTING)

    def testTestfailed(self):
        self.assertAssertionErrorRaised(ImportStatus.TESTFAILED)

    def testAutotested(self):
        self.assertNoneIsReturned(ImportStatus.AUTOTESTED)

    def testProcessing(self):
        self.assertNoneIsReturned(ImportStatus.PROCESSING)

    def testSyncing(self):
        self.assertDateLastSuccessfulIsReturned(ImportStatus.SYNCING)

    def testStopped(self):
        self.assertDateLastSuccessfulIsReturned(ImportStatus.STOPPED)


class TestCreateCodeImport(CodeImportSyncTestCase):
    """Test that `CodeImportSync.createCodeImport` creates a CodeImport with
    the right values from a given ProductSeries.
    """

    def testSubversion(self):
        # Test correct creation of a CodeImport with Subversion details.
        series = self.createTestingSeries('testing')
        code_import = self.code_import_sync.createCodeImport(series)
        self.assertImportMatchesSeries(code_import, series)

    def testTestingCvs(self):
        # Test correct creation of CodeImport with CVS details.
        series = self.createTestingSeries('testing')
        self.updateSeriesWithCvs(series)
        code_import = self.code_import_sync.createCodeImport(series)
        self.assertImportMatchesSeries(code_import, series)

    def testBranchNameConflict(self):
        # If it is not possible to create an import branch using the standard
        # name ~vcs-imports/product/series, an error is logged.
        series = self.createTestingSeries('testing')
        # Create a branch with the standard name, but do not associate it with
        # the productseries, so we will attempt to create a new one.
        vcs_imports = LaunchpadCelebrities().vcs_imports
        branch = getUtility(IBranchSet).new(
            BranchType.IMPORTED,
            name=series.name, creator=vcs_imports, owner=vcs_imports,
            product=series.product, url=None)
        # Then, createCodeImport should fail and log an error.
        code_import = self.code_import_sync.createCodeImport(series)
        self.assertEqual(code_import, None)
        self.assertEqual(self.code_import_sync.logger.error_calls,
            [("Branch name conflict: %s", canonical_url(branch))])


class TestUpdateCodeImport(CodeImportSyncTestCase):
    """Test that `CodeImportSync.updateCodeImport` correctly updates an
    existing CodeImport from its associated ProductSeries.
    """

    def testSubversionToCvs(self):
        # Test updating a code import from Subversion to CVS.
        series = self.createTestingSeries('testing')
        code_import = self.code_import_sync.createCodeImport(series)
        self.updateSeriesWithCvs(series)
        self.code_import_sync.updateCodeImport(series, code_import)
        self.assertImportMatchesSeries(code_import, series)

    def testCvsToSubversion(self):
        # Test updating a code import from CVS to Subversion.
        series = self.createTestingSeries('testing')
        self.updateSeriesWithCvs(series)
        code_import = self.code_import_sync.createCodeImport(series)
        self.updateSeriesWithSubversion(series)
        self.code_import_sync.updateCodeImport(series, code_import)
        self.assertImportMatchesSeries(code_import, series)


class TestCodeImportSync(CodeImportSyncTestCase):
    """Feature tests for `CodeImportSync`."""

    def run_code_import_sync(self):
        """Run the code-import-sync, and flush database updates as needed."""
        flush_database_updates()
        self.code_import_sync.run()
        flush_database_updates()

    def assertSingleCodeImportMatchesSeries(self, series):
        """Fail unless there is a single CodeImport object and it matches
        series.
        """
        all_imports = list(getUtility(ICodeImportSet).getAll())
        self.assertEqual(len(all_imports), 1)
        [code_import] = all_imports
        self.assertImportMatchesSeries(code_import, series)

    def testNewTesting(self):
        # A new TESTING series causes the creation of a new code import with
        # NEW review status.
        testing = self.createTestingSeries('testing')
        self.run_code_import_sync()
        self.assertSingleCodeImportMatchesSeries(testing)

    def testNewProcessing(self):
        # A new PROCESSING series causes the creation of a new code import with
        # REVIEWED review status.
        processing = self.createTestingSeries('processing')
        processing.certifyForSync()
        self.assertEqual(processing.importstatus, ImportStatus.PROCESSING)
        self.run_code_import_sync()
        self.assertSingleCodeImportMatchesSeries(processing)

    def testNewSyncing(self):
        # A new SYNCING series causes the creation of a new code import with
        # REVIEWED review status and a non-NULL date_last_succesful.
        syncing = self.createTestingSeries('syncing')
        syncing.certifyForSync()
        syncing.enableAutoSync()
        self.assertEqual(syncing.importstatus, ImportStatus.SYNCING)
        self.createImportBranch(syncing)
        self.run_code_import_sync()
        self.assertSingleCodeImportMatchesSeries(syncing)

    def testUpdateProcessingToSyncing(self):
        # When a code import is created for a PROCESSING series, and the series
        # is ugraded to SYNCING, the code import can be correctly updated.
        series = self.createTestingSeries('processing-syncing')
        series.certifyForSync()
        self.assertEqual(series.importstatus, ImportStatus.PROCESSING)
        self.run_code_import_sync()
        series.enableAutoSync()
        self.assertEqual(series.importstatus, ImportStatus.SYNCING)

        # When code-import-sync runs in production, importd will need to use
        # the CodeImport's branch to publish the import.
        code_import = CodeImport.get(series.id)
        series.import_branch = code_import.branch

        self.run_code_import_sync()
        self.assertSingleCodeImportMatchesSeries(series)

    def testDeleteCodeImport(self):
        # If the productseries import status changes to a value for which we do
        # not create code imports (including None), we delete the CodeImport
        # object and emit a warning that the associated branch maybe should be
        # deleted manually.
        series = self.createTestingSeries('deleted')
        self.run_code_import_sync()
        import_branch = getUtility(ICodeImportSet).get(series.id).branch
        series.markDontSync()
        self.assertEqual(series.importstatus, ImportStatus.DONTSYNC)
        self.run_code_import_sync()
        # code-import-sync should delete the CodeImport object.
        self.assertRaises(NotFoundError,
            getUtility(ICodeImportSet).get, series.id)
        # And it should emit a warning about the orphaned import branch.
        self.assertEqual(self.code_import_sync.logger.warning_calls,
            [("Branch was orphaned, you may want to delete it: %s",
              canonical_url(import_branch))])

    def testReimportProcess(self):
        # In some cases, on the production server, the import_branch of a
        # ProductSeries can change. When the import_branch is set in
        # production, it must use the branch of the corresponding CodeImport if
        # it exists. If the CodeImport was created when ProductSeries used the
        # old import_branch value, that can make it difficult to change the
        # import_branch.
        #
        # Fortunately, import_branch is only set to a different branch when a
        # new import from scratch is done. Since code-import-sync is only run
        # in production during the transition period, the new back-end needs
        # code-import-sync to run to perform the new import. So we can act when
        # we see that the import_branch has been cleared.

        # Initially, we have a SYNCING series, and its associated code import.
        reimport = self.createTestingSeries('reimport')
        reimport.certifyForSync()
        reimport.enableAutoSync()
        self.assertEqual(reimport.importstatus, ImportStatus.SYNCING)
        old_branch = self.createImportBranch(reimport)
        self.run_code_import_sync()

        # Then an import from scratch is requested. The import details in the
        # series are cleared, new ones are installed (potentially the same
        # details, if the reimport is needed because the imported repository
        # has changed), and the existing import branch is renamed.
        reimport.deleteImport()
        old_branch.name = old_branch.name + '-broken'
        self.updateSeriesWithSubversion(reimport)
        reimport.certifyForSync()
        self.assertEqual(reimport.importstatus, ImportStatus.PROCESSING)
        self.assertEqual(reimport.import_branch, None)

        # If we are running in production, that means we are between
        # code-import-backend-transition and code-import-frontend transition.
        # The back-end can only perform the re-import after code-import-sync
        # has run.
        self.run_code_import_sync()
        self.assertSingleCodeImportMatchesSeries(reimport)

        # In this situation, the CodeImport must use a new branch, because the
        # old branch already contained import data.
        code_import = CodeImport.get(reimport.id)
        new_branch = code_import.branch
        self.assertNotEqual(old_branch, new_branch)

        # When the back-end completes the new import, it sets the import_branch
        # to the branch of the CodeImport and puts a value into datelastsynced.
        reimport.enableAutoSync()
        self.assertEqual(reimport.importstatus, ImportStatus.SYNCING)
        code_import = CodeImport.get(reimport.id)
        reimport.import_branch = code_import.branch
        reimport.datelastsynced = datetime.datetime(
            2000, 1, 1, 0, 0, 0, tzinfo=UTC)

        # Then code-import-sync runs again and updates the CodeImport object.
        self.run_code_import_sync()
        self.assertSingleCodeImportMatchesSeries(reimport)


class TestCodeImportSyncScript(TestCase):
    """Tests for the code-import-sync.py script runner."""

    layer = LaunchpadZopelessLayer

    def testItRuns(self):
        # Test that cronscripts/code-import-sync.py runs. We are not testing
        # that it does anything it all, its logic should be trivial, we are
        # testing for dumb mistakes.
        script = os.path.join(
            config.root, 'cronscripts', 'code-import-sync.py')
        process = Popen([script, '-q'],
                        stdout=PIPE, stderr=PIPE, stdin=open('/dev/null'))
        output, error = process.communicate()
        status = process.returncode
        self.assertEqual(status, 0,
                         'code-import-sync.py exited with status=%d\n'
                         '>>>stdout<<<\n%s\n>>>stderr<<<\n%s'
                         % (status, output, error))


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
