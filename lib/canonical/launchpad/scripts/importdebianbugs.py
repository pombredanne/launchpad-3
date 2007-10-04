# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helper class and functions for the import-debian-bugs.py script."""

__metaclass__ = type

from zope.component import getUtility
from canonical.launchpad.interfaces import ILaunchpadCelebrities

from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.launchpad.components.externalbugtracker import (
    get_external_bugtracker)


class DebianBugImportScript(LaunchpadScript):
    """Import Debian bugs into Launchpad.

    New bugs will be filed against the Debian source package in
    Launchpad, with the real Debian bug linked as a bug watch.
    """

    usage = "%(prog)s [options] <debian-bug-1> ... <debian-bug-n>"
    description = __doc__

    def add_my_options(self):
        self.parser.add_option('-n', '--dry-run',
                               action='store_true',
                               help="Don't commit the DB transaction.",
                               dest='dry_run', default=False)

    def main(self):
        if len(self.args) < 1:
            self.parser.print_help()
            return

        external_debbugs = get_external_bugtracker(
            getUtility(ILaunchpadCelebrities).debbugs)
        debian = getUtility(ILaunchpadCelebrities).debian
        for debian_bug in self.args:
            external_debbugs.createLaunchpadBug(debian, debian_bug)

        if self.options.dry_run:
            self.logger.info("Rolling back the transaction.")
            self.txn.abort()
        else:
            self.logger.info("Committing the transaction.")
            self.txn.commit()

