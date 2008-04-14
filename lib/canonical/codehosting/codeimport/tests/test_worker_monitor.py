# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type


import shutil
import StringIO
import tempfile
import unittest

from bzrlib.tests import TestCaseWithMemoryTransport

from twisted.internet import defer, error
from twisted.trial.unittest import TestCase

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.codehosting.codeimport.worker import (
    CodeImportSourceDetails, get_default_bazaar_branch_store)
from canonical.codehosting.codeimport.worker_monitor import (
    CodeImportWorkerMonitor, CodeImportWorkerMonitorProtocol, ExitQuietly,
    read_only_transaction)
from canonical.codehosting.codeimport.tests.test_foreigntree import (
    SubversionServer)
from canonical.codehosting.codeimport.tests.test_worker import (
    clean_up_default_stores_for_import)
from canonical.database.sqlbase import commit
from canonical.launchpad.database import CodeImport, CodeImportJob
from canonical.launchpad.interfaces import (
    CodeImportResultStatus, CodeImportReviewStatus, ICodeImportJobSet,
    ICodeImportJobWorkflow, ICodeImportResultSet, ICodeImportSet)
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.testing.layers import (
    TwistedLayer, TwistedLaunchpadZopelessLayer)
from canonical.twistedsupport.tests.test_processmonitor import (
    makeFailure, ProcessTestsMixin)

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
            self.protocol.resetTimeout()
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


