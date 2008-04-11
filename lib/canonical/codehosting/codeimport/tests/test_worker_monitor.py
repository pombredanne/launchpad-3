# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type


import StringIO
import unittest

from twisted.trial.unittest import TestCase

from zope.component import getUtility

from canonical.codehosting.codeimport.worker_monitor import (
    CodeImportWorkerMonitorProtocol)
from canonical.launchpad.interfaces import ICodeImportJobSet
from canonical.testing.layers import TwistedLayer
from canonical.twistedsupport.tests.test_processmonitor import (
    ProcessTestsMixin)

class TestWorkerMonitorProtocol(ProcessTestsMixin, TestCase):

    layer = TwistedLayer

    class StubWorkerMonitor:

        def __init__(self):
            self.calls = []

        def updateHeartbeat(self, tail):
            self.calls.append(('updateHeartbeat', tail))

    def setUp(self):
        self.worker_monitor = self.StubWorkerMonitor()
        self.log_file = StringIO.StringIO()
        ProcessTestsMixin.setUp(self)

    def makeProtocol(self):
        return CodeImportWorkerMonitorProtocol(
            self.termination_deferred, self.worker_monitor, self.log_file,
            self.clock)

    def test_callsUpdateHeartbeatInConnectionMade(self):
        # The protocol calls updateHeartbeat() when it is connected to the
        # process.
        # connectionMade() is called during setUp().
        self.assertEqual(
            self.worker_monitor.calls,
            [('updateHeartbeat', '')])

    def test_callsUpdateHeartbeatRegularly(self):
        # The protocol calls 'updateHeartbeat' on the worker_monitor every
        # UPDATE_HEARTBEAT_INTERVAL seconds.
        # Forget the call in connectionMade()
        self.worker_monitor.calls = []
        # Advance the simulated time a little to avoid fencepost errors.
        self.clock.advance(0.1)
        # And check that updateHeartbeat is called at the frequency we expect:
        for i in range(4):
            self.assertEqual(
                self.worker_monitor.calls,
                [('updateHeartbeat', '')]*i)
            self.clock.advance(self.protocol.UPDATE_HEARTBEAT_INTERVAL)

    def test_updateHeartbeatStopsOnProcessExit(self):
        # updateHeartbeat is not called after the process has exited.
        # Forget the call in connectionMade()
        self.worker_monitor.calls = []
        self.simulateProcessExit()
        # Advance the simulated time past the time the next update is due.
        self.clock.advance(self.protocol.UPDATE_HEARTBEAT_INTERVAL + 1)
        # Check that updateHeartbeat was not called.
        self.assertEqual(self.worker_monitor.calls, [])

    def test_outReceivedWritesToLogFile(self):
        # outReceived writes the data it is passed into the log file.
        output = ['some data\n', 'some more data\n']
        self.protocol.outReceived(output[0])
        self.assertEqual(self.log_file.getvalue(), output[0])
        self.protocol.outReceived(output[1])
        self.assertEqual(self.log_file.getvalue(), output[0] + output[1])

    def test_outReceivedUpdatesTail(self):
        # outReceived updates the tail of the log, currently and arbitarily
        # defined to be the last 100 bytes of the output.
        self.protocol.outReceived('a' * 150)
        self.assertEqual(self.protocol._tail, 'a'*100)
        self.protocol.outReceived('b' * 50)
        self.assertEqual(self.protocol._tail, 'a'*50 + 'b'*50)


class TestWorkerMonitorIntegration(TestCase):

    def setUp(self):
        self.nukeCodeImportSampleData()
        self.subversion_server = SubversionServer()
        self.subversion_server.setUp()
        self.addCleanup(self.subversion_server.tearDown)
        self.repo_path = tempfile.mkdtmp()
        self.addCleanup(lambda : shutil.rmtree(self.repo_path))
        self.subversion_server.makeRepository(self.repo_path, 'stuff')
        self.machine = self.factory.makeCodeImportMachine(online=True)

    def getStartedJob(self):
        code_import = self.createApprovedCodeImport(
            svn_branch_url=self.repo_path)
        job = getUtility(ICodeImportJobSet).getJobForMachine(self.machine)
        assert code_import == job
        return job

    def test_import(self):
        job = self.getDueJob()
        code_import_id = job.code_import.id
        job_id = job.id
        commit()
        result = CodeImportWorkerMonitor(job_id).run()
        def check_result(ignored):
            self.checkCodeImportResultCreated()
            self.checkBranchImportedOKForCodeImport(code_import_id)
            return ignored
        return result.addCallback(check_result)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
