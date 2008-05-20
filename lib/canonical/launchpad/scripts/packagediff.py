# Copyright 2007 Canonical Ltd.  All rights reserved.
"""PackageDiff cronscript class."""

__metaclass__ = type

__all__ = [
    'ProcessPendingPackageDiffs',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import IPackageDiffSet
from canonical.launchpad.scripts.base import (
    LaunchpadCronScript, LaunchpadScriptFailure)


class ProcessPendingPackageDiffs(LaunchpadCronScript):

    def add_my_options(self):
        # 50 diffs seems to be more them enough to process all uploaded
        # source packages for 1 hour (average upload rate) for ubuntu
        # primary archive, security and PPAs in general.
        self.parser.add_option(
            "-l", "--limit", type="int", default=50,
            help="Maximum number of requests to be processed in this run.")

        self.parser.add_option(
            "-n", "--dry-run",
            dest="dryrun", action="store_true", default=False,
            help="Whether or not to commit the transaction.")

    def main(self):
        """Process pending `PackageDiff` records.

        Collect up to the maximum number of pending `PackageDiff` records
        available and process them.

        Processed diffs results are commited individually.
        """
        if self.args:
            raise LaunchpadScriptFailure("Unhandled arguments %r" % self.args)

        packagediff_set = getUtility(IPackageDiffSet)

        pending_diffs = packagediff_set.getPendingDiffs(
            limit=self.options.limit)
        self.logger.debug(
            'Considering %s diff requests' % pending_diffs.count())

        # Iterate over all pending packagediffs.
        for packagediff in pending_diffs:
            self.logger.debug('Performing %s' % packagediff.title)
            packagediff.performDiff()
            if not self.options.dryrun:
                self.logger.debug('Commiting the transaction.')
                self.txn.commit()
