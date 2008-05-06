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

from canonical.config import config
from canonical.codehosting.codeimport.dispatcher import CodeImportDispatcher
from canonical.codehosting.codeimport.tests.test_foreigntree import (
    _make_silent_logger)
from canonical.launchpad import scripts
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
        self.config_count = 0
        self.pushConfig(forced_hostname='none')
        self.dispatcher = CodeImportDispatcher(_make_silent_logger())

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
        proc = self.dispatcher.dispatchJob(10)
        proc.wait()
        arglist = self.filterOutLoggingOptions(eval(open(output_path).read()))
        self.assertEqual(arglist, ['10'])

    def test_findAndDispatchJob_jobWaiting(self):
        # If there is a job to dispatch, then we call dispatchJob with its id.
        calls = []
        self.pushConfig(forced_hostname=self.machine.hostname)
        self.dispatcher.dispatchJob = lambda job_id: calls.append(job_id)
        self.dispatcher.findAndDispatchJob(StubSchedulerClient(10))
        self.assertEqual(calls, [10])

    def test_findAndDispatchJob_noJobWaiting(self):
        # If there is no job to dispatch, then we just exit quietly.
        calls = []
        self.pushConfig(forced_hostname=self.machine.hostname)
        self.dispatcher.dispatchJob = lambda job_id: calls.append(job_id)
        self.dispatcher.findAndDispatchJob(StubSchedulerClient(0))
        self.assertEqual(calls, [])


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
