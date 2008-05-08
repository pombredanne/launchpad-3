# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Database classes for the CodeImportJob table."""

__metaclass__ = type
__all__ = [
    'CodeImportJob',
    'CodeImportJobSet',
    'CodeImportJobWorkflow',
    ]

from sqlobject import ForeignKey, IntCol, SQLObjectNotFound, StringCol

from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.database.codeimportresult import CodeImportResult
from canonical.launchpad.interfaces import (
    CodeImportJobState, CodeImportMachineState, CodeImportResultStatus,
    CodeImportReviewStatus, ICodeImportEventSet, ICodeImportJob,
    ICodeImportJobSet, ICodeImportJobSetPublic, ICodeImportJobWorkflow,
    ICodeImportJobWorkflowPublic, ICodeImportMachineSet, ICodeImportResultSet)
from canonical.launchpad.validators.person import public_person_validator


class CodeImportJob(SQLBase):
    """See `ICodeImportJob`."""

    implements(ICodeImportJob)

    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    code_import = ForeignKey(
        dbName='code_import', foreignKey='CodeImport', notNull=True)

    machine = ForeignKey(
        dbName='machine', foreignKey='CodeImportMachine',
        notNull=False, default=None)

    date_due = UtcDateTimeCol(notNull=True)

    state = EnumCol(
        enum=CodeImportJobState, notNull=True,
        default=CodeImportJobState.PENDING)

    requesting_user = ForeignKey(
        dbName='requesting_user', foreignKey='Person',
        validator=public_person_validator,
        notNull=False, default=None)

    ordering = IntCol(notNull=False, default=None)

    heartbeat = UtcDateTimeCol(notNull=False, default=None)

    logtail = StringCol(notNull=False, default=None)

    date_started = UtcDateTimeCol(notNull=False, default=None)

    def isOverdue(self):
        """See `ICodeImportJob`."""
        # SQLObject offers no easy way to compare a timestamp to UTC_NOW, so
        # we must use trickery here.

        # First we flush any pending update to self to ensure that the
        # following database query will give the correct result even if
        # date_due was modified in this transaction.
        self.syncUpdate()

        # Then, we try to find a CodeImportJob object with the id of self, and
        # a date_due of now or past. If we find one, this means self is
        # overdue.
        import_job = CodeImportJob.selectOne(
            "id = %s AND date_due <= %s" % sqlvalues(self.id, UTC_NOW))
        return import_job is not None


class CodeImportJobSet(object):
    """See `ICodeImportJobSet`."""

    implements(ICodeImportJobSet, ICodeImportJobSetPublic)

    # CodeImportJob database objects are created using
    # CodeImportJobWorkflow.newJob.

    def getById(self, id):
        """See `ICodeImportJobSet`."""
        try:
            return CodeImportJob.get(id)
        except SQLObjectNotFound:
            return None

    def getJobForMachine(self, hostname):
        """See `ICodeImportJobSet`."""
        machine = getUtility(ICodeImportMachineSet).getByHostname(hostname)
        if machine is None:
            machine = getUtility(ICodeImportMachineSet).new(
                hostname, CodeImportMachineState.ONLINE)
        elif not machine.shouldLookForJob():
            return None
        job = CodeImportJob.selectOne(
            """id IN (SELECT id FROM CodeImportJob
               WHERE date_due <= %s AND state = %s
               ORDER BY requesting_user IS NULL, date_due
               LIMIT 1)"""
            % sqlvalues(UTC_NOW, CodeImportJobState.PENDING))
        if job is not None:
            getUtility(ICodeImportJobWorkflow).startJob(job, machine)
            return job
        else:
            return None


