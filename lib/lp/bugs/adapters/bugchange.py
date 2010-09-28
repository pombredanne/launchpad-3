# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementations for bug changes."""

__metaclass__ = type
__all__ = [
    'BranchLinkedToBug',
    'BranchUnlinkedFromBug',
    'BugConvertedToQuestion',
    'BugDescriptionChange',
    'BugDuplicateChange',
    'BugTagsChange',
    'BugTaskAdded',
    'BugTaskAssigneeChange',
    'BugTaskBugWatchChange',
    'BugTaskImportanceChange',
    'BugTaskMilestoneChange',
    'BugTaskStatusChange',
    'BugTaskTargetChange',
    'BugTitleChange',
    'BugVisibilityChange',
    'BugWatchAdded',
    'BugWatchRemoved',
    'CveLinkedToBug',
    'CveUnlinkedFromBug',
    'SeriesNominated',
    'UnsubscribedFromBug',
    'get_bug_change_class',
    'get_bug_changes',
    ]

from textwrap import dedent

from zope.interface import implements
from zope.security.proxy import isinstance as zope_isinstance

from canonical.launchpad.browser.librarian import ProxiedLibraryFileAlias
from canonical.launchpad.webapp.publisher import canonical_url
from lp.bugs.interfaces.bugchange import IBugChange
from lp.bugs.interfaces.bugtask import IBugTask
from lp.registry.interfaces.product import IProduct


class NoBugChangeFoundError(Exception):
    """Raised when a BugChange class can't be found for an object."""


def get_bug_change_class(obj, field_name):
    """Return a suitable IBugChange to describe obj and field_name."""

    if IBugTask.providedBy(obj):
        lookup = BUGTASK_CHANGE_LOOKUP
    else:
        lookup = BUG_CHANGE_LOOKUP

    try:
        return lookup[field_name]
    except KeyError:
        raise NoBugChangeFoundError(
            "Unable to find a suitable BugChange for field '%s' on object "
            "%s" % (field_name, obj))


def get_bug_changes(bug_delta):
    """Generate `IBugChange` objects describing an `IBugDelta`."""
    # The order of the field names in this list is important; this is
    # the order in which changes will appear both in the bug activity
    # log and in notification emails.
    bug_change_field_names = [
        'duplicateof', 'title', 'description', 'private', 'security_related',
        'tags', 'attachment',
        ]
    for field_name in bug_change_field_names:
        field_delta = getattr(bug_delta, field_name)
        if field_delta is not None:
            bug_change_class = get_bug_change_class(bug_delta.bug, field_name)
            yield bug_change_class(
                when=None, person=bug_delta.user, what_changed=field_name,
                old_value=field_delta['old'], new_value=field_delta['new'])

    if bug_delta.bugtask_deltas is not None:
        bugtask_deltas = bug_delta.bugtask_deltas
        # Use zope_isinstance, to ensure that this Just Works with
        # security-proxied objects.
        if not zope_isinstance(bugtask_deltas, (list, tuple)):
            bugtask_deltas = [bugtask_deltas]

        # The order here is important; see bug_change_field_names.
        bugtask_change_field_names = [
            'target', 'importance', 'status', 'milestone', 'bugwatch',
            'assignee',
            ]
        for bugtask_delta in bugtask_deltas:
            for field_name in bugtask_change_field_names:
                field_delta = getattr(bugtask_delta, field_name)
                if field_delta is not None:
                    bug_change_class = get_bug_change_class(
                        bugtask_delta.bugtask, field_name)
                    yield bug_change_class(
                        bug_task=bugtask_delta.bugtask,
                        when=None, person=bug_delta.user,
                        what_changed=field_name,
                        old_value=field_delta['old'],
                        new_value=field_delta['new'])


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


class AttributeChange(BugChangeBase):
    """A mixin class that provides basic functionality for `IBugChange`s."""

    def __init__(self, when, person, what_changed, old_value, new_value):
        super(AttributeChange, self).__init__(when, person)
        self.new_value = new_value
        self.old_value = old_value
        self.what_changed = what_changed

    def getBugActivity(self):
        """Return the BugActivity data for the textual change."""
        return {
            'newvalue': self.new_value,
            'oldvalue': self.old_value,
            'whatchanged': self.what_changed,
            }


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


