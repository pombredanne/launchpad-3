#!/usr/bin/python

import _pythonpath

import gc
from optparse import OptionParser

from zope.component import getUtility

from canonical.archivepublisher.publishing import getPublisher
from canonical.database.sqlbase import (
    flush_database_updates, clear_current_connection_cache)
from canonical.launchpad.interfaces import (
    IArchiveSet, IDistributionSet, NotFoundError)
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

    parser.add_option("--ppa", action="store_true",
                      dest="ppa", metavar="PPA", default=False,
                      help="Run only over PPA archives.")

    return parser.parse_args()


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

    if not options.ppa:
        log.info("Apt-FTPArchive: %s" % careful_msg(options.careful_apt))
    else:
        log.info("      Indexing: %s" % careful_msg(options.careful_apt))

    log.debug("Initialising zopeless.")
    # Change this when we fix up db security
    txn = initZopeless(dbuser='lucille')

    execute_zcml_for_scripts()

    log.debug("Finding distribution object.")

    try:
        distribution = getUtility(IDistributionSet).getByName(
            options.distribution)
    except NotFoundError, info:
        log.error(info)
        raise

    allowed_suites = set()
    for suite in options.suite:
        try:
            distrorelease, pocket = distribution.getDistroReleaseAndPocket(
                suite)
        except NotFoundError, info:
            log.error(info)
            raise
        allowed_suites.add((distrorelease.name, pocket))

    if not options.ppa:
        archives = [distribution.main_archive]
    else:
        # XXX cprov 20070103: we can optimize the loop by quering only the
        # PPA with modifications pending publication. For now just iterating
        # over all of them should do.
        archives = getUtility(IArchiveSet).getAllPPAs()
        if options.distsroot is not None:
            log.error("We should not define 'distsroot' in PPA mode !")
            return

    for archive in archives:
        if not options.ppa:
            log.info("Processing %s main_archive" % distribution.name)
        else:
            log.info("Processing '%s' PPA" % archive.owner.name)

        publisher = getPublisher(
            archive, distribution, allowed_suites, log, options.distsroot)

        try_and_commit("publishing", publisher.A_publish,
                       options.careful or options.careful_publishing)
        try_and_commit("dominating", publisher.B_dominate,
                       options.careful or options.careful_domination)

        if not options.ppa:
            try_and_commit("doing apt-ftparchive", publisher.C_doFTPArchive,
                           options.careful or options.careful_apt)
        else:
            try_and_commit("building indexes", publisher.C_writeIndexes,
                           options.careful or options.careful_apt)

        try_and_commit("doing release files", publisher.D_writeReleaseFiles,
                       options.careful)

    log.debug("Ciao")


if __name__ == "__main__":
    main()
