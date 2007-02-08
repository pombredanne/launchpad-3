#!/usr/bin/env python
# Copyright 2006 Canonical Ltd.  All rights reserved.

import _pythonpath

from optparse import OptionParser

from canonical.config import config
from canonical.launchpad.scripts.supermirror import mirror, jobmanager
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
    which = arguments.pop(0)
    if arguments:
        parser.error("Unhandled arguments %s" % repr(arguments))

    if which == 'upload':
        errorreports = config.supermirror.upload_errorreports
        manager_class = jobmanager.UploadJobManager
    elif which == 'import':
        errorreports = config.supermirror.import_errorreports
        manager_class = jobmanager.ImportJobManager
    elif which == 'mirror':
        errorreports = config.supermirror.mirror_errorreports
        manager_class = jobmanager.MirrorJobManager
    else:
        parser.error(
            "Expected 'upload', 'import' or 'mirror', but got: %r" % which)

    # Customize the oops reporting config.
    config.launchpad.errorreports.oops_prefix = errorreports.oops_prefix
    config.launchpad.errorreports.errordir = errorreports.errordir
    config.launchpad.errorreports.copy_to_zlog = errorreports.copy_to_zlog

    log = logger(options, 'branch-puller')

    shut_up_deprecation_warning()
    mirror(log, manager_class)

