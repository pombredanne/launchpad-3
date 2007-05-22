# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for BugSubscription."""

__metaclass__ = type
__all__ = ['BugSubscriptionAddView']

from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.interfaces import IBug
from canonical.launchpad.webapp import canonical_url

class BugSubscriptionAddView(SQLObjectAddView):
    """Browser view class for subscribing someone else to a bug."""

    def __init__(self, context, request):
        self._next_url = canonical_url(context)
        SQLObjectAddView.__init__(self, context, request)

    def create(self, person):
        subscription = self.context.bug.subscribe(person)
        self.request.response.addInfoNotification(
            '\'%(name)s\' has been subscribed to this bug.',
            name=person.displayname)
        return subscription

    def nextURL(self):
        return self._next_url
