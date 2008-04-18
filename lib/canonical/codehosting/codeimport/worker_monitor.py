# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Code to talk to the database about what the worker script is doing."""

__metaclass__ = type
__all__ = []


import os
import sys
import tempfile

from twisted.internet import defer, reactor, task
from twisted.python import failure, log
from twisted.python.util import mergeFunctionMetadata

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import begin, commit, rollback
from canonical.codehosting import get_rocketfuel_root
from canonical.codehosting.codeimport.worker import CodeImportSourceDetails
from canonical.launchpad.interfaces import (
    CodeImportResultStatus, ICodeImportJobSet, ICodeImportJobWorkflow,
    ILibraryFileAliasSet)
from canonical.launchpad.ftests import login, logout, ANONYMOUS
from canonical.launchpad.webapp import canonical_url
from canonical.twistedsupport import defer_to_thread
from canonical.twistedsupport.loggingsupport import (
    log_oops_from_failure)
from canonical.twistedsupport.processmonitor import (
    ProcessMonitorProtocolWithTimeout)


class CodeImportWorkerMonitorProtocol(ProcessMonitorProtocolWithTimeout):
    """The protocol by which the child process talks to the monitor.

    In terms of bytes, the protocol is extremely simple: any output is
    stored in the log file and seen as timeout-resetting activity.
    Every UPDATE_HEARTBEAT_INTERVAL seconds we ask the monitor to
    update the heartbeat of the job we are working on and pass the
    tail of the log output.
    """

    UPDATE_HEARTBEAT_INTERVAL = 30

    def __init__(self, deferred, worker_monitor, log_file, clock=None):
        """Construct an instance.

        :param deferred: See `ProcessMonitorProtocol.__init__` -- the deferred
            that will be fired when the process has exited.
        :param worker_monitor: A `CodeImportWorkerMonitor` instance.
        :param log_file: A file object that the output of the child
            process will be logged to.
        :param clock: A provider of Twisted's IReactorTime.  This parameter
            exists to allow testing that does not depend on an external clock.
            If a clock is not passed in explicitly the reactor is used.
        """
        ProcessMonitorProtocolWithTimeout.__init__(
            self, deferred, clock=clock,
            timeout=config.codeimport.worker_inactivity_timeout)
        self.worker_monitor = worker_monitor
        self._tail = ''
        self._log_file = log_file
        self._looping_call = task.LoopingCall(self._updateHeartbeat)
        self._looping_call.clock = self._clock

    def connectionMade(self):
        """See `BaseProtocol.connectionMade`.

        We call updateHeartbeat for the first time when we are
        connected to the process and every UPDATE_HEARTBEAT_INTERVAL
        seconds thereafter.
        """
        ProcessMonitorProtocolWithTimeout.connectionMade(self)
        self._looping_call.start(self.UPDATE_HEARTBEAT_INTERVAL)

    def _updateHeartbeat(self):
        """Ask the monitor to update the heartbeat.

        We use runNotification() to serialize the updates and ensure
        that any errors are handled properly.  We do not return the
        deferred, as we want this function to be called at a frequency
        independent of how long it takes to update the heartbeat."""
        self.runNotification(
            self.worker_monitor.updateHeartbeat, self._tail)

    def outReceived(self, data):
        """See `ProcessProtocol.outReceived`.

        Any output resets the timeout, is stored in the logfile and
        updates the tail of the log.
        """
        self.resetTimeout()
        self._log_file.write(data)
        self._tail = (self._tail + data)[-100:]

    errReceived = outReceived

    def processEnded(self, reason):
        """See `ProcessMonitorProtocolWithTimeout.processEnded`.

        We stop updating the heartbeat when the process exits.
        """
        ProcessMonitorProtocolWithTimeout.processEnded(self, reason)
        self._looping_call.stop()

def read_only_transaction(function):
    """Wrap 'function' in a transaction and Zope session.

    The transaction is always aborted."""
    def transacted(*args, **kwargs):
        begin()
        login(ANONYMOUS)
        try:
            return function(*args, **kwargs)
        finally:
            logout()
            rollback()
    return mergeFunctionMetadata(function, transacted)


def writing_transaction(function):
    """Wrap 'function' in a transaction and Zope session.

    The transaction is committed if 'function' returns normally and
    aborted if it raises an exception."""
    def transacted(*args, **kwargs):
        begin()
        login(ANONYMOUS)
        try:
            ret = function(*args, **kwargs)
        except:
            logout()
            rollback()
            raise
        logout()
        commit()
        return ret
    return mergeFunctionMetadata(function, transacted)


class ExitQuietly(Exception):
    """Raised to indicate that we should abort and exit without fuss.

    Raised when the job we are working on disappears, as we assume
    this is the result of the job being killed or reclaimed.
    """
    pass


