#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0103,W0403

import _pythonpath
from optparse import OptionParser

from twisted.internet import defer, reactor
from twisted.python import log as tplog

from canonical.config import config
from canonical.launchpad.scripts import logger_options
from lp.codehosting.puller import mirror, scheduler
from lp.services.twistedsupport.loggingsupport import (
    LoggingProxy, set_up_logging_for_script)

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
    parser.add_option('--branch-type', action='append', default=[])
    (options, arguments) = parser.parse_args()
    if arguments:
        parser.error("Unhandled arguments %s" % repr(arguments))
    log = set_up_logging_for_script(options, 'supermirror_puller')
    manager = scheduler.JobScheduler(
        LoggingProxy(config.codehosting.codehosting_endpoint, log), log,
        options.branch_type)

    reactor.callWhenRunning(run_mirror, log, manager)
    reactor.run()
