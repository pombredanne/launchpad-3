# Copyright 2006 Canonical Ltd.  All rights reserved.

import os
import socket
import subprocess
import sys

from twisted.internet import defer, error, reactor
from twisted.internet.protocol import ProcessProtocol
from twisted.protocols.policies import TimeoutMixin
from twisted.python import failure

from contrib.glock import GlobalLock, LockAlreadyAcquired

import canonical
from canonical.codehosting import branch_id_to_path
from canonical.config import config
from canonical.launchpad.scripts.supermirror.branchtomirror import (
    BranchToMirror)


MAXIMUM_PROCESSES = 5

# Time in seconds.
INACTIVITY_TIMEOUT = 5


class FireOnExit(ProcessProtocol, TimeoutMixin):

    def __init__(self, deferred, timeout_period):
        self.deferred = deferred
        self._output = ''
        self._error = ''
        self.setTimeout(timeout_period)

    def outReceived(self, data):
        ProcessProtocol.outReceived(self, data)
        self.resetTimeout()
        self._output += data

    def errReceived(self, data):
        ProcessProtocol.errReceived(self, data)
        self.resetTimeout()
        self._error += data

    def processEnded(self, reason):
        ProcessProtocol.processEnded(self, reason)
        self.setTimeout(None)
        self.deferred, deferred = None, self.deferred
        if reason.check(error.ConnectionDone):
            deferred.callback(None)
        else:
            deferred.errback(failure.Failure(Exception(self._error)))


class JobManager:
    """Schedule and manage the mirroring of branches.

    The jobmanager is responsible for organizing the mirroring of all
    branches.
    """

    def __init__(self, branch_status_client, branch_type):
        self.branch_status_client = branch_status_client
        self.branches_to_mirror = []
        self.actualLock = None
        self.branch_type = branch_type
        self.name = 'branch-puller-%s' % branch_type.name.lower()
        self.lockfilename = '/var/lock/launchpad-%s.lock' % self.name
        self._addBranches(
            branch_status_client.getBranchPullQueue(branch_type.name))

    def run(self, logger):
        """Run all branches_to_mirror registered with the JobManager"""
        logger.info('%d branches to mirror', len(self.branches_to_mirror))
        semaphore = defer.DeferredSemaphore(MAXIMUM_PROCESSES)
        deferreds = [
            semaphore.run(self.mirror, branch_to_mirror, logger)
            for branch_to_mirror in self.branches_to_mirror]
        deferred = defer.gatherResults(deferreds)
        deferred.addCallback(self._finishedRunning, logger)
        return deferred

    def _finishedRunning(self, ignored, logger):
        self.branches_to_mirror = []
        logger.info('Mirroring complete')

    def mirror(self, branch_to_mirror, logger):
        path_to_script = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(canonical.__file__))),
            'scripts/mirror-branch.py')
        deferred = defer.Deferred()
        protocol = FireOnExit(deferred, INACTIVITY_TIMEOUT)
        command = [sys.executable, path_to_script] + branch_to_mirror
        reactor.spawnProcess(protocol, sys.executable, command)
        return deferred

    def _addBranches(self, branches_to_pull):
        for branch_id, branch_src, unique_name in branches_to_pull:
            self.branches_to_mirror.append(
                self.getBranchToMirror(branch_id, branch_src, unique_name))

    def getBranchToMirror(self, branch_id, branch_src, unique_name):
        branch_src = branch_src.strip()
        path = branch_id_to_path(branch_id)
        branch_dest = os.path.join(config.supermirror.branchesdest, path)
        return [
            branch_src, branch_dest, str(branch_id), unique_name,
            self.branch_type.name]

    def lock(self):
        self.actualLock = GlobalLock(self.lockfilename)
        try:
            self.actualLock.acquire()
        except LockAlreadyAcquired:
            raise LockError(self.lockfilename)

    def unlock(self):
        self.actualLock.release()

    def recordActivity(self, date_started, date_completed):
        """Record successful completion of the script."""
        self.branch_status_client.recordSuccess(
            self.name, socket.gethostname(), date_started, date_completed)


class LockError(StandardError):

    def __init__(self, lockfilename):
        self.lockfilename = lockfilename

    def __str__(self):
        return 'Jobmanager unable to get master lock: %s' % self.lockfilename