class CodeImportWorkerMonitor:
    """Controller for a single import job.

    An instance of `CodeImportWorkerMonitor` runs a child process to
    perform an import and communicates status to the database.
    """

    path_to_script = os.path.join(
        get_rocketfuel_root(),
        'scripts', 'code-import-worker.py')

    def __init__(self, job_id, logger):
        """Construct an instance.

        :param job_id: The ID of the CodeImportJob we are to work on.
        :param logger: A `Logger` object.
        """
        self._logger = logger
        self._job_id = job_id
        self._call_finish_job = True
        self._log_file = tempfile.TemporaryFile()
        self._source_details = None
        self._code_import_id = None
        self._branch_url = None

    def _logOopsFromFailure(self, failure):
        request = log_oops_from_failure(
            failure, code_import_job_id=self._job_id,
            code_import_id=self._code_import_id, URL=self._branch_url)
        self._logger.info(
            "Logged OOPS id %s: %s: %s",
            request.oopsid, failure.type.__name__, failure.value)

    def getJob(self):
        """Fetch the `CodeImportJob` object we are working on from the DB.

        Only call this from defer_to_thread-ed methods!

        :raises ExitQuietly: if the job is not found.
        """
        job = getUtility(ICodeImportJobSet).getById(self._job_id)
        if job is None:
            self._logger.info(
                "Job %d not found, exiting quietly.", self._job_id)
            self._call_finish_job = False
            raise ExitQuietly
        else:
            return job

    @defer_to_thread
    @read_only_transaction
    def getSourceDetails(self):
        """Get a `CodeImportSourceDetails` for the job we are working on."""
        code_import = self.getJob().code_import
        source_details = CodeImportSourceDetails.fromCodeImport(code_import)
        self._logger.info(
            'Found source details: %s', source_details.asArguments())
        self._branch_url = canonical_url(code_import.branch)
        self._code_import_id = code_import.id
        return source_details

    @defer_to_thread
    @writing_transaction
    def updateHeartbeat(self, tail):
        """Call the updateHeartbeat method for the job we are working on."""
        self._logger.debug("Updating heartbeat.")
        getUtility(ICodeImportJobWorkflow).updateHeartbeat(
            self.getJob(), tail)

    def _createLibrarianFileAlias(self, name, size, file, contentType):
        """Call `ILibraryFileAliasSet.create` with the given parameters.

        This is a separate method that exists only to be patched in
        tests.
        """
        return getUtility(ILibraryFileAliasSet).create(
            name, size, file, contentType)

    @defer_to_thread
    @writing_transaction
    def finishJob(self, status):
        """Call the finishJob method for the job we are working on.

        This method uploads the log file to the librarian first.  If this
        fails, we still try to call finishJob, but return the librarian's
        failure if finishJob succeeded (if finishJob fails, that exception
        'wins').
        """
        job = self.getJob()
        log_file_size = self._log_file.tell()
        librarian_failure = None
        if log_file_size > 0:
            self._log_file.seek(0)
            branch = job.code_import.branch
            log_file_name = '%s-%s-log.txt' % (
                branch.product.name, branch.name)
            try:
                log_file_alias = self._createLibrarianFileAlias(
                    log_file_name, log_file_size, self._log_file,
                    'text/plain')
                self._logger.info(
                    "Uploaded logs to librarian %s.", log_file_alias.getURL())
            except:
                self._logger.error("Upload to librarian failed.")
                self._logOopsFromFailure(failure.Failure())
                log_file_alias = None
        else:
            log_file_alias = None
        getUtility(ICodeImportJobWorkflow).finishJob(
            job, status, log_file_alias)

    def _launchProcess(self, source_details):
        """Launch the code-import-worker.py child process."""
        deferred = defer.Deferred()
        protocol = CodeImportWorkerMonitorProtocol(
            deferred, self, self._log_file)
        command = [sys.executable, self.path_to_script]
        command.extend(source_details.asArguments())
        self._logger.info(
            "Launching worker child process %s.", command)
        reactor.spawnProcess(
            protocol, sys.executable, command, env=os.environ, usePTY=True)
        return deferred

    def run(self):
        """Perform the import."""
        return self.getSourceDetails().addCallback(
            self._launchProcess).addBoth(
            self.callFinishJob).addErrback(
            self._silenceQuietExit)

    def _silenceQuietExit(self, failure):
        """Quietly swallow a ExitQuietly failure."""
        failure.trap(ExitQuietly)
        return None

    def callFinishJob(self, reason):
        """Call finishJob() with the appropriate status."""
        if not self._call_finish_job:
            return reason
        if isinstance(reason, failure.Failure):
            self._log_file.write("Import failed:\n")
            reason.printTraceback(self._log_file)
            self._logOopsFromFailure(reason)
            status = CodeImportResultStatus.FAILURE
        else:
            self._logger.info('Import succeeded.')
            status = CodeImportResultStatus.SUCCESS
        return self.finishJob(status)

