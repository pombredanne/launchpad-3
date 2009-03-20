# Copyright 2008 Canonical Ltd.  All rights reserved.
"""Publisher script functions."""

__all__ = [
    'add_options',
    'run_publisher',
    ]

import gc

from zope.component import getUtility

from canonical.archivepublisher.publishing import getPublisher
from canonical.database.sqlbase import (
    clear_current_connection_cache, flush_database_updates)
from canonical.launchpad.interfaces.archive import (
    ArchivePurpose, MAIN_ARCHIVE_PURPOSES)
from canonical.launchpad.interfaces.distribution import IDistributionSet
from canonical.launchpad.scripts import logger, logger_options
from canonical.launchpad.scripts.base import LaunchpadScriptFailure
from canonical.launchpad.webapp.interfaces import NotFoundError

# XXX Julian 2008-02-07 bug=189866:
# These functions should be in a LaunchpadScript.

def add_options(parser):
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
                           "PRIMARY and PARTNER archives only.")

    parser.add_option("--ppa", action="store_true",
                      dest="ppa", metavar="PPA", default=False,
                      help="Run only over private PPA archives.")

    parser.add_option("--private-ppa", action="store_true",
                      dest="private_ppa", metavar="PRIVATEPPA", default=False,
                      help="Run only over PPA archives.")

    parser.add_option("--partner", action="store_true",
                      dest="partner", metavar="PARTNER", default=False,
                      help="Run only over the partner archive.")


def run_publisher(options, txn, log=None):
    if not log:
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

    exclusive_options = (options.partner, options.ppa, options.private_ppa)
    num_exclusive = [flag for flag in exclusive_options if flag]
    if len(num_exclusive) > 1:
        raise LaunchpadScriptFailure(
            "Can only specify one of partner, ppa and private-ppa")

    log.debug("Finding distribution object.")

    try:
        distribution = getUtility(IDistributionSet).getByName(
            options.distribution)
    except NotFoundError, info:
        raise LaunchpadScriptFailure(info)

    allowed_suites = set()
    for suite in options.suite:
        try:
            distroseries, pocket = distribution.getDistroSeriesAndPocket(
                suite)
        except NotFoundError, info:
            raise LaunchpadScriptFailure(info)
        allowed_suites.add((distroseries.name, pocket))

    if options.partner:
        archives = [distribution.getArchiveByComponent('partner')]
    elif options.ppa or options.private_ppa:
        if options.careful or options.careful_publishing:
            archives = distribution.getAllPPAs()
        else:
            archives = distribution.getPendingPublicationPPAs()

        # Filter out non-private if we're publishing private PPAs only,
        # or filter out private if we're doing non-private.
        if options.private_ppa:
            archives = [archive for archive in archives if archive.private]
        else:
            archives = [
                archive for archive in archives if not archive.private]

        if options.distsroot is not None:
            raise LaunchpadScriptFailure(
                "We should not define 'distsroot' in PPA mode !")
    else:
        archives = [distribution.main_archive]

    # Consider only archives that have their "to be published" flag turned on.
    archives = [archive for archive in archives if archive.publish]

    for archive in archives:
        if archive.purpose in MAIN_ARCHIVE_PURPOSES:
            log.info("Processing %s %s" % (distribution.name, archive.title))
            # Only let the primary/partner archives override the distsroot.
            publisher = getPublisher(
                archive, allowed_suites, log, options.distsroot)
        else:
            log.info("Processing %s" % archive.archive_url)
            publisher = getPublisher(archive, allowed_suites, log)

        try_and_commit("publishing", publisher.A_publish,
                       options.careful or options.careful_publishing)
        # Flag dirty pockets for any outstanding deletions.
        publisher.A2_markPocketsWithDeletionsDirty()
        try_and_commit("dominating", publisher.B_dominate,
                       options.careful or options.careful_domination)

        # The primary archive uses apt-ftparchive to generate the indexes,
        # everything else uses the newer internal LP code.
        if archive.purpose == ArchivePurpose.PRIMARY:
            try_and_commit("doing apt-ftparchive", publisher.C_doFTPArchive,
                           options.careful or options.careful_apt)
        else:
            try_and_commit("building indexes", publisher.C_writeIndexes,
                           options.careful or options.careful_apt)

        try_and_commit("doing release files", publisher.D_writeReleaseFiles,
                       options.careful or options.careful_apt)

    log.debug("Ciao")
