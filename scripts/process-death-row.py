#!/usr/bin/python2.4
"""Death row kickoff script."""

import _pythonpath

from optparse import OptionParser

from zope.component import getUtility

from canonical.launchpad.interfaces import IDistributionSet
from canonical.config import config
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.lp import initZopeless

from canonical.archivepublisher.deathrow import getDeathRow


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
    parser.add_option("--ppa", action="store_true",
                      dest="ppa", metavar="PPA", default=False,
                      help="Run only over PPA archives.")

    logger_options(parser)
    (options, args) = parser.parse_args()
    log = logger(options, "deathrow-distro")

    log.debug("Initialising zopeless.")

    txn = initZopeless(dbuser=config.archivepublisher.dbuser)
    execute_zcml_for_scripts()

    distribution = getUtility(IDistributionSet).getByName(
        options.distribution)

    if not options.ppa:
        archives = distribution.all_distro_archives
    else:
        archives = distribution.getAllPPAs()

    for archive in archives:
        death_row = getDeathRow(archive, log, options.pool_root)
        try:
            # Unpublish death row
            log.debug("Unpublishing death row for %s." % archive.title)
            death_row.reap(options.dry_run)

            if options.dry_run:
                log.debug("Dry run mode; rolling back.")
                txn.abort()
            else:
                log.debug("Committing")
                txn.commit()
        except:
            log.exception("Unexpected exception while doing death-row "
                          "unpublish")
            txn.abort()
            # Continue with other archives.


if __name__ == "__main__":
    main()

