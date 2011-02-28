# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Code for handling bug notification recipients in bug mail."""

__metaclass__ = type
__all__ = [
    'BugNotificationRecipients',
    ]

from zope.interface import implements

from canonical.launchpad.interfaces.launchpad import INotificationRecipientSet
from lp.services.mail.basemailer import RecipientReason
from lp.services.mail.notificationrecipientset import NotificationRecipientSet


class BugNotificationRecipientReason(RecipientReason):
    """A `RecipientReason` subsclass specifically for `BugNotification`s."""

    def _getTemplateValues(self):
        template_values = (
            super(BugNotificationRecipientReason, self)._getTemplateValues())
        if self.recipient != self.subscriber or self.subscriber.is_team:
            template_values['entity_is'] = (
                'You are a member of %s, which is' %
                self.subscriber.displayname)
            template_values['lc_entity_is'] = (
                'you are a member of %s, which is' %
                self.subscriber.displayname)
        return template_values

    @classmethod
    def makeRationale(cls, rationale, person, duplicate_bug=None):
        """See `RecipientReason.makeRationale`."""
        rationale = RecipientReason.makeRationale(rationale, person)
        if duplicate_bug is not None:
            rationale = "%s via Bug %s" % (rationale, duplicate_bug.id)

        return rationale

    @classmethod
    def _getReasonTemplate(cls, reason_string, duplicate_bug=None):
        """Return a reason template to pass to __init__()."""
        if duplicate_bug is not None:
            reason_suffix = " (via bug %s)." % duplicate_bug.id
        else:
            reason_suffix = "."

        reason_parts = {
            'prefix':
                "You received this bug notification because %(lc_entity_is)s",
            'reason': reason_string,
            'suffix': reason_suffix,
            }
        return "%(prefix)s %(reason)s%(suffix)s" % reason_parts

    @classmethod
    def forDupeSubscriber(cls, person, duplicate_bug):
        """Return a `BugNotificationRecipientReason` for a dupe subscriber.
        """
        header = cls.makeRationale(
            'Subscriber of Duplicate', person, duplicate_bug)

        reason = cls._getReasonTemplate(
            "a direct subscriber of a duplicate bug (via bug %s)" %
                duplicate_bug.id)
        return cls(person, person, header, reason)

    @classmethod
    def forDirectSubscriber(cls, person, duplicate_bug=None):
        """Return a `BugNotificationRecipientReason` for a direct subscriber.
        """
        header = cls.makeRationale("Subscriber", person, duplicate_bug)
        reason = cls._getReasonTemplate(
            "a direct subscriber of the bug", duplicate_bug)
        return cls(person, person, header, reason)

    @classmethod
    def forAssignee(cls, person, duplicate_bug=None):
        """Return a `BugNotificationRecipientReason` for a bug assignee."""
        header = cls.makeRationale("Assignee", person, duplicate_bug)
        reason = cls._getReasonTemplate("a bug assignee", duplicate_bug)
        return cls(person, person, header, reason)

    @classmethod
    def forBugSupervisor(cls, person, target, duplicate_bug=None):
        """Return a `BugNotificationRecipientReason` for a bug supervisor."""
        # All displaynames in these reasons should be changed to bugtargetname
        # (as part of bug 113262) once bugtargetname is finalized for packages
        # (bug 113258). Changing it before then would be excessively
        # disruptive.
        header = cls.makeRationale(
            "Bug Supervisor (%s)" % target.displayname, person, duplicate_bug)
        reason = cls._getReasonTemplate(
            "the bug supervisor for %s" % target.displayname, duplicate_bug)
        return cls(person, person, header, reason)

    @classmethod
    def forStructuralSubscriber(cls, person, target, duplicate_bug=None):
        """Return a recipient reason for a structural subscriber."""
        header = cls.makeRationale(
            "Subscriber (%s)" % target.displayname, person, duplicate_bug)
        reason = cls._getReasonTemplate(
            "subscribed to %s" % target.displayname, duplicate_bug)
        return cls(person, person, header, reason)

    @classmethod
    def forRegistrant(cls, person, target, duplicate_bug=None):
        """Return a recipient reason for a registrant."""
        header = cls.makeRationale(
            "Registrant (%s)" % target.displayname, person, duplicate_bug)
        reason = cls._getReasonTemplate(
            "the registrant for %s" % target.displayname, duplicate_bug)
        return cls(person, person, header, reason)


class BugNotificationRecipients(NotificationRecipientSet):
    """A set of emails and rationales notified for a bug change.

    Each email address registered in a BugNotificationRecipients is
    associated to a string and a header that explain why the address is
    being emailed. For instance, if the email address is that of a
    distribution bug supervisor for a bug, the string and header will make
    that fact clear.

    The string is meant to be rendered in the email footer. The header
    is meant to be used in an X-Launchpad-Message-Rationale header.

    The first rationale registered for an email address is the one
    which will be used, regardless of other rationales being added
    for it later. This gives us a predictable policy of preserving
    the first reason added to the registry; the callsite should
    ensure that the manipulation of the BugNotificationRecipients
    instance is done in preferential order.

    Instances of this class are meant to be returned by
    IBug.getBugNotificationRecipients().
    """
    implements(INotificationRecipientSet)

    def __init__(self, duplicateof=None):
        """Constructs a new BugNotificationRecipients instance.

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
        NotificationRecipientSet.__init__(self)
        self.duplicateof = duplicateof
        self.subscription_filters = []

    def _addReason(self, person, reason, header):
        """Adds a reason (text and header) for a person.

        It takes care of modifying the message when the person is notified
        via a duplicate.
        """
        if self.duplicateof is not None:
            reason = reason + " (via bug %s)" % self.duplicateof.id
            header = header + " via Bug %s" % self.duplicateof.id
        reason = "You received this bug notification because you %s." % reason
        self.add(person, reason, header)

    def addDupeSubscriber(self, person, duplicate_bug=None):
        """Registers a subscriber of a duplicate of this bug."""
        reason = "Subscriber of Duplicate"
        if person.isTeam():
            text = ("are a member of %s, which is a subscriber "
                    "of a duplicate bug" % person.displayname)
            reason += " @%s" % person.name
        else:
            text = "are a direct subscriber of a duplicate bug"
        if duplicate_bug is not None:
            text += " (%s)" % duplicate_bug.id
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

    def addStructuralSubscriber(self, person, target, filters=[]):
        """Registers a structural subscriber to this bug's target."""
        reason = "Subscriber (%s)" % target.displayname
        if person.isTeam():
            text = ("are a member of %s, which is subscribed to %s" %
                (person.displayname, target.displayname))
            reason += " @%s" % person.name
        else:
            text = "are subscribed to %s" % target.displayname
        self._addReason(person, text, reason)
        self.subscription_filters.extend(filters)

    def addRegistrant(self, person, upstream):
        """Registers an upstream product registrant for this bug."""
        reason = "Registrant (%s)" % upstream.displayname
        if person.isTeam():
            text = ("are a member of %s, which is the registrant for %s" %
                (person.displayname, upstream.displayname))
            reason += " @%s" % person.name
        else:
            text = "are the registrant for %s" % upstream.displayname
        self._addReason(person, text, reason)

    def update(self, recipient_set):
        """See `INotificationRecipientSet`."""
        super(BugNotificationRecipientSet, self).update(recipient_set)
        self.subscription_filters.extend(
            recipient_set.subscription_filters)
