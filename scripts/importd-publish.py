#!/usr/bin/python2.4
# Copyright 2005 Canonical Ltd.  All rights reserved.
# Author: David Allouche <david@allouche.net>

"""Push a vcs-import branch to the internal publication server.

If the ProductSeries.branch for that import was not set yet, create the Branch
record for that new branch, link to it from the ProductSeries.branch, and push
the branch.

If the ProductSeries.branch for that import was already set, just push the
branch.

Any divergence between the local and the published branch will cause an error.
"""


import _pythonpath

import sys
import logging
from optparse import OptionParser

from canonical.lp import initZopeless
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger, log)
from canonical.launchpad.scripts.importd.bzr_progress import (
    setup_batch_progress)
from canonical.config import config

from canonical.launchpad.scripts.importd.publish import ImportdPublisher


def parse_args(args):
    """Parse command line options"""

    parser = OptionParser()

    # Add the verbose/quiet options.
    logger_options(parser)

    return parser.parse_args(args)


def main(argv):
    options, args = parse_args(argv[1:])
    workingdir, series_id_as_str, push_prefix = args
    series_id = int(series_id_as_str)

    # Get the global logger for this task.
    logger(options, 'importd-publish')

    # We don't want debug messages from bzr at that point.
    bzr_logger = logging.getLogger("bzr")
    bzr_logger.setLevel(logging.INFO)

    # Provide line-by-line progress report from bzrlib, so importd will not
    # kill this script even if it takes some time.
    setup_batch_progress()

    # Setup zcml machinery to be able to use getUtility
    execute_zcml_for_scripts()
    initZopeless(dbuser=config.importd.dbuser)

    # The actual work happens here
    ImportdPublisher(log, workingdir, series_id, push_prefix).publish()

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
