#!/usr/bin/python2.4
# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Script to process requests with a PENDINGSPECIAL status.

For now this script will just deny these PENDINGSPECIAL requests.
"""

import _pythonpath

import optparse
import sys

from zope.component import getUtility

from canonical.config import config
from canonical.lp import initZopeless
from canonical.lp.dbschema import ShippingRequestStatus
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.interfaces import IShippingRequestSet


def main(argv):
    parser = optparse.OptionParser()
    logger_options(parser)
    (options, arguments) = parser.parse_args()
    logger_obj = logger(options, 'shipit-process-requests-pending-special')
    logger_obj.info('Processing requests that were marked as PENDINGSPECIAL.')

    ztm = initZopeless(dbuser=config.shipit.dbuser)
    execute_zcml_for_scripts()

    requestset = getUtility(IShippingRequestSet)
    requestset.processRequestsPendingSpecial(
        status=ShippingRequestStatus.DENIED)
    ztm.commit()

    logger_obj.info('Done.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

