# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from datetime import datetime
import logging
import os
import unittest

import pytz

from bzrlib.branch import Branch
from bzrlib.urlutils import local_path_to_url

from twisted.internet import defer, error, task
from twisted.protocols.basic import NetstringParseError
from twisted.python import failure
from twisted.trial.unittest import TestCase as TrialTestCase

from canonical.codehosting.puller import scheduler
from canonical.codehosting.puller.worker import (
    get_canonical_url_for_branch_name)
from canonical.codehosting.tests.helpers import BranchTestCase
from canonical.config import config
from canonical.launchpad.interfaces import BranchType
from canonical.testing import LaunchpadScriptLayer, reset_logging
from canonical.launchpad.webapp import errorlog


class FakeBranchStatusClient:

    def __init__(self, branch_queues=None):
        self.branch_queues = branch_queues
        self.calls = []

    def getBranchPullQueue(self, branch_type):
        return defer.succeed(self.branch_queues[branch_type])

    def startMirroring(self, branch_id):
        self.calls.append(('startMirroring', branch_id))
        return defer.succeed(None)

    def mirrorComplete(self, branch_id, revision_id):
        self.calls.append(('mirrorComplete', branch_id, revision_id))
        return defer.succeed(None)

    def mirrorFailed(self, branch_id, revision_id):
        self.calls.append(('mirrorFailed', branch_id, revision_id))
        return defer.succeed(None)


class TestJobScheduler(unittest.TestCase):

    def setUp(self):
        self.masterlock = 'master.lock'
        # We set the log level to CRITICAL so that the log messages
        # are suppressed.
        logging.basicConfig(level=logging.CRITICAL)

    def tearDown(self):
        reset_logging()

    def makeFakeClient(self, hosted, mirrored, imported):
        return FakeBranchStatusClient(
            {'HOSTED': hosted, 'MIRRORED': mirrored, 'IMPORTED': imported})

    def makeJobScheduler(self, branch_type, branch_tuples):
        if branch_type == BranchType.HOSTED:
            client = self.makeFakeClient(branch_tuples, [], [])
        elif branch_type == BranchType.MIRRORED:
            client = self.makeFakeClient([], branch_tuples, [])
        elif branch_type == BranchType.IMPORTED:
            client = self.makeFakeClient([], [], branch_tuples)
        else:
            self.fail("Unknown branch type: %r" % (branch_type,))
        return scheduler.JobScheduler(
            client, logging.getLogger(), branch_type)

    def testManagerCreatesLocks(self):
        try:
            manager = self.makeJobScheduler(BranchType.HOSTED, [])
            manager.lockfilename = self.masterlock
            manager.lock()
            self.failUnless(os.path.exists(self.masterlock))
            manager.unlock()
        finally:
            self._removeLockFile()

    def testManagerEnforcesLocks(self):
        try:
            manager = self.makeJobScheduler(BranchType.HOSTED, [])
            manager.lockfilename = self.masterlock
            manager.lock()
            anothermanager = self.makeJobScheduler(BranchType.HOSTED, [])
            anothermanager.lockfilename = self.masterlock
            self.assertRaises(scheduler.LockError, anothermanager.lock)
            self.failUnless(os.path.exists(self.masterlock))
            manager.unlock()
        finally:
            self._removeLockFile()

    def _removeLockFile(self):
        if os.path.exists(self.masterlock):
            os.unlink(self.masterlock)


