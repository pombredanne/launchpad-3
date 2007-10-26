# Copyright 2006 Canonical Ltd.  All rights reserved.

import os
from StringIO import StringIO
import socket
import sys

from twisted.internet import defer, error, reactor
from twisted.internet.protocol import ProcessProtocol
from twisted.protocols.basic import NetstringReceiver, NetstringParseError
from twisted.python import failure
from twisted.web.xmlrpc import Proxy

from contrib.glock import GlobalLock, LockAlreadyAcquired

import canonical
from canonical.codehosting import branch_id_to_path
from canonical.config import config
from canonical.launchpad.webapp import errorlog


class BadMessage(Exception):
    """Raised when the protocol receives a message that we don't recognize."""

    def __init__(self, bad_netstring):
        Exception.__init__(
            self, 'Received unrecognized message: %r' % bad_netstring)


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

    def recordSuccess(self, name, hostname, date_started, date_completed):
        started_tuple = tuple(date_started.utctimetuple())
        completed_tuple = tuple(date_completed.utctimetuple())
        return self.proxy.callRemote(
            'recordSuccess', name, hostname, started_tuple, completed_tuple)


class PullerMasterProtocol(ProcessProtocol, NetstringReceiver):
    """The protocol for receiving events from the puller worker."""

    def __init__(self, deferred, listener):
        """Construct an instance of the protocol, for listening to a worker.

        :param deferred: A Deferred that will be fired when the worker has
            finished (either successfully or unsuccesfully).
        :param listener: A PullerMaster object that is notified when the
            protocol receives events from the worker.
        """
        # This Deferred is created when branch mirroring starts and is fired
        # when it finishes (successfully or otherwise). Once this deferred is
        # created, the termination deferred will not be fired unless
        # _branch_mirror_complete_deferred is fired first.
        self._branch_mirror_complete_deferred = None
        # This Deferred is fired only when the child process has terminated
        # *and* any other operations have completed.
        self._termination_deferred = deferred
        self.listener = listener
        self._resetState()
        self._stderr = StringIO()

    def _processTerminated(self, reason):
        if self._termination_deferred is None:
            # We have already fired the deferred and do not want to do so
            # again.
            return
        # Make sure we won't fire the Deferred twice
        deferred = self._termination_deferred
        self._termination_deferred = None
        if self._branch_mirror_complete_deferred is not None:
            # If we've started mirroring the branch, wait for that to finish
            # before firing the termination deferred.
            self._branch_mirror_complete_deferred.addCallback(
                self._fireTerminationDeferred, deferred, reason)
            self._branch_mirror_complete_deferred.addErrback(deferred.errback)
        else:
            # Otherwise, just fire it.
            self._fireTerminationDeferred(None, deferred, reason)

    def _fireTerminationDeferred(self, ignored, deferred, reason):
        if reason.check(error.ConnectionDone):
            deferred.callback(None)
        else:
            reason.error = self._stderr.getvalue()
            self._stderr.truncate(0)
            deferred.errback(reason)

    def _resetState(self):
        self._current_command = None
        self._expected_args = None
        self._current_args = []

    def dataReceived(self, data):
        NetstringReceiver.dataReceived(self, data)
        # XXX: JonathanLange 2007-10-16
        # bug=http://twistedmatrix.com/trac/ticket/2851: There are no hooks in
        # NetstringReceiver to catch a NetstringParseError. The best we can do
        # is check the value of brokenPeer.
        if self.brokenPeer:
            self.unexpectedError(failure.Failure(NetstringParseError(data)))

    def stringReceived(self, line):
        if (self._current_command is not None
            and self._expected_args is not None):
            self._current_args.append(line)
        elif self._current_command is not None:
            self._expected_args = int(line)
        else:
            if getattr(self, 'do_%s' % line, None) is None:
                self.unexpectedError(failure.Failure(BadMessage(line)))
            else:
                self._current_command = line

        if len(self._current_args) == self._expected_args:
            method = getattr(self, 'do_%s' % self._current_command)
            try:
                method(*self._current_args)
            finally:
                self._resetState()

    def do_startMirroring(self):
        self._branch_mirror_complete_deferred = defer.maybeDeferred(
            self.listener.startMirroring)
        self._branch_mirror_complete_deferred.addErrback(self.unexpectedError)

    def do_mirrorSucceeded(self, latest_revision):
        self._branch_mirror_complete_deferred.addCallback(
            lambda ignored: self.listener.mirrorSucceeded(latest_revision))

    def do_mirrorFailed(self, reason, oops):
        self._branch_mirror_complete_deferred.addCallback(
            lambda ignored: self.listener.mirrorFailed(reason, oops))

    def outReceived(self, data):
        self.dataReceived(data)

    def errReceived(self, data):
        self._stderr.write(data)

    def unexpectedError(self, failure):
        """Called when we receive data that violates the protocol.

        This could be because the client didn't send a netstring, or sent an
        recognized command, or sent the wrong number of arguments for a
        command etc.

        Calling this method kills the child process and fires the completion
        deferred that was provided to the constructor.
        """
        try:
            self.transport.signalProcess('KILL')
        except error.ProcessExitedAlready:
            # The process has already died. Fine.
            pass
        self._processTerminated(failure)

    def processEnded(self, reason):
        ProcessProtocol.processEnded(self, reason)
        self._processTerminated(reason)


