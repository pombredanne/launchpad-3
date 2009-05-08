# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for methods of CodeImport and CodeImportSet."""

from datetime import datetime, timedelta
import unittest

import pytz
from sqlobject import SQLObjectNotFound
from storm.store import Store
from zope.component import getUtility

from canonical.codehosting.codeimport.tests.test_workermonitor import (
    nuke_codeimport_sample_data)
from lp.code.model.codeimport import CodeImportSet
from lp.code.model.codeimportevent import CodeImportEvent
from lp.code.model.codeimportjob import (
    CodeImportJob, CodeImportJobSet)
from lp.code.model.codeimportresult import CodeImportResult
from lp.code.interfaces.codeimport import (
    CodeImportReviewStatus, ICodeImportSet)
from lp.registry.interfaces.person import IPersonSet
from lp.code.interfaces.codeimport import RevisionControlSystems
from lp.code.interfaces.codeimportjob import ICodeImportJobWorkflow
from lp.code.interfaces.codeimportresult import CodeImportResultStatus
from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.testing import (
    LaunchpadObjectFactory, TestCaseWithFactory, time_counter)
from canonical.testing import (
    DatabaseFunctionalLayer, LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer)


class TestCodeImportCreation(unittest.TestCase):
    """Test the creation of CodeImports."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.factory = LaunchpadObjectFactory()
        login('no-priv@canonical.com')

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
        CodeImportSet().delete(code_import_event.code_import)
        # CodeImportEvent.get should not raise anything.
        # But since it populates the object cache, we must invalidate it.
        Store.of(code_import_event).invalidate(code_import_event)
        self.assertRaises(
            SQLObjectNotFound, CodeImportEvent.get, code_import_event_id)

    def test_deleteIncludesResult(self):
        """Ensure deleting CodeImport objects deletes associated results."""
        code_import_result = self.factory.makeCodeImportResult()
        code_import_result_id = code_import_result.id
        CodeImportSet().delete(code_import_result.code_import)
        # CodeImportResult.get should not raise anything.
        # But since it populates the object cache, we must invalidate it.
        Store.of(code_import_result).invalidate(code_import_result)
        self.assertRaises(
            SQLObjectNotFound, CodeImportResult.get, code_import_result_id)


class TestCodeImportStatusUpdate(TestCaseWithFactory):
    """Test the status updates of CodeImports."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Log in a VCS Imports member.
        TestCaseWithFactory.setUp(self, 'david.allouche@canonical.com')
        self.import_operator = getUtility(IPersonSet).getByEmail(
            'david.allouche@canonical.com')
        # Remove existing jobs.
        for job in CodeImportJob.select():
            job.destroySelf()

    def makeApprovedImportWithPendingJob(self):
        code_import = self.factory.makeCodeImport()
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.REVIEWED},
            self.import_operator)
        return code_import

    def makeApprovedImportWithRunningJob(self):
        code_import = self.makeApprovedImportWithPendingJob()
        job = CodeImportJobSet().getJobForMachine('machine')
        self.assertEqual(code_import.import_job, job)
        return code_import

    def test_approve(self):
        # Approving a code import will create a job for it.
        code_import = self.factory.makeCodeImport()
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.REVIEWED},
            self.import_operator)
        self.assertIsNot(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.REVIEWED, code_import.review_status)

    def test_suspend_no_job(self):
        # Suspending a new import has no impact on jobs.
        code_import = self.factory.makeCodeImport()
        code_import.updateFromData(
            {'review_status':CodeImportReviewStatus.SUSPENDED},
            self.import_operator)
        self.assertIs(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.SUSPENDED, code_import.review_status)

    def test_suspend_pending_job(self):
        # Suspending an approved import with a pending job, removes job.
        code_import = self.makeApprovedImportWithPendingJob()
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.SUSPENDED},
            self.import_operator)
        self.assertIs(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.SUSPENDED, code_import.review_status)

    def test_suspend_running_job(self):
        # Suspending an approved import with a running job leaves job.
        code_import = self.makeApprovedImportWithRunningJob()
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.SUSPENDED},
            self.import_operator)
        self.assertIsNot(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.SUSPENDED, code_import.review_status)

    def test_invalidate_no_job(self):
        # Invalidating a new import has no impact on jobs.
        code_import = self.factory.makeCodeImport()
        code_import.updateFromData(
            {'review_status':CodeImportReviewStatus.INVALID},
            self.import_operator)
        self.assertIs(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.INVALID, code_import.review_status)

    def test_invalidate_pending_job(self):
        # Invalidating an approved import with a pending job, removes job.
        code_import = self.makeApprovedImportWithPendingJob()
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.INVALID},
            self.import_operator)
        self.assertIs(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.INVALID, code_import.review_status)

    def test_invalidate_running_job(self):
        # Invalidating an approved import with a running job leaves job.
        code_import = self.makeApprovedImportWithRunningJob()
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.INVALID},
            self.import_operator)
        self.assertIsNot(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.INVALID, code_import.review_status)

    def test_markFailing_no_job(self):
        # Marking a new import as failing has no impact on jobs.
        code_import = self.factory.makeCodeImport()
        code_import.updateFromData(
            {'review_status':CodeImportReviewStatus.FAILING},
            self.import_operator)
        self.assertIs(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.FAILING, code_import.review_status)

    def test_markFailing_pending_job(self):
        # Marking an import with a pending job as failing, removes job.
        code_import = self.makeApprovedImportWithPendingJob()
        code_import.updateFromData(
            {'review_status':CodeImportReviewStatus.FAILING},
            self.import_operator)
        self.assertIs(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.FAILING, code_import.review_status)

    def test_markFailing_running_job(self):
        # Marking an import with a running job as failing leaves job.
        code_import = self.makeApprovedImportWithRunningJob()
        code_import.updateFromData(
            {'review_status':CodeImportReviewStatus.FAILING},
            self.import_operator)
        self.assertIsNot(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.FAILING, code_import.review_status)