class TestPullerMasterProtocol(TrialTestCase):
    """Tests for the process protocol used by the job manager."""

    class StubPullerListener:
        """Stub listener object that records calls."""

        def __init__(self):
            self.calls = []

        def startMirroring(self):
            self.calls.append('startMirroring')

        def mirrorSucceeded(self, last_revision):
            self.calls.append(('mirrorSucceeded', last_revision))

        def mirrorFailed(self, message, oops):
            self.calls.append(('mirrorFailed', message, oops))

        def progressMade(self):
            self.calls.append('progressMade')


    class StubTransport:
        """Stub transport that implements the minimum for a ProcessProtocol.

        We're manually feeding data to the protocol, so we don't need a real
        transport.
        """

        def __init__(self):
            self.calls = []

        def loseConnection(self):
            self.calls.append('loseConnection')

        def signalProcess(self, signal_name):
            self.calls.append(('signalProcess', signal_name))


    def setUp(self):
        self.arbitrary_branch_id = 1
        self.listener = self.StubPullerListener()
        self.termination_deferred = defer.Deferred()
        self.clock = task.Clock()
        self.protocol = scheduler.PullerMasterProtocol(
            self.termination_deferred, self.listener, self.clock)
        self.protocol.transport = self.StubTransport()
        self.protocol.connectionMade()

    def assertProtocolSuccess(self):
        self.assertEqual(False, self.protocol.unexpected_error_received)

    def convertToNetstring(self, string):
        return '%d:%s,' % (len(string), string)

    def sendToProtocol(self, *arguments):
        for argument in arguments:
            self.protocol.outReceived(self.convertToNetstring(str(argument)))

    def test_startMirroring(self):
        """Receiving a startMirroring message notifies the listener."""
        self.sendToProtocol('startMirroring', 0)
        self.assertEqual(['startMirroring'], self.listener.calls)
        self.assertProtocolSuccess()

    def test_mirrorSucceeded(self):
        """Receiving a mirrorSucceeded message notifies the listener."""
        self.sendToProtocol('startMirroring', 0)
        self.listener.calls = []
        self.sendToProtocol('mirrorSucceeded', 1, 1234)
        self.assertEqual([('mirrorSucceeded', '1234')], self.listener.calls)
        self.assertProtocolSuccess()

    def test_mirrorFailed(self):
        """Receiving a mirrorFailed message notifies the listener."""
        self.sendToProtocol('startMirroring', 0)
        self.listener.calls = []
        self.sendToProtocol('mirrorFailed', 2, 'Error Message', 'OOPS')
        self.assertEqual(
            [('mirrorFailed', 'Error Message', 'OOPS')], self.listener.calls)
        self.assertProtocolSuccess()

    def test_timeoutWithoutProgress(self):
        """If we don't receive any messages after the configured timeout
        period, then we kill the child process.
        """
        self.protocol.connectionMade()
        self.clock.advance(config.supermirror.worker_timeout + 1)
        return self.assertFailure(
            self.termination_deferred, scheduler.TimeoutError)

    def assertMessageResetsTimeout(self, *message):
        """Assert that sending the message resets the protocol timeout."""
        self.assertTrue(2 < config.supermirror.worker_timeout)
        self.clock.advance(config.supermirror.worker_timeout - 1)
        self.sendToProtocol(*message)
        self.clock.advance(2)
        self.assertEqual(False, self.protocol.unexpected_error_received)

    def test_progressMadeResetsTimeout(self):
        """Receiving 'progressMade' resets the timeout."""
        self.assertMessageResetsTimeout('progressMade', 0)

    def test_startMirroringResetsTimeout(self):
        """Receiving 'progressMade' resets the timeout."""
        self.assertMessageResetsTimeout('startMirroring', 0)

    def test_mirrorSucceededDoesNotResetTimeout(self):
        """Receiving 'mirrorSucceeded' resets the timeout.

        It's possible that in pathological cases, the worker process might
        hang around even after it has said that it's finished. When that
        happens, we want to kill it quickly so that we can continue mirroring
        other branches.
        """
        self.sendToProtocol('startMirroring', 0)
        self.clock.advance(config.supermirror.worker_timeout - 1)
        self.sendToProtocol('mirrorSucceeded', 1, 'rev1')
        self.clock.advance(2)
        return self.assertFailure(
            self.termination_deferred, scheduler.TimeoutError)

    def test_mirrorFailedDoesNotResetTimeout(self):
        """Receiving 'mirrorFailed' resets the timeout.

        mirrorFailed doesn't reset the timeout for the same reasons as
        mirrorSucceeded.
        """
        self.sendToProtocol('startMirroring', 0)
        self.clock.advance(config.supermirror.worker_timeout - 1)
        self.sendToProtocol('mirrorFailed', 2, 'error message', 'OOPS')
        self.clock.advance(2)
        return self.assertFailure(
            self.termination_deferred, scheduler.TimeoutError)

    def test_progressMade(self):
        """Receiving a progressMade message notifies the listener."""
        self.sendToProtocol('progressMade', 0)
        self.assertEqual(['progressMade'], self.listener.calls)
        self.assertProtocolSuccess()

    def test_processTermination(self):
        """The protocol fires a Deferred when it is terminated."""
        self.protocol.processEnded(failure.Failure(error.ProcessDone(None)))
        return self.termination_deferred

    def test_processTerminationCancelsTimeout(self):
        """When the process ends (for any reason) cancel the timeout."""
        self.protocol._processTerminated(
            failure.Failure(error.ConnectionDone()))
        self.clock.advance(config.supermirror.worker_timeout * 2)
        self.assertProtocolSuccess()

    def test_terminatesWithError(self):
        """When the child process terminates with an unexpected error, raise
        an error that includes the contents of stderr and the exit condition.
        """

        def check_failure(failure):
            self.assertEqual('error message', failure.error)
            return failure

        self.termination_deferred.addErrback(check_failure)

        self.protocol.errReceived('error ')
        self.protocol.errReceived('message')
        self.protocol.processEnded(
            failure.Failure(error.ProcessTerminated(exitCode=1)))

        return self.assertFailure(
            self.termination_deferred, error.ProcessTerminated)

    def test_stderrFailsProcess(self):
        """If the process prints to stderr, then the Deferred fires an
        errback, even if it terminated successfully.
        """

        def check_failure(failure):
            self.assertEqual('error message', failure.error)
            return failure

        self.termination_deferred.addErrback(check_failure)

        self.protocol.errReceived('error ')
        self.protocol.errReceived('message')
        self.protocol.processEnded(failure.Failure(error.ProcessDone(None)))

        return self.termination_deferred

    def test_unrecognizedMessage(self):
        """The protocol notifies the listener when it receives an unrecognized
        message.
        """
        self.protocol.outReceived(self.convertToNetstring('foo'))

        def check_failure(exception):
            self.assertEqual(
                [('signalProcess', 'KILL')], self.protocol.transport.calls)
            self.assertTrue('foo' in str(exception))

        deferred = self.assertFailure(
            self.termination_deferred, scheduler.BadMessage)

        return deferred.addCallback(check_failure)

    def test_invalidNetstring(self):
        """The protocol terminates the session if it receives an unparsable
        netstring.
        """
        self.protocol.outReceived('foo')

        def check_failure(exception):
            self.assertEqual(
                ['loseConnection', ('signalProcess', 'KILL')],
                self.protocol.transport.calls)
            self.assertTrue('foo' in str(exception))

        deferred = self.assertFailure(
            self.termination_deferred, NetstringParseError)

        return deferred.addCallback(check_failure)


