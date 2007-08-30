#!/usr/bin/python2.4

import _pythonpath

import gc
from optparse import OptionParser

from zope.component import getUtility

from canonical.archivepublisher.publishing import getPublisher
from canonical.database.sqlbase import (
    flush_database_updates, clear_current_connection_cache)
from canonical.launchpad.interfaces import (
    IDistributionSet, NotFoundError)
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.lp import initZopeless
from canonical.lp.dbschema import ArchivePurpose


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
                      help="Override the dists path for generation of the "
                           "PRIMARY archive only.")

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
            log.exception("Unexpected exception while %s" % description)
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
            distroseries, pocket = distribution.getDistroSeriesAndPocket(
                suite)
        except NotFoundError, info:
            log.error(info)
            raise
        allowed_suites.add((distroseries.name, pocket))

    if not options.ppa:
        archives = distribution.all_distro_archives
    else:
        if options.careful or options.careful_publishing:
            archives = distribution.getAllPPAs()
        else:
            archives = distribution.getPendingPublicationPPAs()

        if options.distsroot is not None:
            log.error("We should not define 'distsroot' in PPA mode !")
            return

    for archive in archives:
        if archive.purpose != ArchivePurpose.PPA:
            log.info("Processing %s %s" % (
                distribution.name, archive.title))
        else:
            log.info("Processing %s" % archive.archive_url)

        # Only let the primary archive override the distsroot.
        if archive.purpose == ArchivePurpose.PRIMARY:
            publisher = getPublisher(
                archive, allowed_suites, log, options.distsroot)
        else:
            publisher = getPublisher(archive, allowed_suites, log)

        try_and_commit("publishing", publisher.A_publish,
                       options.careful or options.careful_publishing)
        try_and_commit("dominating", publisher.B_dominate,
                       options.careful or options.careful_domination)

        # The primary archive uses apt-ftparchive to generate the indexes,
        # everything else uses the newer internal LP code.
        if archive.purpose != ArchivePurpose.PRIMARY:
            try_and_commit("building indexes", publisher.C_writeIndexes,
                           options.careful or options.careful_apt)
        else:
            try_and_commit("doing apt-ftparchive", publisher.C_doFTPArchive,
                           options.careful or options.careful_apt)

        try_and_commit("doing release files", publisher.D_writeReleaseFiles,
                       options.careful or options.careful_apt)

    log.debug("Ciao")


if __name__ == "__main__":
    main()
