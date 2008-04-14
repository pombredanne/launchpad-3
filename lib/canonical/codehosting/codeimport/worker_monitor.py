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

from canonical.database.sqlbase import begin, commit, rollback
from canonical.codehosting import get_rocketfuel_root
from canonical.codehosting.codeimport.worker import CodeImportSourceDetails
from canonical.launchpad.interfaces import (
    CodeImportResultStatus, ICodeImportJobSet, ICodeImportJobWorkflow,
    ILibraryFileAliasSet)
from canonical.launchpad.ftests import login, logout, ANONYMOUS
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.lp import initZopeless
from canonical.twistedsupport import defer_to_thread
from canonical.twistedsupport.processmonitor import (
    ProcessMonitorProtocolWithTimeout)


class CodeImportWorkerMonitorProtocol(ProcessMonitorProtocolWithTimeout):

    UPDATE_HEARTBEAT_INTERVAL = 30

    def __init__(self, deferred, worker_monitor, log_file, clock=None):
        ProcessMonitorProtocolWithTimeout.__init__(self, deferred, 100, clock)
        self.worker_monitor = worker_monitor
        self._tail = ''
        self._log_file = log_file
        self._looping_call = task.LoopingCall(self._updateHeartbeat)
        self._looping_call.clock = self._clock

    def connectionMade(self):
        ProcessMonitorProtocolWithTimeout.connectionMade(self)
        self._looping_call.start(self.UPDATE_HEARTBEAT_INTERVAL)

    def _updateHeartbeat(self):
        self.runNotification(
            self.worker_monitor.updateHeartbeat, self._tail)

    def outReceived(self, data):
        self._log_file.write(data)
        self._tail = (self._tail + data)[-100:]

    errReceived = outReceived

    def processEnded(self, reason):
        ProcessMonitorProtocolWithTimeout.processEnded(self, reason)
        self._looping_call.stop()

def read_only_transaction(function):
    """XXX."""
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
    """XXX."""
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
    pass


class CodeImportWorkerMonitor:

    path_to_script = os.path.join(
        get_rocketfuel_root(),
        'scripts', 'code-import-worker.py')

    def __init__(self, job_id):
        self._job_id = job_id
        self._call_finish_job = True
        self._log_file = tempfile.TemporaryFile()

    def begin(self):
        begin()
        login(ANONYMOUS)

    def rollback(self):
        logout()
        rollback()

    def commit(self):
        logout()
        commit()

    def getJob(self):
        """Only call this from defer_to_thread-ed methods!"""
        job = getUtility(ICodeImportJobSet).getById(self._job_id)
        if job is None:
            self._call_finish_job = False
            raise ExitQuietly
        else:
            return job

    @defer_to_thread
    @read_only_transaction
    def getSourceDetails(self):
        """XXX."""
        return CodeImportSourceDetails.fromCodeImport(
            self.getJob().code_import)

    @defer_to_thread
    @writing_transaction
    def updateHeartbeat(self, tail):
        """XXX."""
        getUtility(ICodeImportJobWorkflow).updateHeartbeat(
            self.getJob(), tail)

    @defer_to_thread
    @writing_transaction
    def finishJob(self, status):
        """XXX."""
        job = self.getJob()
        log_file_size = self._log_file.tell()
        if log_file_size > 0:
            self._log_file.seek(0)
            branch = job.code_import.branch
            log_file_name = '%s-%s-log.txt' % (branch.product.name, branch.name)
            # Watch out for this failing!!
            log_file_alias = getUtility(ILibraryFileAliasSet).create(
                log_file_name, log_file_size, self._log_file,
                'text/plain')
        else:
            log_file_alias = None
        getUtility(ICodeImportJobWorkflow).finishJob(
            job, status, log_file_alias)

    def _launchProcess(self, source_details):
        deferred = defer.Deferred()
        protocol = CodeImportWorkerMonitorProtocol(
            deferred, self, self._log_file)
        command = [sys.executable, self.path_to_script]
        command.extend(source_details.asArguments())
        reactor.spawnProcess(
            protocol, sys.executable, command, env=os.environ, usePTY=True)
        return deferred

    def run(self):
        return self.getSourceDetails().addCallback(
            self._launchProcess).addBoth(
            self.callFinishJob).addErrback(
            self._silenceQuietExit)

    def _silenceQuietExit(self, failure):
        failure.trap(ExitQuietly)
        return None

    def callFinishJob(self, reason):
        if not self._call_finish_job:
            return reason
        if isinstance(reason, failure.Failure):
            self._log_file.write("Import failed:\n")
            reason.printTraceback(self._log_file)
            status = CodeImportResultStatus.FAILURE
        else:
            status = CodeImportResultStatus.SUCCESS
        return self.finishJob(status)

