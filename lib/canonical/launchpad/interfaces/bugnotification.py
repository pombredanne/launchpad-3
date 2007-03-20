# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Bug notifications."""

__metaclass__ = type
__all__ = ['IBugNotification', 'IBugNotificationSet', 'INotificationRecipientSet']

from zope.interface import Attribute, Interface
from zope.schema import Bool, Datetime

from canonical.launchpad.fields import BugField
from canonical.launchpad.interfaces import IHasOwner


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


class INotificationRecipientSet(Interface):
    """Represents a set of email addresses and rationales.

    The pattern for using this are as follows: email addresses in an
    INotificationRecipientSet are being notified because of a specific
    event (for instance, because a bug changed). The rationales describe
    why that email addresses is included in the recipient list,
    detailing subscription types, membership in teams and/or other
    possible reasons.

    You are meant to implement an API that defines how emails and
    rationales are added to an INotificationRecipientSet; this is
    to be kept private between your INotificationRecipientSet
    implementation and the content class which defines the
    subscriptions..
    """

    def getEmails():
        """Returns all email addresses registered, sorted alphabetically."""

    def getReason(email):
        """Returns a reason tuple containing (text, header) for an address."""

    def update(recipient_set):
        """Updates this instance's reasons with reasons from another BNR."""



