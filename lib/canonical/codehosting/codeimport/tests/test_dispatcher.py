# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the code import dispatcher."""

__metaclass__ = type


from optparse import OptionParser
import os
import shutil
import socket
import sys
import tempfile
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
from canonical.launchpad import scripts
from canonical.launchpad.interfaces import (
    CodeImportMachineOfflineReason, CodeImportMachineState,
    ICodeImportJobWorkflow, ICodeImportMachineSet)
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.testing.layers import TwistedLaunchpadZopelessLayer


class StubSchedulerClient:
    """A stub scheduler client that returns a pre-arranged answer."""

    def __init__(self, id_to_return):
        self.id_to_return = id_to_return

    def getJobForMachine(self, machine):
        return self.id_to_return


class TestCodeImportDispatcherUnit(TestCase):
    """Unit tests for `CodeImportDispatcher`."""

    layer = TwistedLaunchpadZopelessLayer

    def setUp(self):
        nuke_codeimport_sample_data()
        self.config_count = 0
        self.pushConfig(forced_hostname='none')
        self.factory = LaunchpadObjectFactory()
        self._machine = self.factory.makeCodeImportMachine(
            set_online=True, hostname='machine')

    def switchDbUser(self):
        self.layer.txn.commit()
        self.layer.switchDbUser('codeimportdispatcher')
        self.dispatcher = CodeImportDispatcher(
            self.layer.txn, _make_silent_logger())

    @property
    def machine(self):
        return getUtility(ICodeImportMachineSet).getByHostname('machine')

    def pushConfig(self, **args):
        """Push some key-value pairs into the codeimportdispatcher config.

        The config values will be restored during test tearDown.
        """
        self.config_count += 1
        name = 'test%d' % self.config_count
        body = '\n'.join(["%s: %s"%(k, v) for k, v in args.iteritems()])
        config.push(name, dedent("""
            [codeimportdispatcher]
            %s
            """ % body))
        self.addCleanup(config.pop, name)

    def test_getHostname(self):
        # By default, getHostname return the same as socket.gethostname()
        self.switchDbUser()
        self.assertEqual(
            self.dispatcher.getHostname(),
            socket.gethostname())

    def test_getHostnameOverride(self):
        # getHostname can be overriden by the config for testing, however.
        self.switchDbUser()
        self.pushConfig(forced_hostname='test-value')
        self.assertEqual(
            self.dispatcher.getHostname(),
            'test-value')

    def writePythonScript(self, script_path, script_body):
        """Write out an executable Python script.

        This method writes a script header and `script_body` (which should be
        a list of lines of Python source) to `script_path` and makes the file
        executable.
        """
        script = open(script_path, 'w')
        script.write("#!%s\n" % sys.executable)
        for script_line in script_body:
            script.write(script_line + '\n')
        os.chmod(script_path, 0700)

    def filterOutLoggingOptions(self, arglist):
        """Remove the standard logging options from a list of arguments."""
        parser = OptionParser()
        scripts.logger_options(parser)
        options, args = parser.parse_args(arglist)
        return args

    def test_dispatchJob(self):
        # dispatchJob launches a process described by its
        # worker_script attribute with a given job id as an argument.

        # We create a script that writes its command line arguments to
        # some a temporary file and examine that.
        self.switchDbUser()
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir)
        script_path = os.path.join(tmpdir, 'script.py')
        output_path = os.path.join(tmpdir, 'output.txt')
        self.writePythonScript(
            script_path,
            ['import sys',
             'open(%r, "w").write(str(sys.argv[1:]))' % output_path])
        self.dispatcher.worker_script = script_path
        proc = self.dispatcher.dispatchJob(10)
        proc.wait()
        arglist = self.filterOutLoggingOptions(eval(open(output_path).read()))
        self.assertEqual(arglist, ['10'])

    def createJobRunningOnMachine(self, machine):
        """Create a job in the database and mark it as running on `machine`.
        """
        job = self.factory.makeCodeImportJob()
        getUtility(ICodeImportJobWorkflow).startJob(job, machine)
        flush_database_updates()

    def test_shouldLookForJob_machineIsOffline(self):
        # When the machine is offline, the dispatcher doesn't look for any
        # jobs.
        self.machine.setOffline(CodeImportMachineOfflineReason.STOPPED)
        self.switchDbUser()
        self.assertFalse(self.dispatcher.shouldLookForJob(self.machine))

    def test_shouldLookForJob_machineIsQuiescingNoJobsRunning(self):
        # When the machine is quiescing and no jobs are running on this
        # machine, the dispatcher doesn't look for any jobs and sets the
        # machine to be offline.
        self.machine.setQuiescing(self.factory.makePerson(), "reason")
        self.switchDbUser()
        self.assertFalse(self.dispatcher.shouldLookForJob(self.machine))
        self.assertEqual(self.machine.state, CodeImportMachineState.OFFLINE)

    def test_shouldLookForJob_machineIsQuiescingWithJobsRunning(self):
        # When the machine is quiescing and there are jobs running on this
        # machine, the dispatcher doesn't look for any more jobs.
        self.createJobRunningOnMachine(self.machine)
        self.machine.setQuiescing(self.factory.makePerson(), "reason")
        self.switchDbUser()
        self.assertFalse(self.dispatcher.shouldLookForJob(self.machine))
        self.assertEqual(self.machine.state, CodeImportMachineState.QUIESCING)

    def test_shouldLookForJob_enoughJobsRunningOnMachine(self):
        # When there are already enough jobs running on this machine, the
        # dispatcher doesn't look for any more jobs.
        for i in range(config.codeimportdispatcher.max_jobs_per_machine):
            self.createJobRunningOnMachine(self.machine)
        self.switchDbUser()
        self.assertFalse(self.dispatcher.shouldLookForJob(self.machine))

    def test_shouldLookForJob_shouldLook(self):
        # If the machine is online and there are not already
        # max_jobs_per_machine jobs running, then we should look for a job.
        self.switchDbUser()
        self.assertTrue(self.dispatcher.shouldLookForJob(self.machine))

    def test_findAndDispatchJob_jobWaiting(self):
        # If there is a job to dispatch, then we call dispatchJob with its id.
        calls = []
        self.pushConfig(forced_hostname=self.machine.hostname)
        self.switchDbUser()
        self.dispatcher.dispatchJob = lambda job_id: calls.append(job_id)
        self.dispatcher.findAndDispatchJob(StubSchedulerClient(10))
        self.assertEqual(calls, [10])

    def test_findAndDispatchJob_noJobWaiting(self):
        # If there is no job to dispatch, then we just exit quietly.
        calls = []
        self.pushConfig(forced_hostname=self.machine.hostname)
        self.switchDbUser()
        self.dispatcher.dispatchJob = lambda job_id: calls.append(job_id)
        self.dispatcher.findAndDispatchJob(StubSchedulerClient(0))
        self.assertEqual(calls, [])


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
