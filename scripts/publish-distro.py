#!/usr/bin/python2.4

import _pythonpath

import gc
import logging
from optparse import OptionParser

from zope.component import getUtility

from canonical.archivepublisher.diskpool import DiskPool
from canonical.archivepublisher.config import Config, LucilleConfigError
from canonical.archivepublisher.publishing import Publisher
from canonical.database.sqlbase import (
    flush_database_updates, clear_current_connection_cache)
from canonical.launchpad.interfaces import (
    IDistributionSet, NotFoundError)
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.lp import initZopeless


def parse_options():
    parser = OptionParser()
    logger_options(parser)

    parser.add_option("-C", "--careful", action="store_true",
                      dest="careful", metavar="", default=False,
                      help="Turns on all the below careful options.")

    parser.add_option("-P", "--careful-publishing", action="store_true",
                      dest="careful_publishing", metavar="", default=False,
                      help="Make the package publishing process careful.")

    parser.add_option("-D", "--careful-domination", action="store_true",
                      dest="careful_domination", metavar="", default=False,
                      help="Make the domination process careful.")

    parser.add_option("-A", "--careful-apt", action="store_true",
                      dest="careful_apt", metavar="", default=False,
                      help="Make the apt-ftparchive run careful.")

    parser.add_option("-d", "--distribution",
                      dest="distribution", metavar="DISTRO", default="ubuntu",
                      help="The distribution to publish.")

    parser.add_option('-s', '--suite', metavar='SUITE', dest='suite',
                      action='append', type='string', default=[],
                      help='The suite to publish')

    parser.add_option("-R", "--distsroot",
                      dest="distsroot", metavar="SUFFIX", default=None,
                      help="Override the dists path for generation")

    return parser.parse_args()


def getPublisher(options, log):
    log.debug("Finding distribution object.")

    try:
        distro = getUtility(IDistributionSet).getByName(options.distribution)
    except NotFoundError, info:
        log.error(info)
        raise

    allowed_suites = set()
    for suite in options.suite:
        try:
            distrorelease, pocket = distro.getDistroReleaseAndPocket(suite)
        except NotFoundError, info:
            log.error(info)
            raise
        allowed_suites.add((distrorelease.name, pocket))

    log.debug("Finding configuration.")
    try:
        pubconf = Config(distro)
    except LucilleConfigError, info:
        log.error(info)
        raise

    if options.distsroot is not None:
        log.debug("Overriding dists root with %s." % options.distsroot)
        pubconf.distsroot = options.distsroot

    # It may be the first time we're publishing this distribution; make
    # sure the required directories exist.
    log.debug("Making directories as needed.")
    pubconf.setupArchiveDirs()

    log.debug("Preparing on-disk pool representation.")
    dp = DiskPool(pubconf.poolroot, logging.getLogger("DiskPool"))
    # Set the diskpool's log level to INFO to suppress debug output
    dp.logger.setLevel(20)

    log.debug("Preparing publisher.")
    return Publisher(log, pubconf, dp, distro, allowed_suites)


def main():
    options, args = parse_options()
    assert len(args) == 0, "publish-distro takes no arguments, only options."

    log = logger(options, "publish-distro")

    def careful_msg(what):
        """Quick handy util for the below."""
        if options.careful:
            return "Careful (Overridden)"
        if what:
            return "Careful"
        return "Normal"

    def try_and_commit(description, func, *args):
        try:
            func(*args)
            log.debug("Committing.")
            flush_database_updates()
            txn.commit()
            log.debug("Flushing caches.")
            clear_current_connection_cache()
            gc.collect()
        except:
            log.exception("Bad muju while %s" % description)
            txn.abort()
            raise

    log.info("  Distribution: %s" % options.distribution)
    log.info("    Publishing: %s" % careful_msg(options.careful_publishing))
    log.info("    Domination: %s" % careful_msg(options.careful_domination))
    log.info("Apt-FTPArchive: %s" % careful_msg(options.careful_apt))

    log.debug("Initialising zopeless.")

    # Change this when we fix up db security
    txn = initZopeless(dbuser='lucille')

    execute_zcml_for_scripts()

    publisher = getPublisher(options, log)

    try_and_commit("publishing", publisher.A_publish,
                   options.careful or options.careful_publishing)
    try_and_commit("dominating", publisher.B_dominate,
                   options.careful or options.careful_domination)
    try_and_commit("doing apt-ftparchive", publisher.C_doFTPArchive,
                   options.careful or options.careful_apt)
    try_and_commit("doing release files", publisher.D_writeReleaseFiles,
                   options.careful or options.careful_apt)

    log.debug("Ciao")


if __name__ == "__main__":
    main()