class TestPullerMaster(TrialTestCase):

    def setUp(self):
        self.status_client = FakeBranchStatusClient()
        self.arbitrary_branch_id = 1
        self.eventHandler = scheduler.PullerMaster(
            self.arbitrary_branch_id, 'arbitrary-source', 'arbitrary-dest',
            BranchType.HOSTED, logging.getLogger(), self.status_client)

    def makeFailure(self, exception_factory, *args, **kwargs):
        """Make a Failure object from the given exception factory.

        Any other arguments are passed straight on to the factory.
        """
        try:
            raise exception_factory(*args, **kwargs)
        except:
            return failure.Failure()

    def _getLastOOPSFilename(self, time):
        """Find the filename for the OOPS logged at 'time'."""
        utility = errorlog.globalErrorUtility
        error_dir = utility.errordir(time)
        oops_id = utility._findLastOopsId(error_dir)
        second_in_day = time.hour * 3600 + time.minute * 60 + time.second
        oops_prefix = config.launchpad.errorreports.oops_prefix
        return os.path.join(
            error_dir, '%05d.%s%s' % (second_in_day, oops_prefix, oops_id))

    def getLastOOPS(self, time):
        """Return the OOPS report logged at the given time."""
        oops_filename = self._getLastOOPSFilename(time)
        oops_report = open(oops_filename, 'r')
        try:
            return errorlog.ErrorReport.read(oops_report)
        finally:
            oops_report.close()

    def test_unexpectedError(self):
        """The puller master logs an OOPS when it receives an unexpected
        error.
        """
        now = datetime.now(pytz.timezone('UTC'))
        fail = self.makeFailure(RuntimeError, 'error message')
        self.eventHandler.unexpectedError(fail, now)
        oops = self.getLastOOPS(now)
        self.assertEqual(fail.getTraceback(), oops.tb_text)
        self.assertEqual('error message', oops.value)
        self.assertEqual('RuntimeError', oops.type)
        self.assertEqual(
            get_canonical_url_for_branch_name(
                self.eventHandler.unique_name), oops.url)

    def test_startMirroring(self):
        deferred = self.eventHandler.startMirroring()

        def checkMirrorStarted(ignored):
            self.assertEqual(
                [('startMirroring', self.arbitrary_branch_id)],
                self.status_client.calls)

        return deferred.addCallback(checkMirrorStarted)

    def test_mirrorComplete(self):
        arbitrary_revision_id = 'rev1'
        deferred = self.eventHandler.startMirroring()

        def mirrorSucceeded(ignored):
            self.status_client.calls = []
            return self.eventHandler.mirrorSucceeded(arbitrary_revision_id)
        deferred.addCallback(mirrorSucceeded)

        def checkMirrorCompleted(ignored):
            self.assertEqual(
                [('mirrorComplete', self.arbitrary_branch_id,
                  arbitrary_revision_id)],
                self.status_client.calls)
        return deferred.addCallback(checkMirrorCompleted)

    def test_mirrorFailed(self):
        arbitrary_error_message = 'failed'

        deferred = self.eventHandler.startMirroring()

        def mirrorFailed(ignored):
            self.status_client.calls = []
            return self.eventHandler.mirrorFailed(
                arbitrary_error_message, 'oops')
        deferred.addCallback(mirrorFailed)

        def checkMirrorFailed(ignored):
            self.assertEqual(
                [('mirrorFailed', self.arbitrary_branch_id,
                  arbitrary_error_message)],
                self.status_client.calls)
        return deferred.addCallback(checkMirrorFailed)


