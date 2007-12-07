# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Unit tests for CodeImportJob and CodeImportJobWorkflow."""

__metaclass__ = type

from datetime import datetime
from pytz import UTC
import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.database import (
    CodeImportMachine, CodeImportResult)
from canonical.launchpad.interfaces import (
    CodeImportResultStatus, CodeImportReviewStatus, ICodeImportJobSet,
    ICodeImportSet, ICodeImportJobWorkflow)
from canonical.launchpad.ftests import login
from canonical.testing import LaunchpadFunctionalLayer


def login_for_code_imports():
    """Login as a member of the vcs-imports team.

    CodeImports are currently hidden from regular users currently. Members of
    the vcs-imports team and can access the objects freely.
    """
    # David Allouche is a member of the vcs-imports team.
    login('david.allouche@canonical.com')


class TestCodeImportJobSet(unittest.TestCase):
    """Unit tests for the CodeImportJobSet utility."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login_for_code_imports()

    def test_getByIdExisting(self):
        # CodeImportJobSet.getById retrieves a CodeImportJob by database id.
        job = getUtility(ICodeImportJobSet).getById(1)
        self.assertNotEqual(job, None)
        self.assertEqual(job.id, 1)

    def test_getByIdNotExisting(self):
        # CodeImportJobSet.getById returns None if there is not CodeImportJob
        # with the specified id.
        no_job = getUtility(ICodeImportJobSet).getById(-1)
        self.assertEqual(no_job, None)


class AssertFailureMixin:
    """Helper to test assert statements."""

    def assertFailure(self, message, callable_obj, *args, **kwargs):
        """Fail unless an AssertionError with the specified message is raised
        by callable_obj when invoked with arguments args and keyword
        arguments kwargs.

        If a different type of exception is thrown, it will not be caught, and
        the test case will be deemed to have suffered an error, exactly as for
        an unexpected exception.
        """
        try:
            callable_obj(*args, **kwargs)
        except AssertionError, exception:
            self.assertEqual(str(exception), message)
        else:
            self.fail("AssertionError was not raised")


class AssertSqlNowMixin:
    """Helper to test that SQL values are equal to UTC_NOW."""

    def assertSqlAttributeEqualsNow(self, sql_object, attribute_name):
        """Fail unless the value of the attribute is UTC_NOW.

        :param sql_object: an sqlobject instance.
        :param attribute_name: the name of a database column in the table
            associated to this object.
        """
        sql_class = type(sql_object)
        found_object = sql_class.selectOne(
            'id=%%s AND %s=%%s' % (attribute_name,)
            % sqlvalues(sql_object.id, UTC_NOW))
        self.assertEqual(sql_object, found_object)


class TestCodeImportJobWorkflowNewJob(unittest.TestCase,
        AssertFailureMixin, AssertSqlNowMixin):
    """Unit tests for the CodeImportJobWorkflow.newJob method."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login_for_code_imports()

    def test_wrongReviewStatus(self):
        # CodeImportJobWorkflow.newJob fails if the CodeImport review_status
        # is different from REVIEWED.
        new_import = getUtility(ICodeImportSet).get(2)
        # Checking sampledata expectations.
        self.assertEqual(new_import.branch.unique_name,
                         '~vcs-imports/evolution/import')
        NEW = CodeImportReviewStatus.NEW
        self.assertEqual(new_import.review_status, NEW)
        # Testing newJob failure.
        self.assertFailure(
            "Review status of ~vcs-imports/evolution/import "
            "is not REVIEWED: NEW",
            getUtility(ICodeImportJobWorkflow).newJob, new_import)

    def test_existingJob(self):
        # CodeImportJobWorkflow.newJob fails if the CodeImport is already
        # associated to a CodeImportJob.
        reviewed_import = getUtility(ICodeImportSet).get(1)
        # Checking sampledata expectations.
        self.assertEqual(reviewed_import.branch.unique_name,
                         '~vcs-imports/gnome-terminal/import')
        REVIEWED = CodeImportReviewStatus.REVIEWED
        self.assertEqual(reviewed_import.review_status, REVIEWED)
        self.assertNotEqual(reviewed_import.import_job, None)
        # Testing newJobFailure.
        self.assertFailure(
            "Already associated to a CodeImportJob: "
            "~vcs-imports/gnome-terminal/import",
            getUtility(ICodeImportJobWorkflow).newJob, reviewed_import)

    def getCodeImportForDateDueTest(self):
        """Return a `CodeImport` object for testing how date_due is set.

        We check that it is not associated to any `CodeImportJob` or
        `CodeImportResult`, and we ensure its review_status is REVIEWED.
        """
        new_import = getUtility(ICodeImportSet).get(2)
        # Checking sampledata expectations.
        self.assertEqual(new_import.import_job, None)
        self.assertEqual(
            CodeImportResult.selectBy(code_importID=new_import.id).count(), 0)
        # We need to set review_status to REVIEWED before calling newJob, and
        # the interface marks review_status as read-only.
        REVIEWED = CodeImportReviewStatus.REVIEWED
        removeSecurityProxy(new_import).review_status = REVIEWED
        return new_import

    def test_dateDueNoPreviousResult(self):
        # If there is no CodeImportResult for the CodeImport, then the new
        # CodeImportJob has date_due set to UTC_NOW.
        code_import = self.getCodeImportForDateDueTest()
        job = getUtility(ICodeImportJobWorkflow).newJob(code_import)
        self.assertSqlAttributeEqualsNow(removeSecurityProxy(job), 'date_due')

    def test_dateDueRecentPreviousResult(self):
        # If there is a CodeImportResult for the CodeImport that is more
        # recent than the effective_update_interval, then the new
        # CodeImportJob has date_due set in the future.
        code_import = self.getCodeImportForDateDueTest()
        # Create a CodeImportResult that started a long time ago. This one
        # must be superseded by the more recent one created below.
        machine = CodeImportMachine.get(1)
        FAILURE = CodeImportResultStatus.FAILURE
        CodeImportResult(
            code_import=code_import, machine=machine, status=FAILURE,
            date_job_started=datetime(2000, 1, 1, 12, 0, 0, tzinfo=UTC),
            date_created=datetime(2000, 1, 1, 12, 5, 0, tzinfo=UTC))
        # Create a CodeImportResult that started a shorter time ago than the
        # effective update interval of the code import. This is the most
        # recent one and must supersede the older one.
        interval = code_import.effective_update_interval
        recent_result = CodeImportResult(
            code_import=code_import, machine=machine, status=FAILURE,
            date_job_started=UTC_NOW - interval / 2)
        # When we create the job, its date_due should be set to the date_due
        # of the job that was deleted when the CodeImport review status
        # changed from REVIEWED. That is the date_job_started of the most
        # recent CodeImportResult plus the effective update interval.
        job = getUtility(ICodeImportJobWorkflow).newJob(code_import)
        self.assertEqual(
            code_import.import_job.date_due,
            recent_result.date_job_started + interval)

    def test_dateDueOldPreviousResult(self):
        # If the most recent CodeImportResult for the CodeImport is older than
        # the effective_update_interval, then new CodeImportJob has date_due
        # set to UTC_NOW.
        code_import = self.getCodeImportForDateDueTest()
        # Create a CodeImportResult that started a long time ago.
        machine = CodeImportMachine.get(1)
        FAILURE = CodeImportResultStatus.FAILURE
        CodeImportResult(
            code_import=code_import, machine=machine, status=FAILURE,
            date_job_started=datetime(2000, 1, 1, 12, 0, 0, tzinfo=UTC),
            date_created=datetime(2000, 1, 1, 12, 5, 0, tzinfo=UTC))
        # When we create the job, its date due must be set to UTC_NOW.
        job = getUtility(ICodeImportJobWorkflow).newJob(code_import)
        self.assertSqlAttributeEqualsNow(removeSecurityProxy(job), 'date_due')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
