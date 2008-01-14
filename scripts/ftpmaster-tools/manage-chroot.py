#!/usr/bin/python2.4

"""Copyright Canonical Limited 2005
 Author: Matt Zimmerman <matt.zimmerman@canonical.com>
     based on upload2librarian.py by:
         Daniel Silverstone <daniel.silverstone@canonical.com>
         Celso Providelo <celso.providelo@canonical.com>
 Tool for adding, removing and replacing buildd chroots
"""

import _pythonpath
from optparse import OptionParser
import sys

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IDistributionSet, NotFoundError, PackagePublishingPocket)
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger)
from canonical.launchpad.scripts.ftpmaster import (
    ChrootManager, ChrootManagerError)

from canonical.lp import (
    initZopeless, READ_COMMITTED_ISOLATION)

def main():
    parser = OptionParser()
    logger_options(parser)

    parser.add_option("-d", "--distribution",
                      dest="distribution", metavar="DISTRIBUTION",
                      default="ubuntu", help="Distribution name")

    parser.add_option("-s", "--series",
                      dest="series", metavar="SERIES", default=None,
                      help="Series name")

    parser.add_option("-a", "--architecture",
                      dest="architecture", metavar="ARCH", default=None,
                      help="Architecture tag")

    parser.add_option("-f", "--filepath",
                      dest="filepath", metavar="FILEPATH", default=None,
                      help="Chroot file path")

    (options, args) = parser.parse_args()

    log = logger(options, "manage-chroot")

    try:
        action = args[0]
    except IndexError:
        log.error('manage-chroot.py <add|update|remove|get>')
        return 1

    log.debug("Intitialising connetion.")
    ztm = initZopeless(dbuser="fiera", isolation=READ_COMMITTED_ISOLATION)
    execute_zcml_for_scripts()

    try:
        distribution = getUtility(IDistributionSet)[options.distribution]
    except NotFoundError, info:
        log.error("Distribution not found: %s" % info)
        return 1

    try:
        if options.series is not None:
            series, dummypocket = distribution.getDistroSeriesAndPocket(
                options.series)
        else:
            series = distribution.currentseries
    except NotFoundError, info:
        log.error("Series not found: %s" % info)
        return 1

    try:
        dar = series[options.architecture]
    except NotFoundError, info:
        log.error(info)
        return 1

    log.debug("Initialising ChrootManager for '%s'" % (dar.title))
    chroot_manager = ChrootManager(dar, filepath=options.filepath)

    if action in chroot_manager.allowed_actions:
        chroot_action = getattr(chroot_manager, action)
    else:
        log.error("Unknown action: %s" % action)
        log.error("Allowed actions: %s" % chroot_manager.allowed_actions)
        ztm.abort()
        return 1

    try:
        chroot_action()
    except ChrootManagerError, info:
        log.error(info)
        ztm.abort()
        return 1
    else:
        # collect extra debug messages from chroot_manager
        for debug_message in chroot_manager._messages:
            log.debug(debug_message)

    ztm.commit()
    log.info("Success.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
