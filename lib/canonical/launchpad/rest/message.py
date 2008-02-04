# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad messages."""

__metaclass__ = type
__all__ = [
    'IMessageEntry',
    ]

from zope.schema import Datetime, Object, Text, TextLine

from canonical.lazr.interfaces import IEntry
from canonical.lazr.rest import Entry
from canonical.launchpad.interfaces import IMessage, IPerson


class IMessageEntry(IEntry):
    """The part of a message that we expose through the web service.
    """

    datecreated = Datetime(
            title=_(u'Date Created'), required=True, readonly=True)
    subject = TextLine(title=_(u'Subject'), required=True)
    owner = Object(schema=IPerson)
    parent = Object(schema=IMessage)
    content = Text(title=_(u'Message content'), required=True)
    #distribution = Int(
    #        title=_(u'Distribution'), required=False, readonly=True,
    #        )

class MessageEntry(Entry):
    """An entry."""

    @property
    def content(self):
        return self.context.text_chunks