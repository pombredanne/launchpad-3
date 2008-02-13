# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Unit tests for CodeImportJob and CodeImportJobWorkflow."""

__metaclass__ = type

__all__ = ['NewEvents', 'test_suite']

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
    CodeImportJobState, CodeImportResultStatus, CodeImportEventType,
    CodeImportReviewStatus, ICodeImportEventSet, ICodeImportJobSet,
    ICodeImportSet, ICodeImportJobWorkflow)
from canonical.launchpad.ftests import login
from canonical.launchpad.testing import LaunchpadObjectFactory
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


class AssertSqlDateMixin:
    """Helper to test SQL date values."""

    def assertSqlAttributeEqualsDate(self, sql_object, attribute_name, date):
        """Fail unless the value of the attribute is equal to the date.

        Use this method to test that date value that may be UTC_NOW is equal
        to another date value. Trickery is required because SQLBuilder truth
        semantics cause UTC_NOW to appear equal to all dates.

        :param sql_object: a security-proxied SQLObject instance.
        :param attribute_name: the name of a database column in the table
            associated to this object.
        :param date: `datetime.datetime` object or `UTC_NOW`.
        """
        sql_object = removeSecurityProxy(sql_object)
        sql_object.syncUpdate()
        sql_class = type(sql_object)
        found_object = sql_class.selectOne(
            'id=%%s AND %s=%%s' % (attribute_name,)
            % sqlvalues(sql_object.id, date))
        if found_object is None:
            self.fail(
                "Expected %s to be %s, but it was %s."
                % (attribute_name, date, getattr(sql_object, attribute_name)))


class NewEvents(object):
    """Help in testing the creation of CodeImportEvent objects.

    To test that an operation creates CodeImportEvent objects, create an
    NewEvent object, perform the operation, then test the value of the
    NewEvents instance.

    Doctests should print the NewEvent object, and unittests should iterate
    over it.
    """

    def __init__(self):
        event_set = getUtility(ICodeImportEventSet)
        self.initial = set(event.id for event in event_set.getAll())

    def summary(self):
        """Render a summary of the newly created CodeImportEvent objects."""
        lines = []
        for event in self:
            words = []
            words.append(event.event_type.name)
            if event.code_import is not None:
                words.append(event.code_import.branch.unique_name)
            if event.machine is not None:
                words.append(event.machine.hostname)
            if event.person is not None:
                words.append(event.person.name)
            lines.append(' '.join(words))
        return '\n'.join(lines)

    def __iter__(self):
        """Iterate over the newly created CodeImportEvent objects."""
        event_set = getUtility(ICodeImportEventSet)
        for event in event_set.getAll():
            if event.id in self.initial:
                continue
            yield event


class AssertEventMixin:
    """Helper to test that a CodeImportEvent has the expected values."""

    def assertEventLike(
            self, import_event, event_type, code_import,
            machine=None, person=None):
        """Fail unless `import_event` has the expected attribute values.

        :param import_event: The `CodeImportEvent` to test.
        :param event_type: expected value of import_event.event_type.
        :param code_import: expected value of import_event.code_import.
        :param machine: expected value of import_event.machine.
        :param person: expected value of import_event.person.
        """
        self.assertEqual(import_event.event_type, event_type)
        self.assertEqual(import_event.code_import, code_import)
        self.assertEqual(import_event.machine, machine)
        self.assertEqual(import_event.person, person)


