# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helper functions for the process-accepted.py script."""

__metaclass__ = type
__all__ = [
    'close_bugs',
    'close_bugs_for_queue_item',
    'close_bugs_for_sourcepublication',
    ]

from zope.component import getUtility

from canonical.archiveuploader.tagfiles import parse_tagfile_lines
from canonical.launchpad.interfaces import (
    ArchivePurpose, BugTaskStatus, IBugSet, ILaunchpadCelebrities,
    IPackageUploadSet, NotFoundError, PackagePublishingPocket)

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
    close_bugs_for_queue_item on each of them.
    """
    for queue_id in queue_ids:
        queue_item = getUtility(IPackageUploadSet).get(queue_id)
        close_bugs_for_queue_item(queue_item)

def can_close_bugs(target):
    """Whether or not bugs should be closed in the given target.

    ISourcePackagePublishingHistory and IPackageUpload are the
    currently supported targets.

    Source publications or package uploads targeted to pockets
    PROPOSED/BACKPORTS or any other archive purpose than PRIMARY will
    not automatically close bugs.
    """
    banned_pockets = (
        PackagePublishingPocket.PROPOSED,
        PackagePublishingPocket.BACKPORTS)

    if (target.pocket in banned_pockets or
       target.archive.purpose != ArchivePurpose.PRIMARY):
        return False

    return True

def close_bugs_for_queue_item(queue_item, changesfile_object=None):
    """Close bugs for a given queue item.

    'queue_item' is an IPackageUpload instance and is given by the user.

    'changesfile_object' is optional if not given this function will try
    to use the IPackageUpload.changesfile, which is only available after
    the upload is processed and committed.

    In practice, 'changesfile_object' is only set when we are closing bugs
    in upload-time (see archiveuploader/ftests/nascentupload-closing-bugs.txt).

    Skip bug-closing if the upload is target to pocket PROPOSED or if
    the upload is for a PPA.

    Set the package bugtask status to Fix Released and the changelog is added
    as a comment.
    """
    if not can_close_bugs(queue_item):
        return

    if changesfile_object is None:
        changesfile_object = queue_item.changesfile

    for source_queue_item in queue_item.sources:
        close_bugs_for_sourcepackagerelease(
            source_queue_item.sourcepackagerelease, changesfile_object)

def close_bugs_for_sourcepublication(source_publication):
    """Close bugs for a given sourcepublication.

    Given a `ISourcePackagePublishingHistory` close bugs mentioned in
    upload changesfile.
    """
    if not can_close_bugs(source_publication):
        return

    sourcepackagerelease = source_publication.sourcepackagerelease
    changesfile_object = sourcepackagerelease.upload_changesfile

    # No changesfile available, cannot close bugs.
    if changesfile_object is None:
        return

    close_bugs_for_sourcepackagerelease(
        sourcepackagerelease, changesfile_object)

def close_bugs_for_sourcepackagerelease(source_release, changesfile_object):
    """Close bugs for a given source.

    Given a `ISourcePackageRelease` and a corresponding changesfile object,
    close bugs mentioned in the changesfile in the context of the source.
    """
    bugs_to_close = get_bugs_from_changes_file(changesfile_object)

    # No bugs to be closed by this upload, move on.
    if not bugs_to_close:
        return

    janitor = getUtility(ILaunchpadCelebrities).janitor
    for bug in bugs_to_close:
        edited_task = bug.setStatus(
            target=source_release.sourcepackage,
            status=BugTaskStatus.FIXRELEASED,
            user=janitor)
        if edited_task is not None:
            assert source_release.changelog_entry is not None, (
                "New source uploads should have a changelog.")
            content = (
                "This bug was fixed in the package %s"
                "\n\n---------------\n%s" % (
                source_release.title, source_release.changelog_entry,))
            bug.newMessage(
                owner=janitor,
                subject=bug.followup_subject(),
                content=content)