class TestWorkerMonitorUnit(TestCase):
    """Unit tests for most of the `CodeImportWorkerMonitor` class."""

    layer = TwistedLaunchpadZopelessLayer

    def getResultsForOurCodeImport(self):
        code_import = getUtility(ICodeImportSet).get(self.code_import_id)
        return getUtility(ICodeImportResultSet).getResultsForImport(
            code_import)

    def getOneResultForOurCodeImport(self):
        results = list(self.getResultsForOurCodeImport())
        self.failUnlessEqual(len(results), 1)
        return results[0]

    def setUp(self):
        self.factory = LaunchpadObjectFactory()
        job = self.factory.makeCodeImportJob()
        self.code_import_id = job.code_import.id
        getUtility(ICodeImportJobWorkflow).startJob(
            job, self.factory.makeCodeImportMachine(set_online=True))
        self.job_id = job.id
        self.worker_monitor = CodeImportWorkerMonitor(job.id)
        commit()

    def test_getJob(self):
        # getJob() returns the job whose id we passed to the constructor.
        return self.assertEqual(
            self.worker_monitor.getJob().id, self.job_id)

    def test_getJobWhenJobDeleted(self):
        # If the job has been deleted, getJob sets _call_finish_job to False
        # and raises ExitQuietly.
        job = self.worker_monitor.getJob()
        removeSecurityProxy(job).destroySelf()
        self.assertRaises(ExitQuietly, self.worker_monitor.getJob)
        self.assertNot(self.worker_monitor._call_finish_job)

    def test_getSourceDetails(self):
        # getSourceDetails extracts the details from the CodeImport database
        # object.
        @read_only_transaction
        def check_source_details(details):
            job = self.worker_monitor.getJob()
            self.assertEqual(
                details.svn_branch_url, job.code_import.svn_branch_url)
            self.assertEqual(
                details.cvs_root, job.code_import.cvs_root)
            self.assertEqual(
                details.cvs_module, job.code_import.cvs_module)
        return self.worker_monitor.getSourceDetails().addCallback(
            check_source_details)

    def test_updateHeartbeat(self):
        # The worker monitor's updateHeartbeat method calls the
        # updateHeartbeat job workflow method.
        @read_only_transaction
        def check_updated_details(result):
            job = self.worker_monitor.getJob()
            self.assertEqual(job.logtail, 'log tail')
        return self.worker_monitor.updateHeartbeat('log tail').addCallback(
            check_updated_details)

    def test_finishJobCallsFinishJob(self):
        # The worker monitor's finishJob method calls the
        # finishJob job workflow method.
        @read_only_transaction
        def check_finishJob_called(result):
            # We take as indication that finishJob was called that a
            # CodeImportResult was created.
            self.assertEqual(
                len(list(self.getResultsForOurCodeImport())), 1)
        return self.worker_monitor.finishJob(
            CodeImportResultStatus.SUCCESS).addCallback(
            check_finishJob_called)

    def test_finishJobDoesntUploadEmptyFileToLibrarian(self):
        # The worker monitor's finishJob method does not try to upload an
        # empty log file to the librarian.
        self.assertEqual(self.worker_monitor._log_file.tell(), 0)
        @read_only_transaction
        def check_no_file_uploaded(result):
            result = self.getOneResultForOurCodeImport()
            self.assert_(result.log_file is None)
        return self.worker_monitor.finishJob(
            CodeImportResultStatus.SUCCESS).addCallback(
            check_no_file_uploaded)

    def test_finishJobUploadsNonEmptyFileToLibrarian(self):
        # The worker monitor's finishJob method uploads the log file to the
        # librarian.
        self.worker_monitor._log_file.write('some text')
        @read_only_transaction
        def check_file_uploaded(result):
            result = self.getOneResultForOurCodeImport()
            self.assert_(result.log_file is not None)
            self.assertEqual(result.log_file.read(), 'some text')
        return self.worker_monitor.finishJob(
            CodeImportResultStatus.SUCCESS).addCallback(
            check_file_uploaded)

    def patchOutFinishJob(self):
        calls = []
        def finishJob(status):
            calls.append(status)
            return defer.succeed(None)
        self.worker_monitor.finishJob = finishJob
        return calls

    def test_callFinishJobCallsFinishJobSuccess(self):
        # callFinishJob calls finishJob with CodeImportResultStatus.SUCCESS if
        # its argument is not a Failure.
        calls = self.patchOutFinishJob()
        self.worker_monitor.callFinishJob(None)
        self.assertEqual(calls, [CodeImportResultStatus.SUCCESS])

    def test_callFinishJobCallsFinishJobFailure(self):
        # callFinishJob calls finishJob with CodeImportResultStatus.FAILURE if
        # its argument is a Failure and swallows the failure.
        calls = self.patchOutFinishJob()
        ret = self.worker_monitor.callFinishJob(makeFailure(RuntimeError))
        self.assertEqual(calls, [CodeImportResultStatus.FAILURE])
        return ret

    def test_callFinishJobLogsTracebackOnFailure(self):
        # When callFinishJob is called with a failure, it dumps the traceback
        # of the failure into the log file.
        ret = self.worker_monitor.callFinishJob(makeFailure(RuntimeError))
        self.worker_monitor._log_file.seek(0)
        log_text = self.worker_monitor._log_file.read()
        self.assertIn('RuntimeError', log_text)

    def test_callFinishJobRespects_call_finish_job(self):
        # callFinishJob does not call finishJob if _call_finish_job is False.
        calls = self.patchOutFinishJob()
        self.worker_monitor._call_finish_job = False
        self.worker_monitor.callFinishJob(None)
        self.assertEqual(calls, [])


