# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
"""Message related view classes."""

__metaclass__ = type

__all__ = ['MessageAddView']

from zope.event import notify
from zope.interface import providedBy

from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.event import SQLObjectModifiedEvent
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.snapshot import Snapshot


class MessageAddView(SQLObjectAddView):
    """View class for adding an IMessage to an IMessageTarget."""

    def __init__(self, context, request):
        self._nextURL = '.'
        SQLObjectAddView.__init__(self, context, request)

    def create(self, *args, **kw):
        subject = kw.get('subject')
        content = kw.get('content')
        owner = kw.get('owner')
        unmodified_context = Snapshot(
            self.context, providing=providedBy(self.context))
        msg = self.context.newMessage(owner=owner,
            subject=subject, content=content)
        self._nextURL = canonical_url(self.context)

        return msg

    def add(self, ob):
        return ob

    def nextURL(self):
        return self._nextURL


