# Copyright 2006 Canonical Ltd.  All rights reserved.

import os
import socket
import subprocess
import sys

from twisted.internet import defer, error, reactor
from twisted.internet.protocol import ProcessProtocol
from twisted.protocols.basic import NetstringReceiver
from twisted.protocols.policies import TimeoutMixin
from twisted.python import failure
from twisted.web.xmlrpc import Proxy

from contrib.glock import GlobalLock, LockAlreadyAcquired

import canonical
from canonical.codehosting import branch_id_to_path
from canonical.config import config


MAXIMUM_PROCESSES = 5

# Time in seconds.
INACTIVITY_TIMEOUT = 5


class BranchStatusClient:
    """Twisted client for the branch status methods on the authserver."""

    def __init__(self):
        self.proxy = Proxy(config.supermirror.authserver_url)

    def getBranchPullQueue(self, branch_type):
        return self.proxy.callRemote('getBranchPullQueue', branch_type)

    def startMirroring(self, branch_id):
        return self.proxy.callRemote('startMirroring', branch_id)

    def mirrorComplete(self, branch_id, last_revision_id):
        return self.proxy.callRemote(
            'mirrorComplete', branch_id, last_revision_id)

    def mirrorFailed(self, branch_id, reason):
        return self.proxy.callRemote('mirrorFailed', branch_id, reason)


class FireOnExit(ProcessProtocol, NetstringReceiver):

    def __init__(self, branch_id, deferred, timeout_period, listener):
        self.branch_id = branch_id
        self.deferred = deferred
        self.listener = listener
        self._state = None

    def stringReceived(self, line):
        if line == 'startMirroring':
            self.listener.startMirroring(self.branch_id)
        elif line == 'mirrorSucceeded':
            self._state = 'mirrorSucceeded'
        elif line == 'mirrorFailed':
            self._state = 'mirrorFailed'
        else:
            if self._state == 'mirrorSucceeded':
                self.listener.mirrorSucceeded(self.branch_id, line)
                self._state = None
            elif self._state == 'mirrorFailed':
                self.listener.mirrorFailed(self.branch_id, line)
                self._state = None
            else:
                # XXX: Don't let this be merged.
                raise "Unrecognized: %r" % (line,)

    def outReceived(self, data):
        # Modified version of NetstringReceiver.dataReceived that disconnects
        # the child process
        NetstringReceiver.dataReceived(self, data)

    def processEnded(self, reason):
        ProcessProtocol.processEnded(self, reason)
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
        self.actualLock = None
        self.branch_type = branch_type
        self.name = 'branch-puller-%s' % branch_type.name.lower()
        self.lockfilename = '/var/lock/launchpad-%s.lock' % self.name

    def _run(self, branches_to_pull, logger):
        """Run all branches_to_mirror registered with the JobManager"""
        branches_to_pull = [
            self.getBranchToMirror(*branch) for branch in branches_to_pull]
        logger.info('%d branches to mirror', len(branches_to_pull))
        semaphore = defer.DeferredSemaphore(MAXIMUM_PROCESSES)
        deferreds = [
            semaphore.run(self.mirror, branch_to_mirror, logger)
            for branch_to_mirror in branches_to_pull]
        deferred = defer.gatherResults(deferreds)
        deferred.addCallback(self._finishedRunning, logger)
        return deferred

    def run(self, logger):
        deferred = self.branch_status_client.getBranchPullQueue(
            self.branch_type.name)
        deferred.addCallback(self._run, logger)
        return deferred

    def startMirroring(self, branch_id):
        return self.branch_status_client.startMirroring(branch_id)

    def mirrorFailed(self, branch_id, reason):
        return self.branch_status_client.mirrorFailed(branch_id, reason)

    def mirrorSucceeded(self, branch_id, revision_id):
        return self.branch_status_client.mirrorComplete(
            branch_id, revision_id)

    def _finishedRunning(self, ignored, logger):
        logger.info('Mirroring complete')

    def mirror(self, branch_to_mirror, logger):
        path_to_script = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(canonical.__file__))),
            'scripts/mirror-branch.py')
        deferred = defer.Deferred()
        # XXX: EGREGIOUS
        protocol = FireOnExit(
            int(branch_to_mirror[2]), deferred, INACTIVITY_TIMEOUT, self)
        command = [sys.executable, path_to_script] + branch_to_mirror
        reactor.spawnProcess(protocol, sys.executable, command)
        return deferred

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

