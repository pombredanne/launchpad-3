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


class IAddMessage(Interface):
    """This schema is used to generate the add comment form"""
    title = TextLine(title=_("Subject"), required=True)
    content = Text(title=_("Body"), required=True)


class Dummy(object):
    """This object exists to satisfy the Z3 dependancy that the
    result of the addform's add method is adaptable to the schema
    that was supplied. This seems arbitrary and needs to be fixed
    in Z3, but for the time being work around"""
    implements(IAddMessage)
    title = None
    content = None


def BugMessageFactory(addview=None, title=None, content=None):
    """Create a BugMessage.

    Just like canonical.launchpad.database.message.BugMessageFactory, 
    except it returns a dummy value to keep Z3 happy.
    """
    bugmessage.BugMessageFactory(
            addview=addview, title=title, content=content
            )
    return Dummy()
