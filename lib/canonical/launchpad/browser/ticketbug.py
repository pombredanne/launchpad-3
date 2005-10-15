# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for TicketBug."""

__metaclass__ = type

from zope.component import getUtility
from zope.app.form.browser.add import AddView

from canonical.launchpad.interfaces import ITicketBug, IBugSet
from canonical.launchpad.webapp import canonical_url


__all__ = [
    'TicketBugAddView',
    'TicketBugRemoveView',
    ]

class TicketBugAddView(AddView):

    def create(self, bug):
        # make the support ticket creator a subscriber to the bug
        bug = getUtility(IBugSet).get(bug)
        return self.context.linkBug(bug)

    def add(self, content):
        """Skipping 'adding' this content to a container, because
        this is a placeless system."""
        return content

    def nextURL(self):
        return canonical_url(self.context)


class TicketBugRemoveView(AddView):
    """This is counter-intuitive. We are using the zope addform machinery to
    render the form, so the bug gets passed to the "create" method of this
    class, but we are actually REMOVING the bug.
    """

    def create(self, bug):
        # unsubscribe the ticket requestor from the bug
        bug = getUtility(IBugSet).get(bug)
        return self.context.unLinkBug(bug)

    def add(self, content):
        """Skipping 'adding' this content to a container, because
        this is a placeless system."""
        return content

    def nextURL(self):
        return canonical_url(self.context)


