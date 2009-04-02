#!/usr/bin/python2.4

# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

from zope.component import getUtility

from canonical.database.sqlbase import sqlvalues

from canonical.launchpad.interfaces.archive import ArchivePurpose
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)

# PPAs that we never want to expire.
BLACKLISTED_PPAS = """
adobe-isv
chelsea-team
dennis-team
elvis-team
fluendo-isv
natick-team
netbook-remix-team
netbook-team
oem-solutions-group
payson
transyl
ubuntu-mobile
wheelbarrow
bzr
bzr-beta-ppa
bzr-nightly-ppa
""".split()


class PPABinaryExpirer(LaunchpadCronScript):
    """Helper class for expiring old PPA binaries.
    
    Any PPA binary older than 30 days that is superseded or deleted
    will be marked for immediate expiry.
    """
    blacklist = BLACKLISTED_PPAS

    def add_my_options(self):
        """Add script command line options."""
        self.parser.add_option(
            "-n", "--dry-run", action="store_true",
            dest="dryrun", metavar="DRY_RUN", default=False,
            help="If set, no transactions are committed")

    def determineExpirables(self):
        """Return expirable libraryfilealias IDs."""

        stay_of_execution = '30 days'

        # The subquery here has to repeat the checks for privacy and
        # blacklisting on *other* publications that are also done in
        # the main loop for the archive being considered.
        results = self.store.execute("""
            SELECT lfa.id
            FROM
                LibraryFileAlias AS lfa,
                Archive,
                BinaryPackageFile AS bpf,
                BinaryPackageRelease AS bpr,
                SecureBinaryPackagePublishingHistory AS bpph
            WHERE
                lfa.id = bpf.libraryfile
                AND bpr.id = bpf.binarypackagerelease
                AND bpph.binarypackagerelease = bpr.id
                AND bpph.dateremoved < (
                    CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - interval %s)
                AND bpph.archive = archive.id
                AND archive.purpose = %s
                AND lfa.expires IS NULL
            EXCEPT
            SELECT bpf.libraryfile
            FROM
                BinaryPackageRelease AS bpr,
                BinaryPackageFile AS bpf,
                SecureBinaryPackagePublishingHistory AS bpph,
                Archive AS a,
                Person AS p
            WHERE
                bpr.id = bpf.binarypackagerelease
                AND bpph.binarypackagerelease = bpr.id
                AND bpph.archive = a.id
                AND p.id = a.owner
                AND (
                    p.name IN %s
                    OR a.private IS TRUE
                    OR a.purpose != %s
                    OR dateremoved > 
                        CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - interval %s
                    OR dateremoved IS NULL);
            """ % sqlvalues(
                stay_of_execution, ArchivePurpose.PPA, self.blacklist,
                ArchivePurpose.PPA, stay_of_execution))

        lfa_ids = results.get_all()
        return lfa_ids

    def main(self):
        self.logger.info('Starting the PPA binary expiration')
        self.store = getUtility(IStoreSelector).get(
            MAIN_STORE, DEFAULT_FLAVOR)

        lfa_ids = self.determineExpirables()
        batch_count = 0
        batch_limit = 500
        for id in lfa_ids:
            self.logger.info("Expiring libraryfilealias %s" % id)
            self.store.execute("""
                UPDATE libraryfilealias
                SET expires = CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                WHERE id = %s
                """ % id)
            batch_count += 1
            if batch_count % batch_limit == 0:
                if self.options.dryrun:
                    self.logger.info(
                        "%s done, not committing (dryrun mode)" % batch_count)
                    self.txn.abort()
                else:
                    self.logger.info(
                        "%s done, committing transaction" % batch_count)
                    self.txn.commit()

        if self.options.dryrun:
            self.txn.abort()
        else:
            self.txn.commit()

        self.logger.info('Finished PPA binary expiration')