class BugConvertedToQuestion(BugChangeBase):
    """A bug got converted into a question."""

    def __init__(self, when, person, question):
        super(BugConvertedToQuestion, self).__init__(when, person)
        self.question = question

    def getBugActivity(self):
        """See `IBugChange`."""
        return dict(
            whatchanged='converted to question',
            newvalue=str(self.question.id))

    def getBugNotification(self):
        """See `IBugChange`."""
        return {
            'text': (
                '** Converted to question:\n'
                '   %s' % canonical_url(self.question)),
            }


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
        lines = []
        if self.bug_task.bugwatch:
            lines.append(u"** Also affects: %s via" % (
                self.bug_task.bugtargetname))
            lines.append(u"   %s" % self.bug_task.bugwatch.url)
        else:
            lines.append(u"** Also affects: %s" % (
                self.bug_task.bugtargetname))
        lines.append(u"%13s: %s" % (
            u"Importance", self.bug_task.importance.title))
        if self.bug_task.assignee:
            assignee = self.bug_task.assignee
            lines.append(u"%13s: %s" % (
                u"Assignee", assignee.unique_displayname))
        lines.append(u"%13s: %s" % (
            u"Status", self.bug_task.status.title))
        return {
            'text': '\n'.join(lines),
            }


class SeriesNominated(BugChangeBase):
    """A user nominated the bug to be fixed in a series."""

    def __init__(self, when, person, series):
        super(SeriesNominated, self).__init__(when, person)
        self.series = series

    def getBugActivity(self):
        """See `IBugChange`."""
        return dict(
            whatchanged='nominated for series',
            newvalue=self.series.bugtargetname)

    def getBugNotification(self):
        """See `IBugChange`."""
        return None


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


class BranchLinkedToBug(BugChangeBase):
    """A branch got linked to the bug."""

    def __init__(self, when, person, branch, bug):
        super(BranchLinkedToBug, self).__init__(when, person)
        self.branch = branch
        self.bug = bug

    def getBugActivity(self):
        """See `IBugChange`."""
        if self.branch.private:
            return None
        return dict(
            whatchanged='branch linked',
            newvalue=self.branch.bzr_identity)

    def getBugNotification(self):
        """See `IBugChange`."""
        if self.branch.private or self.bug.is_complete:
            return None
        return {'text': '** Branch linked: %s' % self.branch.bzr_identity}


class BranchUnlinkedFromBug(BugChangeBase):
    """A branch got unlinked from the bug."""

    def __init__(self, when, person, branch, bug):
        super(BranchUnlinkedFromBug, self).__init__(when, person)
        self.branch = branch
        self.bug = bug

    def getBugActivity(self):
        """See `IBugChange`."""
        if self.branch.private:
            return None
        return dict(
            whatchanged='branch unlinked',
            oldvalue=self.branch.bzr_identity)

    def getBugNotification(self):
        """See `IBugChange`."""
        if self.branch.private or self.bug.is_complete:
            return None
        return {'text': '** Branch unlinked: %s' % self.branch.bzr_identity}


class BugDescriptionChange(AttributeChange):
    """Describes a change to a bug's description."""

    def getBugNotification(self):
        from canonical.launchpad.mailnotification import get_unified_diff
        description_diff = get_unified_diff(
            self.old_value, self.new_value, 72)
        notification_text = (
            u"** Description changed:\n\n%s" % description_diff)
        return {'text': notification_text}


class BugDuplicateChange(AttributeChange):
    """Describes a change to a bug's duplicate marker."""

    def getBugActivity(self):
        if self.old_value is not None and self.new_value is not None:
            return {
                'whatchanged': 'changed duplicate marker',
                'oldvalue': str(self.old_value.id),
                'newvalue': str(self.new_value.id),
                }
        elif self.old_value is None:
            return {
                'whatchanged': 'marked as duplicate',
                'newvalue': str(self.new_value.id),
                }
        elif self.new_value is None:
            return {
                'whatchanged': 'removed duplicate marker',
                'oldvalue': str(self.old_value.id),
                }
        else:
            raise AssertionError(
                "There is no change: both the old bug and new bug are None.")

    def getBugNotification(self):
        if self.old_value is not None and self.new_value is not None:
            if self.old_value.private:
                old_value_text = (
                    "** This bug is no longer a duplicate of private bug "
                    "%d" % self.old_value.id)
            else:
                old_value_text = (
                    "** This bug is no longer a duplicate of bug %d\n"
                    "   %s" % (self.old_value.id, self.old_value.title))
            if self.new_value.private:
                new_value_text = (
                    "** This bug has been marked a duplicate of private bug "
                    "%d" % self.new_value.id)
            else:
                new_value_text = (
                    "** This bug has been marked a duplicate of bug "
                    "%(bug_id)d\n   %(bug_title)s\n"
                    " * You can subscribe to bug %(bug_id)d by following "
                    "this link: %(subscribe_link)s" % {
                        'bug_id': self.new_value.id,
                        'bug_title': self.new_value.title,
                        'subscribe_link': canonical_url(
                            self.new_value.default_bugtask,
                            view_name='+subscribe'),
                        })

            text = "\n".join((old_value_text, new_value_text))

        elif self.old_value is None:
            if self.new_value.private:
                text = (
                    "** This bug has been marked a duplicate of private bug "
                    "%d" % self.new_value.id)
            else:
                text = (
                    "** This bug has been marked a duplicate of bug "
                    "%(bug_id)d\n   %(bug_title)s\n"
                    " * You can subscribe to bug %(bug_id)d by following "
                    "this link: %(subscribe_link)s" % {
                        'bug_id': self.new_value.id,
                        'bug_title': self.new_value.title,
                        'subscribe_link': canonical_url(
                            self.new_value.default_bugtask,
                            view_name='+subscribe'),
                        })

        elif self.new_value is None:
            if self.old_value.private:
                text = (
                    "** This bug is no longer a duplicate of private bug "
                    "%d" % self.old_value.id)
            else:
                text = (
                    "** This bug is no longer a duplicate of bug %d\n"
                    "   %s" % (self.old_value.id, self.old_value.title))

        else:
            raise AssertionError(
                "There is no change: both the old bug and new bug are None.")

        return {'text': text}


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
                (self.old_value, self.new_value)],
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


