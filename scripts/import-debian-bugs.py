#!/usr/bin/python2.4
# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Import Debian bugs into Launchpad.

New bugs will be filed againts the Debian source package in Launchpad,
with the real Debian bug linked as a bug watch.
"""

import _pythonpath

from zope.component import getUtility
from canonical.launchpad.interfaces import ILaunchpadCelebrities

from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.launchpad.components.externalbugtracker import (
    get_external_bugtracker)


class DebianBugImportScript(LaunchpadScript):

    description = __doc__
    usage = "%(prog)s [options] <debian-bug-1> ... <debian-bug-n>"

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


if __name__ == '__main__':
    script = DebianBugImportScript(
        'canonical.launchpad.scripts.importdebianbugs')
    script.run()