class TestCodeImportJobWorkflowNewJob(unittest.TestCase,
        AssertFailureMixin, AssertSqlDateMixin):
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
        # Testing newJob failure.
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
        self.assertSqlAttributeEqualsDate(job, 'date_due', UTC_NOW)

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
        self.assertSqlAttributeEqualsDate(
            code_import.import_job, 'date_due',
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
        self.assertSqlAttributeEqualsDate(job, 'date_due', UTC_NOW)


class TestCodeImportJobWorkflowDeletePendingJob(unittest.TestCase,
        AssertFailureMixin):
    """Unit tests for CodeImportJobWorkflow.deletePendingJob."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login_for_code_imports()

    def test_wrongReviewStatus(self):
        # CodeImportJobWorkflow.deletePendingJob fails if the
        # CodeImport review_status is equal to REVIEWED.
        reviewed_import = getUtility(ICodeImportSet).get(1)
        # Checking sampledata expectations.
        self.assertEqual(reviewed_import.branch.unique_name,
                         '~vcs-imports/gnome-terminal/import')
        REVIEWED = CodeImportReviewStatus.REVIEWED
        self.assertEqual(reviewed_import.review_status, REVIEWED)
        # Testing deletePendingJob failure.
        self.assertFailure(
            "The review status of ~vcs-imports/gnome-terminal/import "
            "is REVIEWED.",
            getUtility(ICodeImportJobWorkflow).deletePendingJob,
            reviewed_import)

    def test_noJob(self):
        # CodeImportJobWorkflow.deletePendingJob fails if the
        # CodeImport is not associated to a CodeImportJob.
        new_import = getUtility(ICodeImportSet).get(2)
        # Checking sampledata expectations.
        self.assertEqual(new_import.branch.unique_name,
                         '~vcs-imports/evolution/import')
        NEW = CodeImportReviewStatus.NEW
        self.assertEqual(new_import.review_status, NEW)
        self.assertEqual(new_import.import_job, None)
        # Testing deletePendingJob failure.
        self.assertFailure(
            "Not associated to a CodeImportJob: "
            "~vcs-imports/evolution/import",
            getUtility(ICodeImportJobWorkflow).deletePendingJob,
            new_import)

    def test_wrongJobState(self):
        # CodeImportJobWorkflow.deletePendingJob fails if the state of
        # the CodeImportJob is different from PENDING.
        reviewed_import = getUtility(ICodeImportSet).get(1)
        # Checking sampledata expectations.
        self.assertEqual(reviewed_import.branch.unique_name,
                         '~vcs-imports/gnome-terminal/import')
        # ICodeImport does not allow setting any attribute, so we need to use
        # removeSecurityProxy to set the review_status attribute.
        INVALID = CodeImportReviewStatus.INVALID
        removeSecurityProxy(reviewed_import).review_status = INVALID
        self.assertNotEqual(reviewed_import.import_job, None)
        # ICodeImportJob does not allow setting 'state', so we must
        # use removeSecurityProxy.
        RUNNING = CodeImportJobState.RUNNING
        removeSecurityProxy(reviewed_import.import_job).state = RUNNING
        # Testing deletePendingJob failure.
        self.assertFailure(
            "The CodeImportJob associated to "
            "~vcs-imports/gnome-terminal/import is RUNNING.",
            getUtility(ICodeImportJobWorkflow).deletePendingJob,
            reviewed_import)


class TestCodeImportJobWorkflowRequestJob(unittest.TestCase,
        AssertFailureMixin, AssertSqlDateMixin, AssertEventMixin):
    """Unit tests for CodeImportJobWorkflow.requestJob."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login_for_code_imports()
        self.factory = LaunchpadObjectFactory()

    def test_wrongJobState(self):
        # CodeImportJobWorkflow.requestJob fails if the state of the
        # CodeImportJob is different from PENDING.
        code_import = self.factory.makeCodeImport()
        import_job = self.factory.makeCodeImportJob(code_import)
        person = self.factory.makePerson()
        # ICodeImportJob does not allow setting 'state', so we must
        # use removeSecurityProxy.
        removeSecurityProxy(import_job).state = CodeImportJobState.RUNNING
        self.assertFailure(
            "The CodeImportJob associated with %s is "
            "RUNNING." % code_import.branch.unique_name,
            getUtility(ICodeImportJobWorkflow).requestJob,
            import_job, person)

    def test_alreadyRequested(self):
        # CodeImportJobWorkflow.requestJob fails if the job was requested
        # already, that is, if its requesting_user attribute is set.
        code_import = self.factory.makeCodeImport()
        import_job = self.factory.makeCodeImportJob(code_import)
        person = self.factory.makePerson()
        other_person = self.factory.makePerson()
        # ICodeImportJob does not allow setting requesting_user, so we must
        # use removeSecurityProxy.
        removeSecurityProxy(import_job).requesting_user = person
        self.assertFailure(
            "The CodeImportJob associated with %s was already requested by "
            "%s." % (code_import.branch.unique_name, person.name),
            getUtility(ICodeImportJobWorkflow).requestJob,
            import_job, other_person)

    def test_requestFutureJob(self):
        # CodeImportJobWorkflow.requestJob sets requesting_user and
        # date_due if the current date_due is in the future.
        code_import = self.factory.makeCodeImport()
        pending_job = self.factory.makeCodeImportJob(code_import)
        person = self.factory.makePerson()
        # Set date_due in the future. ICodeImportJob does not allow setting
        # date_due, so we must use removeSecurityProxy.
        removeSecurityProxy(pending_job).date_due = (
            datetime(2100, 1, 1, tzinfo=UTC))
        # requestJob sets both requesting_user and date_due.
        new_events = NewEvents()
        getUtility(ICodeImportJobWorkflow).requestJob(
            pending_job, person)
        self.assertEqual(pending_job.requesting_user, person)
        self.assertSqlAttributeEqualsDate(pending_job, 'date_due', UTC_NOW)
        # When requestJob is successful, it creates a REQUEST event.
        [request_event] = list(new_events)
        self.assertEventLike(
            request_event, CodeImportEventType.REQUEST,
            pending_job.code_import, person=person)

    def test_requestOverdueJob(self):
        # CodeImportJobWorkflow.requestJob only sets requesting_user if the
        # date_due is already past.
        code_import = self.factory.makeCodeImport()
        pending_job = self.factory.makeCodeImportJob(code_import)
        person = self.factory.makePerson()
        # Set date_due in the past. ICodeImportJob does not allow setting
        # date_due, so we must use removeSecurityProxy.
        past_date = datetime(1900, 1, 1, tzinfo=UTC)
        removeSecurityProxy(pending_job).date_due = past_date
        # requestJob only sets requesting_user.
        new_events = NewEvents()
        getUtility(ICodeImportJobWorkflow).requestJob(
            pending_job, person)
        self.assertEqual(pending_job.requesting_user, person)
        self.assertSqlAttributeEqualsDate(
            pending_job, 'date_due', past_date)
        # When requestJob is successful, it creates a REQUEST event.
        [request_event] = list(new_events)
        self.assertEventLike(
            request_event, CodeImportEventType.REQUEST,
            pending_job.code_import, person=person)


class TestCodeImportJobWorkflowStartJob(unittest.TestCase,
        AssertFailureMixin, AssertSqlDateMixin, AssertEventMixin):
    """Unit tests for CodeImportJobWorkflow.startJob."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login_for_code_imports()
        self.factory = LaunchpadObjectFactory()

    def test_wrongJobState(self):
        # Calling startJob with a job whose state is not PENDING is an error.
        machine = self.factory.makeCodeImportMachine()
        code_import = self.factory.makeCodeImport()
        job = self.factory.makeCodeImportJob(code_import)
        # ICodeImportJob does not allow setting 'state', so we must
        # use removeSecurityProxy.
        RUNNING = CodeImportJobState.RUNNING
        removeSecurityProxy(job).state = RUNNING
        # Machines are OFFLINE when they are created.
        machine.setOnline()
        # Testing startJob failure.
        self.assertFailure(
            "The CodeImportJob associated with %s is "
            "RUNNING." % code_import.branch.unique_name,
            getUtility(ICodeImportJobWorkflow).requestJob,
            job, machine)

    def test_offlineMachine(self):
        # Calling startJob with a machine which is not ONLINE is an error.
        machine = self.factory.makeCodeImportMachine()
        code_import = self.factory.makeCodeImport()
        job = self.factory.makeCodeImportJob(code_import)
        # Testing startJob failure.
        self.assertFailure(
            "The machine %s is OFFLINE." % machine.hostname,
            getUtility(ICodeImportJobWorkflow).startJob,
            job, machine)

class TestCodeImportJobWorkflowUpdateHeartbeat(unittest.TestCase,
        AssertFailureMixin, AssertSqlDateMixin, AssertEventMixin):
    """Unit tests for CodeImportJobWorkflow.startJob."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login_for_code_imports()
        self.factory = LaunchpadObjectFactory()

    def test_wrongJobState(self):
        # Calling updateHeartbeat with a job whose state is not RUNNING is an
        # error.
        machine = self.factory.makeCodeImportMachine()
        code_import = self.factory.makeCodeImport()
        job = self.factory.makeCodeImportJob(code_import)
        self.assertFailure(
            "The CodeImportJob associated with %s is "
            "PENDING." % code_import.branch.unique_name,
            getUtility(ICodeImportJobWorkflow).updateHeartbeat,
            job, u'')

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