def download_url_of_bugattachment(attachment):
    """Return the URL of the ProxiedLibraryFileAlias for the attachment."""
    return ProxiedLibraryFileAlias(
        attachment.libraryfile, attachment).http_url


class BugAttachmentChange(AttributeChange):
    """Used to represent a change to an `IBug`'s attachments."""

    def getBugActivity(self):
        if self.old_value is None:
            what_changed = "attachment added"
            old_value = None
            new_value = "%s %s" % (
                self.new_value.title,
                download_url_of_bugattachment(self.new_value))
        else:
            what_changed = "attachment removed"
            attachment = self.new_value
            old_value = "%s %s" % (
                self.old_value.title,
                download_url_of_bugattachment(self.old_value))
            new_value = None

        return {
            'newvalue': new_value,
            'oldvalue': old_value,
            'whatchanged': what_changed,
            }

    def getBugNotification(self):
        if self.old_value is None:
            if self.new_value.is_patch:
                attachment_str = 'Patch'
            else:
                attachment_str = 'Attachment'
            message = '** %s added: "%s"\n   %s' % (
                attachment_str, self.new_value.title,
                download_url_of_bugattachment(self.new_value))
        else:
            if self.old_value.is_patch:
                attachment_str = 'Patch'
            else:
                attachment_str = 'Attachment'
            message = '** %s removed: "%s"\n   %s' % (
                attachment_str, self.old_value.title,
                download_url_of_bugattachment(self.old_value))

        return {'text': message}


class CveLinkedToBug(BugChangeBase):
    """Used to represent the linking of a CVE to a bug."""

    def __init__(self, when, person, cve):
        super(CveLinkedToBug, self).__init__(when, person)
        self.cve = cve

    def getBugActivity(self):
        """See `IBugChange`."""
        return dict(
            newvalue=self.cve.sequence,
            whatchanged='cve linked')

    def getBugNotification(self):
        """See `IBugChange`."""
        return {'text': "** CVE added: %s" % self.cve.url}


class CveUnlinkedFromBug(BugChangeBase):
    """Used to represent the unlinking of a CVE from a bug."""

    def __init__(self, when, person, cve):
        super(CveUnlinkedFromBug, self).__init__(when, person)
        self.cve = cve

    def getBugActivity(self):
        """See `IBugChange`."""
        return dict(
            oldvalue=self.cve.sequence,
            whatchanged='cve unlinked')

    def getBugNotification(self):
        """See `IBugChange`."""
        return {'text': "** CVE removed: %s" % self.cve.url}


