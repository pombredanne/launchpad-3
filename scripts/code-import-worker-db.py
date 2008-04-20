#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""When passed a CodeImportJob id on the command line, process that job.

The actual work of processing a job is done by the code-import-worker.py
script which this process runs as a child process and updates the database on
its progress and result.

This script is usually run by the code-import-dispatcher cronscript.
"""

__metaclass__ = type


# pylint: disable-msg=W0403
import _pythonpath

from twisted.internet import defer, reactor
from twisted.python import log

from canonical.codehosting.codeimport.worker_monitor import (
    CodeImportWorkerMonitor)
from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.twistedsupport.loggingsupport import set_up_oops_reporting


class CodeImportWorker(LaunchpadScript):

    def __init__(self, name, dbuser=None, test_args=None):
        LaunchpadScript.__init__(self, name, dbuser, test_args)
        set_up_oops_reporting(name)

    def main(self):
        reactor.callWhenRunning(self._run_reactor)
        reactor.run()

    def _run_reactor(self):
        defer.maybeDeferred(self._main).addErrback(
            log.err).addCallback(
            lambda ignored: reactor.stop())

    def _main(self):
        arg, = self.args
        return CodeImportWorkerMonitor(int(arg), self.logger).run()

if __name__ == '__main__':
    script = CodeImportWorker('codeimportworker')
    script.run()
