# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for BugSubscription."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.browser.addview import SQLObjectAddView

from canonical.launchpad.interfaces import IBugSubscription

from canonical.launchpad.webapp import canonical_url


__all__ = [
    'BugSubscriptionAddView',
    ]

class BugSubscriptionAddView(SQLObjectAddView):

    def create(self, person):
        return self.context.subscribe(person)

    def nextURL(self):
        return canonical_url(self.context)