class BugTaskAttributeChange(AttributeChange):
    """Used to represent a change in a BugTask's attributes.

    This is a base class. Implementations should define
    `display_attribute` and optionally override
    `display_activity_label` and/or `display_notification_label`.

    `display_attribute` is the name of an attribute on the value
    objects that, when fetched, is usable when recording activity and
    sending notifications.
    """

    def __init__(self, bug_task, when, person, what_changed, old_value,
                 new_value):
        super(BugTaskAttributeChange, self).__init__(
            when, person, what_changed, old_value, new_value)
        self.bug_task = bug_task

        if self.old_value is None:
            self.display_old_value = None
        else:
            self.display_old_value = getattr(
                self.old_value, self.display_attribute)

        if self.new_value is None:
            self.display_new_value = None
        else:
            self.display_new_value = getattr(
                self.new_value, self.display_attribute)

    @property
    def display_activity_label(self):
        """The label to use when recording activity.

        By default, it is the same as attribute that changed.
        """
        return self.what_changed

    @property
    def display_notification_label(self):
        """The label to use for notifications.

        By default, it is the same as the attribute that changed,
        capitalized.
        """
        return self.what_changed.capitalize()

    def getBugActivity(self):
        """Return the bug activity data for this change as a dict.

        The `whatchanged` value of the dict refers to the `BugTask`'s
        target so as to make it clear in which task the change was made.
        """
        return {
            'whatchanged': '%s: %s' % (
                self.bug_task.bugtargetname, self.display_activity_label),
            'oldvalue': self.display_old_value,
            'newvalue': self.display_new_value,
            }

    def getBugNotification(self):
        """Return the bug notification text for this change.

        The notification will refer to the `BugTask`'s target so as to
        make it clear in which task the change was made.
        """
        text = (
            u"** Changed in: %(bug_target_name)s\n"
            "%(label)13s: %(oldval)s => %(newval)s\n" % {
                'bug_target_name': self.bug_task.bugtargetname,
                'label': self.display_notification_label,
                'oldval': self.display_old_value,
                'newval': self.display_new_value,
            })

        return {'text': text.rstrip()}


class BugTaskImportanceChange(BugTaskAttributeChange):
    """Represents a change in BugTask.importance."""

    # Use `importance.title` in activity records and notifications.
    display_attribute = 'title'


class BugTaskStatusChange(BugTaskAttributeChange):
    """Represents a change in BugTask.status."""

    # Use `status.title` in activity records and notifications.
    display_attribute = 'title'


class BugTaskMilestoneChange(BugTaskAttributeChange):
    """Represents a change in BugTask.milestone."""

    # Use `milestone.name` in activity records and notifications.
    display_attribute = 'name'


class BugTaskBugWatchChange(BugTaskAttributeChange):
    """Represents a change in BugTask.bugwatch."""

    # Use the term "remote watch" as this is used in the UI.
    display_activity_label = 'remote watch'
    display_notification_label = 'Remote watch'

    # Use `bugwatch.title` in activity records and notifications.
    display_attribute = 'title'


class BugTaskAssigneeChange(AttributeChange):
    """Represents a change in BugTask.assignee."""

    def __init__(self, bug_task, when, person,
                 what_changed, old_value, new_value):
        super(BugTaskAssigneeChange, self).__init__(
            when, person, what_changed, old_value, new_value)
        self.bug_task = bug_task

    def getBugActivity(self):
        """See `IBugChange`."""
        def assignee_for_display(assignee):
            if assignee is None:
                return None
            else:
                return assignee.unique_displayname

        return {
            'whatchanged': '%s: assignee' % self.bug_task.bugtargetname,
            'oldvalue': assignee_for_display(self.old_value),
            'newvalue': assignee_for_display(self.new_value),
            }

    def getBugNotification(self):
        """See `IBugChange`."""
        def assignee_for_display(assignee):
            if assignee is None:
                return "(unassigned)"
            else:
                return assignee.unique_displayname

        return {
            'text': (
                u"** Changed in: %s\n"
                u"     Assignee: %s => %s" % (
                    self.bug_task.bugtargetname,
                    assignee_for_display(self.old_value),
                    assignee_for_display(self.new_value))),
            }


class BugTaskTargetChange(AttributeChange):
    """Used to represent a change in a BugTask's target."""

    def __init__(self, bug_task, when, person,
                 what_changed, old_value, new_value):
        super(BugTaskTargetChange, self).__init__(
            when, person, what_changed, old_value, new_value)
        self.bug_task = bug_task

    def getBugActivity(self):
        """See `IBugChange`."""
        return {
            'whatchanged': 'affects',
            'oldvalue': self.old_value.bugtargetname,
            'newvalue': self.new_value.bugtargetname,
            }

    def getBugNotification(self):
        """See `IBugChange`."""
        if IProduct.providedBy(self.old_value):
            template = u"** Project changed: %s => %s"
        else:
            template = u"** Package changed: %s => %s"
        text = template % (
            self.old_value.bugtargetname,
            self.new_value.bugtargetname)
        return {'text': text}


BUG_CHANGE_LOOKUP = {
    'description': BugDescriptionChange,
    'private': BugVisibilityChange,
    'security_related': BugSecurityChange,
    'tags': BugTagsChange,
    'title': BugTitleChange,
    'attachment': BugAttachmentChange,
    'duplicateof': BugDuplicateChange,
    }


BUGTASK_CHANGE_LOOKUP = {
    'importance': BugTaskImportanceChange,
    'status': BugTaskStatusChange,
    'target': BugTaskTargetChange,
    'milestone': BugTaskMilestoneChange,
    'bugwatch': BugTaskBugWatchChange,
    'assignee': BugTaskAssigneeChange,
    }
