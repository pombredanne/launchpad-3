# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the code import dispatcher."""

__metaclass__ = type


import socket
from textwrap import dedent
from unittest import TestLoader

from twisted.trial.unittest import TestCase

from zope.component import getUtility

from canonical.config import config
from canonical.codehosting.codeimport.dispatcher import CodeImportDispatcher
from canonical.codehosting.codeimport.tests.test_foreigntree import (
    _make_silent_logger)
from canonical.codehosting.codeimport.tests.test_worker_monitor import (
    nuke_codeimport_sample_data)
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.interfaces import (
    CodeImportMachineOfflineReason, CodeImportMachineState,
    ICodeImportJobWorkflow)
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.testing.layers import LaunchpadZopelessLayer

class CodeImportDispatcherTestMixin:

    layer = LaunchpadZopelessLayer

    def pushConfig(self, **args):
        """XXX."""
        self.config_count += 1
        name = 'test%d' % self.config_count
        body = '\n'.join(["%s: %s" for k, v in args.iteritems()])
        config.push(name, dedent("""
            [codeimportdispatcher]
            %s
            """ % body))
        self.addCleanup(config.pop, name)

    def setUp(self):
        nuke_codeimport_sample_data()
        self.config_count = 0
        self.pushConfig(forced_hostname='none')
        self.dispatcher = self.Dispatcher(
            LaunchpadZopelessLayer.txn, _make_silent_logger())
        self.factory = LaunchpadObjectFactory()


class TestCodeImportDispatcherUnit(CodeImportDispatcherTestMixin, TestCase):
    """Unit tests for most of `CodeImportDispatcher`."""

    Dispatcher = CodeImportDispatcher

    def test_getHostname(self):
        # By default, getHostname return the same as socket.gethostname()
        self.assertEqual(
            self.dispatcher.getHostname(),
            socket.gethostname())

    def test_getHostnameOverride(self):
        # getHostname can be overriden by the config for testing, however.
        self.pushConfig(forced_hostname='test-value')
        self.assertEqual(
            self.dispatcher.getHostname(),
            'test-value')

    def test_dispatchJob(self):
        # dispatchJob launches a process described by worker_script
        # with a given job id as an argument.
        # create script that writes command line arguments to some tmpfile
        # assign this to worker_script
        self.dispatcher.dispatchJob(10)
        # assert stuff about contents of tmpfile.  I guess we'll need
        # to wait a while or call os.wait or stash the child pid
        # somewhere to know that the test is done...

    def test_getJobForMachine(self):
        # getJobForMachine calls getJobForMachine on the endpoint
        # described by the codeimportscheduler_url config entry.
        # Fire up an xml-rpc server that always answers 42
        self.pushConfig(codeimportscheduler_url='...')
        job_id = self.dispatcher.getJobForMachine(
            self.factory.makeCodeImportMachine(set_online=True))
        self.assertEqual(job_id, 42)


class TestCodeImportDispatcherDispatchJobs(
    CodeImportDispatcherTestMixin, TestCase):
    """Tests for `CodeImportDispatcher.dispatchJobs`."""

    class Dispatcher(CodeImportDispatcher):

        _job_id = 42

        def getHostname(self):
            return 'machine'

        def getJobForMachine(self, machine):
            self._calls.append(('getJobForMachine', machine.hostname))
            return self._job_id

        def dispatchJob(self, job_id):
            self._calls.append(('dispatchJob', job_id))

    def setUp(self):
        CodeImportDispatcherTestMixin.setUp(self)
        self.machine = self.factory.makeCodeImportMachine(
            set_online=True, hostname='machine')
        self.dispatcher._calls = []

    def createJobRunningOnOurMachine(self):
        """XXX."""
        job = self.factory.makeCodeImportJob()
        getUtility(ICodeImportJobWorkflow).startJob(job, self.machine)
        flush_database_updates()

    def test_machineIsOffline(self):
        # When the machine is offline, the dispatcher doesn't look for any
        # jobs.
        self.machine.setOffline(CodeImportMachineOfflineReason.STOPPED)
        self.dispatcher.dispatchJobs()
        self.assertEqual(self.dispatcher._calls, [])

    def test_machineIsQuiescingNoJobsRunning(self):
        # When the machine is quiescing and no jobs are running on this
        # machine, the dispatcher doesn't look for any jobs and sets the
        # machine to be offline.
        self.machine.setQuiescing(self.factory.makePerson(), "reason")
        self.dispatcher.dispatchJobs()
        #LaunchpadZopelessLayer.txn.begin() ?
        self.assertEqual(self.dispatcher._calls, [])
        self.assertEqual(self.machine.state, CodeImportMachineState.OFFLINE)

    def test_machineIsQuiescingWithJobsRunning(self):
        # When the machine is quiescing and there are jobs running on this
        # machine, the dispatcher doesn't look for any more jobs.
        self.createJobRunningOnOurMachine()
        self.machine.setQuiescing(self.factory.makePerson(), "reason")
        self.dispatcher.dispatchJobs()
        self.assertEqual(self.dispatcher._calls, [])
        self.assertEqual(self.machine.state, CodeImportMachineState.QUIESCING)

    def test_enoughJobsRunningOnMachine(self):
        # When there are already enough jobs running on this machine, the
        # dispatcher doesn't look for any more jobs.
        for i in range(config.codeimportdispatcher.max_jobs_per_machine):
            self.createJobRunningOnOurMachine()
        self.dispatcher.dispatchJobs()
        self.assertEqual(self.dispatcher._calls, [])

    def test_dispatchJob(self):
        # If the machine is online and there are not already
        # max_jobs_per_machine jobs running, then we dispatch the job.
        self.dispatcher.dispatchJobs()
        self.assertEqual(
            self.dispatcher._calls,
            [('getJobForMachine', 'machine'), ('dispatchJob', 42)])

    def test_noJobWaiting(self):
        # If there is no job to dispatch, then we just exit quietly.
        self.dispatcher._job_id = 0
        self.dispatcher.dispatchJobs()
        self.assertEqual(
            self.dispatcher._calls,
            [('getJobForMachine', 'machine')])


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
