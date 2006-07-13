#!/usr/bin/python

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
    IDistributionSet, NotFoundError)
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger)
from canonical.launchpad.scripts.ftpmaster import (
    ChrootManager, ChrootManagerError)

from canonical.lp import initZopeless
from canonical.lp.dbschema import PackagePublishingPocket

def main():
    parser = OptionParser()
    logger_options(parser)

    parser.add_option("-d", "--distribution",
                      dest="distribution", metavar="DISTRIBUTION",
                      default="ubuntu", help="distribution name")

    parser.add_option("-s", "--suite",
                      dest="suite", metavar="SUITE", default=None,
                      help="suite name")

    parser.add_option("-a", "--architecture",
                      dest="architecture", metavar="ARCH", default=None,
                      help="architecture tag")

    parser.add_option("-f", "--filepath",
                      dest="filepath", metavar="FILEPATH", default=None,
                      help="chroot file path")

    (options, args) = parser.parse_args()

    log = logger(options, "manage-chroot")

    try:
        action = args[0]
    except IndexError:
        log.error('manage-chroot.py <add|update|remove|get>')
        return 1

    ztm = initZopeless(dbuser="fiera")
    execute_zcml_for_scripts()

    try:
        distribution = getUtility(IDistributionSet)[options.distribution]
    except NotFoundError, info:
        log.error("Distribution not found: %s" % info)
        return 1

    try:
        if options.suite is not None:
            release, pocket = distribution.getDistroReleaseAndPocket(
                options.suite)
        else:
            release = distribution.currentrelease
            pocket = PackagePublishingPocket.RELEASE
    except NotFoundError, info:
        log.error("Suite not found: %s" % info)
        return 1

    try:
        dar = release[options.architecture]
    except NotFoundError, info:
        log.error(info)
        return 1

    chroot_manager = ChrootManager(dar, pocket)
    try:
        try:
            chroot_action = getattr(chroot_manager, action)
        except AttributeError:
            log.error("Unknown action: %s" % action)
            ztm.abort()
            return 1

        chroot_action(filepath=options.filepath)

    except ChrootManagerError, info:
        log.error(info)
        ztm.abort()
        return 1

    ztm.commit()
    log.info("Success.")
    return 0



if __name__ == '__main__':
    sys.exit(main())
