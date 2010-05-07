# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper class and functions for the import-debian-bugs.py script."""

__metaclass__ = type

from zope.component import getUtility

from canonical.database.sqlbase import ZopelessTransactionManager
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.scripts.logger import log
from lp.bugs.externalbugtracker import get_external_bugtracker
from lp.bugs.interfaces.bugtask import IBugTaskSet
from lp.bugs.scripts.checkwatches import CheckwatchesMaster


def import_debian_bugs(bugs_to_import):
    """Import the specified Debian bugs into Launchpad."""
    debbugs = getUtility(ILaunchpadCelebrities).debbugs
    txn = ZopelessTransactionManager._installed
    external_debbugs = get_external_bugtracker(debbugs)
    bug_watch_updater = CheckwatchesMaster(txn, log)
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
        bug = bug_watch_updater.importBug(
            external_debbugs, debbugs, debian, debian_bug)

        [debian_task] = bug.bugtasks
        bug_watch_updater.updateBugWatches(
            external_debbugs, [debian_task.bugwatch])
        getUtility(IBugTaskSet).createTask(
            bug, getUtility(ILaunchpadCelebrities).bug_watch_updater,
            distribution=getUtility(ILaunchpadCelebrities).ubuntu,
            sourcepackagename=debian_task.sourcepackagename)
        log.info(
            "Imported debbugs #%s as Launchpad bug #%s." % (
                debian_bug, bug.id))
