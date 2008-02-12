# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for BugSubscription."""

__metaclass__ = type
__all__ = ['BugSubscriptionAddView']

from zope.component import getUtility

from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.interfaces import ILaunchBag
from canonical.launchpad.webapp import canonical_url


class BugSubscriptionAddView(SQLObjectAddView):
    """Browser view class for subscribing someone else to a bug."""

    def __init__(self, context, request):
        self._next_url = canonical_url(context)
        SQLObjectAddView.__init__(self, context, request)

    def create(self, person):
        subscription = self.context.bug.subscribe(
            person, getUtility(ILaunchBag).user)
        if person.isTeam():
            message = '%s team has been subscribed to this bug.'
        else:
            message = '%s has been subscribed to this bug.'
        self.request.response.addInfoNotification(message %
                                                  person.displayname)
        return subscription

    def nextURL(self):
        return self._next_url
