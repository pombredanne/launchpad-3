#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

""" """

__metaclass__ = type


# pylint: disable-msg=W0403
import _pythonpath

from optparse import OptionParser

from twisted.internet import defer, reactor
from twisted.python import log

from canonical.codehosting.codeimport.worker_monitor import (
    CodeImportWorkerMonitor)
from canonical.launchpad import scripts
from canonical.lp import initZopeless


class CodeImportWorker:

    def __init__(self):
        parser = OptionParser()
        scripts.logger_options(parser)
        options, self.args = parser.parse_args()
        self.logger = scripts.logger(options, 'code-import-worker')

    def main(self):
        def go():
            initZopeless(implicitBegin=False)
            scripts.execute_zcml_for_scripts()
            arg, = self.args
            return CodeImportWorkerMonitor(int(arg), self.logger).run()
        def wrap():
            defer.maybeDeferred(go).addErrback(
                log.err).addCallback(
                lambda ignored: reactor.stop())
        reactor.callWhenRunning(wrap)
        reactor.run()


if __name__ == '__main__':
    script = CodeImportWorker()
    script.main()
