#!/usr/bin/python2.4
# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

# Stop lint warning about relative import:
# pylint: disable-msg=W0403


"""Death row processor script.

This script removes obsolete files from the selected archive(s) pool.

You can select a specific distribution or let it default to 'ubuntu'.

It operates in 2 modes:
 * all distribution archive (PRIMARY and PARTNER) [default]
 * all PPAs [--ppa]

You can optionally specify a different 'pool-root' path which will be used
as the base path for removing files, instead of the real archive pool root.
This feature is used to inspect the removed files without actually modifying
the archive tree.

There is also a 'dry-run' mode that can be used to operate on the real
archive tree without removing the files.
"""

import _pythonpath

from zope.component import getUtility

from canonical.archivepublisher.deathrow import getDeathRow
from canonical.config import config
from canonical.launchpad.interfaces import IDistributionSet
from canonical.launchpad.scripts.base import LaunchpadScript


class DeathRowProcessor(LaunchpadScript):

    def add_my_options(self):
        self.parser.add_option(
            "-n", "--dry-run", action="store_true", default=False,
            help="Dry run: goes through the motions but commits to nothing.")

        self.parser.add_option(
            "-d", "--distribution", metavar="DISTRO", default='ubuntu',
            help="Specified the distribution name.")

        self.parser.add_option(
            "-p", "--pool-root", metavar="PATH",
            help="Override the path to the pool folder")

        self.parser.add_option(
            "--ppa", action="store_true", default=False,
            help="Run only over PPA archives.")

    def main(self):
        distribution = getUtility(IDistributionSet).getByName(
            self.options.distribution)

        if self.options.ppa:
            archives = distribution.getAllPPAs()
        else:
            archives = distribution.all_distro_archives

        for archive in archives:
            self.processDeathRow(archive)

    def processDeathRow(self, archive):
        """Process death-row for the given archive.

        It handles the current DB transaction according with the results
        of the operatin just executed, i.e, commits successfull runs and
        aborts runs with errors. It also respects 'dry-run' command-line
        option.
        """
        death_row = getDeathRow(
            archive, self.logger, self.options.pool_root)
        self.logger.debug(
            "Unpublishing death row for %s." % archive.title)
        try:
            death_row.reap(self.options.dry_run)
        except:
            self.logger.exception(
                "Unexpected exception while doing death-row unpublish")
            self.txn.abort()
        else:
            if self.options.dry_run:
                self.logger.debug("Dry run mode; rolling back.")
                self.txn.abort()
            else:
                self.logger.debug("Committing")
                self.txn.commit()


if __name__ == "__main__":
    script = DeathRowProcessor(
        'process-death-row', dbuser=config.archivepublisher.dbuser)
    script.lock_and_run()

