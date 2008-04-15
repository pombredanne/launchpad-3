#!/usr/bin/python2.4
# Copyright 2006-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

import _pythonpath
from optparse import OptionParser

from twisted.internet import defer, reactor

from canonical.codehosting.puller import mirror, scheduler
from canonical.launchpad.interfaces import BranchType
from canonical.launchpad.scripts import logger_options
from canonical.twistedsupport.loggingsupport import set_up_logging_for_script

def clean_shutdown(ignored):
    reactor.stop()


def shutdown_with_errors(failure):
    log.err(failure)
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
    which = arguments.pop(0)
    if arguments:
        parser.error("Unhandled arguments %s" % repr(arguments))

    branch_type_map = {
        'upload': BranchType.HOSTED,
        'mirror': BranchType.MIRRORED,
        'import': BranchType.IMPORTED
        }

    try:
        branch_type = branch_type_map[which]
    except KeyError:
        parser.error(
            'Expected one of %s, but got: %r'
            % (branch_type_map.keys(), which))

    log = set_up_logging_for_script(options, 'branch-puller')
    manager = scheduler.JobScheduler(
        scheduler.BranchStatusClient(), log, branch_type)

    reactor.callWhenRunning(run_mirror, log, manager)
    reactor.run()
