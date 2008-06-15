
import sys
import logging
import optparse

import _pythonpath

from canonical.lp import initZopeless
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger as logger_from_options)
from canonical.launchpad.scripts.keyringtrustanalyser import *

def readClusters(fp):
    """Read clusters of email addresses from the file (separated by blank
    lines), and yield them as sets."""
    cluster = set()
    for line in fp:
        line = line.strip()
        if line:
            cluster.add(line)
        elif cluster:
            yield cluster
            cluster = set()
    if cluster:
        yield cluster

def main(argv):
    parser = optparse.OptionParser(
        description="This script reads a list of email address clusters. "
        "and updates the Launchpad database to match by adding email "
        "addresses to existing accounts, merging accounts and "
        "creating new accounts")
    parser.add_option('-i', '--input', metavar='FILE', action='store',
                      help='Read clusters from the given file',
                      type='string', dest='input', default=None)

    logger_options(parser, logging.WARNING)

    options, args = parser.parse_args(argv[1:])

    # get logger
    logger = logger_from_options(options)

    if options.input is not None:
        logger.debug('openning %s', options.input)
        fp = open(options.input, 'r')
    else:
        fp = sys.stdin

    logger.info('Setting up utilities')
    execute_zcml_for_scripts()

    logger.info('Connecting to database')
    ztm = initZopeless()

    mergeClusters(readClusters(fp), ztm, logger)

    logger.info('Done')

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