class PullerMaster:
    """Controller for a single puller worker.

    The `PullerMaster` kicks off a child worker process and handles the events
    generated by that process.
    """

    def __init__(self, branch_id, source_url, unique_name, branch_type,
                 logger, client):
        """Construct a PullerMaster object.

        :param branch_id: The database ID of the branch to be mirrored.
        :param source_url: The location from which the branch is to be
            mirrored.
        :param unique_name: The unique name of the branch to be mirrored.
        :param branch_type: The BranchType of the branch to be mirrored (e.g.
            BranchType.HOSTED).
        :param logger: A Python logging object.
        :param client: An asynchronous client for the branch status XML-RPC
            service.
        """
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
        protocol = PullerMasterProtocol(deferred, self)
        command = [
            sys.executable, path_to_script, self.source_url,
            self.destination_url, str(self.branch_id), self.unique_name,
            self.branch_type.name]
        reactor.spawnProcess(protocol, sys.executable, command)
        return deferred

    def run(self):
        deferred = self.mirror()
        deferred.addErrback(self.unexpectedError)
        return deferred

    def startMirroring(self):
        self.logger.info(
            'Mirroring branch %d: %s to %s', self.branch_id, self.source_url,
            self.destination_url)
        return self.branch_status_client.startMirroring(self.branch_id)

    def mirrorFailed(self, reason, oops):
        self.logger.info('Recorded %s', oops)
        self.logger.info('Recorded failure: %s', str(reason))
        return self.branch_status_client.mirrorFailed(self.branch_id, reason)

    def mirrorSucceeded(self, revision_id):
        self.logger.info('Successfully mirrored to rev %s', revision_id)
        return self.branch_status_client.mirrorComplete(
            self.branch_id, revision_id)

    def unexpectedError(self, failure):
        request = errorlog.ScriptRequest([
            ('branch_id', self.branch_id),
            ('source', self.source_url),
            ('dest', self.destination_url),
            ('error-explanation', failure.getErrorMessage())])
        request.URL = get_canonical_url(self.unique_name)
        errorlog.globalErrorUtility.raising(
            (failure.value, failure.type, failure.getTraceback()), request)
        self.logger.info('Recorded %s', request.oopsid)


class JobScheduler:
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

    def _run(self, puller_masters):
        """Run all branches_to_mirror registered with the JobScheduler."""
        self.logger.info('%d branches to mirror', len(puller_masters))
        assert config.supermirror.maximum_workers is not None, (
            "config.supermirror.maximum_workers is not defined.")
        semaphore = defer.DeferredSemaphore(
            config.supermirror.maximum_workers)
        deferreds = [
            semaphore.run(puller_master.run)
            for puller_master in puller_masters]
        deferred = defer.gatherResults(deferreds)
        deferred.addCallback(self._finishedRunning)
        return deferred

    def run(self):
        deferred = self.branch_status_client.getBranchPullQueue(
            self.branch_type.name)
        deferred.addCallback(self.getPullerMasters)
        deferred.addCallback(self._run)
        return deferred

    def _finishedRunning(self, ignored):
        self.logger.info('Mirroring complete')
        return ignored

    def getPullerMaster(self, branch_id, branch_src, unique_name):
        branch_src = branch_src.strip()
        return PullerMaster(
            branch_id, branch_src, unique_name, self.branch_type, self.logger,
            self.branch_status_client)

    def getPullerMasters(self, branches_to_pull):
        return [
            self.getPullerMaster(*branch) for branch in branches_to_pull]

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
        return self.branch_status_client.recordSuccess(
            self.name, socket.gethostname(), date_started, date_completed)


class LockError(StandardError):

    def __init__(self, lockfilename):
        self.lockfilename = lockfilename

    def __str__(self):
        return 'Jobmanager unable to get master lock: %s' % self.lockfilename

