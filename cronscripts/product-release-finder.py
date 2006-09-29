#!/usr/bin/env python
# Copyright 2004-2006 Canonical Ltd.  All rights reserved.
"""Upstream Product Release Finder.

Scan FTP and HTTP sites specified for each ProductSeries in the database
to identify files and create new ProductRelease records for them.
"""

import _pythonpath
import sys
import optparse

from canonical.config import config
from canonical.lp import initZopeless
from canonical.launchpad.scripts import (execute_zcml_for_scripts,
                                         logger, logger_options)
from canonical.launchpad.scripts.productreleasefinder.finder import (
    ProductReleaseFinder)


def main(argv):
    # Parse command-line arguments
    parser = optparse.OptionParser()
    logger_options(parser)
    (options, args) = parser.parse_args(argv[1:])

    execute_zcml_for_scripts()
    ztm = initZopeless(dbuser=config.productreleasefinder.dbuser,
                       implicitBegin=False)

    log = logger(options, "productreleasefinder")

    prf = ProductReleaseFinder(ztm, log)
    prf.findReleases()

if __name__ == "__main__":
    sys.exit(main(sys.argv))