class TestCodeImportResultsAttribute(unittest.TestCase):
    """Test the results attribute of a CodeImport."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        unittest.TestCase.setUp(self)
        login('no-priv@canonical.com')
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


class TestConsecutiveFailureCount(TestCaseWithFactory):
    """Tests for `ICodeImport.consecutive_failure_count`."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        login('no-priv@canonical.com')
        self.machine = self.factory.makeCodeImportMachine()
        self.machine.setOnline()

    def makeRunningJob(self, code_import):
        """Make and return a CodeImportJob object with state==RUNNING.

        This is suitable for passing into finishJob().
        """
        if code_import.import_job is None:
            job = self.factory.makeCodeImportJob(code_import)
        else:
            job = code_import.import_job
        getUtility(ICodeImportJobWorkflow).startJob(job, self.machine)
        return job

    def failImport(self, code_import):
        """Create if necessary a job for `code_import` and have it fail."""
        running_job = self.makeRunningJob(code_import)
        getUtility(ICodeImportJobWorkflow).finishJob(
            running_job, CodeImportResultStatus.FAILURE, None)

    def succeedImport(self, code_import):
        """Create if necessary a job for `code_import` and have it succeed."""
        running_job = self.makeRunningJob(code_import)
        getUtility(ICodeImportJobWorkflow).finishJob(
            running_job, CodeImportResultStatus.SUCCESS, None)

    def test_consecutive_failure_count_zero_initially(self):
        # A new code import has a consecutive_failure_count of 0.
        code_import = self.factory.makeCodeImport()
        self.assertEqual(0, code_import.consecutive_failure_count)

    def test_consecutive_failure_count_succeed(self):
        # A code import that has succeeded once has a consecutive_failure_count
        # of 1.
        code_import = self.factory.makeCodeImport()
        self.succeedImport(code_import)
        self.assertEqual(0, code_import.consecutive_failure_count)

    def test_consecutive_failure_count_fail(self):
        # A code import that has failed once has a consecutive_failure_count
        # of 1.
        code_import = self.factory.makeCodeImport()
        self.failImport(code_import)
        self.assertEqual(1, code_import.consecutive_failure_count)

    def test_consecutive_failure_count_fail_fail(self):
        # A code import that has failed twice has a consecutive_failure_count
        # of 2.
        code_import = self.factory.makeCodeImport()
        self.failImport(code_import)
        self.failImport(code_import)
        self.assertEqual(2, code_import.consecutive_failure_count)

    def test_consecutive_failure_count_fail_fail_succeed(self):
        # A code import that has failed twice then succeeded has a
        # consecutive_failure_count of 0.
        code_import = self.factory.makeCodeImport()
        self.failImport(code_import)
        self.failImport(code_import)
        self.succeedImport(code_import)
        self.assertEqual(0, code_import.consecutive_failure_count)

    def test_consecutive_failure_count_fail_succeed_fail(self):
        # A code import that has failed then succeeded then failed again has a
        # consecutive_failure_count of 1.
        code_import = self.factory.makeCodeImport()
        self.failImport(code_import)
        self.succeedImport(code_import)
        self.failImport(code_import)
        self.assertEqual(1, code_import.consecutive_failure_count)

    def test_consecutive_failure_count_succeed_fail_succeed(self):
        # A code import that has failed then succeeded then failed again has a
        # consecutive_failure_count of 1.
        code_import = self.factory.makeCodeImport()
        self.succeedImport(code_import)
        self.failImport(code_import)
        self.succeedImport(code_import)
        self.assertEqual(0, code_import.consecutive_failure_count)

    def test_consecutive_failure_count_other_import_non_interference(self):
        # The failure or success of other code imports does not affect
        # consecutive_failure_count.
        code_import = self.factory.makeCodeImport()
        other_import = self.factory.makeCodeImport()
        self.failImport(code_import)
        self.assertEqual(1, code_import.consecutive_failure_count)
        self.failImport(other_import)
        self.assertEqual(1, code_import.consecutive_failure_count)
        self.succeedImport(code_import)
        self.assertEqual(0, code_import.consecutive_failure_count)
        self.succeedImport(other_import)
        self.assertEqual(0, code_import.consecutive_failure_count)
        self.failImport(code_import)
        self.assertEqual(1, code_import.consecutive_failure_count)
        self.failImport(other_import)
        self.assertEqual(1, code_import.consecutive_failure_count)


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
    from zope.security.proxy import removeSecurityProxy
    naked_import = removeSecurityProxy(code_import)
    naked_import.updateFromData(
        {'review_status': CodeImportReviewStatus.REVIEWED},
        factory.makePerson())
    if last_update is None:
        # If last_update is not specfied, presumably we don't care what it is
        # so we just use some made up value.
        last_update = datetime(2008, 1, 1, tzinfo=pytz.UTC)
    naked_import.date_last_successful = last_update


def deactivate(project_or_product):
    """Mark `project_or_product` as not active."""
    from zope.security.proxy import removeSecurityProxy
    removeSecurityProxy(project_or_product).active = False


class TestGetActiveImports(TestCaseWithFactory):
    """Tests for CodeImportSet.getActiveImports()."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Prepare by deleting all the import data in the sample data.

        This means that the tests only have to care about the import
        data they create.
        """
        super(TestGetActiveImports, self).setUp()
        nuke_codeimport_sample_data()
        login('no-priv@canonical.com')

    def tearDown(self):
        super(TestGetActiveImports, self).tearDown()
        logout()

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
        deactivate(code_import.product)
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
        deactivate(code_import.product.project)
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
                if code_import.branch.product.project and not project_active:
                    deactivate(code_import.branch.product.project)
                if not product_active:
                    deactivate(code_import.branch.product)
                if project_active != False and product_active:
                    expected.add(code_import)
                source[code_import] = (product_active, project_active)
        results = set(getUtility(ICodeImportSet).getActiveImports())
        errors = []
        for extra in results - expected:
            errors.append(('extra', source[extra]))
        for missing in expected - results:
            errors.append(('extra', source[missing]))
        self.assertEquals(errors, [])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
