# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helper class and functions for the import-debian-bugs.py script."""

__metaclass__ = type

from zope.component import getUtility
from canonical.launchpad.interfaces import IBugTaskSet, ILaunchpadCelebrities

from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.launchpad.scripts.logger import log
from canonical.launchpad.components.externalbugtracker import (
    get_external_bugtracker)


def import_debian_bugs(*bugs_to_import):
    """Import the specified Debian bugs into Launchpad."""
    debbugs = getUtility(ILaunchpadCelebrities).debbugs
    external_debbugs = get_external_bugtracker(debbugs)
    debian = getUtility(ILaunchpadCelebrities).debian
    for debian_bug in bugs_to_import:
        existing_bug_ids = [
            str(bug.id) for bug in debbugs.getBugsWatching(debian_bug)]
        if len(existing_bug_ids) > 0:
            log.warning(
                "Not importing debbugs #%s, since it's already linked"
                " from LP bug(s) #%s." % (
                    debian_bug, ', '.join(existing_bug_ids)))
            continue
        bug = external_debbugs.importBug(debian, debian_bug)
        [debian_task] = bug.bugtasks
        getUtility(IBugTaskSet).createTask(
            bug, getUtility(ILaunchpadCelebrities).bug_watch_updater,
            distribution=getUtility(ILaunchpadCelebrities).ubuntu,
            sourcepackagename=debian_task.sourcepackagename)
        log.info(
            "Imported debbugs #%s as Launchpad bug #%s." % (
                debian_bug, bug.id))



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

        import_debian_bugs(*self.args)

        if self.options.dry_run:
            self.logger.info("Rolling back the transaction.")
            self.txn.abort()
        else:
            self.logger.info("Committing the transaction.")
            self.txn.commit()

