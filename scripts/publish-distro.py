#!/usr/bin/python

import logging
import gc

import _pythonpath

from optparse import OptionParser

from canonical.lp import initZopeless
from canonical.database.sqlbase import (
    flush_database_updates,
    clear_current_connection_cache)

from canonical.archivepublisher.diskpool import DiskPool, Poolifier, POOL_DEBIAN
from canonical.archivepublisher.config import Config, LucilleConfigError
from canonical.archivepublisher.publishing import Publisher

from canonical.launchpad.database import Distribution
from canonical.launchpad.scripts import (execute_zcml_for_scripts,
                                         logger, logger_options)


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

    parser.add_option("-R", "--distsroot",
                      dest="distsroot", metavar="SUFFIX", default=None,
                      help="Override the dists path for generation")

    return parser.parse_args()


def getPublisher(options, log):
    log.debug("Finding distribution object.")
    distro = Distribution.selectOneBy(name=options.distribution)

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
    dp = DiskPool(Poolifier(POOL_DEBIAN),
                  pubconf.poolroot, logging.getLogger("DiskPool"))
    # Set the diskpool's log level to INFO to suppress debug output
    dp.logger.setLevel(20)
    dp.scan()

    log.debug("Preparing publisher.")
    return Publisher(log, pubconf, dp, distro)


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
                   options.careful)
    try_and_commit("santising links", publisher.E_sanitiseLinks)

    log.debug("Ciao")


if __name__ == "__main__":
    main()
