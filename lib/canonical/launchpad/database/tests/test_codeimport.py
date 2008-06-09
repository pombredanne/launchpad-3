# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for methods of CodeImport and CodeImportSet."""

from datetime import datetime, timedelta
import unittest

import pytz
from sqlobject import SQLObjectNotFound
from sqlobject.sqlbuilder import SQLConstant
from zope.component import getUtility

from canonical.codehosting.codeimport.publish import ensure_series_branch
from canonical.codehosting.codeimport.tests.test_worker_monitor import (
    nuke_codeimport_sample_data)
from canonical.database.sqlbase import flush_database_updates
from canonical.database.constants import DEFAULT
from canonical.launchpad.database.codeimport import CodeImportSet
from canonical.launchpad.database.codeimportevent import CodeImportEvent
from canonical.launchpad.database.codeimportjob import (
    CodeImportJob, CodeImportJobSet)
from canonical.launchpad.database.codeimportresult import CodeImportResult
from canonical.launchpad.database.productseries import ProductSeries
from canonical.launchpad.interfaces import (
    BranchCreationException, BranchType, CodeImportJobState,
    CodeImportReviewStatus, IBranchSet, ICodeImportSet, ILaunchpadCelebrities,
    IPersonSet, ImportStatus, RevisionControlSystems)
from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.testing import (
    LaunchpadObjectFactory, TestCaseWithFactory, time_counter)
from canonical.testing import LaunchpadFunctionalLayer, LaunchpadZopelessLayer


class TestCodeImportCreation(unittest.TestCase):
    """Test the creation of CodeImports."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.factory = LaunchpadObjectFactory()
        login(ANONYMOUS)

    def tearDown(self):
        logout()

    def test_new_svn_import(self):
        """A new subversion code import should have NEW status."""
        code_import = CodeImportSet().new(
            registrant=self.factory.makePerson(),
            product=self.factory.makeProduct(),
            branch_name='imported',
            rcs_type=RevisionControlSystems.SVN,
            svn_branch_url=self.factory.getUniqueURL())
        self.assertEqual(
            CodeImportReviewStatus.NEW,
            code_import.review_status)
        # No job is created for the import.
        self.assertTrue(code_import.import_job is None)

    def test_reviewed_svn_import(self):
        """A specific review status can be set for a new import."""
        code_import = CodeImportSet().new(
            registrant=self.factory.makePerson(),
            product=self.factory.makeProduct(),
            branch_name='imported',
            rcs_type=RevisionControlSystems.SVN,
            svn_branch_url=self.factory.getUniqueURL(),
            review_status=CodeImportReviewStatus.REVIEWED)
        self.assertEqual(
            CodeImportReviewStatus.REVIEWED,
            code_import.review_status)
        # A job is created for the import.
        self.assertTrue(code_import.import_job is not None)

    def test_new_cvs_import(self):
        """A new CVS code import should have NEW status."""
        code_import = CodeImportSet().new(
            registrant=self.factory.makePerson(),
            product=self.factory.makeProduct(),
            branch_name='imported',
            rcs_type=RevisionControlSystems.CVS,
            cvs_root=self.factory.getUniqueURL(),
            cvs_module='module')
        self.assertEqual(
            CodeImportReviewStatus.NEW,
            code_import.review_status)
        # No job is created for the import.
        self.assertTrue(code_import.import_job is None)

    def test_reviewed_cvs_import(self):
        """A specific review status can be set for a new import."""
        code_import = CodeImportSet().new(
            registrant=self.factory.makePerson(),
            product=self.factory.makeProduct(),
            branch_name='imported',
            rcs_type=RevisionControlSystems.CVS,
            cvs_root=self.factory.getUniqueURL(),
            cvs_module='module',
            review_status=CodeImportReviewStatus.REVIEWED)
        self.assertEqual(
            CodeImportReviewStatus.REVIEWED,
            code_import.review_status)
        # A job is created for the import.
        self.assertTrue(code_import.import_job is not None)


class TestCodeImportDeletion(unittest.TestCase):
    """Test the deletion of CodeImports."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.factory = LaunchpadObjectFactory()
        # Log in a vcs import member.
        login('david.allouche@canonical.com')

    def tearDown(self):
        logout()

    def test_delete(self):
        """Ensure CodeImport objects can be deleted via CodeImportSet."""
        code_import = self.factory.makeCodeImport()
        CodeImportSet().delete(code_import)

    def test_deleteIncludesJob(self):
        """Ensure deleting CodeImport objects deletes associated jobs."""
        code_import = self.factory.makeCodeImport()
        code_import_job = self.factory.makeCodeImportJob(code_import)
        job_id = code_import_job.id
        CodeImportJobSet().getById(job_id)
        job = CodeImportJobSet().getById(job_id)
        assert job is not None
        CodeImportSet().delete(code_import)
        job = CodeImportJobSet().getById(job_id)
        assert job is None

    def test_deleteIncludesEvent(self):
        """Ensure deleting CodeImport objects deletes associated events."""
        code_import_event = self.factory.makeCodeImportEvent()
        code_import_event_id = code_import_event.id
        # CodeImportEvent.get should not raise anything.
        # But since it populates the object cache, we must expire it.
        CodeImportEvent.get(code_import_event_id).expire()
        CodeImportSet().delete(code_import_event.code_import)
        self.assertRaises(
            SQLObjectNotFound, CodeImportEvent.get, code_import_event_id)

    def test_deleteIncludesResult(self):
        """Ensure deleting CodeImport objects deletes associated results."""
        code_import_result = self.factory.makeCodeImportResult()
        code_import_result_id = code_import_result.id
        # CodeImportResult.get should not raise anything.
        # But since it populates the object cache, we must expire it.
        CodeImportResult.get(code_import_result_id).expire()
        CodeImportSet().delete(code_import_result.code_import)
        self.assertRaises(
            SQLObjectNotFound, CodeImportResult.get, code_import_result_id)


