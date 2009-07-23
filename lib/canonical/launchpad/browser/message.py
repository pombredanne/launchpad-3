# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Message related view classes."""

__metaclass__ = type

__all__ = ['MessageAddView']

from zope.interface import implements

from canonical.launchpad import _
from canonical.launchpad.interfaces.message import IIndexedMessage, IMessage
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
from canonical.launchpad.webapp.launchpadform import action, LaunchpadFormView


# XXX: salgado, 2008-10-16: This view is currently unused because it's only
# used by bounties and those are not exposed anywhere. It is also untested, so
# it's very likely it doesn't work -- I only touched it because I wanted to
# get rid of SQLObjectAddView and this was the last place using it.
class MessageAddView(LaunchpadFormView):
    """View class for adding an IMessage to an IBug."""

    schema = IMessage
    label = 'Add message or comment'
    field_names = ['subject', 'content']

    @action(_('Add'), name='add')
    def add_action(self, action, data):
        self.context.newMessage(
            owner=self.user, subject=data['subject'], content=data['content'])
        self.next_url = canonical_url(self.context)


class BugMessageCanonicalUrlData:
    """Bug messages have a canonical_url within the primary bugtask."""
    implements(ICanonicalUrlData)
    rootsite = 'bugs'

    def __init__(self, bug, message):
        self.inside = bug.bugtasks[0]
        self.path = "comments/%d" % list(bug.messages).index(message)


class IndexedBugMessageCanonicalUrlData:
    """An optimized bug message canonical_url implementation.

    This implementation relies on the message being decorated with
    its index and context.
    """
    implements(ICanonicalUrlData)
    rootsite = 'bugs'

    def __init__(self, message):
        self.inside = message.inside
        self.path = "comments/%d" % message.index


def message_to_canonical_url_data(message):
    """This factory creates `ICanonicalUrlData` for BugMessage."""
    if IIndexedMessage.providedBy(message):
        return IndexedBugMessageCanonicalUrlData(message)
    else:
        if message.bugs.count() == 0:
            # Will result in a ComponentLookupError
            return None
        return BugMessageCanonicalUrlData(message.bugs[0], message)
