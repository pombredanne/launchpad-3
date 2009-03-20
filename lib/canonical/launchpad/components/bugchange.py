# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementations for bug changes."""

__metaclass__ = type
__all__ = [
    'BranchLinkedToBug',
    'BranchUnlinkedFromBug',
    'BugDescriptionChange',
    'BugTagsChange',
    'BugTaskAdded',
    'BugTitleChange',
    'BugVisibilityChange',
    'BugWatchAdded',
    'BugWatchRemoved',
    'UnsubscribedFromBug',
    'get_bug_change_class',
    ]

from textwrap import dedent

from zope.interface import implements

from canonical.launchpad.interfaces.bugchange import (
    IBugChange)


def get_bug_change_class(obj, field_name):
    """Return a suitable IBugChange to describe obj and field_name."""
    try:
        return BUG_CHANGE_LOOKUP[field_name]
    except KeyError:
        return BugChangeBase


class BugChangeBase:
    """An abstract base class for Bug[Task]Changes."""

    implements(IBugChange)

    def __init__(self, when, person):
        self.person = person
        self.when = when

    def getBugActivity(self):
        """Return the `BugActivity` entry for this change."""
        raise NotImplementedError(self.getBugActivity)

    def getBugNotification(self):
        """Return the `BugNotification` for this event."""
        raise NotImplementedError(self.getBugNotification)

    def getBugNotificationRecipients(self):
        """Return the recipients for this event."""
        raise NotImplementedError(self.getBugNotificationRecipients)


class AttributeChange(BugChangeBase):
    """A mixin class that provides basic functionality for `IBugChange`s."""

    def __init__(self, when, person, what_changed, old_value, new_value,
                 recipients=None):
        super(AttributeChange, self).__init__(when, person)
        self.new_value = new_value
        self.old_value = old_value
        self.what_changed = what_changed
        self.recipients = recipients

    def getBugActivity(self):
        """Return the BugActivity data for the textual change."""
        return {
            'newvalue': self.new_value,
            'oldvalue': self.old_value,
            'whatchanged': self.what_changed,
            }

    def getBugNotificationRecipients(self):
        return self.recipients


class UnsubscribedFromBug(BugChangeBase):
    """A user got unsubscribed from a bug."""

    def __init__(self, when, person, unsubscribed_user):
        super(UnsubscribedFromBug, self).__init__(when, person)
        self.unsubscribed_user = unsubscribed_user

    def getBugActivity(self):
        """See `IBugChange`."""
        return dict(
            whatchanged='removed subscriber %s' % (
                self.unsubscribed_user.displayname))

    def getBugNotification(self):
        """See `IBugChange`."""
        return None


class BugTaskAdded(BugChangeBase):
    """A bug task got added to the bug."""

    def __init__(self, when, person, bug_task):
        super(BugTaskAdded, self).__init__(when, person)
        self.bug_task = bug_task

    def getBugActivity(self):
        """See `IBugChange`."""
        return dict(
            whatchanged='bug task added',
            newvalue=self.bug_task.bugtargetname)

    def getBugNotification(self):
        """See `IBugChange`."""
        if self.bug_task.bugwatch:
            change_info = u"** Also affects: %s via\n" % (
                self.bug_task.bugtargetname)
            change_info += u"   %s\n" % self.bug_task.bugwatch.url
        else:
            change_info = u"** Also affects: %s\n" % (
                self.bug_task.bugtargetname)
        change_info += u"%13s: %s\n" % (u"Importance",
            self.bug_task.importance.title)
        if self.bug_task.assignee:
            assignee = self.bug_task.assignee
            change_info += u"%13s: %s\n" % (u"Assignee",
                assignee.unique_displayname)
        change_info += u"%13s: %s" % (
            u"Status", self.bug_task.status.title)
        return {
            'text': change_info,
            }

    def getBugNotificationRecipients(self):
        """See `IBugChange`."""
        # Send the notification to the default recipients.


class BugWatchAdded(BugChangeBase):
    """A bug watch was added to the bug."""

    def __init__(self, when, person, bug_watch):
        super(BugWatchAdded, self).__init__(when, person)
        self.bug_watch = bug_watch

    def getBugActivity(self):
        """See `IBugChange`."""
        return dict(
            whatchanged='bug watch added',
            newvalue=self.bug_watch.url)

    def getBugNotification(self):
        """See `IBugChange`."""
        return {
            'text': (
                "** Bug watch added: %s #%s\n"
                "   %s" % (
                    self.bug_watch.bugtracker.title, self.bug_watch.remotebug,
                    self.bug_watch.url)),
            }

    def getBugNotificationRecipients(self):
        """See `IBugChange`."""
        return None


class BugWatchRemoved(BugChangeBase):
    """A bug watch was removed from the bug."""

    def __init__(self, when, person, bug_watch):
        super(BugWatchRemoved, self).__init__(when, person)
        self.bug_watch = bug_watch

    def getBugActivity(self):
        """See `IBugChange`."""
        return dict(
            whatchanged='bug watch removed',
            oldvalue=self.bug_watch.url)

    def getBugNotification(self):
        """See `IBugChange`."""
        return {
            'text': (
                "** Bug watch removed: %s #%s\n"
                "   %s" % (
                    self.bug_watch.bugtracker.title, self.bug_watch.remotebug,
                    self.bug_watch.url)),
            }

    def getBugNotificationRecipients(self):
        """See `IBugChange`."""
        return None


