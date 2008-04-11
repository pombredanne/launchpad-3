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
    aborted if it raises."""
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


class ExitWithoutCallingFinishJob(Exception):
    """A special exception to be raised when we should exit quietly.

    """
    pass


@defer_to_thread
@writing_transaction
def finish_job(job_id, status, log_file_object):
    """Call `finishJob` for the job of id 'job_id'."""
    job = getUtility(ICodeImportJobSet).getById(job_id)
    if job is None:
        return
    log_file_size = log_file_object.tell()
    if log_file_size > 0:
        log_file_object.seek(0)
        branch = job.code_import.branch
        log_file_name = '%s-%s-log.txt' % (branch.product.name, branch.name)
        # Watch out for this failing!!
        log_file_alias = getUtility(ILibraryFileAliasSet).create(
            log_file_name, log_file_size, log_file_object,
            'text/plain')
    else:
        log_file_alias = None
    getUtility(ICodeImportJobWorkflow).finishJob(job, status, log_file_alias)


@defer_to_thread
@read_only_transaction
def get_source_details(job_id):
    """Get a `CodeImportSourceDetails` object for the job of id 'job_id'."""
    job = getUtility(ICodeImportJobSet).getById(job_id)
    if job is None:
        raise ExitWithoutCallingFinishJob
    return CodeImportSourceDetails.fromCodeImport(
        job.code_import)


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


class CodeImportWorkerMonitor:

    path_to_script = os.path.join(
        get_rocketfuel_root(),
        'scripts', 'code-import-worker.py')

    def __init__(self, job_id, logger):
        self.job_id = job_id
        self.call_finish_job = True
        self.logger = logger

    @defer_to_thread
    @writing_transaction
    def updateHeartbeat(self, tail):
        """Call `updateHeartbeat` for the job of id 'job_id'."""
        job = getUtility(ICodeImportJobSet).getById(self.job_id)
        if job is None:
            self.call_finish_job = False
            raise ExitWithoutCallingFinishJob
        getUtility(ICodeImportJobWorkflow).updateHeartbeat(job, tail)

    def _launchProcess(self, source_details):
        deferred = defer.Deferred()
        self.tmpfile = tempfile.TemporaryFile()
        protocol = CodeImportWorkerMonitorProtocol(
            deferred, self.job_id, self.tmpfile)
        command = [sys.executable, self.path_to_script]
        command.extend(source_details.asArguments())
        print command
        reactor.spawnProcess(
            protocol, sys.executable, command, env=os.environ, usePTY=True)
        deferred.addErrback(self._silenceQuietDeath)
        deferred.addBoth(self.callFinishJob)
        return deferred

    def run(self):
        return get_source_details(self.job_id).addCallback(
            self._launchProcess)

    def _silenceQuietDeath(self, failure):
        failure.trap(ExitWithoutCallingFinishJob)
        self.call_finish_job = False
        return None

    def callFinishJob(self, reason):
        if not self.call_finish_job:
            return
        if isinstance(reason, failure.Failure):
            status = CodeImportResultStatus.FAILURE
        else:
            status = CodeImportResultStatus.SUCCESS
        return finish_job(self.job_id, status, self.tmpfile)

