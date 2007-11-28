# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helper class and functions for the import-debian-bugs.py script."""

__metaclass__ = type

from zope.component import getUtility
from canonical.launchpad.interfaces import IBugTaskSet, ILaunchpadCelebrities

from canonical.launchpad.scripts.logger import log
from canonical.launchpad.components.externalbugtracker import (
    get_external_bugtracker)


def import_debian_bugs(bugs_to_import):
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
