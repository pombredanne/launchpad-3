# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementations for bug changes."""

__metaclass__ = type
__all__ = [
    'BugChangeBase',
    'BugDescriptionChange',
    'BugTitleChange',
    'get_bug_change_class',
]

from textwrap import dedent

from zope.interface import implements

from canonical.launchpad.interfaces.bugchange import (
    IBugChange)
from canonical.launchpad.mailnotification import get_unified_diff


def get_bug_change_class(obj, field_name):
    """Return a suitable IBugChange to describe obj and field_name."""
    try:
        return BUG_CHANGE_LOOKUP[field_name]
    except KeyError:
        return BugChangeBase


class BugChangeBase:
    """An abstract base class for Bug[Task]Changes."""

    implements(IBugChange)

    def __init__(self, when, person, what_changed, old_value, new_value):
        self.new_value = new_value
        self.old_value = old_value
        self.person = person
        self.what_changed = what_changed
        self.when = when

    def getBugActivity(self):
        """Return the `BugActivity` entry for this change."""
        raise NotImplementedError(self.getBugActivity)

    def getBugNotification(self):
        """Return the `BugNotification` for this event."""
        raise NotImplementedError(self.getBugNotification)

    def getBugNotificationRecipients(self):
        """Return any recipients for the `BugNotification`s."""
        raise NotImplementedError(self.getBugNotificationRecipients)


class TextualBugChange(BugChangeBase):
    """Describes a textual attribute change to a bug."""

    def getBugActivity(self):
        """Return the BugActivity data for the textual change."""
        return {
            'newvalue': self.new_value,
            'oldvalue': self.old_value,
            'whatchanged': self.what_changed,
            }


class BugDescriptionChange(TextualBugChange):
    """Describes a change to a bug's description."""

    def getBugNotification(self):
        description_diff = get_unified_diff(
            self.old_value, self.new_value, 72)
        notification_text = (
            u"** Description changed:\n\n%s" % description_diff)
        return {'text': notification_text}


class BugTitleChange(TextualBugChange):
    """Describes a change to a bug's title, aka summary."""

    def getBugNotification(self):
        notification_text = dedent("""\
            ** Summary changed:

            - %s
            + %s""" % (self.old_value, self.new_value))
        return {'text': notification_text}



BUG_CHANGE_LOOKUP = {
    'description': TextualBugChange,
    'name': TextualBugChange,
    'title': TextualBugChange,
    }
