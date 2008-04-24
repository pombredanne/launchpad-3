# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'MessageHeldEvent',
    ]


from zope.interface import implements

from canonical.launchpad.event.sqlobjectevent import SQLObjectCreatedEvent
from canonical.launchpad.event.interfaces import IMessageHeldEvent


class MessageHeldEvent(SQLObjectCreatedEvent):
    """See `IMessageHeldEvent`."""

    implements(IMessageHeldEvent)

    def __init__(self, mailing_list, message):
        """Create a message held event.

        :param mailing_list: The IMailingList that the message is held for.
        :param message: The IMessageApproval object representing the held
            message.
        """
        super(MessageHeldEvent, self).__init__(message)
        self.mailing_list = mailing_list
        self.message_id = message.message_id
