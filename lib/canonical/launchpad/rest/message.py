# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad messages."""

__metaclass__ = type
__all__ = [
    'IMessageEntry',
    'MessageEntry'
    ]

from zope.component import adapts
from zope.schema import Datetime, Object, Text, TextLine

from canonical.lazr import decorates
from canonical.lazr.interfaces import IEntry
from canonical.lazr.rest import Entry
from canonical.launchpad.interfaces import IMessage, IPerson


class IMessageEntry(IEntry):
    """The part of a message that we expose through the web service.
    """

    datecreated = Datetime(
            title=u'Date Created', required=True, readonly=True)
    subject = TextLine(title=u'Subject', required=True)
    owner = Object(schema=IPerson)
    parent = Object(schema=IMessage)
    content = Text(title=u'Message content', required=True)


class MessageEntry(Entry):
    """An entry."""
    adapts(IMessage)
    decorates(IMessageEntry)
    schema = IMessageEntry

    @property
    def content(self):
        return self.context.text_contents