class TestPullerMasterIntegration(BranchTestCase, TrialTestCase):
    """Tests for the puller master that launch sub-processes."""

    layer = LaunchpadScriptLayer

    def setUp(self):
        BranchTestCase.setUp(self)
        self.db_branch = self.makeBranch(BranchType.HOSTED)
        self.bzr_tree = self.createTemporaryBazaarBranchAndTree('src-branch')
        self.client = FakeBranchStatusClient()

    def run(self, result):
        # We want to use Trial's run() method so we can return Deferreds.
        return TrialTestCase.run(self, result)

    def _dumpError(self, failure):
        # XXX: JonathanLange 2007-10-17: It would be nice if we didn't have to
        # do this manually, and instead the test automatically gave us the
        # full error.
        error = getattr(failure, 'error', 'No stderr stored.')
        print error
        return failure

    def test_mirror(self):
        """Actually mirror a branch using a worker sub-process.

        This test actually launches a worker process and makes sure that it
        runs successfully and that we report the successful run.
        """
        revision_id = self.bzr_tree.branch.last_revision()
        puller_master = scheduler.PullerMaster(
            self.db_branch.id, local_path_to_url('src-branch'),
            self.db_branch.unique_name, self.db_branch.branch_type,
            logging.getLogger(), self.client)
        puller_master.destination_url = os.path.abspath('dest-branch')
        deferred = puller_master.mirror().addErrback(self._dumpError)

        def check_authserver_called(ignored):
            self.assertEqual(
                [('startMirroring', self.db_branch.id),
                 ('mirrorComplete', self.db_branch.id, revision_id)],
                self.client.calls)
            return ignored
        deferred.addCallback(check_authserver_called)

        def check_branch_mirrored(ignored):
            self.assertEqual(
                revision_id,
                Branch.open(puller_master.destination_url).last_revision())
            return ignored
        deferred.addCallback(check_branch_mirrored)

        return deferred


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
