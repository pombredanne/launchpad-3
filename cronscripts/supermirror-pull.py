#!/usr/bin/env python
# Copyright 2006 Canonical Ltd.  All rights reserved.

import _pythonpath

from optparse import OptionParser

from canonical.launchpad.scripts.supermirror import mirror
from canonical.launchpad.scripts import logger_options, logger


if __name__ == '__main__':
    parser = OptionParser()
    logger_options(parser)
    (options, arguments) = parser.parse_args()
    if arguments:
        parser.error("Unhandled arguments %s" % repr(arguments))

    log = logger(options, 'branch-puller')

    mirror(log)

