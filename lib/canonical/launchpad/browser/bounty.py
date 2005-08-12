# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['BountyView', 'BountySetAddView']

from zope.component import getUtility
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.form.browser.add import AddView
from zope.security.interfaces import Unauthorized

from canonical.launchpad.interfaces import IBounty, IBountySet, ILaunchBag
from canonical.lp.dbschema import BountySubscription

class BountySubscriberPortletMixin:

    def getWatches(self):
        return [s for s in self.context.subscriptions
                if s.subscription == BountySubscription.WATCH]

    def getCCs(self):
        return [s for s in self.context.subscriptions
                if s.subscription == BountySubscription.CC]

    def getIgnores(self):
        return [s for s in self.context.subscriptions
                if s.subscription == BountySubscription.IGNORE]


class BountyView(BountySubscriberPortletMixin):

    __used_for__ = IBounty

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.subscription = None
        self.notices = []

        # figure out who the user is for this transaction
        self.user = getUtility(ILaunchBag).user

        # establish if a subscription form was posted
        formsub = request.form.get('Subscribe', None)
        if formsub is not None:
            newsub = request.form.get('subscription', None)
            if newsub == 'watch':
                self.context.subscribe(self.user, BountySubscription.WATCH)
            elif newsub == 'email':
                self.context.subscribe(self.user, BountySubscription.CC)
            elif newsub == 'none':
                self.context.unsubscribe(self.user)
            self.notices.append("Your subscription to this bounty has been "
                "updated.")

        # establish if this user has a subscription to the bounty
        if self.user is not None:
            for subscription in self.context.subscriptions:
                if subscription.person.id == self.user.id:
                    self.subscription = subscription.subscription
                    break

    def subscriptionTypeIsCC(self):
        return self.subscription == BountySubscription.CC

    def subscriptionTypeIsWatch(self):
        return self.subscription == BountySubscription.WATCH


class BountySetAddView(AddView):

    __used_for__ = IBountySet

    def __init__(self, context, request):
        self.request = request
        self.context = context
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # add the owner information for the bounty
        owner = getUtility(ILaunchBag).user
        if not owner:
            raise Unauthorized(
                "Must have an authenticated user in order to create a bounty")
        # XXX Mark Shuttleworth need the fancy-person selector to select a
        # reviewer
        reviewer = owner
        bounty = getUtility(IBountySet).new(
            name=data['name'],
            title=data['title'],
            summary=data['summary'],
            description=data['description'],
            usdvalue=data['usdvalue'],
            owner=owner,
            reviewer=reviewer)
        notify(ObjectCreatedEvent(bounty))
        self._nextURL = data['name']
        return bounty

    def nextURL(self):
        return self._nextURL
