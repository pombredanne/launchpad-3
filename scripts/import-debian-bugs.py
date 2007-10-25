#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Import Debian bugs into Launchpad, linking them to Ubuntu.

New bugs will be filed against the Debian source package in
Launchpad, with the real Debian bug linked as a bug watch.

An Ubuntu task will be created for each imported bug.
"""

import _pythonpath

from canonical.config import config
from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.launchpad.scripts.importdebianbugs import import_debian_bugs


class DebianBugImportScript(LaunchpadScript):
    """Import Debian bugs into Launchpad, linking them to Ubuntu.

    New bugs will be filed against the Debian source package in
    Launchpad, with the real Debian bug linked as a bug watch.

    An Ubuntu task will be created for each imported bug.
    """

    usage = "%(prog)s [options] <debian-bug-1> ... <debian-bug-n>"
    description = __doc__

    def add_my_options(self):
        self.parser.add_option(
            '-n', '--dry-run', action='store_true',
           help="Don't commit the DB transaction.",
           dest='dry_run', default=False)

    def main(self):
        if len(self.args) < 1:
            self.parser.print_help()
            return

        import_debian_bugs(self.args)

        if self.options.dry_run:
            self.logger.info("Dry run - rolling back the transaction.")
            self.txn.abort()
        else:
            self.logger.info("Committing the transaction.")
            self.txn.commit()


if __name__ == '__main__':
    script = DebianBugImportScript(
        'canonical.launchpad.scripts.importdebianbugs',
        dbuser=config.checkwatches.dbuser)
    script.run()
