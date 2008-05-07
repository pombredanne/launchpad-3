# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for methods of CodeImport and CodeImportSet."""

import unittest

from sqlobject import SQLObjectNotFound
from zope.component import getUtility

from canonical.launchpad.database.codeimport import CodeImportSet
from canonical.launchpad.database.codeimportevent import CodeImportEvent
from canonical.launchpad.database.codeimportjob import (
    CodeImportJob, CodeImportJobSet)
from canonical.launchpad.database.codeimportresult import CodeImportResult
from canonical.launchpad.interfaces import (
    CodeImportJobState, CodeImportReviewStatus,
    IPersonSet, RevisionControlSystems)
from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.testing import LaunchpadFunctionalLayer


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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
