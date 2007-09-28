import logging
import os
import shutil
import sys
import tempfile
import unittest

import bzrlib

from twisted.conch.ssh.common import NS
from twisted.trial.unittest import TestCase as TrialTestCase

from canonical.codehosting import branch_id_to_path
from canonical.config import config
from canonical.launchpad.interfaces import BranchType
from canonical.launchpad.scripts.supermirror.branchtomirror import (
    BranchToMirror, PullerWorkerProtocol)
from canonical.launchpad.scripts.supermirror.tests import createbranch
from canonical.launchpad.scripts.supermirror import jobmanager
from canonical.authserver.client.branchstatus import BranchStatusClient
from canonical.authserver.tests.harness import AuthserverTacTestSetup
from canonical.testing import LaunchpadFunctionalLayer, reset_logging


class TestJobManager(unittest.TestCase):

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

    def makeJobManager(self, branch_type, branch_tuples):
        if branch_type == BranchType.HOSTED:
            client = self.makeFakeClient(branch_tuples, [], [])
        elif branch_type == BranchType.MIRRORED:
            client = self.makeFakeClient([], branch_tuples, [])
        elif branch_type == BranchType.IMPORTED:
            client = self.makeFakeClient([], [], branch_tuples)
        else:
            self.fail("Unknown branch type: %r" % (branch_type,))
        return jobmanager.JobManager(client, branch_type)

    def testManagerCreatesLocks(self):
        try:
            manager = self.makeJobManager(BranchType.HOSTED, [])
            manager.lockfilename = self.masterlock
            manager.lock()
            self.failUnless(os.path.exists(self.masterlock))
            manager.unlock()
        finally:
            self._removeLockFile()

    def testManagerEnforcesLocks(self):
        try:
            manager = self.makeJobManager(BranchType.HOSTED, [])
            manager.lockfilename = self.masterlock
            manager.lock()
            anothermanager = self.makeJobManager(BranchType.HOSTED, [])
            anothermanager.lockfilename = self.masterlock
            self.assertRaises(jobmanager.LockError, anothermanager.lock)
            self.failUnless(os.path.exists(self.masterlock))
            manager.unlock()
        finally:
            self._removeLockFile()

    def _removeLockFile(self):
        if os.path.exists(self.masterlock):
            os.unlink(self.masterlock)


class TestJobManagerInLaunchpad(TrialTestCase):
    layer = LaunchpadFunctionalLayer

    testdir = None

    def setUp(self):
        self.testdir = tempfile.mkdtemp()
        # Change the HOME environment variable in order to ignore existing
        # user config files.
        os.environ.update({'HOME': self.testdir})
        self.authserver = AuthserverTacTestSetup()
        self.authserver.setUp()

    def tearDown(self):
        shutil.rmtree(self.testdir)
        self.authserver.tearDown()

    def _getBranchDir(self, branchname):
        return os.path.join(self.testdir, branchname)

    def assertMirrored(self, branch_to_mirror):
        """Assert that branch_to_mirror's source and destinations have the same
        revisions.

        :param branch_to_mirror: a BranchToMirror instance.
        """
        source_branch = bzrlib.branch.Branch.open(branch_to_mirror.source)
        dest_branch = bzrlib.branch.Branch.open(branch_to_mirror.dest)
        self.assertEqual(source_branch.last_revision(),
                         dest_branch.last_revision())

    def testJobRunner(self):
        client = jobmanager.BranchStatusClient()
        manager = jobmanager.JobManager(client, BranchType.HOSTED)

        branches = [
            self._makeBranch("brancha", 1, client),
            self._makeBranch("branchb", 2, client),
            self._makeBranch("branchc", 3, client),
            self._makeBranch("branchd", 4, client),
            self._makeBranch("branche", 5, client)]
        manager.branches_to_mirror = [
            [branch.source, branch.dest, str(branch.branch_id),
             branch.unique_name, 'HOSTED']
            for branch in branches]

        deferred = manager.run(logging.getLogger())

        def check_mirrored(ignored):
            self.assertEqual(len(manager.branches_to_mirror), 0)
            for branch in branches:
                self.assertMirrored(branch)

        return deferred.addCallback(check_mirrored)

    def _makeBranch(self, relativedir, target, branch_status_client):
        """Given a relative directory, make a strawman branch and return it.

        @param relativedir - The directory to make the branch
        @output BranchToMirror - A branch object representing the strawman
                                    branch
        """
        unique_name = '~testuser/+junk/' + relativedir
        branchdir = os.path.join(self.testdir, relativedir)
        createbranch(branchdir)
        if target == None:
            targetdir = None
        else:
            targetdir = os.path.join(self.testdir, branch_id_to_path(target))
        protocol = PullerWorkerProtocol(
            sys.stdout, sys.stderr, logging.getLogger(), branch_status_client)
        return BranchToMirror(
                branchdir, targetdir, target, unique_name, branch_type=None,
                protocol=protocol)