class CodeImportJobWorkflow:
    """See `ICodeImportJobWorkflow`."""

    implements(ICodeImportJobWorkflow, ICodeImportJobWorkflowPublic)

    def newJob(self, code_import):
        """See `ICodeImportJobWorkflow`."""
        assert code_import.review_status == CodeImportReviewStatus.REVIEWED, (
            "Review status of %s is not REVIEWED: %s" % (
            code_import.branch.unique_name, code_import.review_status.name))
        assert code_import.import_job is None, (
            "Already associated to a CodeImportJob: %s" % (
            code_import.branch.unique_name))

        job = CodeImportJob(code_import=code_import, date_due=UTC_NOW)

        # Find the most recent CodeImportResult for this CodeImport. We sort
        # by date_created because we do not have an index on date_job_started
        # in the database, and that should give the same sort order.
        most_recent_result_list = list(CodeImportResult.selectBy(
            code_import=code_import).orderBy(['-date_created']).limit(1))

        if len(most_recent_result_list) != 0:
            [most_recent_result] = most_recent_result_list
            interval = code_import.effective_update_interval
            date_due = most_recent_result.date_job_started + interval
            job.date_due = max(job.date_due, date_due)
            job.sync()

        return job

    def deletePendingJob(self, code_import):
        """See `ICodeImportJobWorkflow`."""
        assert code_import.review_status != CodeImportReviewStatus.REVIEWED, (
            "The review status of %s is %s." % (
            code_import.branch.unique_name, code_import.review_status.name))
        assert code_import.import_job is not None, (
            "Not associated to a CodeImportJob: %s" % (
            code_import.branch.unique_name,))
        assert code_import.import_job.state == CodeImportJobState.PENDING, (
            "The CodeImportJob associated to %s is %s." % (
            code_import.branch.unique_name,
            code_import.import_job.state.name))
        # CodeImportJobWorkflow is the only class that is allowed to delete
        # CodeImportJob rows, so destroySelf is not exposed in ICodeImportJob.
        removeSecurityProxy(code_import).import_job.destroySelf()

    def requestJob(self, import_job, user):
        """See `ICodeImportJobWorkflow`."""
        assert import_job.state == CodeImportJobState.PENDING, (
            "The CodeImportJob associated with %s is %s."
            % (import_job.code_import.branch.unique_name,
               import_job.state.name))
        assert import_job.requesting_user is None, (
            "The CodeImportJob associated with %s "
            "was already requested by %s."
            % (import_job.code_import.branch.unique_name,
               import_job.requesting_user.name))
        # CodeImportJobWorkflow is the only class that is allowed to set the
        # date_due and requesting_user attributes of CodeImportJob, they are
        # not settable through ICodeImportJob. So we must use
        # removeSecurityProxy here.
        if not import_job.isOverdue():
            removeSecurityProxy(import_job).date_due = UTC_NOW
        removeSecurityProxy(import_job).requesting_user = user
        getUtility(ICodeImportEventSet).newRequest(
            import_job.code_import, user)

    def startJob(self, import_job, machine):
        """See `ICodeImportJobWorkflow`."""
        assert import_job.state == CodeImportJobState.PENDING, (
            "The CodeImportJob associated with %s is %s."
            % (import_job.code_import.branch.unique_name,
               import_job.state.name))
        assert machine.state == CodeImportMachineState.ONLINE, (
            "The machine %s is %s."
            % (machine.hostname, machine.state.name))
        # CodeImportJobWorkflow is the only class that is allowed to set the
        # date_created, heartbeat, logtail, machine and state attributes of
        # CodeImportJob, they are not settable through ICodeImportJob. So we
        # must use removeSecurityProxy here.
        naked_job = removeSecurityProxy(import_job)
        naked_job.date_started = UTC_NOW
        naked_job.heartbeat = UTC_NOW
        naked_job.logtail = u''
        naked_job.machine = machine
        naked_job.state = CodeImportJobState.RUNNING
        getUtility(ICodeImportEventSet).newStart(
            import_job.code_import, machine)

    def updateHeartbeat(self, import_job, logtail):
        """See `ICodeImportJobWorkflow`."""
        assert import_job.state == CodeImportJobState.RUNNING, (
            "The CodeImportJob associated with %s is %s."
            % (import_job.code_import.branch.unique_name,
               import_job.state.name))
        # CodeImportJobWorkflow is the only class that is allowed to
        # set the heartbeat and logtail attributes of CodeImportJob,
        # they are not settable through ICodeImportJob. So we must use
        # removeSecurityProxy here.
        naked_job = removeSecurityProxy(import_job)
        naked_job.heartbeat = UTC_NOW
        naked_job.logtail = logtail

    def finishJob(self, import_job, status, logfile_alias):
        """See `ICodeImportJobWorkflow`."""
        assert import_job.state == CodeImportJobState.RUNNING, (
            "The CodeImportJob associated with %s is %s."
            % (import_job.code_import.branch.unique_name,
               import_job.state.name))
        code_import = import_job.code_import
        machine = import_job.machine
        result = getUtility(ICodeImportResultSet).new(
            code_import=code_import, machine=machine,
            log_excerpt=import_job.logtail,
            requesting_user=import_job.requesting_user,
            log_file=logfile_alias, status=status,
            date_job_started=import_job.date_started)
        # CodeImportJobWorkflow is the only class that is allowed to delete
        # CodeImportJob objects, there is no method in the ICodeImportJob
        # interface to do this. So we must use removeSecurityProxy here.
        naked_job = removeSecurityProxy(import_job)
        naked_job.destroySelf()
        # Only start a new one if not invalid or suspended.
        if code_import.review_status == CodeImportReviewStatus.REVIEWED:
            self.newJob(code_import)
        # If the status was successful, update the date_last_successful and
        # arrange for the branch to be mirrored.
        if status == CodeImportResultStatus.SUCCESS:
            naked_import = removeSecurityProxy(code_import)
            naked_import.date_last_successful = result.date_created
            code_import.branch.requestMirror()
        getUtility(ICodeImportEventSet).newFinish(
            code_import, machine)
