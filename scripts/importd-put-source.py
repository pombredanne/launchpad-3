#!/usr/bin/python2.4
# Copyright 2005 Canonical Ltd.  All rights reserved.
# Author: David Allouche <david@allouche.net>

"""Upload a cscvs source tree to a remote repository of source trees.

usage: importd-put-source.py local_source remote_dir

local_source must be the absolute path where to find the local source tree to
upload.

remote_dir must be the URL of a directory. If that directory does not exist,
its parent must exist and the directory will be created. Then a
$local_source.tgz tarball will be created, uploaded to remote_dir as $(basename
local_source).tgz.swp, and finally renamed to $(basename local_source).tgz,
replacing the old tarball.

If remote_dir contains any name except $(basename local_source).tgz, they will
be deleted at the beginning of the script. That is needed because the bzrlib
SFTP tranport may use a temporary name during the upload and we do not want to
accumulate files left behind by interrupted uploads.

The basename of local_source is used to avoid confusing between cvs source
trees (cvsworking) and svn source trees (svnworking).
"""


import _pythonpath

import sys
import logging
from optparse import OptionParser

from canonical.launchpad.scripts import logger_options, logger, log
from canonical.launchpad.scripts.importd.bzr_progress import (
    setup_batch_progress)

from canonical.launchpad.scripts.importd.sourcetransport import (
    ImportdSourceTransport)


def parse_args(args):
    """Parse command line options"""

    parser = OptionParser()

    # Add the verbose/quiet options.
    logger_options(parser)

    return parser.parse_args(args)


def main(argv):
    options, args = parse_args(argv[1:])
    local_source, remote_dir = args

    # Get the global logger for this task.
    logger(options, 'importd-get-source')

    # We use bzrlib transport facility and we don't want debug messages from
    # bzr at that point.
    bzr_logger = logging.getLogger("bzr")
    bzr_logger.setLevel(logging.INFO)

    # We use the bzrlib progress reporting facility to notify importd of
    # progress. We want produce line-by-line progress report.
    setup_batch_progress()

    # The actual work happens here.
    ImportdSourceTransport(log, local_source, remote_dir).putImportdSource()

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
