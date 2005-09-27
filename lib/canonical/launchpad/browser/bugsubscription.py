# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for BugSubscription."""

__metaclass__ = type
__all__ = ['BugSubscriptionAddView']

from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.interfaces import IBug
from canonical.launchpad.webapp import canonical_url

class BugSubscriptionAddView(SQLObjectAddView):

    def __init__(self, context, request):
        # Get the absolute URL of the IBugTask context before magic
        # IBug adaptation.
        self._next_url = canonical_url(context)
        context = IBug(context)
        self.context = context
        self.request = request
        SQLObjectAddView.__init__(self, context, request)

    def create(self, person):
        return self.context.subscribe(person)

    def nextURL(self):
        return self._next_url

