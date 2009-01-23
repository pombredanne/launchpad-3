#!/usr/bin/python2.4

# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

from zope.component import getUtility

from canonical.launchpad.interfaces.archive import ArchivePurpose
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


class PPABinaryExpirer(LaunchpadCronScript):
    """Helper class for expiring old PPA binaries.
    
    Any PPA binary older than 30 days that is superseded or deleted
    will be marked for immediate expiry.  It's done with pure SQL rather
    than Python for speed reasons.
    """

    def main(self):
        self.logger.info('Starting the PPA binary expiration')

        stay_of_execution = '30 days'

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

        store.execute("""
            UPDATE libraryfilealias
            SET expires=now()
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
                bpph.dateremoved < (now() - interval '%s') AND
                archive.id = bpph.archive AND
                archive.purpose = %s AND
                NOT EXISTS (
                    SELECT TRUE FROM binarypackagepublishinghistory as bpph2,
                                     binarypackagerelease as bpr2
                    WHERE
                        bpph2.binarypackagerelease = bpph.binarypackagerelease
                        AND
                        (now() - bpph2.dateremoved < interval '%s'
                         OR
                         dateremoved IS NULL
                        )
                );
        """ % (stay_of_execution, ArchivePurpose.PPA.value,
               stay_of_execution))

        self.txn.commit()
        self.logger.info('Finished PPA binary expiration')

