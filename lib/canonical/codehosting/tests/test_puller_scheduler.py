import logging
import os
import unittest

from bzrlib.branch import Branch
from bzrlib.urlutils import local_path_to_url

from twisted.internet import defer, error
from twisted.protocols.basic import NetstringParseError
from twisted.python import failure
from twisted.trial.unittest import TestCase as TrialTestCase

from canonical.codehosting.puller import scheduler
from canonical.codehosting.tests.helpers import BranchTestCase
from canonical.launchpad.interfaces import BranchType
from canonical.testing import LaunchpadScriptLayer, reset_logging


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
        self.protocol = scheduler.PullerMasterProtocol(
            self.termination_deferred, self.listener)
        self.protocol.transport = self.StubTransport()

    def convertToNetstring(self, string):
        return '%d:%s,' % (len(string), string)

    def sendToProtocol(self, *arguments):
        for argument in arguments:
            self.protocol.outReceived(self.convertToNetstring(str(argument)))

    def test_startMirroring(self):
        """Receiving a startMirroring message notifies the listener."""
        self.sendToProtocol('startMirroring', 0)
        self.assertEqual(['startMirroring'], self.listener.calls)

    def test_mirrorSucceeded(self):
        """Receiving a mirrorSucceeded message notifies the listener."""
        self.sendToProtocol('startMirroring', 0)
        self.listener.calls = []
        self.sendToProtocol('mirrorSucceeded', 1, 1234)
        self.assertEqual([('mirrorSucceeded', '1234')], self.listener.calls)

    def test_mirrorFailed(self):
        """Receiving a mirrorFailed message notifies the listener."""
        self.sendToProtocol('startMirroring', 0)
        self.listener.calls = []
        self.sendToProtocol('mirrorFailed', 2, 'Error Message', 'OOPS')
        self.assertEqual(
            [('mirrorFailed', 'Error Message', 'OOPS')], self.listener.calls)

    def test_processTermination(self):
        """The protocol fires a Deferred when it is terminated."""
        self.protocol.processEnded(failure.Failure(error.ProcessDone(None)))
        return self.termination_deferred

    def test_deferredWaitsForListener(self):
        """If the process terminates while we are waiting """

    def test_terminatesWithError(self):
        """When the child process terminates with an unexpected error, raise
        an error that includes the contents of stderr and the exit condition.
        """

        def check_failure(failure):
            self.assertEqual('error message', failure.error)
            return failure

        self.termination_deferred.addErrback(check_failure)
        deferred = self.assertFailure(
            self.termination_deferred, error.ProcessTerminated)

        self.protocol.errReceived('error ')
        self.protocol.errReceived('message')
        self.protocol.processEnded(
            failure.Failure(error.ProcessTerminated(exitCode=1)))

        return deferred

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
        # XXX - it would be nice if we didn't have to do this manually, if
        # instead the test gave us the full error automatically.
        error = getattr(failure, 'error', 'No stderr stored.')
        print error
        return failure

    def test_mirror(self):
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
