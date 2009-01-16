#!/usr/bin/python2.4

# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

# This script expires PPA binaries that are superseded or deleted, and
# are older than 30 days.  It's done with pure SQL rather than Python
# for speed reasons.

import _pythonpath

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


class PPABinaryExpirer(LaunchpadCronScript):
    """Helper class for expiring old PPA binaries.
    
    Any PPA binary older than 30 days that is superseded or deleted
    will be marked for immediate expiry.  The associated publishing
    record is also marked as OBSOLETE so that it is prevented from
    being copied in the future.
    """

    def main(self):
        self.logger.info('Starting the PPA binary expiration')

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

        # A temp table is used to collect the necessary row IDs for
        # updating, since we need to update two tables at once and the
        # selection criteria is time-based (which would change on the
        # second query if done with two).

        store.execute("""
        CREATE TEMP TABLE tmp_lfa_expiration_data (
            lfa_id integer,
            bpph_id integer);

        INSERT INTO tmp_lfa_expiration_data (lfa_id, bpph_id)
        SELECT
            lfa.id AS lfa_id, bpph.id AS bpph_id
        FROM
            libraryfilealias lfa,
            binarypackagefile bpf,
            binarypackagerelease bpr,
            binarypackagepublishinghistory bpph,
            archive
        WHERE
            lfa.id = bpf.libraryfile AND
            bpr.id = bpf.binarypackagerelease AND
            bpph.binarypackagerelease = bpr.id AND
            bpph.status IN (3,4) AND
            bpph.dateremoved < (now() - interval '30 days') AND
            archive.id = bpph.archive AND
            archive.purpose = 2;

        UPDATE libraryfilealias
        SET expires=now()
        FROM tmp_lfa_expiration_data
        WHERE libraryfilealias.id = tmp_lfa_expiration_data.lfa_id;

        UPDATE securebinarypackagepublishinghistory
        SET status = 5
        FROM tmp_lfa_expiration_data
        WHERE
            securebinarypackagepublishinghistory.id = 
                tmp_lfa_expiration_data.bpph_id;
        """)

        self.txn.commit()
        self.logger.info('Finished the package cache update')

if __name__ == '__main__':
    script = PPABinaryExpirer(
        'expire-ppa-binaries', dbuser=config.librarian_gc.dbuser)
    script.lock_and_run()

