#!/usr/bin/python2.4
# Copyright 2006-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

import _pythonpath
from optparse import OptionParser

from twisted.internet import defer, reactor
from twisted.python import log as tplog
from twisted.web.xmlrpc import Proxy

from lp.codehosting.puller import mirror, scheduler
from canonical.config import config
from canonical.launchpad.scripts import logger_options
from canonical.twistedsupport.loggingsupport import set_up_logging_for_script

def clean_shutdown(ignored):
    reactor.stop()


def shutdown_with_errors(failure):
    tplog.err(failure)
    failure.printTraceback()
    reactor.stop()


def run_mirror(log, manager):
    # It's conceivable that mirror() might raise an exception before it
    # returns a Deferred -- maybeDeferred means we don't have to worry.
    deferred = defer.maybeDeferred(mirror, log, manager)
    deferred.addCallback(clean_shutdown)
    deferred.addErrback(shutdown_with_errors)


if __name__ == '__main__':
    parser = OptionParser()
    logger_options(parser)
    (options, arguments) = parser.parse_args()
    if arguments:
        parser.error("Unhandled arguments %s" % repr(arguments))
    log = set_up_logging_for_script(options, 'supermirror_upload_puller')
    manager = scheduler.JobScheduler(
        Proxy(config.codehosting.branch_puller_endpoint), log)

    reactor.callWhenRunning(run_mirror, log, manager)
    reactor.run()
