#!/usr/bin/python2.4
# Copyright 2005 Canonical Ltd.  All rights reserved.
# Author: David Allouche <david@allouche.net>

"""Download a cscvs source tree from a remote repository of source trees.

usage: importd-get-source.py local_source remote_dir

local_source must be the absolute path where to unpack the retrieved source
tree.

remote_dir must be the URL of a directory containing a gzipped tarball
"$(basename local_source).tgz".

The remote tarball will be downloaded as $local_source.tgz, and untarred as
$local_source. Any of those names already in use will be deleted at the
beginning of the script.

The basename of local_source is used to avoid confusing between cvs source
trees (cvsworking) and svn source trees (svnworking).

XXX: As a transition feature, if the remote tarball is not present but the
local_source is present locally, that script will behave like
importd-put-source.py -- David Allouche 2006-08-02
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
    ImportdSourceTransport(log, local_source, remote_dir).getImportdSource()

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
