#!/usr/bin/python
# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Script to export ShipIt orders into csv files."""

import _pythonpath

import optparse
import sys

from zope.component import getUtility

from canonical.config import config
from canonical.lp import initZopeless, READ_COMMITTED_ISOLATION
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.interfaces import (
    IShippingRequestSet, ShippingRequestPriority)


def parse_options(args):
    """Parse options for exporting ShipIt orders."""
    parser = optparse.OptionParser(
        usage='%prog --priority=normal|high')
    parser.add_option(
        '--priority',
        dest='priority',
        default=None,
        action='store',
        help='Export only orders with the given priority'
        )

    # Add the verbose/quiet options.
    logger_options(parser)

    options, args = parser.parse_args(args)

    return options


def main(argv):
    options = parse_options(argv[1:])
    logger_obj = logger(options, 'shipit-export-orders')
    logger_obj.info('Exporting %s priority ShipIt orders' % options.priority)

    if options.priority == 'normal':
        priority = ShippingRequestPriority.NORMAL
    elif options.priority == 'high':
        priority = ShippingRequestPriority.HIGH
    else:
        logger_obj.error(
            'Wrong value for argument --priority: %s' % options.priority)
        return 1

    ztm = initZopeless(dbuser=config.shipit.exporter_dbuser,
                       isolation=READ_COMMITTED_ISOLATION)
    execute_zcml_for_scripts()

    requestset = getUtility(IShippingRequestSet)
    requestset.exportRequestsToFiles(priority, ztm)

    logger_obj.info('Done.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

