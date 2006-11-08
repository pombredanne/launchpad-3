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
    IShippingRequestSet, ShipItConstants, ShippingRequestPriority)
from canonical.lp.dbschema import ShipItDistroRelease


def parse_options(args):
    """Parse options for exporting ShipIt orders."""
    parser = optparse.OptionParser(
        usage='%prog --priority=normal|high')
    parser.add_option(
        '--priority',
        dest='priority',
        default=None,
        action='store',
        help='Export only requests with the given priority'
        )
    parser.add_option(
        '--distrorelease',
        dest='distrorelease',
        default=None,
        action='store',
        help='Export only requests for CDs of the given distrorelease'
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

    distrorelease = ShipItConstants.current_distrorelease
    if options.distrorelease is not None:
        try:
            distrorelease = ShipItDistroRelease.items[
                options.distrorelease.upper()]
        except KeyError:
            valid_names = ", ".join(
                release.name for release in ShipItDistroRelease.items)
            logger_obj.error(
                'Invalid value for argument --distrorelease: %s. Valid '
                'values are: %s' % (options.distrorelease, valid_names))
            return 1

    ztm = initZopeless(dbuser=config.shipit.dbuser,
                       isolation=READ_COMMITTED_ISOLATION)
    execute_zcml_for_scripts()

    requestset = getUtility(IShippingRequestSet)
    requestset.exportRequestsToFiles(priority, ztm, distrorelease)

    logger_obj.info('Done.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