class FakeBranchStatusClient:
    """A dummy branch status client implementation for testing getBranches()"""

    def __init__(self, branch_queues):
        self.branch_queues = branch_queues

    def getBranchPullQueue(self, branch_type):
        return self.branch_queues[branch_type]


class TestPullerMasterProtocol(unittest.TestCase):
    """Tests for the process protocol used by the job manager."""

    class PullerListener:
        """Fake listener object that records calls."""

        def __init__(self):
            self.calls = []

        def startMirroring(self, branch_id):
            self.calls.append(('startMirroring', branch_id))

        def mirrorSucceeded(self, branch_id, last_revision):
            self.calls.append(('mirrorSucceeded', branch_id, last_revision))

        def mirrorFailed(self, branch_id, message):
            self.calls.append(('mirrorFailed', branch_id, message))


    class FakeTransport:
        """Fake transport that only implements loseConnection.

        We're manually feeding data to the protocol, so we don't need a real
        transport.
        """
        def loseConnection(self):
            pass


    def setUp(self):
        arbitrary_timeout_period = 20
        self.arbitrary_branch_id = 1
        self.listener = TestPullerMasterProtocol.PullerListener()
        self.protocol = jobmanager.FireOnExit(
            self.arbitrary_branch_id, None, arbitrary_timeout_period,
            self.listener)
        self.protocol.transport = TestPullerMasterProtocol.FakeTransport()

    def convertToNetstring(self, string):
        return '%d:%s,' % (len(string), string)

    def test_startMirroring(self):
        """Receiving a startMirroring message notifies the listener."""
        self.protocol.outReceived(self.convertToNetstring('startMirroring'))
        self.assertEqual(
            [('startMirroring', self.arbitrary_branch_id)],
            self.listener.calls)

    def test_mirrorSucceeded(self):
        """Receiving a mirrorSucceeded message notifies the listener."""
        self.protocol.outReceived(
            self.convertToNetstring('mirrorSucceeded'))
        self.protocol.outReceived(self.convertToNetstring('1234'))
        self.assertEqual(
            [('mirrorSucceeded', self.arbitrary_branch_id, '1234')],
            self.listener.calls)

    def test_mirrorFailed(self):
        """Receiving a mirrorFailed message notifies the listener."""
        self.protocol.outReceived(
            self.convertToNetstring('mirrorFailed'))
        self.protocol.outReceived(self.convertToNetstring('Error Message'))
        self.assertEqual(
            [('mirrorFailed', self.arbitrary_branch_id, 'Error Message')],
            self.listener.calls)


class TestMirroringEvents(TrialTestCase):
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        self.authserver = AuthserverTacTestSetup()
        self.authserver.setUp()
        self.status_client = jobmanager.BranchStatusClient()
        self.eventHandler = jobmanager.JobManager(
            self.status_client, BranchType.HOSTED)

    def tearDown(self):
        self.authserver.tearDown()

    def test_startMirroring(self):
        arbitrary_branch_id = 1
        self.eventHandler.startMirroring(arbitrary_branch_id)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