class BranchLinkedToBug(BugChangeBase):
    """A branch got linked to the bug."""

    def __init__(self, when, person, branch):
        super(BranchLinkedToBug, self).__init__(when, person)
        self.branch = branch

    def getBugActivity(self):
        """See `IBugChange`."""
        return dict(
            whatchanged='branch linked',
            newvalue=self.branch.bzr_identity)

    def getBugNotification(self):
        """See `IBugChange`."""
        return {'text': '** Branch linked: %s' % self.branch.bzr_identity}

    def getBugNotificationRecipients(self):
        """See `IBugChange`."""
        # Send the notification to the default recipients.
        return None


class BranchUnlinkedFromBug(BugChangeBase):
    """A branch got unlinked from the bug."""

    def __init__(self, when, person, branch):
        super(BranchUnlinkedFromBug, self).__init__(when, person)
        self.branch = branch

    def getBugActivity(self):
        """See `IBugChange`."""
        return dict(
            whatchanged='branch unlinked',
            oldvalue=self.branch.bzr_identity)

    def getBugNotification(self):
        """See `IBugChange`."""
        return {'text': '** Branch unlinked: %s' % self.branch.bzr_identity}

    def getBugNotificationRecipients(self):
        """See `IBugChange`."""
        # Send the notification to the default recipients.
        return None


class BugDescriptionChange(AttributeChange):
    """Describes a change to a bug's description."""

    def getBugNotification(self):
        from canonical.launchpad.mailnotification import get_unified_diff
        description_diff = get_unified_diff(
            self.old_value, self.new_value, 72)
        notification_text = (
            u"** Description changed:\n\n%s" % description_diff)
        return {'text': notification_text}


class BugTitleChange(AttributeChange):
    """Describes a change to a bug's title, aka summary."""

    def getBugActivity(self):
        activity = super(BugTitleChange, self).getBugActivity()

        # We return 'summary' instead of 'title' for title changes
        # because the bug's title is referred to as its summary in the
        # UI.
        activity['whatchanged'] = 'summary'
        return activity

    def getBugNotification(self):
        notification_text = dedent("""\
            ** Summary changed:

            - %s
            + %s""" % (self.old_value, self.new_value))
        return {'text': notification_text}


class BugVisibilityChange(AttributeChange):
    """Describes a change to a bug's visibility."""

    def _getVisibilityString(self, private):
        """Return a string representation of `private`.

        :return: 'Public' if private is False, 'Private' if
            private is True.
        """
        if private:
            return 'Private'
        else:
            return 'Public'

    def getBugActivity(self):
        # Use _getVisibilityString() to set old and new values
        # correctly. We lowercase them for UI consistency in the
        # activity log.
        old_value = self._getVisibilityString(self.old_value)
        new_value = self._getVisibilityString(self.new_value)
        return {
           'oldvalue': old_value.lower(),
           'newvalue': new_value.lower(),
           'whatchanged': 'visibility',
           }

    def getBugNotification(self):
        visibility_string = self._getVisibilityString(self.new_value)
        return {'text': "** Visibility changed to: %s" % visibility_string}


class BugSecurityChange(AttributeChange):
    """Describes a change to a bug's security setting."""

    activity_mapping = {
        (False, True): ('no', 'yes'),
        (True, False): ('yes', 'no'),
        }

    notification_mapping = {
        (False, True):
            u"** This bug has been flagged as a security vulnerability",
        (True, False):
            u"** This bug is no longer flagged as a security vulnerability",
        }

    def getBugActivity(self):
        old_value, new_value = self.activity_mapping[
            (self.old_value, self.new_value)]
        return {
           'oldvalue': old_value,
           'newvalue': new_value,
           'whatchanged': 'security vulnerability',
           }

    def getBugNotification(self):
        return {
            'text': self.notification_mapping[
                (self.old_value, self.new_value)]
            }


class BugTagsChange(AttributeChange):
    """Used to represent a change to an `IBug`s tags."""

    def getBugActivity(self):
        # Convert the new and old values into space-separated strings of
        # tags.
        new_value = " ".join(sorted(set(self.new_value)))
        old_value = " ".join(sorted(set(self.old_value)))

        return {
            'newvalue': new_value,
            'oldvalue': old_value,
            'whatchanged': self.what_changed,
            }

    def getBugNotification(self):
        new_tags = set(self.new_value)
        old_tags = set(self.old_value)
        added_tags = new_tags.difference(old_tags)
        removed_tags = old_tags.difference(new_tags)

        messages = []
        if len(added_tags) > 0:
            messages.append(
                "** Tags added: %s" % " ".join(sorted(added_tags)))
        if len(removed_tags) > 0:
            messages.append(
                "** Tags removed: %s" % " ".join(sorted(removed_tags)))

        return {'text': "\n".join(messages)}


class BugAttachmentChange(AttributeChange):
    """Used to represent a change to an `IBug`'s attachments."""

    def getBugActivity(self):
        if self.old_value is None:
            what_changed = "attachment added"
            old_value = None
            new_value = "%s %s" % (
                self.new_value.title, self.new_value.libraryfile.http_url)
        else:
            what_changed = "attachment removed"
            attachment = self.new_value
            old_value = "%s %s" % (
                self.old_value.title, self.old_value.libraryfile.http_url)
            new_value = None

        return {
            'newvalue': new_value,
            'oldvalue': old_value,
            'whatchanged': what_changed,
            }

    def getBugNotification(self):
        if self.old_value is None:
            message = '** Attachment added: "%s"\n   %s' % (
                self.new_value.title, self.new_value.libraryfile.http_url)
        else:
            message = '** Attachment removed: "%s"\n   %s' % (
                self.old_value.title, self.old_value.libraryfile.http_url)

        return {'text': message}


BUG_CHANGE_LOOKUP = {
    'description': BugDescriptionChange,
    'private': BugVisibilityChange,
    'security_related': BugSecurityChange,
    'tags': BugTagsChange,
    'title': BugTitleChange,
    'attachment': BugAttachmentChange,
    }
