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

from twisted.internet import reactor
from twisted.trial.unittest import TestCase
from twisted.web.server import Site
from twisted.web.xmlrpc import XMLRPC

from zope.component import getUtility

from canonical.config import config
from canonical.codehosting.codeimport.dispatcher import CodeImportDispatcher
from canonical.codehosting.codeimport.tests.test_foreigntree import (
    _make_silent_logger)
from canonical.codehosting.codeimport.tests.test_worker_monitor import (
    nuke_codeimport_sample_data)
from canonical.codehosting.codeimport.worker_monitor import (
    writing_transaction)
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad import scripts
from canonical.launchpad.interfaces import (
    CodeImportMachineOfflineReason, CodeImportMachineState,
    ICodeImportJobWorkflow)
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.testing.layers import TwistedLaunchpadZopelessLayer
from canonical.twistedsupport import defer_to_thread

class CodeImportDispatcherTestMixin:
    """Helper class for testing CodeImportDispatcher.

    Subclasses must define a 'Dispatcher' attribute, an instance of which will
    be created during setUp().
    """

    layer = TwistedLaunchpadZopelessLayer

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

    def setUp(self):
        nuke_codeimport_sample_data()
        self.config_count = 0
        self.pushConfig(forced_hostname='none')
        self.dispatcher = self.Dispatcher(
            TwistedLaunchpadZopelessLayer.txn, _make_silent_logger())
        self.factory = LaunchpadObjectFactory()


class StubScheduler(XMLRPC):
    """A stub version of the CodeImportScheduler XML-RPC service."""

    def __init__(self, id_to_return):
        """Initialize the instance.

        :param id_to_return: Calls to `getJobForMachine` will return this
            value.
        """
        XMLRPC.__init__(self)
        self.id_to_return = id_to_return

    def xmlrpc_getJobForMachine(self, machine_name):
        """Return the pre-arranged answer."""
        return self.id_to_return

class StubSchedulerFixture:
    """A fixture to set up and tear down the stub scheduler XML-RPC service.
    """

    def __init__(self, id_to_return):
        """Initialize the instance.

        :param id_to_return: Calls to `getJobForMachine` on the XML-RPC
            service will return this value.
        """
        self.id_to_return = id_to_return

    def setUp(self):
        """Set up the stub service."""
        self.port = reactor.listenTCP(
            0, Site(StubScheduler(self.id_to_return)))

    def tearDown(self):
        """Tear down the stub service."""
        return self.port.stopListening()

    def get_url(self):
        """Return the URL of the stub service's endpoint."""
        tcp_port = self.port.getHost().port
        return 'http://localhost:%s/' % tcp_port


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
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir)
        script_path = os.path.join(tmpdir, 'script.py')
        output_path = os.path.join(tmpdir, 'output.txt')
        self.writePythonScript(
            script_path,
            ['import sys',
             'open(%r, "w").write(str(sys.argv[1:]))' % output_path])
        self.dispatcher.worker_script = script_path
        self.dispatcher.dispatchJob(10)
        # It's a little bit dodgy to call os.wait() here: we don't know for
        # certain that it will be the child launched in dispatchJob that will
        # be reaped, but it is still extremely likely.
        os.wait()
        arglist = self.filterOutLoggingOptions(eval(open(output_path).read()))
        self.assertEqual(arglist, ['10'])

    def test_getJobForMachine(self):
        # getJobForMachine calls getJobForMachine on the endpoint
        # described by the codeimportscheduler_url config entry.
        stub_scheduler_fixture = StubSchedulerFixture(42)
        stub_scheduler_fixture.setUp()
        self.addCleanup(stub_scheduler_fixture.tearDown)
        self.pushConfig(
            codeimportscheduler_url=stub_scheduler_fixture.get_url())
        @defer_to_thread
        @writing_transaction
        def get_job_id():
            return self.dispatcher.getJobForMachine(
                self.factory.makeCodeImportMachine(set_online=True))
        return get_job_id().addCallback(self.assertEqual, 42)


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
        # max_jobs_per_machine jobs running, then we look for and dispatch
        # exactly one job.
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
