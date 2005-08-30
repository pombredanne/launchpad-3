# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'BountyView',
    'BountyLinkView',
    'BountyEditView',
    'BountyAddView',
    'BountySetView'
    ]

from zope.component import getUtility
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.form.browser.add import AddView
from zope.security.interfaces import Unauthorized
from zope.app.form.browser.editview import EditView

from canonical.launchpad.interfaces import (
    IBounty, IBountySet, ILaunchBag, IProduct, IProject, IDistribution)

from canonical.launchpad.webapp import canonical_url


class BountyView:

    __used_for__ = IBounty

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.subscription = None
        self.notices = []

        # figure out who the user is for this transaction
        self.user = getUtility(ILaunchBag).user

        # establish if a subscription form was posted
        newsub = request.form.get('subscribe', None)
        if newsub is not None and self.user and request.method == 'POST':
            if newsub == 'Subscribe':
                self.context.subscribe(self.user)
            elif newsub == 'Unsubscribe':
                self.context.unsubscribe(self.user)
            self.notices.append("Your subscription to this bounty has been "
                "updated.")

        # establish if this user has a subscription to the bounty
        if self.user is not None:
            for subscription in self.context.subscriptions:
                if subscription.person.id == self.user.id:
                    self.subscription = subscription
                    break


class BountyEditView(EditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))


class BountyLinkView(AddView):

    def __init__(self, context, request):
        self.request = request
        self.context = context
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        bounty = data['bounty']
        bountylink = self.context.ensureRelatedBounty(bounty)
        self._nextURL = canonical_url(self.context)
        return bounty

    def nextURL(self):
        return self._nextURL


class BountyAddView(AddView):

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
        # if the context is a product, or a project, or a distribution, then
        # we need to link to it
        if IProduct.providedBy(self.context) or \
           IProject.providedBy(self.context) or \
           IDistribution.providedBy(self.context):
            self.context.ensureRelatedBounty(bounty)
        notify(ObjectCreatedEvent(bounty))
        self._nextURL = canonical_url(bounty)
        return bounty

    def nextURL(self):
        return self._nextURL


class BountySetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.bounties = getUtility(IBountySet)

    def top_bounties(self):
        return self.bounties.top_bounties

