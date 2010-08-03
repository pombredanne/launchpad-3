#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Initialise a new distroseries from its parent"""

import _pythonpath

import sys
from optparse import OptionParser

from zope.component import getUtility
from contrib.glock import GlobalLock

from canonical.config import config
from canonical.launchpad.interfaces import IDistributionSet, NotFoundError
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.lp import initZopeless

from lp.soyuz.scripts.initialise_distroseries import (
    InitialiseDistroSeries, ParentSeriesRequired, PendingBuilds, 
    QueueNotEmpty, SeriesAlreadyInUse)

def main():
    # Parse command-line arguments
    parser = OptionParser()
    logger_options(parser)

    parser.add_option("-N", "--dry-run", action="store_true",
                      dest="dryrun", metavar="DRY_RUN", default=False,
                      help="Whether to treat this as a dry-run or not.")

    parser.add_option("-d", "--distro", dest="distribution", metavar="DISTRO",
                      default="ubuntu",
                      help="Distribution name")

    (options, args) = parser.parse_args()

    log = logger(options, "initialise")

    if len(args) != 1:
        log.error("Need to be given exactly one non-option argument. "
                  "Namely the distroseries to initialise.")
        return 1

    distroseries_name = args[0]

    log.debug("Acquiring lock")
    lock = GlobalLock('/var/lock/launchpad-initialise.lock')
    lock.acquire(blocking=True)

    log.debug("Initialising connection.")

    execute_zcml_for_scripts()
    ztm = initZopeless(dbuser=config.archivepublisher.dbuser)

    try:
        # 'ubuntu' is the default option.distribution value
        distribution = getUtility(IDistributionSet)[options.distribution]
        distroseries = distribution[distroseries_name]
    except NotFoundError, info:
        log.error(info)
        return 1

    try:
        log.debug('Check empty mutable queues in parentseries')
        log.debug('Check for no pending builds in parentseries')
        log.debug('Copying distroarchseries from parent '
                      'and setting nominatedarchindep.')
        ids = InitialiseDistroSeries(distroseries)
        log.debug('initialising from parent, copying publishing records.')
        ids.initialise()
    except ParentSeriesRequired:
        log.error("Parent series required.")
        return 1
    except PendingBuilds:
        log.error("Parent series has pending builds.")
        return 1
    except QueueNotEmpty:
        log.error("Parent series queues are not empty.")
        return 1
    except SeriesAlreadyInUse:
        log.error("Series is already in use.")
        return 1

    if options.dryrun:
        log.debug('Dry-Run mode, transaction aborted.')
        ztm.abort()
    else:
        log.debug('Committing transaction.')
        ztm.commit()

    log.debug("Releasing lock")
    lock.release()
    return 0


if __name__ == '__main__':
    sys.exit(main())

