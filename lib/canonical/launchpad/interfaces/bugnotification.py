# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Bug notifications."""

__metaclass__ = type
__all__ = [
    'IBugNotification',
    'IBugNotificationSet',
    'BugNotificationRecipients',
    ]

from zope.interface import Attribute, Interface, implements
from zope.schema import Bool, Datetime

from canonical.launchpad.fields import BugField
from canonical.launchpad.interfaces.launchpad import (
    IHasOwner, INotificationRecipientSet)


class IBugNotification(IHasOwner):
    """A textual representation of bug changes."""

    id = Attribute('id')
    message = Attribute(
        "The message containing the text representation of the changes"
        " to the bug.")
    bug = BugField(title=u"The bug this notification is for.", required=True)
    is_comment = Bool(
        title=u"Comment", description=u"Is the message a comment?",
        required=True)
    date_emailed = Datetime(
        title=u"Date emailed",
        description=u"When was the notification sent? None, if it hasn't"
                     " been sent yet.",
        required=False)


class IBugNotificationSet(Interface):
    """The set of bug notifications."""

    def getNotificationsToSend():
        """Returns the notifications pending to be sent."""


class BugNotificationRecipients:
    """Or BNR. A set of emails and rationales notified for a bug change.

    Each email address registered in a BNR instance is associated to a
    string and a header that explain why the address is being emailed.
    For instance, if the email address is that of a distribution bug
    contact for a bug, the string and header will make that fact clear.

    The string is meant to be rendered in the email footer. The header
    is meant to be used in an X-Launchpad-Message-Rationale header.

    The first rationale registered for an email address is the one
    which will be used, regardless of other rationales being added
    for it later. This gives us a predictable policy of preserving
    the first reason added to the registry; the callsite should
    ensure that the manipulation of the BNR instance is done in
    preferential order.

    Instances of this class are meant to be returned by
    IBug.getBugNotificationRecipients().
    """
    implements(INotificationRecipientSet)
    def __init__(self, duplicateof=None):
        """Constructs a new BNR instance.

        If this bug is a duplicate, duplicateof should be used to
        specify which bug ID it is a duplicate of.

        Note that there are two duplicate situations that are
        important:
          - One is when this bug is a duplicate of another bug:
            the subscribers to the main bug get notified of our
            changes.
          - Another is when the bug we are changing has
            duplicates; in that case, direct subscribers of
            duplicate bugs get notified of our changes.
        These two situations are catered respectively by the
        duplicateof parameter above and the addDupeSubscriber method.
        Don't confuse them!
        """
        self._reasons = {}
        self.duplicateof = duplicateof

    def _addReason(self, person, reason, header):
        # Adds a reason (text and header) to the local dict of reasons,
        # keyed on email address. The reason we use email address as the
        # key is that we want to ensure we never send emails twice to
        # the same person; this can happen when a person is subscribed
        # to a bug both directly and via a team subscription.
        if self.duplicateof is not None:
            reason = reason + " (via bug %s)" % self.duplicateof.id
            header = header + " via Bug %s" % self.duplicateof.id
        reason = "You received this bug notification because you %s." % reason
        # Inline the import to avoid circularity. I hate helpers.py
        from canonical.launchpad.helpers import contactEmailAddresses
        for email in contactEmailAddresses(person):
            if email not in self._reasons:
                # This implements the first-rationale policy presented
                # in the class docstring.
                self._reasons[email] = (reason, header)

    def update(self, recipients):
        """See INotificationRecipientSet"""
        for email in recipients.getEmails():
            if email not in self._reasons:
                # For the same reason as in _addReason, we don't clobber
                # existing _reasons.
                self._reasons[email] = recipients.getReason(email)

    def getReason(self, email):
        """See INotificationRecipientSet"""
        return self._reasons[email]

    def getEmails(self):
        """See INotificationRecipientSet"""
        return sorted(self._reasons.keys())

    def addDupeSubscriber(self, person):
        """Registers a subscriber of a duplicate of this bug."""
        reason = "Subscriber of Duplicate"
        if person.isTeam():
            text = ("are a member of %s, which is a subscriber "
                    "of a duplicate bug" % person.displayname)
            reason += " @%s" % person.name
        else:
            text = "are a direct subscriber of a duplicate bug"
        self._addReason(person, text, reason)

    def addDirectSubscriber(self, person):
        """Registers a direct subscriber of this bug."""
        reason = "Subscriber"
        if person.isTeam():
            text = ("are a member of %s, which is a direct subscriber"
                    % person.displayname)
            reason += " @%s" % person.name
        else:
            text = "are a direct subscriber of the bug"
        self._addReason(person, text, reason)

    def addAssignee(self, person):
        """Registers an assignee of a bugtask of this bug."""
        reason = "Assignee"
        if person.isTeam():
            text = ("are a member of %s, which is a bug assignee"
                    % person.displayname)
            reason += " @%s" % person.name
        else:
            text = "are a bug assignee"
        self._addReason(person, text, reason)

    def addDistroBugContact(self, person, distro):
        """Registers a distribution bug contact for this bug."""
        reason = "Bug Contact (%s)" % distro.displayname
        if person.isTeam():
            text = ("are a member of %s, which is the bug contact for %s" %
                (person.displayname, distro.displayname))
            reason += " @%s" % person.name
        else:
            text = "are the bug contact for %s" % distro.displayname
        self._addReason(person, text, reason)

    def addPackageBugContact(self, person, package):
        """Registers a package bug contact for this bug."""
        reason = "Bug Contact (%s)" % package.displayname
        if person.isTeam():
            text = ("are a member of %s, which is a bug contact for %s" %
                (person.displayname, package.displayname))
            reason += " @%s" % person.name
        else:
            text = "are a bug contact for %s" % package.displayname
        self._addReason(person, text, reason)

    def addUpstreamBugContact(self, person, upstream):
        """Registers an upstream bug contact for this bug."""
        reason = "Bug Contact (%s)" % upstream.displayname
        if person.isTeam():
            text = ("are a member of %s, which is the bug contact for %s" %
                (person.displayname, upstream.displayname))
            reason += " @%s" % person.name
        else:
            text = "are the bug contact for %s" % upstream.displayname
        self._addReason(person, text, reason)

    def addUpstreamRegistrant(self, person, upstream):
        """Registers an upstream product registrant for this bug."""
        reason = "Registrant (%s)" % upstream.displayname
        if person.isTeam():
            text = ("are a member of %s, which is the registrant for %s" %
                (person.displayname, upstream.displayname))
            reason += " @%s" % person.name
        else:
            text = "are the registrant for %s" % upstream.displayname
        self._addReason(person, text, reason)



