# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'BountySetNavigation',
    'BountiesAppMenu',
    'BountyContextMenu',
    'BountyView',
    'BountyLinkView',
    'BountyEditView',
    'BountyAddView',
    'BountySetView'
    ]

from zope.component import getUtility
from zope.event import notify
from zope.lifecycleevent import ObjectCreatedEvent
from zope.app.form.browser.add import AddView
from zope.security.interfaces import Unauthorized
from zope.app.form.browser.editview import EditView

from canonical.launchpad.interfaces import (
    IBounty, IBountySet, ILaunchBag, IProduct, IProject, IDistribution)

from canonical.launchpad.webapp import (
    canonical_url, LaunchpadView, ApplicationMenu, ContextMenu, Link,
    enabled_with_permission, GetitemNavigation)


class BountySetNavigation(GetitemNavigation):

    usedfor = IBountySet


class BountiesAppMenu(ApplicationMenu):
    usedfor = IBountySet
    facet = 'bounties'
    links = ['new']

    def new(self):
        text = "Register a bounty"
        return Link('+new', text, icon="add")


class BountyContextMenu(ContextMenu):
    usedfor = IBounty
    links = ['edit', 'subscription', 'administer']

    def edit(self):
        text = 'Edit bounty'
        return Link('+edit', text, icon='edit')

    def subscription(self):
        user = getUtility(ILaunchBag).user
        if (user is not None and
            get_subscription_for_person(user, self.context) is not None):
            text = 'Unsubscribe from Bounty'
            icon = 'remove'
        elif user is None:
            text = 'Subscribe/Unsubscribe'
            icon = 'edit'
        else:
            text = 'Subscribe to Bounty'
            icon = 'add'
        return Link('+subscribe', text, icon=icon)

    @enabled_with_permission('launchpad.Admin')
    def administer(self):
        text = 'Administer'
        return Link('+admin', text, icon='edit')


def get_subscription_for_person(person, bounty):
    """Return the subscription the person has on the bounty, or None if there
    is not such subscription.
    """
    # XXX: SteveAlexander 2005-09-23:
    # Refactor to method on IBounty.
    for subscription in bounty.subscriptions:
        if subscription.person.id == person.id:
            return subscription
    return None


class BountyView(LaunchpadView):
    """View class used for bounty pages."""

    __used_for__ = IBounty

    def initialize(self):
        self.notices = []
        # establish if a subscription form was posted
        newsub = self.request.form.get('subscribe', None)
        if newsub is not None and self.user and self.request.method == 'POST':
            if newsub == 'Subscribe':
                self.context.subscribe(self.user)
            elif newsub == 'Unsubscribe':
                self.context.unsubscribe(self.user)
            self.notices.append(
                "Your subscription to this bounty has been updated.")

    @property
    def subscription(self):
        """establish if this user has a subscription"""
        if self.user is None:
            return None
        return get_subscription_for_person(self.user, self.context)


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
        # XXX Mark Shuttleworth 2004-11-09:
        # Need the fancy-person selector to select a reviewer.
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


class BountySetView(LaunchpadView):

    def initialize(self):
        self.bounties = getUtility(IBountySet)

    def top_bounties(self):
        return self.bounties.top_bounties

