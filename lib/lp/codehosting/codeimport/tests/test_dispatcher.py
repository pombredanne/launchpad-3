# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the code import dispatcher."""

__metaclass__ = type


from optparse import OptionParser
import os
import shutil
import socket
import tempfile
from unittest import TestLoader

from canonical.launchpad import scripts
from canonical.launchpad.scripts.logger import QuietFakeLogger
from canonical.testing.layers import TwistedLaunchpadZopelessLayer

from lp.codehosting.codeimport.dispatcher import CodeImportDispatcher
from lp.testing import TestCase


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
        self.pushConfig('codeimportdispatcher', forced_hostname='none')

    def makeDispatcher(self, worker_limit=None):
        """Make a `CodeImportDispatcher`."""
        return CodeImportDispatcher(QuietFakeLogger(), worker_limit)

    def test_getHostname(self):
        # By default, getHostname return the same as socket.gethostname()
        dispatcher = self.makeDispatcher()
        self.assertEqual(socket.gethostname(), dispatcher.getHostname())

    def test_getHostnameOverride(self):
        # getHostname can be overriden by the config for testing, however.
        dispatcher = self.makeDispatcher()
        self.pushConfig('codeimportdispatcher', forced_hostname='test-value')
        self.assertEqual('test-value', dispatcher.getHostname())

    def writePythonScript(self, script_path, script_body):
        """Write out an executable Python script.

        This method writes a script header and `script_body` (which should be
        a list of lines of Python source) to `script_path` and makes the file
        executable.
        """
        script = open(script_path, 'w')
        for script_line in script_body:
            script.write(script_line + '\n')

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
        dispatcher = self.makeDispatcher()
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir)
        script_path = os.path.join(tmpdir, 'script.py')
        output_path = os.path.join(tmpdir, 'output.txt')
        self.writePythonScript(
            script_path,
            ['import sys',
             'open(%r, "w").write(str(sys.argv[1:]))' % output_path])
        dispatcher.worker_script = script_path
        proc = dispatcher.dispatchJob(10)
        proc.wait()
        arglist = self.filterOutLoggingOptions(eval(open(output_path).read()))
        self.assertEqual(arglist, ['10'])

    def test_findAndDispatchJob_jobWaiting(self):
        # If there is a job to dispatch, then we call dispatchJob with its id
        # and the worker_limit supplied to the dispatcher.
        calls = []
        worker_limit = self.factory.getUniqueInteger()
        dispatcher = self.makeDispatcher(worker_limit)
        dispatcher.dispatchJob = \
            lambda job_id, limit: calls.append((job_id, limit))
        dispatcher.findAndDispatchJob(StubSchedulerClient(10))
        self.assertEqual(
            calls, [(10, worker_limit)])

    def test_findAndDispatchJob_noJobWaiting(self):
        # If there is no job to dispatch, then we just exit quietly.
        calls = []
        dispatcher = self.makeDispatcher()
        self.dispatcher.dispatchJob = \
            lambda job_id, limit: calls.append((job_id, limit))
        dispatcher.findAndDispatchJob(StubSchedulerClient(0))
        self.assertEqual(calls, [])


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
