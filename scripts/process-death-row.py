#!/usr/bin/python2.4
"""Death row kickoff script."""

import _pythonpath

import logging
from optparse import OptionParser

from canonical.lp import initZopeless
from canonical.launchpad.database import Distribution
from canonical.launchpad.scripts import (execute_zcml_for_scripts,
                                         logger, logger_options)

from canonical.archivepublisher.diskpool import DiskPool
from canonical.archivepublisher.config import Config, LucilleConfigError
from canonical.archivepublisher.deathrow import DeathRow


def getDeathRow(distroname, log, pool_root_override):
    distro = Distribution.byName(distroname)

    log.debug("Grab Lucille config.")
    try:
        pubconf = Config(distro)
    except LucilleConfigError, info:
        log.error(info)
        raise

    if pool_root_override is not None:
        pool_root = pool_root_override
    else:
        pool_root = pubconf.poolroot

    temp_root = pubconf.temproot

    log.debug("Preparing on-disk pool representation.")
    dp = DiskPool(pool_root, temp_root, logging.getLogger("DiskPool"))
    # Set the diskpool's log level to INFO to suppress debug output
    dp.logger.setLevel(20)

    log.debug("Preparing death row.")
    return DeathRow(distro, dp, log)


def main():
    parser = OptionParser()
    parser.add_option("-n", "--dry-run", action="store_true",
                      dest="dry_run", metavar="", default=False,
                      help=("Dry run: goes through the motions but "
                            "commits to nothing."))
    parser.add_option("-d", "--distribution",
                      dest="distribution", metavar="DISTRO",
                      help="Specified the distribution name.")
    parser.add_option("-p", "--pool-root", metavar="PATH",
                      help="Override the path to the pool folder")

    logger_options(parser)
    (options, args) = parser.parse_args()
    log = logger(options, "deathrow-distro")

    log.debug("Initialising zopeless.")
    # XXX Change this when we fix up db security
    txn = initZopeless(dbuser='lucille')
    execute_zcml_for_scripts()

    distroname = options.distribution
    death_row = getDeathRow(distroname, log, options.pool_root)
    try:
        # Unpublish death row
        log.debug("Unpublishing death row.")
        death_row.reap(options.dry_run)

        if options.dry_run:
            log.debug("Dry run mode; rolling back.")
            txn.abort()
        else:
            log.debug("Committing")
            txn.commit()
    except:
        log.exception("Bad muju while doing death-row unpublish")
        txn.abort()
        raise


if __name__ == "__main__":
    main()

