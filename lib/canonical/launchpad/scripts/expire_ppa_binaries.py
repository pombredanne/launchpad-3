#!/usr/bin/python2.4

# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

from zope.component import getUtility

from canonical.database.sqlbase import sqlvalues

from canonical.launchpad.interfaces.archive import ArchivePurpose, IArchiveSet
from canonical.launchpad.interfaces.distribution import IDistributionSet
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

    def expirePPA(self, archive):
        """Expire the librarian binaries for `archive`."""

        stay_of_execution = '30 days'
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        store.execute("""
            UPDATE libraryfilealias AS lfa
            SET expires=now()
            FROM
                binarypackagefile bpf,
                binarypackagerelease bpr,
                binarypackagepublishinghistory bpph,
                archive
            WHERE
                archive.id = %s AND
                lfa.id = bpf.libraryfile AND
                bpr.id = bpf.binarypackagerelease AND
                archive.id = bpph.archive AND
                bpph.binarypackagerelease = bpr.id AND
                bpph.dateremoved < (
                    CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - interval %s) AND
                lfa.expires IS NULL AND
                bpr.id NOT IN (
                    SELECT bpph2.binarypackagerelease
                    FROM BinaryPackagePublishingHistory AS bpph2,
                         archive as a2,
                         person
                    WHERE 
                      a2.id = bpph2.archive AND
                      person.id = a2.owner AND
                      (
                      person.name IN %s
                      OR
                      a2.private IS TRUE
                      OR
                      dateremoved IS NULL
                      OR
                      dateremoved > (
                        CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - interval %s)
                      )
                );
        """ % sqlvalues(
            archive.id, stay_of_execution, self.blacklist, stay_of_execution))

    def main(self):
        self.logger.info('Starting the PPA binary expiration')

        ubuntu = getUtility(IDistributionSet)['ubuntu']
        archives = getUtility(IArchiveSet).getArchivesForDistribution(
            ubuntu, purposes=ArchivePurpose.PPA)

        for archive in archives:
            if archive.private:
                self.logger.info(
                    "Skipping private PPA for '%s'" % archive.owner.name)
                continue
            if archive.owner.name in self.blacklist:
                self.logger.info(
                    "Skipping blacklisted PPA for '%s'" % archive.owner.name)
                continue
            self.expirePPA(archive)
            if self.options.dryrun:
                self.txn.abort()
            else:
                self.txn.commit()
            self.logger.info("Processed %s" % archive.owner.name)

        self.logger.info('Finished PPA binary expiration')

