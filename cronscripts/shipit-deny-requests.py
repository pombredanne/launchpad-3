#!/usr/bin/python
# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Script to deny requests with a TOBEDENIED status"""

import _pythonpath

import optparse
import sys

from zope.component import getUtility

from canonical.config import config
from canonical.lp import initZopeless
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.interfaces import IShippingRequestSet


def main(argv):
    parser = optparse.OptionParser()
    logger_options(parser)
    (options, arguments) = parser.parse_args()
    logger_obj = logger(options, 'shipit-deny-requests')
    logger_obj.info('Denying requests that were marked to be denied.')

    ztm = initZopeless(dbuser=config.shipit.dbuser)
    execute_zcml_for_scripts()

    requestset = getUtility(IShippingRequestSet)
    requestset.denyRequestsPendingDenial()
    ztm.commit()

    logger_obj.info('Done.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

