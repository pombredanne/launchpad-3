# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad messages."""

__metaclass__ = type
__all__ = [
    'IMessageEntry',
    'MessageCollection',
    'MessageEntry'
    ]

from zope.component import adapts
from zope.schema import Datetime, Object, Text, TextLine

from canonical.lazr.interfaces import IEntry
from canonical.lazr.rest import Entry, Collection
from canonical.lp import decorates
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
    #distribution = Int(
    #        title=u'Distribution', required=False, readonly=True,
    #        )


class MessageEntry(Entry):
    """An entry."""
    adapts(IMessage)
    decorates(IMessageEntry)
    schema = IMessageEntry

    parent_collection_name = 'messages'

    def fragment(self):
        """The URL fragment for a message is the message ID."""
        return self.context.rfc822msgid

    @property
    def content(self):
        return self.context.text_contents


class MessageCollection(Collection):
    """A collection of messages."""

    def lookupEntry(self, id):
        """Find a message by ID."""
        message = self.context.get(id)
        if message is None:
            return None
        else:
            return message[0]

    def find(self):
        """Messages can't be listed directly."""
        return None