class TestWorkerMonitorRunNoProcess(TestCase):
    """Tests for `CodeImportWorkerMonitor.run` that don't launch a subprocess.
    """

    class WorkerMonitor(CodeImportWorkerMonitor):

        def _launchProcess(self, source_details):
            return self.process_deferred

        def finishJob(self, status):
            self.result_status = status
            return defer.succeed(None)

    layer = TwistedLaunchpadZopelessLayer

    def setUp(self):
        self.factory = LaunchpadObjectFactory()
        job = self.factory.makeCodeImportJob()
        self.code_import_id = job.code_import.id
        getUtility(ICodeImportJobWorkflow).startJob(
            job, self.factory.makeCodeImportMachine(set_online=True))
        self.job_id = job.id
        self.worker_monitor = self.WorkerMonitor(job.id)
        commit()

    @read_only_transaction
    def checkFinishJobCalledWithStatus(self, ignored, status):
        """ """
        self.assertEqual(self.worker_monitor.result_status, status)

    def test_success(self):
        self.worker_monitor.process_deferred = defer.succeed(None)
        deferred = self.worker_monitor.run().addCallback(
            self.checkFinishJobCalledWithStatus,
            CodeImportResultStatus.SUCCESS)
        return deferred

    def test_failure(self):
        self.worker_monitor.process_deferred = defer.fail(RuntimeError())
        deferred = self.worker_monitor.run().addCallback(
            self.checkFinishJobCalledWithStatus,
            CodeImportResultStatus.FAILURE)
        return deferred

    def test_quiet_exit(self):
        self.worker_monitor.process_deferred = defer.fail(ExitQuietly())
        return self.worker_monitor.run()

    def test_quiet_exit_from_finishJob(self):
        self.worker_monitor.process_deferred = defer.succeed(None)
        def finishJob(reason):
            raise ExitQuietly
        self.worker_monitor.finishJob = finishJob
        deferred = self.worker_monitor.run()
        return deferred


class TestWorkerMonitorIntegration(TestCase, TestCaseWithMemoryTransport):

    layer = TwistedLaunchpadZopelessLayer

    def nukeCodeImportSampleData(self):
        """Delete all the sample data that might interfere with tests."""
        for job in CodeImportJob.select():
            job.destroySelf()
        for code_import in CodeImport.select():
            code_import.destroySelf()

    def setUp(self):
        TestCaseWithMemoryTransport.setUp(self)
        self.factory = LaunchpadObjectFactory()
        self.nukeCodeImportSampleData()
        self.repo_path = tempfile.mkdtemp()
        self.addCleanup(lambda : shutil.rmtree(self.repo_path))
        self.subversion_server = SubversionServer(self.repo_path)
        self.subversion_server.setUp()
        self.addCleanup(self.subversion_server.tearDown)
        self.svn_branch_url = self.subversion_server.makeBranch(
            'trunk', [('README', 'contents')])
        self.machine = self.factory.makeCodeImportMachine(set_online=True)

    def createApprovedCodeImport(self, svn_branch_url):
        code_import = self.factory.makeCodeImport(
            svn_branch_url=svn_branch_url)
        source_details = CodeImportSourceDetails.fromCodeImport(code_import)
        clean_up_default_stores_for_import(source_details)
        self.addCleanup(
            lambda : clean_up_default_stores_for_import(source_details))
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.REVIEWED},
            self.factory.makePerson())
        getUtility(ICodeImportJobWorkflow).newJob(code_import)
        return code_import

    def getStartedJob(self):
        code_import = self.createApprovedCodeImport(
            svn_branch_url=self.svn_branch_url)
        job = getUtility(ICodeImportJobSet).getJobForMachine(self.machine)
        self.assertEqual(code_import, job.code_import)
        return job

    def checkCodeImportResultCreated(self, code_import_id):
        code_import = getUtility(ICodeImportSet).get(code_import_id)
        results = list(getUtility(ICodeImportResultSet).getResultsForImport(
            code_import))
        self.failUnless(len(results), 1)

    def checkBranchImportedOKForCodeImport(self, code_import_id):
        code_import = getUtility(ICodeImportSet).get(code_import_id)
        tree_path = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(tree_path))

        bazaar_tree = get_default_bazaar_branch_store().pull(
            code_import.branch.id, tree_path)

        self.assertEqual(2, len(bazaar_tree.branch.revision_history()))

    def test_import(self):
        job = self.getStartedJob()
        code_import_id = job.code_import.id
        job_id = job.id
        commit()
        result = CodeImportWorkerMonitor(job_id).run()
        @read_only_transaction
        def check_result(ignored):
            self.checkCodeImportResultCreated(code_import_id)
            self.checkBranchImportedOKForCodeImport(code_import_id)
            return ignored
        return result.addCallback(check_result)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
