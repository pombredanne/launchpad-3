#!/usr/bin/python2.4
# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

import _pythonpath
from optparse import OptionParser

from twisted.internet import reactor

from canonical.authserver.client.branchstatus import BranchStatusClient
from canonical.config import config
from canonical.launchpad.interfaces import BranchType
from canonical.launchpad.scripts import logger_options, logger
from canonical.codehosting.puller import mirror, scheduler


def run_mirror(log, manager):
    deferred = mirror(log, manager)
    deferred.addCallback(lambda ignored: reactor.stop())


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

    log = logger(options, 'branch-puller')
    manager = scheduler.JobManager(BranchStatusClient(), log, branch_type)

    reactor.callWhenRunning(run_mirror, log, manager)
    reactor.run()