class TestCodeImportStatusUpdate(unittest.TestCase):
    """Test the status updates of CodeImports."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        unittest.TestCase.setUp(self)
        # Log in a VCS Imports member.
        login('david.allouche@canonical.com')
        self.factory = LaunchpadObjectFactory()
        self.code_import = self.factory.makeCodeImport()
        self.import_operator = getUtility(IPersonSet).getByEmail(
            'david.allouche@canonical.com')
        # Remove existing jobs.
        for job in CodeImportJob.select():
            job.destroySelf()

    def tearDown(self):
        logout()

    def test_approve(self):
        """Approving a code import will create a job for it."""
        self.code_import.approve({}, self.import_operator)
        self.assertTrue(self.code_import.import_job is not None)
        self.assertEqual(
            CodeImportReviewStatus.REVIEWED,
            self.code_import.review_status)

    def test_suspend_no_job(self):
        """Suspending a new import has no impact on jobs."""
        self.code_import.suspend({}, self.import_operator)
        self.assertTrue(self.code_import.import_job is None)
        self.assertEqual(
            CodeImportReviewStatus.SUSPENDED,
            self.code_import.review_status)

    def test_suspend_pending_job(self):
        """Suspending an approved import with a pending job, removes job."""
        self.code_import.approve({}, self.import_operator)
        self.assertEqual(
            CodeImportJobState.PENDING,
            self.code_import.import_job.state)
        self.code_import.suspend({}, self.import_operator)
        self.assertTrue(self.code_import.import_job is None)
        self.assertEqual(
            CodeImportReviewStatus.SUSPENDED,
            self.code_import.review_status)

    def test_suspend_running_job(self):
        """Suspending an approved import with a running job leaves job."""
        self.code_import.approve({}, self.import_operator)
        self.assertEqual(
            CodeImportJobState.PENDING,
            self.code_import.import_job.state)
        # Have a machine claim the job.
        job = CodeImportJobSet().getJobForMachine('machine')
        # Make sure we have the correct job.
        self.assertEqual(self.code_import.import_job, job)
        self.code_import.suspend({}, self.import_operator)
        self.assertTrue(self.code_import.import_job is not None)
        self.assertEqual(
            CodeImportReviewStatus.SUSPENDED,
            self.code_import.review_status)

    def test_invalidate_no_job(self):
        """Invalidating a new import has no impact on jobs."""
        self.code_import.invalidate({}, self.import_operator)
        self.assertTrue(self.code_import.import_job is None)
        self.assertEqual(
            CodeImportReviewStatus.INVALID,
            self.code_import.review_status)

    def test_invalidate_pending_job(self):
        """Invalidating an approved import with a pending job, removes job."""
        self.code_import.approve({}, self.import_operator)
        self.assertEqual(
            CodeImportJobState.PENDING,
            self.code_import.import_job.state)
        self.code_import.invalidate({}, self.import_operator)
        self.assertTrue(self.code_import.import_job is None)
        self.assertEqual(
            CodeImportReviewStatus.INVALID,
            self.code_import.review_status)

    def test_invalidate_running_job(self):
        """Invalidating an approved import with a running job leaves job."""
        self.code_import.approve({}, self.import_operator)
        self.assertEqual(
            CodeImportJobState.PENDING,
            self.code_import.import_job.state)
        # Have a machine claim the job.
        job = CodeImportJobSet().getJobForMachine('machine')
        # Make sure we have the correct job.
        self.assertEqual(self.code_import.import_job, job)
        self.code_import.invalidate({}, self.import_operator)
        self.assertTrue(self.code_import.import_job is not None)
        self.assertEqual(
            CodeImportReviewStatus.INVALID,
            self.code_import.review_status)


class TestCodeImportResultsAttribute(unittest.TestCase):
    """Test the results attribute of a CodeImport."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        unittest.TestCase.setUp(self)
        login(ANONYMOUS)
        self.factory = LaunchpadObjectFactory()
        self.code_import = self.factory.makeCodeImport()

    def tearDown(self):
        logout()

    def test_no_results(self):
        # Initially a new code import will have no results.
        self.assertEqual([], list(self.code_import.results))

    def test_single_result(self):
        # A result associated with the code import can be accessed directly
        # from the code import object.
        import_result = self.factory.makeCodeImportResult(self.code_import)
        results = list(self.code_import.results)
        self.assertEqual(1, len(results))
        self.assertEqual(import_result, results[0])

    def test_result_ordering(self):
        # The results query will order the results by job started time, with
        # the most recent import first.
        when = time_counter(
            origin=datetime(2007, 9, 9, 12, tzinfo=pytz.UTC),
            delta=timedelta(days=1))
        first = self.factory.makeCodeImportResult(
            self.code_import, date_started=when.next())
        second = self.factory.makeCodeImportResult(
            self.code_import, date_started=when.next())
        third = self.factory.makeCodeImportResult(
            self.code_import, date_started=when.next())
        self.assertTrue(first.date_job_started < second.date_job_started)
        self.assertTrue(second.date_job_started < third.date_job_started)
        results = list(self.code_import.results)
        self.assertEqual(third, results[0])
        self.assertEqual(second, results[1])
        self.assertEqual(first, results[2])

    def test_result_ordering_paranoia(self):
        # Similar to test_result_ordering, but with results created in reverse
        # order (this wouldn't really happen) but it shows that the id of the
        # import result isn't used to sort by.
        when = time_counter(
            origin=datetime(2007, 9, 11, 12, tzinfo=pytz.UTC),
            delta=timedelta(days=-1))
        first = self.factory.makeCodeImportResult(
            self.code_import, date_started=when.next())
        second = self.factory.makeCodeImportResult(
            self.code_import, date_started=when.next())
        third = self.factory.makeCodeImportResult(
            self.code_import, date_started=when.next())
        self.assertTrue(first.date_job_started > second.date_job_started)
        self.assertTrue(second.date_job_started > third.date_job_started)
        results = list(self.code_import.results)
        self.assertEqual(first, results[0])
        self.assertEqual(second, results[1])
        self.assertEqual(third, results[2])


