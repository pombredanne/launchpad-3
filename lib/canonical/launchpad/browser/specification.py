# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Specification views."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IProduct, IDistribution, ILaunchBag, ISpecification, ISpecificationSet)
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.addview import SQLObjectAddView

from canonical.launchpad.webapp import canonical_url

__all__ = [
    'SpecificationView',
    'SpecificationAddView',
    'SpecificationEditView',
    ]


class SpecificationView:

    __used_for__ = ISpecification

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.review = None
        self.notices = []

        # figure out who the user is for this transaction
        self.user = getUtility(ILaunchBag).user

        # establish if a subscription form was posted
        newsub = request.form.get('subscribe', None)
        if newsub is not None and self.user and request.method == 'POST':
            if newsub == 'Subscribe':
                self.context.subscribe(self.user)
                self.notices.append("You have subscribed to this spec.")
            elif newsub == 'Unsubscribe':
                self.context.unsubscribe(self.user)
                self.notices.append("You have unsubscribed from this spec.")

        # see if we are clearing a review
        review = request.form.get('review', None)
        if review == 'Review Complete' and self.user and \
           request.method == 'POST':
            self.context.unqueue(self.user)
            self.notices.append('Thank you for your review.')

        if self.user is not None:
            # establish if this user has a review queued on this spec
            for review in self.context.reviews:
                if review.reviewer.id == self.user.id:
                    self.review = review
                    msg = "Your review was requested by %s"
                    msg %= review.requestor.browsername
                    if review.queuemsg:
                        msg = msg + ': ' + review.queuemsg
                    self.notices.append(msg)
                    break

    @property
    def subscription(self):
        """establish if this user has a subscription"""
        if self.user is None:
            return None
        for subscription in self.context.subscriptions:
            if subscription.person.id == self.user.id:
                return subscription
        return None


class SpecificationAddView(SQLObjectAddView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        SQLObjectAddView.__init__(self, context, request)

    def create(self, name, title, specurl, summary, priority, status,
        owner, assignee=None, drafter=None, approver=None):
        """Create a new Specification."""
        #Inject the relevant product or distribution into the kw args.
        product = None
        distribution = None
        if IProduct.providedBy(self.context):
            product = self.context.id
        elif IDistribution.providedBy(self.context):
            distribution = self.context.id
        # clean up name
        name = name.strip().lower()
        spec = getUtility(ISpecificationSet).new(name, title, specurl,
            summary, priority, status, owner, product=product,
            distribution=distribution, assignee=assignee, drafter=drafter,
            approver=approver)
        self._nextURL = canonical_url(spec)
        return spec

    def add(self, content):
        """Skipping 'adding' this content to a container, because
        this is a placeless system."""
        return content

    def nextURL(self):
        return self._nextURL


class SpecificationEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))

