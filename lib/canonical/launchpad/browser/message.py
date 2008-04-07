# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
"""Message related view classes."""

__metaclass__ = type

__all__ = ['MessageAddView']

from zope.interface import providedBy, implements

from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
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


class BugMessageCanonicalUrlData:
    """Bug messages have a canonical_url within the primary bugtask."""
    implements(ICanonicalUrlData)
    rootsite = 'bugs'

    def __init__(self, bug, message):
        self.inside = bug.bugtasks[0]
        self.path = "comments/%d" % list(bug.messages).index(message)


def message_to_canonical_url_data(message):
    """This factory creates `ICanonicalUrlData` for BugMessage."""
    if message.bugs.count() == 0:
        # Will result in a ComponentLookupError
        return None
    return BugMessageCanonicalUrlData(message.bugs[0], message)
