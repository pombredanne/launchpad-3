# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Bug notifications."""

__metaclass__ = type
__all__ = [
    'IBugNotification',
    'IBugNotificationSet',
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
