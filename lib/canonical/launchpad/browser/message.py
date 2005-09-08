# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'MessagesView',
    'MessageAddView',
    ]

from zope.interface import implements
from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IMessagesView, ILaunchBag, ITicket)

from canonical.database.constants import UTC_NOW
from canonical.lp.dbschema import TicketStatus

from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.webapp import canonical_url

class MessagesView(object):
    implements(IMessagesView)
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def add(self, ob):
        return ob

    def nextURL(self):
        return '..'


class MessageAddView(SQLObjectAddView):
    """Adds a Message to the underlying context. This is used to add a
    message to a Ticket, or a Bug, and could be used for other types of
    object in Launchpad that have a series of comments or messages 
    associated with them.
    """

    def __init__(self, context, request):
        self._nextURL = '.'
        SQLObjectAddView.__init__(self, context, request)

    def create(self, *args, **kw):
        subject = kw.get('subject')
        content = kw.get('content')
        owner = kw.get('owner')
        msg = self.context.newMessage(owner=owner,
            subject=subject, content=content)
        if ITicket.providedBy(self.context):
            resolved = kw.get('resolved', None)
            if resolved is not None:
                self.context.mark_resolved(owner)
            if owner.id != self.context.owner.id and \
               self.context.status == TicketStatus.NEW:
                self.context.accept()
        self._nextURL = canonical_url(self.context)

    def add(self, ob):
        return ob

    def nextURL(self):
        return self._nextURL


