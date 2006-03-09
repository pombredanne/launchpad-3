#!/usr/bin/python
# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Script to export ShipIt orders into csv files."""

import _pythonpath

from cStringIO import StringIO
from datetime import datetime
import csv
import optparse
import sys

from zope.component import getUtility

import pytz

from canonical.config import config
from canonical.uuid import generate_uuid
from canonical.lp import initZopeless
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.interfaces import (
    IShippingRunSet, IShipmentSet, ILibraryFileAliasSet, IShippingRequestSet,
    ShippingRequestPriority)


# The maximum number of requests in a single shipping run
MAX_SHIPPINGRUN_SIZE = 10000


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


def create_shippingrun(request_ids, ztm, logger_obj):
    """Create a new ShippingRun containing all the given requests."""
    requestset = getUtility(IShippingRequestSet)
    shipmentset = getUtility(IShipmentSet)
    shippingrun = getUtility(IShippingRunSet).new()
    for request_id in request_ids:
        request = requestset.get(request_id)
        if not request.isApproved():
            # This request's status may have been changed after we started
            # running the script. Now it's not approved anymore and we can't
            # export it.
            continue
        assert not request.cancelled
        assert request.shipment is None
        shipment = shipmentset.new(
            request, request.shippingservice, shippingrun)
    return shippingrun


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

    ztm = initZopeless(dbuser=config.shipitexporter.dbuser)
    execute_zcml_for_scripts()
    ztm.begin()
    requestset = getUtility(IShippingRequestSet)
    request_ids = [
        request.id for request in requestset.getUnshippedRequests(priority)]
    ztm.commit()

    # The MAX_SHIPPINGRUN_SIZE is not a hard limit, and it doesn't make sense
    # to split a shippingrun into two just because there's 10 requests more
    # than the limit, so we only split them if there's at least 50% more
    # requests than MAX_SHIPPINGRUN_SIZE.
    file_counter = 1
    while len(request_ids):
        ztm.begin()
        if len(request_ids) > MAX_SHIPPINGRUN_SIZE * 1.5:
            request_ids_subset = request_ids[:MAX_SHIPPINGRUN_SIZE]
            request_ids[:MAX_SHIPPINGRUN_SIZE] = []
        else:
            request_ids_subset = request_ids[:]
            request_ids = []
        shippingrun = create_shippingrun(request_ids_subset, ztm, logger_obj)

        csv_file = shippingrun.exportToCSVFile()
        # Seek to the beginning of the file, so the librarian can read it.
        csv_file.seek(0)

        # Send the file to librarian.
        fileset = getUtility(ILibraryFileAliasSet)
        now = datetime.now(pytz.timezone('UTC'))
        filename = 'Ubuntu'
        if options.priority == 'high':
            filename += '-High-Pri'
        filename += '-%s-%d.%s.csv' % (
                now.strftime('%y-%m-%d'), file_counter, generate_uuid()
                )
        shippingrun.csvfile = fileset.create(
            name=filename, size=len(csv_file.getvalue()), file=csv_file,
            contentType='text/plain')
        ztm.commit()
        file_counter += 1

    logger_obj.info('Done.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

