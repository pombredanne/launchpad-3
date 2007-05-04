# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helper functions for the process-accepted.py script."""

__metaclass__ = type
__all__ = ['close_bugs']

from zope.component import getUtility

from canonical.archivepublisher.tagfiles import parse_tagfile_lines
from canonical.launchpad.interfaces import (
    IBugSet, IDistroReleaseQueueSet, NotFoundError)
from canonical.lp.dbschema import BugTaskStatus

def get_bugs_from_changes_file(changes_file):
    """Parse the changes file and return a list of bugs referenced by it.

    The bugs is specified in the Launchpad-bugs-fixed header, and are
    separated by a space character. Nonexistent bug ids are ignored.
    """
    contents = changes_file.read()
    changes_lines = ["%s\n" % line for line in contents.splitlines()]
    tags = parse_tagfile_lines(changes_lines, allow_unsigned=True)
    bugs_fixed_line = tags.get('launchpad-bugs-fixed', '')
    bugs = []
    for bug_id in bugs_fixed_line.split():
        if not bug_id.isdigit():
            continue
        bug_id = int(bug_id)
        try:
            bug = getUtility(IBugSet).get(bug_id)
        except NotFoundError:
            continue
        else:
            bugs.append(bug)
    return bugs


def close_bugs(queue_ids):
    """Close any bugs referenced by the queue items.

    For each bug, the package bugtask status is set to Fix Released, and
    the changelog is added as a comment.
    """
    for queue_id in queue_ids:
        queue_item = getUtility(IDistroReleaseQueueSet).get(queue_id)
        bugs_to_close = get_bugs_from_changes_file(queue_item.changesfile)
        if not bugs_to_close:
            # No bugs to be closed by this upload, move on to the next
            # queue item.
            continue
        for source_queue_item in queue_item.sources:
            source_release = source_queue_item.sourcepackagerelease
            for bug in bugs_to_close:
                edited_task = bug.setStatus(
                    target=source_release.sourcepackage,
                    status=BugTaskStatus.FIXRELEASED,
                    user=source_release.creator)
                if edited_task is not None:
                    assert source_release.changelog is not None, (
                        "New source uploads should have a changelog.")
                    bug.newMessage(
                        owner=source_release.creator,
                        subject=bug.followup_subject(),
                        content=source_release.changelog)


