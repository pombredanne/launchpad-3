# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helper functions for the process-accepted.py script."""

__metaclass__ = type
__all__ = ['close_bugs', 'closeBugsForQueueItem']

from zope.component import getUtility

from canonical.archiveuploader.tagfiles import parse_tagfile_lines
from canonical.launchpad.interfaces import (
    BugTaskStatus, IBugSet, IPackageUploadSet, NotFoundError)
from canonical.lp.dbschema import PackagePublishingPocket

def get_bugs_from_changes_file(changes_file):
    """Parse the changes file and return a list of bugs referenced by it.

    The bugs is specified in the Launchpad-bugs-fixed header, and are
    separated by a space character. Nonexistent bug ids are ignored.
    """
    contents = changes_file.read()
    changes_lines = contents.splitlines(True)
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

    Retrieve PackageUpload objects for the given ID list and perform
    closeBugsForQueueItem on each of them.
    """
    for queue_id in queue_ids:
        queue_item = getUtility(IPackageUploadSet).get(queue_id)
        closeBugsForQueueItem(queue_item)


def closeBugsForQueueItem(queue_item, changesfile_object=None):
    """Close bugs for a given queue item.

    'queue_item' is an IPackageUpload instance and is given by the user.

    'changesfile_object' is optional if not given this function will try
    to use the IPackageUpload.changesfile, which is only available after
    the upload is processed and committed.

    In practice, 'changesfile_object' is only set when we are closing bugs
    in upload-time (see archiveuploader/ftests/nascentupload-closing-bugs.txt).

    Skip bug-closing if the upload is target to pocket PROPOSED.

    Set the package bugtask status to Fix Released and the changelog is added
    as a comment.
    """
    if queue_item.pocket == PackagePublishingPocket.PROPOSED:
        return

    if changesfile_object is None:
        changesfile_object = queue_item.changesfile

    bugs_to_close = get_bugs_from_changes_file(changesfile_object)

    # No bugs to be closed by this upload, move on.
    if not bugs_to_close:
        return

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