class TestReviewStatusFromImportStatus(unittest.TestCase):
    """Tests for `CodeImportSet.reviewStatusFromImportStatus`."""
    # XXX: MichaelHudson 2008-05-20, bug=232076: This class is testing
    # functionality that is is only necessary for the transition from the old
    # to the new code import system, and should be deleted after that process
    # is done.

    def setUp(self):
        self.code_import_set = CodeImportSet()

    def assertImportStatusTranslatesTo(self, import_status, expected):
        """Assert that `import_status` is translated into `expected`."""
        review_status = self.code_import_set._reviewStatusFromImportStatus(
            import_status)
        self.assertEqual(review_status, expected)

    def assertImportStatusDoesNotTranslate(self, import_status):
        """Assert that trying to translate `import_status` raises."""
        self.assertRaises(AssertionError,
            self.code_import_set._reviewStatusFromImportStatus, import_status)

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


class TestDateLastSuccessfulFromProductSeries(unittest.TestCase):
    """Tests for `CodeImportSet._dateLastSuccessfulFromProductSeries`."""
    # XXX: MichaelHudson 2008-05-20, bug=232076: This class is testing
    # functionality that is is only necessary for the transition from the old
    # to the new code import system, and should be deleted after that process
    # is done.

    def setUp(self):
        # dateLastSuccessfulFromProductSeries does not need database access.
        self.code_import_set = CodeImportSet()

    def makeStubSeries(self, import_status):
        """Create a stub ProductSeries.

        The returned 'series' will have a datelastsynced and the given import
        status.
        """
        series = StubProductSeries()
        series.importstatus = import_status
        series.datelastsynced = datetime(2000, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
        return series

    def assertDateLastSuccessfulIsReturned(self, import_status):
        """Assert that the datelastsynced is return for the given status."""
        series = self.makeStubSeries(import_status)
        date_last_successful = \
            self.code_import_set._dateLastSuccessfulFromProductSeries(series)
        self.assertEqual(date_last_successful, series.datelastsynced)

    def assertNoneIsReturned(self, import_status):
        """Assert that None is returned for a given status."""
        series = self.makeStubSeries(import_status)
        date_last_successful = \
            self.code_import_set._dateLastSuccessfulFromProductSeries(series)
        self.assertEqual(date_last_successful, None)

    def assertAssertionErrorRaised(self, import_status):
        """Assert that an AssertionError is raised for the given status."""
        series = self.makeStubSeries(import_status)
        self.assertRaises(AssertionError,
            self.code_import_set._dateLastSuccessfulFromProductSeries, series)

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


class TestDateCreatedFromProductSeries(unittest.TestCase):
    """Tests for `CodeImportSet._dateLastSuccessfulFromProductSeries`."""
    # XXX: MichaelHudson 2008-05-20, bug=232076: This class is testing
    # functionality that is is only necessary for the transition from the old
    # to the new code import system, and should be deleted after that process
    # is done.

    def setUp(self):
        # dateLastSuccessfulFromProductSeries does not need database access.
        self.code_import_set = CodeImportSet()

    def makeSeries(self, dateprocessapproved, dateautotested):
        """Create a stub ProductSeries.

        The returned 'series' will have a datelastsynced and the given import
        status.
        """
        series = StubProductSeries()
        series.dateprocessapproved = dateprocessapproved
        series.dateautotested = dateautotested
        return series

    def assertEqualsCarefully(self, expected, result):
        """Assert that expected equals results, taking care with SQLConstants.

        Instances of SQLConstant are 'equal' to anything:

            >>> from sqlobject.sqlbuilder import SQLConstant
            >>> SQLConstant("hi") == None
            ((hi) IS NULL)
            >>> bool(SQLConstant("hi") == None)
            True

        So we have to treat instances of this class separately.
        """
        if isinstance(result, SQLConstant) or \
               isinstance(expected, SQLConstant):
            self.assertTrue(expected is result)
        else:
            self.assertEquals(expected, result)

    def test_neitherSet(self):
        series = self.makeSeries(
            dateprocessapproved=None,
            dateautotested=None)
        self.assertEqualsCarefully(
            DEFAULT,
            self.code_import_set._dateCreatedFromProductSeries(series))

    def test_dateprocessapprovedSet(self):
        series = self.makeSeries(
            dateprocessapproved=datetime(2007, 1, 1),
            dateautotested=None)
        self.assertEqualsCarefully(
            datetime(2007, 1, 1),
            self.code_import_set._dateCreatedFromProductSeries(series))

    def test_dateautotestedSet(self):
        series = self.makeSeries(
            dateprocessapproved=None,
            dateautotested=datetime(2007, 1, 1))
        self.assertEqualsCarefully(
            datetime(2007, 1, 1),
            self.code_import_set._dateCreatedFromProductSeries(series))

    def test_dateautotestedFirst(self):
        series = self.makeSeries(
            dateprocessapproved=datetime(2008, 1, 1),
            dateautotested=datetime(2007, 1, 1))
        self.assertEqualsCarefully(
            datetime(2007, 1, 1),
            self.code_import_set._dateCreatedFromProductSeries(series))

    def test_dateprocessapprovedFirst(self):
        series = self.makeSeries(
            dateprocessapproved=datetime(2007, 1, 1),
            dateautotested=datetime(2008, 1, 1))
        self.assertEqualsCarefully(
            datetime(2007, 1, 1),
            self.code_import_set._dateCreatedFromProductSeries(series))


class TestUpdateIntervalFromProductSeries(unittest.TestCase):
    """Tests for `CodeImportSet._updateIntervalFromProductSeries`."""
    # XXX: MichaelHudson 2008-05-20, bug=232076: This class is testing
    # functionality that is is only necessary for the transition from the old
    # to the new code import system, and should be deleted after that process
    # is done.

    def setUp(self):
        # _updateIntervalFromProductSeries does not need database access.
        self.code_import_set = CodeImportSet()

    def makeSeries(self, rcstype, syncinterval):
        """Create a stub ProductSeries.

        If syncinterval is None, set series.syncinterval to the default value.
        Otherwise, set it to syncinterval.
        """
        series = StubProductSeries()
        series.rcstype = rcstype
        # Total hack to avoid duplicating knowledge about what the defaults
        # are into the test.
        ProductSeries.certifyForSync.im_func(series)
        if syncinterval is not None:
            # If this fails, it's a bug in the test.
            self.assertNotEquals(series.syncinterval, syncinterval)
            series.syncinterval = syncinterval
        return series

    def test_defaultCVS(self):
        # update_interval should be set to None from a CVS import with the
        # default syncinterval.
        series = self.makeSeries(
            RevisionControlSystems.CVS, None)
        self.assertEquals(
            None,
            self.code_import_set._updateIntervalFromProductSeries(series))

    def test_defaultSubversion(self):
        # update_interval should be set to None from a Subversion import with
        # the default syncinterval.
        series = self.makeSeries(
            RevisionControlSystems.SVN, None)
        self.assertEquals(
            None,
            self.code_import_set._updateIntervalFromProductSeries(series))

    def test_nonDefaultCVS(self):
        # A CVS import with a changed syncinterval should have that copied to
        # update_interval.
        series = self.makeSeries(
            RevisionControlSystems.CVS, timedelta(hours=1))
        self.assertEquals(
            timedelta(hours=1),
            self.code_import_set._updateIntervalFromProductSeries(series))

    def test_nonDefaultSubversion(self):
        # A Subversion import with a changed syncinterval should have that
        # copied to update_interval.
        series = self.makeSeries(
            RevisionControlSystems.SVN, timedelta(hours=1))
        self.assertEquals(
            timedelta(hours=1),
            self.code_import_set._updateIntervalFromProductSeries(series))


class TestNewFromProductSeries(unittest.TestCase):
    """Tests for `CodeImportSet.newFromProductSeries`."""
    # XXX: MichaelHudson 2008-05-20, bug=232076: This class is testing
    # functionality that is is only necessary for the transition from the old
    # to the new code import system, and should be deleted after that process
    # is done.

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        self.code_import_set = getUtility(ICodeImportSet)
        self.factory = LaunchpadObjectFactory()
        # Log in a vcs import member.
        login('david.allouche@canonical.com')

    def tearDown(self):
        logout()

    def createTestingSeries(self):
        """Create an import series in with TESTING importstatus."""
        series = self.factory.makeSeries()
        series.importstatus = ImportStatus.TESTING
        self.updateSeriesWithSubversion(series)
        # ProductSeries may have datelastsynced for any importstatus, but it
        # must only be copied to the CodeImport in some cases.
        from zope.security.proxy import removeSecurityProxy
        removeSecurityProxy(series).datelastsynced = \
            datetime(2000, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
        return series

    def createSyncingSeries(self):
        series = self.factory.makeSeries()
        series.importstatus = ImportStatus.SYNCING
        self.updateSeriesWithSubversion(series)
        ensure_series_branch(series)
        # ProductSeries may have datelastsynced for any importstatus, but it
        # must only be copied to the CodeImport in some cases.
        from zope.security.proxy import removeSecurityProxy
        removeSecurityProxy(series).datelastsynced = \
            datetime(2000, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
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

    def snapshotSeries(self, series):
        """Take a snapshot of the ProductSeries `series`.

        Because `newFromProductSeries` mutates the series it is passed, we
        need to capture the state of the series before we call it.
        """
        return dict(
            cvsmodule=series.cvsmodule,
            cvsroot=series.cvsroot,
            datelastsynced=series.datelastsynced,
            id=series.id,
            import_branch=series.import_branch,
            importstatus=series.importstatus,
            rcstype=series.rcstype,
            svnrepository=series.svnrepository,
            )

    def assertImportMatchesSeriesSnapshot(self, code_import, snapshot):
        """Assert `code_import` is consistent with the `snapshot` of a series.

        See `snapshotSeries`.
        """
        # Since ProductSeries does not record who requested an import, all
        # CodeImports created by the sync script are recorded as registered by
        # the vcs-imports user.
        self.assertEqual(code_import.registrant.name, u'vcs-imports')

        # The VCS details must be identical.
        self.assertEqual(code_import.rcs_type, snapshot['rcstype'])
        self.assertEqual(
            code_import.svn_branch_url, snapshot['svnrepository'])
        self.assertEqual(code_import.cvs_root, snapshot['cvsroot'])
        self.assertEqual(code_import.cvs_module, snapshot['cvsmodule'])

        # dateLastSuccessfulFromProductSeries is carefully unit-tested in
        # TestDateLastSuccessfulFromProductSeries, so we can rely on it here.
        stub_series = StubProductSeries()
        stub_series.importstatus = snapshot['importstatus']
        stub_series.datelastsynced = snapshot['datelastsynced']
        last_successful = \
            CodeImportSet()._dateLastSuccessfulFromProductSeries(stub_series)
        self.assertEqual(code_import.date_last_successful, last_successful)

        # reviewStatusFromImportStatus is carefully unit-tested in
        # TestReviewStatusFromImportStatus, so we can rely on it here.
        review_status = CodeImportSet()._reviewStatusFromImportStatus(
            snapshot['importstatus'])
        self.assertEqual(code_import.review_status, review_status)

        # If series.import_branch was set, it should have been transferred to
        # code_import.branch.
        if snapshot['import_branch'] is not None:
            self.assertEqual(code_import.branch, snapshot['import_branch'])

        self.assertEqual(
            code_import.source_product_series.id, snapshot['id'])

    def testSubversion(self):
        # Test correct creation of a CodeImport with Subversion details.
        series = self.createTestingSeries()
        snapshot = self.snapshotSeries(series)
        code_import = self.code_import_set.newFromProductSeries(series)
        self.assertImportMatchesSeriesSnapshot(code_import, snapshot)

    def testCvs(self):
        # Test correct creation of CodeImport with CVS details.
        series = self.createTestingSeries()
        self.updateSeriesWithCvs(series)
        snapshot = self.snapshotSeries(series)
        code_import = self.code_import_set.newFromProductSeries(series)
        self.assertImportMatchesSeriesSnapshot(code_import, snapshot)

    def testSyncingSeries(self):
        # Test correct creation of CodeImport with from SYNCING series.
        series = self.createSyncingSeries()
        snapshot = self.snapshotSeries(series)
        code_import = self.code_import_set.newFromProductSeries(series)
        self.assertImportMatchesSeriesSnapshot(code_import, snapshot)

    def testConvertingSyncingSeriesCreatesJob(self):
        # If we convert a ProductSeries that is active, we should create a
        # code import job.
        series = self.createSyncingSeries()
        code_import = self.code_import_set.newFromProductSeries(series)
        self.assertTrue(code_import.import_job is not None)

    def testStopsSeries(self):
        # When a code import is created from a series, that series is marked
        # as STOPPED.
        series = self.createSyncingSeries()
        self.code_import_set.newFromProductSeries(series)
        self.assertEqual(series.importstatus, ImportStatus.STOPPED)

    def testClearsImportBranchSetsUserBranch(self):
        # When a code import is created from a series, the series' user_branch
        # is set to the value of the import_branch field, which is cleared.
        series = self.createSyncingSeries()
        series_branch = series.import_branch
        self.code_import_set.newFromProductSeries(series)
        self.assertEqual(series_branch, series.user_branch)
        self.assertEqual(None, series.import_branch)

    def testBranchNameConflict(self):
        # If it is not possible to create an import branch using the standard
        # name ~vcs-imports/product/series, an error is raised.
        series = self.createTestingSeries()
        # Create a branch with the standard name, but do not associate it with
        # the productseries, so we will attempt to create a new one.
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        branch = getUtility(IBranchSet).new(
            BranchType.IMPORTED,
            name=series.name, registrant=vcs_imports, owner=vcs_imports,
            product=series.product, url=None)
        self.assertRaises(BranchCreationException,
                          self.code_import_set.newFromProductSeries, series)


def make_active_import(factory, project_name=None, product_name=None,
                       branch_name=None, svn_branch_url=None,
                       cvs_root=None, cvs_module=None,
                       last_update=None):
    """Make a new CodeImport for a new Product, maybe in a new Project.

    The import will be 'active' in the sense used by
    `ICodeImportSet.getActiveImports`.
    """
    if project_name is not None:
        project = factory.makeProject(name=project_name)
    else:
        project = None
    product = factory.makeProduct(
        name=product_name, displayname=product_name, project=project)
    code_import = factory.makeCodeImport(
        product=product, branch_name=branch_name,
        svn_branch_url=svn_branch_url, cvs_root=cvs_root,
        cvs_module=cvs_module)
    make_import_active(factory, code_import, last_update)
    return code_import


def make_import_active(factory, code_import, last_update=None):
    """Make `code_import` active as per `ICodeImportSet.getActiveImports`."""
    code_import.approve({}, factory.makePerson(password='whatever'))
    from zope.security.proxy import removeSecurityProxy
    if last_update is None:
        # If last_update is not specfied, presumably we don't care what it is
        # so we just use some made up value.
        last_update = datetime(2008, 1, 1, tzinfo=pytz.UTC)
    removeSecurityProxy(code_import).date_last_successful = last_update
    flush_database_updates()


class TestGetActiveImports(TestCaseWithFactory):
    """Tests for CodeImportSet.getActiveImports()."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Prepare by deleting all the import data in the sample data.

        This means that the tests only have to care about the import
        data they create.
        """
        super(TestGetActiveImports, self).setUp()
        nuke_codeimport_sample_data()

    def testEmpty(self):
        # We start out with no code imports, so getActiveImports() returns no
        # results.
        results = getUtility(ICodeImportSet).getActiveImports()
        self.assertEquals(list(results), [])

    def testOneSeries(self):
        # When there is one active import, it is returned.
        code_import = make_active_import(self.factory)
        results = getUtility(ICodeImportSet).getActiveImports()
        self.assertEquals(list(results), [code_import])

    def testOneSeriesWithProject(self):
        # Code imports for products with a project should be returned too.
        code_import = make_active_import(
            self.factory, project_name="whatever")
        results = getUtility(ICodeImportSet).getActiveImports()
        self.assertEquals(list(results), [code_import])

    def testExcludeDeactivatedProducts(self):
        # Deactivating a product means that code imports associated to it are
        # no longer returned.
        code_import = make_active_import(self.factory)
        self.failUnless(code_import.product.active)
        results = getUtility(ICodeImportSet).getActiveImports()
        self.assertEquals(list(results), [code_import])
        code_import.product.active = False
        flush_database_updates()
        results = getUtility(ICodeImportSet).getActiveImports()
        self.assertEquals(list(results), [])

    def testExcludeDeactivatedProjects(self):
        # Deactivating a project means that code imports associated to
        # products in it are no longer returned.
        code_import = make_active_import(
            self.factory, project_name="whatever")
        self.failUnless(code_import.product.project.active)
        results = getUtility(ICodeImportSet).getActiveImports()
        self.assertEquals(list(results), [code_import])
        code_import.product.project.active = False
        flush_database_updates()
        results = getUtility(ICodeImportSet).getActiveImports()
        self.assertEquals(list(results), [])

    def testSorting(self):
        # Returned code imports are sorted by product name, then branch name.
        prod1_a = make_active_import(
            self.factory, product_name='prod1', branch_name='a')
        prod2_a = make_active_import(
            self.factory, product_name='prod2', branch_name='a')
        prod1_b = self.factory.makeCodeImport(
            product=prod1_a.product, branch_name='b')
        make_import_active(self.factory, prod1_b)
        results = getUtility(ICodeImportSet).getActiveImports()
        self.assertEquals(
            list(results), [prod1_a, prod1_b, prod2_a])

    def testSearchByProduct(self):
        # Searching can filter by product name and other texts.
        code_import = make_active_import(
            self.factory, product_name='product')
        results = getUtility(ICodeImportSet).getActiveImports(
            text='product')
        self.assertEquals(
            list(results), [code_import])

    def testSearchByProductWithProject(self):
        # Searching can filter by product name and other texts, and returns
        # matching imports even if the associated product is in a project
        # which does not match.
        code_import = make_active_import(
            self.factory, project_name='whatever', product_name='product')
        results = getUtility(ICodeImportSet).getActiveImports(
            text='product')
        self.assertEquals(
            list(results), [code_import])

    def testSearchByProject(self):
        # Searching can filter by project name and other texts.
        code_import = make_active_import(
            self.factory, project_name='project', product_name='product')
        results = getUtility(ICodeImportSet).getActiveImports(
            text='project')
        self.assertEquals(
            list(results), [code_import])

    def testSearchByProjectWithNonMatchingProduct(self):
        # If a project matches the text, it's an easy mistake to make to
        # consider all the products with no project as matching too.
        code_import_1 = make_active_import(
            self.factory, product_name='product1')
        code_import_2 = make_active_import(
            self.factory, project_name='thisone', product_name='product2')
        results = getUtility(ICodeImportSet).getActiveImports(
            text='thisone')
        self.assertEquals(
            list(results), [code_import_2])

    def testJoining(self):
        # Test that the query composed by CodeImportSet.composeQueryString
        # gets the joins right.  We create code imports for each of the
        # possibilities of active or inactive product and active or inactive
        # or absent project.
        expected = set()
        source = {}
        for project_active in [True, False, None]:
            for product_active in [True, False]:
                if project_active is not None:
                    project_name = self.factory.getUniqueString()
                else:
                    project_name = None
                code_import = make_active_import(
                    self.factory, project_name=project_name)
                if code_import.branch.product.project:
                    code_import.branch.product.project.active = project_active
                code_import.branch.product.active = product_active
                if project_active != False and product_active:
                    expected.add(code_import)
                source[code_import] = (product_active, project_active)
        flush_database_updates()
        results = set(getUtility(ICodeImportSet).getActiveImports())
        errors = []
        for extra in results - expected:
            errors.append(('extra', source[extra]))
        for missing in expected - results:
            errors.append(('extra', source[missing]))
        self.assertEquals(errors, [])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
