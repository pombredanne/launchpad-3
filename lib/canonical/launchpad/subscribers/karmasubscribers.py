""" karmasubscribers.py -- handles all karma assignments done in the
launchpad application."""

from canonical.launchpad.database import Person
from canonical.launchpad.mailnotification import get_changes
from canonical.lp.dbschema import KarmaField, BugAssignmentStatus


def bug_added(bug, event):
    owner = getattr(bug, 'owner', None)
    if owner:
        owner.assignKarma(KarmaField.BUG_REPORT)


def bug_comment_added(bugmessage, event):
    bugmessage.message.owner.assignKarma(KarmaField.BUG_COMMENT)


def bug_assignment_modified(assignment, event):
    person = Person.get(event.principal.id)
    # XXX: Should we give Karma points to users who change priority
    # and severity too?
    fields = (("bugstatus", None),)
    changes = get_changes(before=event.object_before_modification,
                          after=event.object, fields=fields)

    for field in changes:
        if field == "bugstatus":
            if changes[field]["new"] == BugAssignmentStatus.FIXED:
                # Can we assume that this is the user that really fixed
                # the bug and give Karma points to him?
                person.assignKarma(KarmaField.BUG_FIX)

