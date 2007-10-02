# Copyright 2006 Canonical Ltd.  All rights reserved.

import os
import socket
import sys

from twisted.internet import defer, error, reactor
from twisted.internet.protocol import ProcessProtocol
from twisted.protocols.basic import NetstringReceiver
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

    def __init__(self, deferred, timeout_period, listener):
        self.deferred = deferred
        self.listener = listener
        self._deferred = None
        self._commands = {
            'startMirroring': 0, 'mirrorSucceeded': 1, 'mirrorFailed': 2}
        self._resetState()

    def _resetState(self):
        self._current_command = None
        self._current_args = []

    def stringReceived(self, line):
        if line in self._commands:
            self._current_command = line
        elif self._current_command is not None:
            self._current_args.append(line)
        else:
            # XXX: Don't let this be merged.
            raise "Unrecognized: %r" % (line,)

        if len(self._current_args) == self._commands[self._current_command]:
            method = getattr(self, 'do_%s' % self._current_command)
            try:
                method(*self._current_args)
            finally:
                self._resetState()

    def do_startMirroring(self):
        self._deferred = defer.maybeDeferred(self.listener.startMirroring)

    def do_mirrorSucceeded(self, latest_revision):
        self._deferred.addCallback(
            lambda ignored: self.listener.mirrorSucceeded(latest_revision))

    def do_mirrorFailed(self, reason, oops):
        self._deferred.addCallback(
            lambda ignored: self.listener.mirrorFailed(reason, oops))

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
            deferred.errback(failure.Failure(Exception(reason)))


class BranchToMirror:

    def __init__(self, branch_id, source_url, unique_name, branch_type,
                 logger, client):
        self.branch_id = branch_id
        self.source_url = source_url.strip()
        path = branch_id_to_path(branch_id)
        self.destination_url = os.path.join(
            config.supermirror.branchesdest, path)
        self.unique_name = unique_name
        self.branch_type = branch_type
        self.logger = logger
        self.branch_status_client = client

    def mirror(self):
        path_to_script = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(canonical.__file__))),
            'scripts/mirror-branch.py')
        deferred = defer.Deferred()
        protocol = FireOnExit(deferred, INACTIVITY_TIMEOUT, self)
        command = [
            sys.executable, path_to_script, self.source_url,
            self.destination_url, str(self.branch_id), self.unique_name,
            self.branch_type.name]
        reactor.spawnProcess(protocol, sys.executable, command)
        return deferred

    def startMirroring(self):
        self.logger.info(
            'Mirroring branch %d: %s to %s', self.branch_id, self.source_url,
            self.destination_url)
        return self.branch_status_client.startMirroring(self.branch_id)

    def mirrorFailed(self, reason, oops):
        self.logger.info('Recorded failure: %s', str(reason))
        return self.branch_status_client.mirrorFailed(self.branch_id, reason)

    def mirrorSucceeded(self, revision_id):
        self.logger.info('Successfully mirrored to rev %s', revision_id)
        return self.branch_status_client.mirrorComplete(
            self.branch_id, revision_id)


class JobManager:
    """Schedule and manage the mirroring of branches.

    The jobmanager is responsible for organizing the mirroring of all
    branches.
    """

    def __init__(self, branch_status_client, logger, branch_type):
        self.branch_status_client = branch_status_client
        self.logger = logger
        self.actualLock = None
        self.branch_type = branch_type
        self.name = 'branch-puller-%s' % branch_type.name.lower()
        self.lockfilename = '/var/lock/launchpad-%s.lock' % self.name

    def _run(self, branches_to_pull):
        """Run all branches_to_mirror registered with the JobManager"""
        self.logger.info('%d branches to mirror', len(branches_to_pull))
        semaphore = defer.DeferredSemaphore(MAXIMUM_PROCESSES)
        deferreds = [
            semaphore.run(branch_to_mirror.mirror)
            for branch_to_mirror in branches_to_pull]
        deferred = defer.gatherResults(deferreds)
        deferred.addCallback(self._finishedRunning)
        return deferred

    def run(self):
        deferred = self.branch_status_client.getBranchPullQueue(
            self.branch_type.name)
        deferred.addCallback(self.getBranchesToMirror)
        deferred.addCallback(self._run)
        return deferred

    def _finishedRunning(self, ignored):
        self.logger.info('Mirroring complete')

    def getBranchToMirror(self, branch_id, branch_src, unique_name):
        branch_src = branch_src.strip()
        return BranchToMirror(
            branch_id, branch_src, unique_name, self.branch_type, self.logger,
            self.branch_status_client)

    def getBranchesToMirror(self, branches_to_pull):
        return [
            self.getBranchToMirror(*branch) for branch in branches_to_pull]

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

