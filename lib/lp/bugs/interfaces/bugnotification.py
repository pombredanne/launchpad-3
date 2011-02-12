# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Bug notifications."""

__metaclass__ = type
__all__ = [
    'IBugNotification',
    'IBugNotificationSet',
    'IBugNotificationRecipient',
    ]

from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Datetime,
    TextLine,
    )

from canonical.launchpad import _
from lp.registry.interfaces.role import IHasOwner
from lp.services.fields import BugField


class IBugNotification(IHasOwner):
    """A textual representation of bug changes."""

    id = Attribute('id')
    message = Attribute(
        "The message containing the text representation of the changes"
        " to the bug.")
    activity = Attribute(
        "The bug activity object corresponding to this notification.  Will "
        "be None for older notification objects, and will be None if the "
        "bugchange object that provides the data for the change returns None "
        "for getBugActivity.")
    bug = BugField(title=u"The bug this notification is for.",
                   required=True)
    is_comment = Bool(
        title=u"Comment", description=u"Is the message a comment?",
        required=True)
    date_emailed = Datetime(
        title=u"Date emailed",
        description=u"When was the notification sent? None, if it hasn't"
                     " been sent yet.",
        required=False)
    recipients = Attribute(
        "The people to which this notification should be sent.")


class IBugNotificationSet(Interface):
    """The set of bug notifications."""

    def getNotificationsToSend():
        """Returns the notifications pending to be sent."""

    def addNotification(self, bug, is_comment, message, recipients, activity):
        """Create a new `BugNotification`.

        Create a new `BugNotification` object and the corresponding
        `BugNotificationRecipient` objects.
        """


class IBugNotificationRecipient(Interface):
    """A recipient of a bug notification."""

    bug_notification = Attribute(
        "The bug notification this recipient should receive.")
    person = Attribute(
        "The person to send the bug notification to.")
    reason_header = TextLine(
        title=_('Reason header'),
        description=_("The value for the "
                      "`X-Launchpad-Message-Rationale` header."))
    reason_body = TextLine(
        title=_('Reason body'),
        description=_("The reason for this notification."))
