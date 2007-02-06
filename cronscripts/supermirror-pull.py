#!/usr/bin/env python
# Copyright 2006 Canonical Ltd.  All rights reserved.

import _pythonpath

from optparse import OptionParser

from canonical.config import config
from canonical.launchpad.scripts.supermirror import mirror
from canonical.launchpad.scripts import logger_options, logger
import bzrlib.repository


def shut_up_deprecation_warning():
    # XXX: quick hack to disable the deprecation warning for old repository
    # formats -- DavidAllouche 2006-01-29
    bzrlib.repository._deprecation_warning_done = True


if __name__ == '__main__':
    parser = OptionParser()
    logger_options(parser)
    (options, arguments) = parser.parse_args()
    if arguments:
        parser.error("Unhandled arguments %s" % repr(arguments))

    # Customize the oops reporting config
    oops_prefix = config.supermirror.errorreports.oops_prefix
    config.launchpad.errorreports.oops_prefix = oops_prefix
    errordir = config.supermirror.errorreports.errordir
    config.launchpad.errorreports.errordir = errordir
    copy_to_zlog = config.supermirror.errorreports.copy_to_zlog
    config.launchpad.errorreports.copy_to_zlog = copy_to_zlog

    log = logger(options, 'branch-puller')

    shut_up_deprecation_warning()
    mirror(log)

