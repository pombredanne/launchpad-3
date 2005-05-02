# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from zope.interface import implements, Interface
from zope.schema import Text, TextLine
from zope.app import zapi

from canonical.launchpad.interfaces import IMessagesView
from canonical.launchpad.database \
        import LibraryFileAlias, Message, MessageChunk
from canonical.launchpad.database import bugmessage

class MessagesView(object):
    implements(IMessagesView)
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def add(self, ob):
        return ob

    def nextURL(self):
        return '..'
